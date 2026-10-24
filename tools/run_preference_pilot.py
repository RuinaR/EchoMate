"""One-base, fixed-reference, bounded QLoRA DPO research pilot.

Initial SFT adapter is read-only. Its reference log probabilities are computed
once before updates, bound to the exact dataset/template/model/adapter, and
never refreshed from the changing policy. One graph lives on GPU at a time.
"""
import argparse
import gc
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import random
import struct
import time
from unittest.mock import patch

VERIFIED_VERSIONS=dict(torch='2.9.1+cu128',transformers='5.20.1',peft='0.21.2',bitsandbytes='0.50.2')


def validate_tiny_proof(tiny,versions):
    if (versions!=VERIFIED_VERSIONS or tiny.get('versions')!=versions or tiny.get('status')!='TINY_DPO_COMPATIBILITY_NOT_12B_QUALITY' or tiny.get('cuda') is not True
            or not all(tiny.get(k) is True for k in ('single_graph_gradient_verified','replay_metrics_exact','replay_weights_exact'))
            or tiny.get('quantization')!=dict(kind='nf4',double_quant=True,compute_dtype='bfloat16')):
        raise ValueError('Same-version and quantization tiny NF4 DPO/replay proof required')


def load_pairs(source,pairs,export):
    from preference_pairs import pair_audit
    from persona_dataset import compiler_hashes
    raw=Path(source).read_bytes();pair_raw=Path(pairs).read_bytes()
    data,accepted,_=pair_audit(raw,json.loads(pair_raw));root=Path(export)
    summary=json.loads((root/'summary.json').read_text('utf-8'))
    if (summary['source_sha256']!=hashlib.sha256(raw).hexdigest() or summary['pairs_sha256']!=hashlib.sha256(pair_raw).hexdigest()
            or summary['compiler_hashes']!=compiler_hashes() or summary['pair_compiler_sha256']!=hashlib.sha256((Path(__file__).parent/'preference_pairs.py').read_bytes()).hexdigest()):raise ValueError('Preference export binding changed')
    expected={r['id']:(r['group'],r['split']) for r,_ in accepted};seen=set();records=[]
    for split in ('train','development'):
        raw_export=(root/(split+'.jsonl')).read_bytes()
        if hashlib.sha256(raw_export).hexdigest()!=summary[split+'_sha256']:raise ValueError('Preference tokens changed')
        for line in raw_export.splitlines():
            row=json.loads(line);n=len(row['prompt'])
            if row['id'] in seen or expected.get(row['id'])!=(row['group'],split) or row['split']!=split:raise ValueError('Preference source identity/split')
            for branch in ('chosen','rejected'):
                item=row[branch];ids=item['input_ids'];labels=item['labels']
                if (not 0<n<len(ids)<=512 or len(ids)!=len(labels) or ids[:n]!=row['prompt'] or labels[:n]!=[-100]*n or labels[n:]!=ids[n:]
                        or not all(type(v) is int and 0<=v<262144 for v in ids)):raise ValueError('Complete preference mask boundary required')
            seen.add(row['id']);records.append(row)
    if seen!=set(expected):raise ValueError('Incomplete preference export')
    train=[r for r in records if r['split']=='train'];dev=[r for r in records if r['split']=='development']
    if not 40<=len(train)<=128 or len(train)%4 or not 4<=len(dev)<=32:raise ValueError('Bounded preference pilot with checkpoint replay window')
    if {r['group'] for r in train}&{r['group'] for r in dev}:raise ValueError('Preference source-family leakage')
    return data,summary,train,dev


