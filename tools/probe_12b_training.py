"""Offline, two-step 64-token NF4/BF16 API probe, never operating training.

Requires a passed matching tiny recipe report and unchanged host admission.
The full 1800-token curriculum is explicitly outside this probe's budget.
"""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import struct
import time
from unittest.mock import patch


def run(model_path,output,tiny_report,scale=False,compact=None,curriculum=None,suffix_layers=None):
    if curriculum and (compact or suffix_layers!=4 or scale):raise ValueError("Sealed full curriculum requires suffix4 only")
    if suffix_layers is not None and not curriculum:raise ValueError("Suffix recipe requires full audited curriculum")
    repo=Path(__file__).resolve().parents[1];root=Path(output).resolve()
    if not root.is_relative_to(repo/'local_data'):raise ValueError('Private fresh output required')
    root.mkdir(parents=True,exist_ok=False)
    tiny=json.loads(Path(tiny_report).read_text('utf-8'))
    if tiny.get('status')!='TINY_API_PASS_NOT_12B_QUALITY' or not tiny.get('frozen_bf16') or not tiny.get('roundtrip'):raise ValueError('Matching tiny proof required')
    if suffix_layers and (tiny.get('last_layers')!=1 or tiny.get('prefix_requires_grad') is not False):raise ValueError('Actual tiny NF4 frozen-prefix proof required')
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    from echomate_bot.model_registry import ModelValidator
    from echomate_bot.loader_memory import memory_snapshot,MemoryRecorder,loading_reserve,release_idle_cuda,GIB
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.instance import InstanceLease
    from training_budget import estimate
    from qlora_recipe import prepare_frozen_bf16,supervised_loss
    entry=ModelValidator().validate(model_path)
    if not entry.compatible:raise ValueError('Validated local model required')
    source=Path(entry.path);rows={};index=json.loads((source/'model.safetensors.index.json').read_text())
    for name in sorted(set(index['weight_map'].values())):
        with (source/name).open('rb') as f:
            size=struct.unpack('<Q',f.read(8))[0];rows.update({k:v for k,v in json.loads(f.read(size)).items() if k!='__metadata__'})
    config=json.loads((source/'config.json').read_text());budget=estimate(rows,config['text_config'],sequence=1800 if curriculum else (128 if compact else 64),frozen_bf16=True,supervised_tokens=48 if curriculum else (32 if compact else 16),last_layers=suffix_layers)
    report=dict(status='NOT_STARTED',budget=budget,stages=[],source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),real_discord=False,quality='NOT_VERIFIED')
    model=None;optimizer=None;lease=None;recorder=None;loss=None;params=None;started=time.monotonic()
    try:
        health=check_resources();report['before']=memory_snapshot();report['health']=health
        if budget['planning_required_vram']>health['free_vram_mib']*1024**2:raise RuntimeError('Static VRAM budget not met')
        reserve,preparation=loading_reserve(entry);model_memory_budget(reserve,preparation)
        lease=InstanceLease()
        import torch
        from transformers import AutoModelForMultimodalLM,BitsAndBytesConfig
        from peft import LoraConfig,get_peft_model,PeftModel
        torch.manual_seed(20261024);torch.set_num_threads(2)
        records=None;tokenizer=None
        if compact or curriculum:
            from transformers import AutoTokenizer
            from compact_training import compile_records,evaluate,load_full_records
            tokenizer=AutoTokenizer.from_pretrained(entry.path,local_files_only=True,trust_remote_code=False)
            records=load_full_records(curriculum,repo/"tests/fixtures/conditioned_curriculum.json",entry.path) if curriculum else compile_records(tokenizer,compact)
            report['data']=dict(kind='full' if curriculum else 'compact',train=sum(r['split']=='train' for r in records),development_validation=8,max_tokens=max(len(r['input_ids']) for r in records),source_sha256=records[0]['source_sha256'])
            if curriculum:
                records=[dict(r,cohort='full_development') for r in records]
                regressions=compile_records(tokenizer,repo/'tests/fixtures/compact_training.json')
                records.extend(dict(r,cohort='compact_consumed_regression') for r in regressions if r['split']=='validation')
                report['data']['prior_consumed_regression']=8


        def sample():
            row=memory_snapshot()
            if torch.cuda.is_initialized():row.update(gpu_allocated=torch.cuda.memory_allocated(),gpu_reserved=torch.cuda.memory_reserved())
            return row
        def stage(name):
            torch.cuda.synchronize();health=check_resources();row=dict(name=name,seconds=time.monotonic()-started,health=health,**sample())
            report['stages'].append(row);(root/'progress.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            if row['ram_available']<3*GIB or row['commit_available']<2*GIB or health['free_vram_mib']<2048:raise RuntimeError('Stage resource reserve not met')
        def fresh():
            health=check_resources()
            if budget['planning_required_vram']>health['free_vram_mib']*1024**2:raise RuntimeError('Reload VRAM admission')
            model_memory_budget(reserve,preparation)
            base,info=AutoModelForMultimodalLM.from_pretrained(entry.path,local_files_only=True,trust_remote_code=False,
                output_loading_info=True,device_map={'':0},dtype=torch.bfloat16,attn_implementation='sdpa',
                quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16))
            if any(info.get(k) for k in ('missing_keys','mismatched_keys','error_msgs')):raise RuntimeError('Incomplete weights')
            return prepare_frozen_bf16(base)
        with MemoryRecorder(sample=sample,interval=.1) as recorder:
            model=fresh();stage('loaded_frozen_bf16')
            model=get_peft_model(model,LoraConfig(r=4,lora_alpha=8,lora_dropout=0,
                target_modules=([t['name'].removesuffix('.weight') for t in budget['targets']] if suffix_layers else r'.*language_model\.layers\.\d+\.self_attn\.(q_proj|v_proj)'),task_type='CAUSAL_LM'))
            if suffix_layers:
                from qlora_recipe import prepare_suffix_inputs,prove_suffix_graph
                first=config['text_config']['num_hidden_layers']-suffix_layers
                prepare_suffix_inputs(model,first)
                report['prefix_proof']=prove_suffix_graph(model,first,torch.tensor([[2,4,6,8,1]],device='cuda'))
                stage('actual_prefix_proved_before_full_input')
            params=[(n,p) for n,p in model.named_parameters() if p.requires_grad]
            assert sum(p.numel() for n,p in params)==budget['adapter_parameters']
            assert all('lora_' in n for n,p in params)
            # Avoid a full duplicate of frozen base tensors: compare bounded
            # sentinels, plus all base parameter version counters around steps.
            frozen=[(p,p._version,p.detach().flatten()[:16].cpu().clone()) for n,p in model.named_parameters() if not p.requires_grad]
            report.update(trainable=sum(p.numel() for n,p in params),embedding_dtype=str(model.get_input_embeddings().weight.dtype),tied_head=model.get_input_embeddings().weight is model.get_output_embeddings().weight)
            if records:
                report['before_quality_private']=evaluate(model,[r for r in records if r['split']=='validation'],root/'baseline-generations.jsonl',stage)
                stage('baseline_development_generation')
                batches=[(r['input_ids'],r['labels']) for r in records if r['split']=='train']
            else:batches=[(list(range(2,66)),[-100]*48+list(range(50,66)))]
            report['training_losses']=[]
            def epoch():
                nonlocal loss,ids,labels
                model.train()
                for input_ids,target in batches:
                    ids=torch.tensor([input_ids],device='cuda');labels=torch.tensor([target],device='cuda')
                    loss=supervised_loss(model,ids,labels);assert torch.isfinite(loss);loss.backward()
                    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters() if p.requires_grad)
                    assert any(p.grad.abs().sum()>0 for p in model.parameters() if p.requires_grad)
                    optimizer.step();optimizer.zero_grad(set_to_none=True);report['training_losses'].append(float(loss.detach()))
                    stage('training_step_'+str(len(report['training_losses'])))
            ids=None;labels=None

            optimizer=torch.optim.AdamW([p for n,p in params],lr=.0001)
            model.train();stage('before_backward');epoch()
            assert all(p._version==v and torch.equal(p.detach().flatten()[:16].cpu(),saved) for p,v,saved in frozen)
            model.eval()
            with torch.no_grad():expected=model(input_ids=ids,logits_to_keep=1).logits.detach().cpu()
            model.save_pretrained(root/'checkpoint',safe_serialization=True);torch.save(optimizer.state_dict(),root/'optimizer.pt')
            report.update(loss=float(loss.detach()),cooperative_stop_step=len(batches),base_sentinels_and_versions_unchanged=True)
            frozen=None;params=None;optimizer=None;model=None;loss=None;gc.collect();release_idle_cuda(torch);stage('unloaded')
            model=PeftModel.from_pretrained(fresh(),root/'checkpoint',is_trainable=True,local_files_only=True).eval()
            if suffix_layers:
                prepare_suffix_inputs(model,first)
                report['resumed_prefix_proof']=prove_suffix_graph(model,first,torch.tensor([[2,4,6,8,1]],device='cuda'))
                model.eval()
            with torch.no_grad():actual=model(input_ids=ids,logits_to_keep=1).logits.detach().cpu()
            torch.testing.assert_close(expected,actual,atol=.002,rtol=.002)
            optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=.0001)
            optimizer.load_state_dict(torch.load(root/'optimizer.pt',map_location='cpu',weights_only=True))
            epoch()
            assert all(int(s['step'])==2*len(batches) for s in optimizer.state.values());stage('resumed_final_step')
            report.update(status='12B_SHORT_BACKWARD_RESUME_PASS_NOT_QUALITY',roundtrip=True)
            if records:
                report['after_quality_private']=evaluate(model,[r for r in records if r['split']=='validation'],root/'candidate-generations.jsonl',stage)
                for field in ('before_quality_private','after_quality_private'):
                    for row in report[field]:row['text']=tokenizer.decode(row['output_ids'],skip_special_tokens=True)
                model.save_pretrained(root/'candidate-final',safe_serialization=True)
                stage('candidate_saved_not_applied')
                report['status']='12B_FULL_SUFFIX_TRAINED_REQUIRES_QUALITY_REVIEW' if curriculum else '12B_COMPACT_TRAINED_REQUIRES_QUALITY_REVIEW'

            if scale:
                report['scaling']=[]
                for sequence in (128,256):
                    plan=estimate(rows,config['text_config'],sequence=sequence,frozen_bf16=True,supervised_tokens=16)
                    current=check_resources();available=current['free_vram_mib']*1024**2+torch.cuda.memory_reserved()
                    if plan['planning_required_vram']>available:
                        report['scaling'].append(dict(sequence=sequence,status='BLOCKED_STATIC_VRAM'));break
                    optimizer.zero_grad(set_to_none=True);loss=None;gc.collect();torch.cuda.empty_cache()
                    torch.cuda.reset_peak_memory_stats();baseline=torch.cuda.memory_allocated();tick=time.monotonic()
                    ids=(torch.arange(sequence,device='cuda')%64+2).unsqueeze(0);labels=ids.clone();labels[:,:-16]=-100
                    loss=supervised_loss(model,ids,labels);assert torch.isfinite(loss);loss.backward();stage('scaling_'+str(sequence))
                    report['scaling'].append(dict(sequence=sequence,status='BACKWARD_PASS',seconds=time.monotonic()-tick,
                        baseline_allocated=baseline,peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved()))
                    optimizer.zero_grad(set_to_none=True);loss=None

    except BaseException as exc:
        report.update(status='STOPPED',error=type(exc).__name__,reason=getattr(exc,'reason',None));raise
    finally:
        model=None;optimizer=None;loss=None;params=None
        if 'frozen' in locals():frozen=None
        gc.collect()
        if 'torch' in locals():release_idle_cuda(torch)
        if lease:lease.close()
        if recorder:report['memory']=recorder.report()
        report.update(after=memory_snapshot(),elapsed=time.monotonic()-started)
        (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('memory','budget','stages')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--output',required=True);p.add_argument('--tiny-report',required=True);p.add_argument('--scale',action='store_true');p.add_argument('--compact');p.add_argument('--curriculum');p.add_argument('--suffix-layers',type=int,choices=[4]);a=p.parse_args()
    import faulthandler
    faulthandler.dump_traceback_later(900,exit=True)
    with patch('socket.socket.connect',side_effect=AssertionError('No network')),patch('socket.getaddrinfo',side_effect=AssertionError('No network')):
        run(a.model,a.output,a.tiny_report,a.scale,a.compact,a.curriculum,a.suffix_layers)
