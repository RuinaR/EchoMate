"""Isolated tiny Unified DPO gradient and exact checkpoint replay proof.

No dataset download, real Discord, operating model or adapter promotion.
CPU is the default; explicit CUDA mode uses NF4 and the shared instance lease.
"""
import argparse
import gc
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
from unittest.mock import patch


def run(output,*,cuda=False):
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CUBLAS_WORKSPACE_CONFIG=':4096:8')
    import torch
    from transformers import Gemma4UnifiedTextConfig,Gemma4UnifiedForCausalLM,BitsAndBytesConfig
    from peft import get_peft_model,LoraConfig,PeftModel
    from pilot_state import private_path,cosine,save,restore
    from preference_learning import completion_logps,dpo_loss,sequential_pair_backward
    from qlora_recipe import prepare_frozen_bf16,training_checkpoint_mode
    from echomate_bot.instance import InstanceLease
    from echomate_bot.loader_memory import memory_snapshot,release_idle_cuda
    from echomate_bot.processes import check_resources
    out=private_path(output)
    if out.exists():raise FileExistsError('Fresh private proof only')
    out.mkdir(parents=True);torch.set_num_threads(1);torch.manual_seed(58)
    lease=None
    if cuda:
        health=check_resources()
        if health['free_vram_mib']<4096:raise ValueError('Tiny CUDA proof needs 4GiB free')
        lease=InstanceLease()
    device='cuda' if cuda else 'cpu';model=None;base=None;optimizer=None;scheduler=None
    report=dict(status='NOT_STARTED',cuda=cuda,real_discord=False,versions={n:version(n) for n in ('torch','transformers','peft','bitsandbytes')},before=memory_snapshot(),quantization=dict(kind='nf4',double_quant=True,compute_dtype='bfloat16') if cuda else None)
    def guard():
        if cuda:
            h=check_resources();m=memory_snapshot()
            if h['free_vram_mib']<2048 or m['ram_available']<3*1024**3 or m['commit_available']<2*1024**3:raise ValueError('Tiny DPO stage reserve')
    try:
        cfg=Gemma4UnifiedTextConfig(vocab_size=32,hidden_size=64,intermediate_size=128,num_hidden_layers=2,num_attention_heads=2,num_key_value_heads=1,head_dim=32,global_head_dim=32,layer_types=['sliding_attention','full_attention'],max_position_embeddings=128,use_cache=False)
        base=Gemma4UnifiedForCausalLM(cfg).to(torch.bfloat16)
        if cuda:
            base.save_pretrained(out/'tiny-base')
            base=None;gc.collect()
            base=Gemma4UnifiedForCausalLM.from_pretrained(out/'tiny-base',dtype=torch.bfloat16,device_map={'':'cuda'},local_files_only=True,quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True))
        if cuda:base=prepare_frozen_bf16(base)
        else:
            base.requires_grad_(False)
            base.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
        model=get_peft_model(base,LoraConfig(r=4,lora_alpha=8,lora_dropout=.05,target_modules=r'model\.layers\.\d+\.self_attn\.(q_proj|v_proj)',task_type='CAUSAL_LM'))
        training_checkpoint_mode(model)
        chosen=(torch.arange(24,device=device).remainder(25).add(2).unsqueeze(0),None)
        rejected=(torch.arange(28,device=device).flip(0).remainder(25).add(2).unsqueeze(0),None)
        def masked(example):
            ids=example[0];labels=ids.clone();labels[:,:-8]=-100;return ids,labels
        chosen=masked(chosen);rejected=masked(rejected)
        model.eval()
        with torch.no_grad():reference=tuple(float(completion_logps(model,*e)) for e in (chosen,rejected))
        model.train();rng=torch.get_rng_state();cuda_rng=torch.cuda.get_rng_state_all() if cuda else []
        objective=dpo_loss(completion_logps(model,*chosen),completion_logps(model,*rejected),*reference);objective.backward()
        expected=[p.grad.detach().cpu().clone() for p in model.parameters() if p.requires_grad];model.zero_grad(set_to_none=True)
        torch.set_rng_state(rng)
        if cuda:torch.cuda.set_rng_state_all(cuda_rng)
        result=sequential_pair_backward(model,chosen,rejected,reference,observe=lambda phase:guard())
        actual=[p.grad.detach().cpu() for p in model.parameters() if p.requires_grad]
        delta=max(float((a-b).abs().max()) for a,b in zip(actual,expected))
        for a,b in zip(actual,expected):torch.testing.assert_close(a,b,atol=1e-6,rtol=1e-5)
        report.update(reference=reference,gradient_max_abs_delta=delta,loss_absolute_delta=abs(result['loss']-float(objective.detach())),single_graph_gradient_verified=True)
        model.zero_grad(set_to_none=True);expected=None;actual=None;objective=None
        params=[p for p in model.parameters() if p.requires_grad];optimizer=torch.optim.AdamW(params,lr=1e-4);scheduler=cosine(optimizer,3)
        data_hash=hashlib.sha256(b'tiny-original-dpo-sequences-v1').hexdigest();config=dict(beta=.1,reference=list(reference),mode='sequential_replay_sum_logps')
        def step():
            guard();optimizer.zero_grad(set_to_none=True);metrics=sequential_pair_backward(model,chosen,rejected,reference,observe=lambda phase:guard())
            norm=torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True)
            if not all(p.grad is not None and torch.isfinite(p.grad).all() for p in params):raise ValueError('Invalid preference gradients')
            optimizer.step();scheduler.step();metrics['gradient_norm']=float(norm);return metrics
        report['step1']=step();save(out/'step1',model,optimizer,scheduler,step=1,data_hash=data_hash,config=config)
        metrics=step();weights=[p.detach().cpu().clone() for p in params]
        base=model.unload();model=None;optimizer=None;scheduler=None;params=None;gc.collect()
        model=PeftModel.from_pretrained(base,out/'step1/adapter',local_files_only=True,is_trainable=True)
        params=[p for p in model.parameters() if p.requires_grad];optimizer=torch.optim.AdamW(params,lr=1e-4);scheduler=cosine(optimizer,3)
        assert restore(out/'step1',optimizer,scheduler,data_hash=data_hash,config=config)==1
        replay=step()
        if metrics!=replay or not all(torch.equal(p.detach().cpu(),w) for p,w in zip(params,weights)):raise ValueError('Preference checkpoint replay differs')
        report.update(replay_metrics_exact=True,replay_weights_exact=True,status='TINY_DPO_COMPATIBILITY_NOT_12B_QUALITY')
        if cuda:report.update(peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved(),health_after=check_resources())
    except BaseException as error:
        report.update(status='STOPPED',error=type(error).__name__)
        raise
    finally:
        model=None;base=None;optimizer=None;scheduler=None;gc.collect();release_idle_cuda(torch)
        if lease:lease.close()
        report['after']=memory_snapshot();(out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('before','after')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--cuda',action='store_true');a=p.parse_args()
    with patch('socket.socket.connect',side_effect=AssertionError('Offline')),patch('socket.getaddrinfo',side_effect=AssertionError('Offline')):run(a.output,cuda=a.cuda)
