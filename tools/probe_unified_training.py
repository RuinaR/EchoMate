"""Bounded synthetic Unified/PEFT CPU or tiny CUDA NF4 compatibility probe.

No 12B weights, production profiles, datasets or operating adapters are read.
One GPU model at a time; checkpoint/resume proves APIs, never persona quality.
"""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import time
from unittest.mock import patch


def run(output,gpu=False,frozen_bf16=False,last_layers=None):
    if last_layers is not None and (last_layers!=1 or not gpu or not frozen_bf16):raise ValueError("Suffix probe requires tiny NF4 BF16")
    root=Path(output).resolve();repo=Path(__file__).resolve().parents[1]
    if not root.is_relative_to(repo/'local_data'):raise ValueError('Private output required')
    root.mkdir(parents=True,exist_ok=False)
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    if not gpu:os.environ['CUDA_VISIBLE_DEVICES']=''
    from echomate_bot.loader_memory import memory_snapshot,MemoryRecorder,release_idle_cuda
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.instance import InstanceLease
    health=check_resources() if gpu else None;model_memory_budget(128*1024**2)
    if gpu and health['free_vram_mib']<2048:raise RuntimeError('Tiny probe headroom')
    import torch
    from transformers import Gemma4UnifiedTextConfig,Gemma4UnifiedVisionConfig,Gemma4UnifiedAudioConfig,Gemma4UnifiedConfig,Gemma4UnifiedForConditionalGeneration,BitsAndBytesConfig
    from peft import LoraConfig,get_peft_model,PeftModel,prepare_model_for_kbit_training
    torch.set_num_threads(1);torch.manual_seed(20261024)
    started=time.monotonic();lease=InstanceLease() if gpu else None;model=None;optimizer=None;refs=None;expected=None
    from importlib.metadata import version
    report=dict(device='cuda' if gpu else 'cpu',before=memory_snapshot(),health=health,stages=[],seed=20261024,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),frozen_bf16=frozen_bf16,last_layers=last_layers,
        versions={n:version(n) for n in ('torch','transformers','peft','bitsandbytes')})
    def stage(name):
        row=dict(name=name,seconds=time.monotonic()-started,**memory_snapshot())
        if gpu:
            row.update(health=check_resources(),allocated=torch.cuda.memory_allocated(),reserved=torch.cuda.memory_reserved())
            if row['allocated']>512*1024**2:raise RuntimeError('Tiny model exceeded sealed 512MiB bound')
        report['stages'].append(row)
    def fresh():
        opts=dict(local_files_only=True,trust_remote_code=False,attn_implementation='eager')
        if gpu:opts.update(device_map={'':0},dtype=torch.bfloat16,quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16))
        base=Gemma4UnifiedForConditionalGeneration.from_pretrained(root/'base',**opts)
        if gpu:
            if frozen_bf16:
                from qlora_recipe import prepare_frozen_bf16
                base=prepare_frozen_bf16(base)
            else:base=prepare_model_for_kbit_training(base,gradient_checkpointing_kwargs={'use_reentrant':False})
        return base
    try:
        text=Gemma4UnifiedTextConfig(vocab_size=64,hidden_size=64,intermediate_size=128,num_hidden_layers=2,
            num_attention_heads=4,num_key_value_heads=2,head_dim=16,global_head_dim=16,
            layer_types=['sliding_attention','full_attention'],max_position_embeddings=64,sliding_window=16,use_cache=False)
        config=Gemma4UnifiedConfig(text_config=text,vision_config=Gemma4UnifiedVisionConfig(patch_size=2,pooling_kernel_size=1,mm_embed_dim=64,mm_posemb_size=8),audio_config=Gemma4UnifiedAudioConfig(audio_embed_dim=8))
        base=Gemma4UnifiedForConditionalGeneration(config).cpu();base.save_pretrained(root/'base',safe_serialization=True);del base;gc.collect()
        with MemoryRecorder(interval=.2) as recorder:
            model=fresh();stage('prepared')
            targets=r'.*language_model\.layers\.'+('1' if last_layers else r'\d+')+r'\.self_attn\.(q_proj|v_proj)'
            model=get_peft_model(model,LoraConfig(r=2,lora_alpha=4,lora_dropout=0,target_modules=targets,task_type='CAUSAL_LM'))
            if last_layers:
                from qlora_recipe import prepare_suffix_inputs
                prepare_suffix_inputs(model,1)
                def prefix_observed(module,args,result):
                    report['prefix_requires_grad']=bool(result.requires_grad)
                    assert not result.requires_grad
                hook=model.get_base_model().model.language_model.layers[0].register_forward_hook(prefix_observed)
            trained=[(n,p) for n,p in model.named_parameters() if p.requires_grad]
            assert trained and all('language_model.layers.' in n and 'lora_' in n for n,p in trained)
            refs=[(p,p.detach().clone()) for n,p in model.named_parameters() if not p.requires_grad]
            report['embedding_dtype']=str(model.get_input_embeddings().weight.dtype)
            report['tied_head']=model.get_input_embeddings().weight is model.get_output_embeddings().weight
            report['trainable']=sum(p.numel() for n,p in trained);report['adapter_targets']=sorted({n.split('.lora_')[0] for n,p in trained})
            ids=torch.tensor([[2,4,7,9,12,15,19,1]],device='cuda' if gpu else 'cpu')
            optimizer=torch.optim.AdamW([p for n,p in trained],lr=.001)
            model.train()
            from qlora_recipe import supervised_loss
            labels=ids.clone();labels[:,:4]=-100
            loss=supervised_loss(model,ids,labels) if frozen_bf16 else model(input_ids=ids,labels=ids).loss
            assert torch.isfinite(loss);loss.backward()
            if last_layers:hook.remove()
            assert any(p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().sum()>0 for n,p in trained)
            optimizer.step();optimizer.zero_grad();stage('step1')
            assert all(torch.equal(p.detach(),old) for p,old in refs)
            model.eval()
            with torch.no_grad():expected=model(input_ids=ids).logits.detach().cpu()
            # Cooperative stop at the optimizer boundary, then persist own state.
            model.save_pretrained(root/'checkpoint',safe_serialization=True)
            torch.save(optimizer.state_dict(),root/'optimizer.pt')
            report.update(loss=float(loss.detach()),cooperative_stop_step=1,base_tensors_unchanged=True)
            model=None;optimizer=None;refs=None;trained=None;loss=None;gc.collect()
            if gpu:release_idle_cuda(torch)
            stage('unloaded_for_resume')
            model=PeftModel.from_pretrained(fresh(),root/'checkpoint',is_trainable=True,local_files_only=True).eval()
            if last_layers:prepare_suffix_inputs(model,1)
            with torch.no_grad():actual=model(input_ids=ids).logits.detach().cpu()
            assert torch.allclose(expected,actual,atol=1e-5,rtol=1e-4)
            optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=.001)
            optimizer.load_state_dict(torch.load(root/'optimizer.pt',map_location='cpu',weights_only=True))
            model.train();loss=supervised_loss(model,ids,labels) if frozen_bf16 else model(input_ids=ids,labels=ids).loss
            loss.backward();optimizer.step();optimizer.zero_grad()
            assert all(int(s['step'])==2 for s in optimizer.state.values())
            stage('resumed_step2');report.update(status='TINY_API_PASS_NOT_12B_QUALITY',roundtrip=True,optimizer_resume_step=2)
        report['memory']=recorder.report()
    except BaseException as exc:
        report.update(status='STOPPED',error=type(exc).__name__);raise
    finally:
        model=None;optimizer=None;refs=None;expected=None;gc.collect()
        if gpu:release_idle_cuda(torch)
        if lease:lease.close()
        report.update(after=memory_snapshot(),elapsed=time.monotonic()-started)
        (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('memory','stages')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--gpu',action='store_true');p.add_argument('--frozen-bf16',action='store_true');p.add_argument('--last-layers',type=int,choices=[1]);a=p.parse_args()
    import faulthandler
    faulthandler.dump_traceback_later(180,exit=True)
    with patch('socket.socket.connect',side_effect=AssertionError('No network')),patch('socket.getaddrinfo',side_effect=AssertionError('No network')):
        run(a.output,a.gpu,a.frozen_bf16,a.last_layers)