def run(a):
    from pilot_state import private_path
    from run_persona_pilot import private_adapter,development_regression,clear_unused_before_phase
    from persona_dataset import compile_records
    from training_budget import estimate,GIB
    from echomate_bot.loader_memory import memory_snapshot,loading_reserve,release_idle_cuda,MemoryRecorder
    from echomate_bot.processes import check_resources,model_memory_budget,ResourceLimitError
    from echomate_bot.instance import InstanceLease
    from echomate_bot.model_registry import ModelValidator
    out=private_path(a.output)
    if out.exists():raise FileExistsError('Fresh private preference output only')
    out.mkdir(parents=True)
    data,summary,train,dev=load_pairs(a.source,a.pairs,a.export)
    initial,initial_hashes=private_adapter(a.initial_adapter)
    if initial is None:raise ValueError('Explicit fixed SFT reference adapter required')
    tiny_raw=Path(a.tiny_proof).read_bytes();tiny=json.loads(tiny_raw);versions={n:version(n) for n in ('torch','transformers','peft','bitsandbytes')}
    validate_tiny_proof(tiny,versions)
    entry=ModelValidator().validate(a.model)
    if not entry.compatible:raise ValueError('Validated base required')
    model_root=Path(entry.path);headers={};rows={}
    for name in sorted(set(json.loads((model_root/'model.safetensors.index.json').read_text('utf-8'))['weight_map'].values())):
        with (model_root/name).open('rb') as f:raw=f.read(struct.unpack('<Q',f.read(8))[0])
        headers[name]=hashlib.sha256(raw).hexdigest();rows.update({k:v for k,v in json.loads(raw).items() if k!='__metadata__'})
    cfg=json.loads((model_root/'config.json').read_text('utf-8'))['text_config']
    for n,h in summary['tokenizer_hashes'].items():
        if n not in ('config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja') or hashlib.sha256((model_root/n).read_bytes()).hexdigest()!=h:raise ValueError('Preference tokenizer binding')
    examples=[r[b] for r in train+dev for b in ('chosen','rejected')]
    length=max(len(r['input_ids']) for r in examples);target=max(sum(x!=-100 for x in r['labels']) for r in examples)
    plan=estimate(rows,cfg,rank=4,sequence=length,supervised_tokens=target,frozen_bf16=True,checkpoint_inputs=True)
    report=dict(status='NOT_STARTED',objective='DPO',data_hash=summary['source_sha256'],data=summary,budget=plan,headers=headers,versions=versions,initial_adapter_hashes=initial_hashes,
        stages=[],phase_profiles=[],cache_events=[],trials=[],real_discord=False,model_load_attempts=0,quality='NOT_VERIFIED',tiny_proof_sha256=hashlib.sha256(tiny_raw).hexdigest())
    base=None;model=None;optimizer=None;scheduler=None;params=None;lease=None;recorder=None;started=time.monotonic()
    try:
        report.update(health=check_resources(),before=memory_snapshot())
        if report['health']['free_vram_mib']*1024**2<plan['planning_required_vram']:
            report['status']='BLOCKED_STATIC_VRAM';return
        reserve,preparation=loading_reserve(entry);model_memory_budget(reserve,preparation);lease=InstanceLease()
        import torch
        from transformers import AutoModelForMultimodalLM,AutoTokenizer,BitsAndBytesConfig
        from peft import PeftModel
        from qlora_recipe import prepare_frozen_bf16,training_checkpoint_mode,supervised_loss
        from preference_learning import completion_logps,dpo_loss,sequential_pair_backward
        from pilot_state import cosine,save,restore
        from training_profile import PhasePeaks
        from compact_training import visible_result
        os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8';torch.set_num_threads(2);torch.use_deterministic_algorithms(True);torch.manual_seed(881);random.seed(881)
        phases=PhasePeaks(torch,True)
        report['code_hashes']={n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in ('run_preference_pilot.py','preference_learning.py','preference_pairs.py','pilot_state.py','qlora_recipe.py','training_budget.py')}
        def sample():
            m=memory_snapshot();pa,pr=phases.peaks();m.update(gpu_allocated=torch.cuda.memory_allocated(),gpu_reserved=torch.cuda.memory_reserved(),gpu_peak_allocated=pa,gpu_peak_reserved=pr);return m
        def guard():
            h=check_resources();m=memory_snapshot()
            if h['free_vram_mib']<2048 or m['ram_available']<3*GIB or m['commit_available']<2*GIB:raise ResourceLimitError('DPO stage reserve','dpo_resource',dict(health=h,**m))
            return h,m
        def stage(name):
            boundary=phases.boundary(name)
            if boundary:report['phase_profiles'].append(boundary)
            h,m=guard();report['stages'].append(dict(name=name,seconds=time.monotonic()-started,health=h,**sample()))
            (out/'progress.json').write_text(json.dumps(report),encoding='utf-8')
        def hygiene(name):
            tick=time.monotonic();event=clear_unused_before_phase(torch,True);report['cache_events'].append(dict(phase=name,seconds=time.monotonic()-tick,**event));guard()
        tokenizer=AutoTokenizer.from_pretrained(a.model,local_files_only=True,trust_remote_code=False)
        cohort,sft_summary=compile_records(data,tokenizer);cohort=[r for r in cohort if r['split']=='development']
        sft_summary['tokenizer_hashes']=summary['tokenizer_hashes']
        if any((a.regression_source,a.regression_export,a.regression_ids)):
            if not all((a.regression_source,a.regression_export,a.regression_ids)):raise ValueError('Complete regression binding required')
            if json.loads(Path(a.regression_source).read_text('utf-8'))['characters']!=data['characters']:raise ValueError('Identical regression cards required')
            extra,manifest=development_regression(a.regression_source,a.regression_export,a.regression_ids,sft_summary,512);cohort+=extra;report['development_regression']=manifest
        report['development_generation_ids']=[r['id'] for r in cohort]
        if not 4<=len(cohort)<=24 or len({r['id'] for r in cohort})!=len(cohort):raise ValueError('Bounded paired generation cohort')
        def evaluate(current,name):
            result=[];current.eval();hygiene(name)
            for row in cohort:
                ids=torch.tensor([row['prompt']],device='cuda');tick=time.monotonic()
                class Clock:
                    count=0;first=None
                    def put(self,value):
                        self.count+=1
                        if self.count==2:self.first=time.monotonic()
                    def end(self):pass
                clock=Clock()
                with torch.no_grad():generated=current.generate(input_ids=ids,logits_to_keep=1,max_new_tokens=192,max_time=30,do_sample=False,use_cache=True,eos_token_id=[tokenizer.eos_token_id,tokenizer.convert_tokens_to_ids('<turn|>')],pad_token_id=tokenizer.eos_token_id,streamer=clock)
                tokens=generated[0,len(row['prompt']):].cpu().tolist();item=dict(id=row['id'],seconds=time.monotonic()-tick,ttft=None if clock.first is None else clock.first-tick,output_tokens=len(tokens),output_ids=tokens,raw=tokenizer.decode(tokens,skip_special_tokens=False),**visible_result(tokenizer,tokens));result.append(item)
                with (out/(name+'-generations.jsonl')).open('a',encoding='utf-8') as f:f.write(json.dumps(item,ensure_ascii=False)+'\n')
                stage(name+'_generation_'+str(len(result)))
            return result
        def tensors(row,branch):
            item=row[branch];return torch.tensor([item['input_ids']],device='cuda'),torch.tensor([item['labels']],device='cuda')
        with MemoryRecorder(sample=sample,interval=.2) as recorder:
            if check_resources()['free_vram_mib']*1024**2<plan['planning_required_vram']:raise ValueError('Pre-load DPO VRAM changed')
            report['status']='LOADING';report['model_load_attempts']+=1
            base,info=AutoModelForMultimodalLM.from_pretrained(a.model,local_files_only=True,trust_remote_code=False,output_loading_info=True,device_map={'':0},dtype=torch.bfloat16,attn_implementation='sdpa',quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16))
            if any(info.get(k) for k in ('missing_keys','mismatched_keys','error_msgs')):raise ValueError('Incomplete base')
            base=prepare_frozen_bf16(base);stage('prepared_single_base')
            report['status']='BASELINE';report['baseline']=evaluate(base,'baseline')
            model=PeftModel.from_pretrained(base,initial,is_trainable=True,local_files_only=True);training_checkpoint_mode(model);stage('initial_sft_adapter')
            params=[p for p in model.parameters() if p.requires_grad]
            if sum(p.numel() for p in params)!=plan['adapter_parameters']:raise ValueError('Adapter geometry differs')
            report['status']='INITIAL_SFT_EVALUATION';report['previous']=evaluate(model,'initial_sft')
            report['status']='FIXED_REFERENCE_PRECOMPUTE';references={};model.eval();hygiene('precompute_fixed_sft_reference')
            with torch.no_grad():
                for row in train+dev:
                    refs=[float(completion_logps(model,*tensors(row,b))) for b in ('chosen','rejected')]
                    if not all(__import__('math').isfinite(x) and x<=0 for x in refs):raise ValueError('Invalid reference log probabilities')
                    references[row['id']]=refs;stage('reference_'+str(len(references)))
            binding=dict(data_hash=summary['source_sha256'],pair_hash=summary['pairs_sha256'],headers=headers,initial_adapter=initial_hashes,versions=versions,tokenizer=summary['tokenizer_hashes'],reference_mode='fixed_initial_sft_eval',logps=references)
            reference_raw=json.dumps(binding,sort_keys=True).encode('utf-8');(out/'fixed-reference.json').write_bytes(reference_raw);ref_hash=hashlib.sha256(reference_raw).hexdigest();report['reference_sha256']=ref_hash
            beta=.1;lr=5e-6;steps=len(train)//4;optimizer=torch.optim.AdamW(params,lr=lr);scheduler=cosine(optimizer,steps)
            frozen=[(p,p._version,p.detach().flatten()[:16].cpu().clone()) for p in model.parameters() if not p.requires_grad]
            trial=dict(lr=lr,beta=beta,optimizer_steps=steps,steps=[]);report['trials']=[trial]
            config=dict(objective='DPO',beta=beta,lr=lr,accumulation=4,dropout=.05,reference_sha256=ref_hash,pairs_sha256=summary['pairs_sha256'],activation_policy=plan['activation_policy'])
            order=list(train);random.seed(991);random.shuffle(order);torch.manual_seed(991);torch.cuda.manual_seed_all(991)
            def update(window,record=False):
                optimizer.zero_grad(set_to_none=True);values=[];hygiene('before_update')
                for i,row in enumerate(window):
                    guard();observe=(lambda label:stage('first_pair_'+str(i)+'_'+label)) if record else (lambda label:guard())
                    metrics=sequential_pair_backward(model,tensors(row,'chosen'),tensors(row,'rejected'),references[row['id']],beta=beta,scale=1/len(window),observe=observe);values.append(metrics);guard()
                if any(p.grad is None or not torch.isfinite(p.grad).all() for p in params):raise ValueError('Missing/nonfinite DPO gradients')
                norm=torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True);optimizer.step();scheduler.step();optimizer.zero_grad(set_to_none=True)
                return dict(loss=sum(v['loss'] for v in values)/len(values),gradient_norm=float(norm),learning_rate=optimizer.param_groups[0]['lr'])
            report['status']='PREFERENCE_TRAINING';training_checkpoint_mode(model)
            for step in range(steps):
                metrics=update(order[step*4:(step+1)*4],record=step==0);trial['steps'].append(metrics);stage('update_'+str(step+1))
                if step==7:save(out/'step8',model,optimizer,scheduler,step=8,data_hash=summary['source_sha256'],config=config);stage('checkpoint_saved_step8')
                if step==8:
                    weights=[p.detach().cpu().clone() for p in params];base=model.unload();model=None;optimizer=None;scheduler=None;params=None;gc.collect();release_idle_cuda(torch)
                    model=PeftModel.from_pretrained(base,out/'step8/adapter',is_trainable=True,local_files_only=True);params=[p for p in model.parameters() if p.requires_grad];optimizer=torch.optim.AdamW(params,lr=lr);scheduler=cosine(optimizer,steps)
                    assert restore(out/'step8',optimizer,scheduler,data_hash=summary['source_sha256'],config=config)==8
                    replay=update(order[32:36]);trial['resume_metrics_match']=metrics==replay;trial['resume_weights_match']=all(torch.equal(p.detach().cpu(),w) for p,w in zip(params,weights));weights=None
                    if not trial['resume_metrics_match'] or not trial['resume_weights_match']:raise ValueError('DPO optimizer/RNG replay diverged')
                    stage('checkpoint_replay_step9')
            trial['base_sentinels_versions_unchanged']=all(p._version==v and torch.equal(p.detach().flatten()[:16].cpu(),s) for p,v,s in frozen)
            if not trial['base_sentinels_versions_unchanged']:raise ValueError('Frozen base changed')
            model.eval();hygiene('development');losses=[]
            with torch.no_grad():
                for row in dev:losses.append(float(dpo_loss(completion_logps(model,*tensors(row,'chosen')),completion_logps(model,*tensors(row,'rejected')),*references[row['id']],beta=beta)));guard()
            trial['development_loss']=sum(losses)/len(losses);trial['generation']=evaluate(model,'dpo')
            save(out/('step'+str(steps)),model,optimizer,scheduler,step=steps,data_hash=summary['source_sha256'],config=config);report['latest_checkpoint']='step'+str(steps);stage('checkpoint_saved_final')
            report['status']='PILOT_COMPLETE_REQUIRES_QUALITY_REVIEW'
    except BaseException as error:
        report.update(status='STOPPED',error=type(error).__name__,reason=str(error),resource_reason=getattr(error,'reason',None),resource_details=getattr(error,'details',None));raise
    finally:
        model=None;base=None;optimizer=None;scheduler=None;params=None;gc.collect()
        if 'torch' in locals():release_idle_cuda(torch)
        if lease:lease.close()
        if recorder:report['memory']=recorder.report()
        report.update(after=memory_snapshot(),elapsed=time.monotonic()-started);(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=report['status'],seconds=report['elapsed'])))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('model','source','pairs','export','initial-adapter','tiny-proof','output'):p.add_argument('--'+n,required=True)
    p.add_argument('--regression-source');p.add_argument('--regression-export');p.add_argument('--regression-ids',nargs='+');a=p.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    import faulthandler
    faulthandler.dump_traceback_later(2400,exit=True)
    with patch('socket.socket.connect',side_effect=AssertionError('Offline')),patch('socket.getaddrinfo',side_effect=AssertionError('Offline')):run(a)
