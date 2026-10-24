"""Bounded one-epoch LR comparison using one resident local NF4 base.

No Runtime, operating settings/DB, network, final corpus, or adapter promotion.
Data/header admission precedes model loading; no truncation, packing or padding.
"""
import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import random
import struct
import time
from unittest.mock import patch


def pilot_protocol(train_count,dev_count,learning_rates):
    if not 64<=train_count<=512 or train_count%4 or not 16<=dev_count<=128 or dev_count%4:
        raise ValueError('Bounded complete pilot size/splits')
    rates=tuple(learning_rates)
    if not 1<=len(rates)<=3 or len(set(rates))!=len(rates) or any(r not in (5e-5,1e-4,2e-4) for r in rates):
        raise ValueError('Explicit limited learning rate choices')
    return dict(optimizer_steps=train_count//4,learning_rates=rates)


def run(model_path,source,export_path,output,tiny_proof,replay_proof,*,learning_rates=(1e-4,),source_queue=None,original_source=None):
    repo=Path(__file__).resolve().parents[1];out=Path(output).resolve()
    if not out.is_relative_to(repo/'local_data') or out.exists():raise ValueError('Fresh private output required')
    out.mkdir(parents=True)
    tiny_raw=Path(tiny_proof).read_bytes();tiny=json.loads(tiny_raw)
    if tiny.get('status')!='TINY_NEW_RECIPE_PASS_NOT_12B_QUALITY' or not tiny.get('replay'):raise ValueError('New NF4 dropout/accumulation/RNG proof required')
    replay_raw=Path(replay_proof).read_bytes();proof=json.loads(replay_raw)
    if not proof.get('deterministic') or not proof.get('repeat_metrics_equal') or proof.get('repeat_max_adapter_difference')!=0:raise ValueError('Actual deterministic backward replay proof required')
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8' # this research child only
    from echomate_bot.loader_memory import memory_snapshot,MemoryRecorder,loading_reserve,release_idle_cuda,GIB
    from echomate_bot.processes import check_resources,model_memory_budget,ResourceLimitError
    from echomate_bot.model_registry import ModelValidator
    from echomate_bot.instance import InstanceLease
    from training_budget import estimate
    from persona_dataset import audit,compiler_hashes
    raw=Path(source).read_bytes();data=json.loads(raw);source_records,_=audit(data);data_hash=hashlib.sha256(raw).hexdigest()
    if data['provenance']['kind']=='source_conditioned_authored':
        if not source_queue or not original_source:raise ValueError('Derived data requires original and acquired source queue')
        queue_raw=Path(source_queue).read_bytes()
        if hashlib.sha256(queue_raw).hexdigest()!=data['source_manifest']['queue_sha256']:raise ValueError('Source queue changed')
        from curate_training_situations import lineage
        lineage(data,json.loads(queue_raw),json.loads(Path(original_source).read_text('utf-8')))
    expected={r['id']:(r['group'],r['split'],r['character']) for r in source_records if r['split'] in ('train','development')}
    exported=Path(export_path);summary=json.loads((exported/'summary.json').read_text('utf-8'))
    if summary['source_sha256']!=data_hash:raise ValueError('Data export changed')
    if summary.get('compiler_hashes')!=compiler_hashes():raise ValueError('Prompt compiler changed; re-export before training')
    records=[];seen=set()
    for split in ('train','development'):
        b=(exported/(split+'.jsonl')).read_bytes()
        if hashlib.sha256(b).hexdigest()!=summary[split+'_sha256']:raise ValueError('Export integrity')
        for line in b.splitlines():
            r=json.loads(line);n=len(r['prompt'])
            if r['id'] in seen or expected.get(r['id'])!=(r['group'],split,r['character']):raise ValueError('Export source binding')
            seen.add(r['id'])
            if r['split']!=split or r['input_ids'][:n]!=r['prompt'] or r['labels'][:n]!=[-100]*n or r['labels'][n:]!=r['input_ids'][n:]:raise ValueError('Mask boundary')
            records.append(r)
    if seen!=set(expected):raise ValueError('Incomplete source export')
    train=[r for r in records if r['split']=='train'];dev=[r for r in records if r['split']=='development']
    protocol=pilot_protocol(len(train),len(dev),learning_rates)
    if set(r['group'] for r in train)&set(r['group'] for r in dev):raise ValueError('Source family leakage')
    total_steps=protocol['optimizer_steps']
    entry=ModelValidator().validate(model_path)
    if not entry.compatible:raise ValueError('Existing model must validate')
    model_root=Path(entry.path)
    for n,digest in summary['tokenizer_hashes'].items():
        if n not in ('config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja') or hashlib.sha256((model_root/n).read_bytes()).hexdigest()!=digest:raise ValueError('Tokenizer binding')
    index=json.loads((model_root/'model.safetensors.index.json').read_text('utf-8'));rows={};headers={}
    for name in sorted(set(index['weight_map'].values())):
        with (model_root/name).open('rb') as f:head=f.read(struct.unpack('<Q',f.read(8))[0])
        headers[name]=hashlib.sha256(head).hexdigest();rows.update({k:v for k,v in json.loads(head).items() if k!='__metadata__'})
    cfg=json.loads((model_root/'config.json').read_text('utf-8'))['text_config']
    length=max(len(r['input_ids']) for r in train);target=max(sum(v!=-100 for v in r['labels']) for r in train)
    plan=estimate(rows,cfg,rank=4,sequence=length,supervised_tokens=target,frozen_bf16=True)
    report=dict(status='NOT_STARTED',quality='NOT_VERIFIED',data_hash=data_hash,data=summary,budget=plan,headers=headers,stages=[],trials=[],real_discord=False,tiny_proof_sha256=hashlib.sha256(tiny_raw).hexdigest())
    report.update(deterministic=True,replay_proof_sha256=hashlib.sha256(replay_raw).hexdigest())
    # Fixed before generation: legacy two-source core plus two new source groups.
    cohort=dev[:8]+[r for r in dev if r['id'].startswith('bst-authored-')][:8]
    report.update(protocol=protocol,development_generation_ids=[r['id'] for r in cohort],model_load_attempts=0)
    model=None;base=None;optimizer=None;scheduler=None;recorder=None;lease=None;trained=None;frozen=None;ids=None;labels=None;loss=None;expected=None;started=time.monotonic()
    try:
        import subprocess
        from echomate_bot.processes import background_options
        def usage():return int(subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=5,**background_options()).splitlines()[0])
        health=check_resources();report.update(before=memory_snapshot(),health=health,gpu_utilization_percent=usage())
        if plan['planning_required_vram']>health['free_vram_mib']*1024**2:
            report['status']='BLOCKED_STATIC_VRAM';return
        reserve,preparation=loading_reserve(entry);model_memory_budget(reserve,preparation);lease=InstanceLease()
        import torch
        torch.use_deterministic_algorithms(True)
        from transformers import AutoModelForMultimodalLM,AutoTokenizer,BitsAndBytesConfig
        from peft import get_peft_model,LoraConfig,PeftModel
        from qlora_recipe import prepare_frozen_bf16,supervised_loss
        from compact_training import visible_result
        from pilot_state import train_window,cosine,save,inspect,restore
        from importlib.metadata import version
        report.update(versions={n:version(n) for n in ('torch','transformers','peft','bitsandbytes')},
            code_hashes={n:hashlib.sha256((repo/'tools'/n).read_bytes()).hexdigest() for n in ('run_persona_pilot.py','pilot_state.py','persona_dataset.py','qlora_recipe.py','training_budget.py')})
        torch.set_num_threads(2);torch.manual_seed(881);random.seed(881)
        tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,trust_remote_code=False)
        def sample():
            v=memory_snapshot()
            if torch.cuda.is_initialized():v.update(gpu_allocated=torch.cuda.memory_allocated(),gpu_reserved=torch.cuda.memory_reserved(),gpu_peak_allocated=torch.cuda.max_memory_allocated(),gpu_peak_reserved=torch.cuda.max_memory_reserved())
            return v
        def stage(name):
            torch.cuda.synchronize();v=dict(name=name,seconds=time.monotonic()-started,health=check_resources(),gpu_utilization_percent=usage(),**sample());report['stages'].append(v)
            (out/'progress.json').write_text(json.dumps(report),encoding='utf-8')
            reason='ram' if v['ram_available']<3*GIB else 'commit' if v['commit_available']<2*GIB else 'vram' if v['health']['free_vram_mib']<2048 else None
            if reason:raise ResourceLimitError('Pilot stage reserve',reason,v)
        def evaluate(current,name):
            selected=cohort;result=[];current.eval()
            for r in selected:
                ids=torch.tensor([r['prompt']],device='cuda');tick=time.monotonic()
                class Clock:
                    count=0;first=None
                    def put(self,value):
                        self.count+=1
                        if self.count==2:self.first=time.monotonic()
                    def end(self):pass
                clock=Clock()
                with torch.no_grad():generated=current.generate(input_ids=ids,max_new_tokens=192,max_time=30,do_sample=False,use_cache=True,
                    eos_token_id=[tokenizer.eos_token_id,tokenizer.convert_tokens_to_ids('<turn|>')],pad_token_id=tokenizer.eos_token_id,streamer=clock)
                tokens=generated[0,len(r['prompt']):].cpu().tolist()
                result.append(dict(id=r['id'],seconds=time.monotonic()-tick,ttft=None if clock.first is None else clock.first-tick,
                    output_tokens=len(tokens),output_ids=tokens,raw=tokenizer.decode(tokens,skip_special_tokens=False),**visible_result(tokenizer,tokens)))
                with (out/(name+'-generations.jsonl')).open('a',encoding='utf-8') as f:f.write(json.dumps(result[-1],ensure_ascii=False)+'\n')
                stage(name+'_generation_'+str(len(result)))
            return result
        with MemoryRecorder(sample=sample,interval=.2) as recorder:
            current=check_resources()
            if plan['planning_required_vram']>current['free_vram_mib']*1024**2:raise ResourceLimitError('Pre-load VRAM changed','vram',current)
            model_memory_budget(reserve,preparation)
            report['model_load_attempts']+=1
            base,info=AutoModelForMultimodalLM.from_pretrained(model_path,local_files_only=True,trust_remote_code=False,output_loading_info=True,
                device_map={'':0},dtype=torch.bfloat16,attn_implementation='sdpa',quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16))
            if any(info.get(k) for k in ('missing_keys','mismatched_keys','error_msgs')):raise ValueError('Incomplete weights')
            base=prepare_frozen_bf16(base);stage('loaded_single_base')
            # Newly configured dropout/accumulation: bounded 128 -> 256 -> actual
            # max length. No synthetic 512/1024 padding experiment is needed.
            model=get_peft_model(base,LoraConfig(r=4,lora_alpha=8,lora_dropout=.05,target_modules=r'.*language_model\.layers\.\d+\.self_attn\.(q_proj|v_proj)',task_type='CAUSAL_LM'))
            for n in (128,256,length):
                ids=(torch.arange(n,device='cuda')%64+2).unsqueeze(0);labels=ids.clone();labels[:,:-target]=-100
                loss=supervised_loss(model,ids,labels);loss.backward();model.zero_grad(set_to_none=True);loss=None;stage('backward_length_'+str(n))
            base=model.unload();model=None;gc.collect();release_idle_cuda(torch)
            report['baseline']=evaluate(base,'baseline')
            for lr in protocol['learning_rates']:
                torch.manual_seed(881);torch.cuda.manual_seed_all(881);random.seed(881)
                trial=dict(lr=lr,rank=4,alpha=8,dropout=.05,accumulation=4,max_grad_norm=1.,epochs=1,warmup_ratio=.05,scheduler='cosine',deterministic=True,optimizer_steps=total_steps,steps=[])
                report['trials'].append(trial)
                model=get_peft_model(base,LoraConfig(r=4,lora_alpha=8,lora_dropout=.05,target_modules=r'.*language_model\.layers\.\d+\.self_attn\.(q_proj|v_proj)',task_type='CAUSAL_LM'))
                trained=[p for p in model.parameters() if p.requires_grad];assert sum(p.numel() for p in trained)==plan['adapter_parameters']
                frozen=[(p,p._version,p.detach().flatten()[:16].cpu().clone()) for p in model.parameters() if not p.requires_grad]
                optimizer=torch.optim.AdamW(trained,lr=lr);scheduler=cosine(optimizer,total_steps,.05)
                order=list(range(len(train)));random.shuffle(order)
                batches=[(train[i]['input_ids'],train[i]['labels']) for i in order]
                name='lr-'+str(lr);checkpoint=out/name/'step8';config={k:trial[k] for k in ('lr','rank','alpha','dropout','accumulation','max_grad_norm','epochs','warmup_ratio','scheduler','deterministic','optimizer_steps')}
                for step in range(total_steps):
                    value=train_window(model,batches[step*4:(step+1)*4],optimizer,scheduler,supervised_loss);trial['steps'].append(value);stage(name+'_step_'+str(step+1))
                    if step==7:save(checkpoint,model,optimizer,scheduler,step=8,data_hash=data_hash,config=config)
                    if step==8:
                        expected=[p.detach().cpu().clone() for p in model.parameters() if p.requires_grad]
                        inspect(checkpoint,data_hash=data_hash,config=config)
                        base=model.unload();model=None;optimizer=None;scheduler=None;trained=None;gc.collect();release_idle_cuda(torch)
                        model=PeftModel.from_pretrained(base,checkpoint/'adapter',is_trainable=True,local_files_only=True)
                        trained=[p for p in model.parameters() if p.requires_grad];optimizer=torch.optim.AdamW(trained,lr=lr);scheduler=cosine(optimizer,total_steps,.05)
                        assert restore(checkpoint,optimizer,scheduler,data_hash=data_hash,config=config)==8
                        replay=train_window(model,batches[32:36],optimizer,scheduler,supervised_loss)
                        trial['resume_expected_metrics']=value;trial['resume_actual_metrics']=replay
                        trial['resume_absolute_deltas']={k:abs(replay[k]-value[k]) for k in value}
                        trial['resume_metrics_match']=replay==value
                        trial['resume_weights_match']=all(torch.equal(p.detach().cpu(),v) for p,v in zip(trained,expected));expected=None
                        if not trial['resume_metrics_match'] or not trial['resume_weights_match']:raise ValueError('Actual dropout RNG replay diverged')
                        stage(name+'_replayed_step9')
                assert all(p._version==version and torch.equal(p.detach().flatten()[:16].cpu(),sentinel) for p,version,sentinel in frozen)
                frozen=None;trial['base_sentinels_versions_unchanged']=True
                model.eval()
                with torch.no_grad():trial['development_loss']=sum(float(supervised_loss(model,torch.tensor([r['input_ids']],device='cuda'),torch.tensor([r['labels']],device='cuda'))) for r in dev)/len(dev)
                trial['generation']=evaluate(model,name)
                save(out/name/('step'+str(total_steps)),model,optimizer,scheduler,step=total_steps,data_hash=data_hash,config=config)
                base=model.unload();model=None;trained=None;optimizer=None;scheduler=None;gc.collect();release_idle_cuda(torch);stage(name+'_adapter_unloaded')
            report['status']='PILOT_COMPLETE_REQUIRES_QUALITY_REVIEW'
    except BaseException as e:
        report.update(status='STOPPED',error=type(e).__name__,reason=getattr(e,'reason',None),resource_details=getattr(e,'details',None));raise
    finally:
        model=None;base=None;optimizer=None;scheduler=None;trained=None;frozen=None;ids=None;labels=None;loss=None;expected=None
        gc.collect()
        if 'torch' in locals():release_idle_cuda(torch)
        if lease:lease.close()
        if recorder:report['memory']=recorder.report()
        report.update(after=memory_snapshot(),elapsed=time.monotonic()-started)
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=report['status'],seconds=report['elapsed'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--source',required=True);p.add_argument('--export',required=True);p.add_argument('--output',required=True);p.add_argument('--tiny-proof',required=True);p.add_argument('--replay-proof',required=True)
    p.add_argument('--learning-rates',nargs='+',type=float,default=[1e-4]);p.add_argument('--source-queue');p.add_argument('--original-source');a=p.parse_args()
    import faulthandler
    faulthandler.dump_traceback_later(1500,exit=True)
    with patch('socket.socket.connect',side_effect=AssertionError('Offline')),patch('socket.getaddrinfo',side_effect=AssertionError('Offline')):
        run(a.model,a.source,a.export,a.output,a.tiny_proof,a.replay_proof,learning_rates=a.learning_rates,source_queue=a.source_queue,original_source=a.original_source)
