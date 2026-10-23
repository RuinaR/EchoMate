"""Evaluation-only official Qwen minimal-persona comparison; never app loader."""
import argparse
from copy import deepcopy
import gc
import hashlib
import json
from pathlib import Path
import time
from unittest.mock import patch
from dialogue_eval_core import private_root,save,digest
from diagnose_persona_pipeline import scenarios,minimal_messages


async def gemma_minimal(args):
    from echomate_bot.inference import LocalBackend
    from echomate_bot.instance import InstanceLease
    from echomate_bot.character_profiles import presets
    from echomate_bot.model_registry import ModelValidator,ModelRegistry
    from echomate_bot.loader_memory import loading_reserve,MemoryRecorder
    from echomate_bot.processes import check_resources,model_memory_budget
    from dialogue_eval_core import metrics_since
    root=private_root(args.output);root.mkdir(parents=True,exist_ok=False)
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:raise ValueError('Incompatible Gemma')
    if check_resources()['free_vram_mib']<10240:raise RuntimeError('Need 10GiB free VRAM')
    model_memory_budget(*loading_reserve(entry))
    profiles=presets()
    for p in profiles.values():p['name']='EchoMate'
    save(root/'seal.json',dict(profiles=profiles,cases=scenarios(),parameters=dict(sampling=False,max_new_tokens=768),
        builder_sha256=hashlib.sha256(Path('tools/diagnose_persona_pipeline.py').read_bytes()).hexdigest(),
        condition='A2 all numeric traits+same descriptive card; no lore/examples/retrieval; same prompt hashes as C'))
    lease=InstanceLease();backend=LocalBackend(adapter=None);results=[];summary={};resolve=ModelRegistry.resolve
    try:
        with MemoryRecorder(interval=1) as recorder,patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)):
            t=time.monotonic();await backend.ready();await backend.probe();summary['load_seconds']=time.monotonic()-t
            for case in scenarios():
                for key,profile in profiles.items():
                    check_resources();messages=minimal_messages(profile,case['text']);cursor=backend.metrics[-1];t=time.monotonic()
                    output=await backend._job(messages,weight='base',budget=768)
                    results.append(dict(case=case['id'],profile=key,arm='A2',output=output,prompt=digest(messages),
                        seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor)))
                    save(root/'results-private.json',results);print('minimal',len(results),flush=True)
            if args.compare_root:
                from dialogue_eval_judge import judge
                comparison=private_root(args.compare_root)
                groups={'A2':results,
                    'B':[r for r in json.loads((comparison/'gemma/results-private.json').read_text('utf-8')) if r['arm']=='B']}
                for folder,arm in (('alternative','C'),('alternative-native','C-native')):
                    candidate=json.loads((comparison/folder/'results-private.json').read_text('utf-8'))
                    if len(candidate)==16 and all(r['complete'] for r in candidate):groups[arm]=candidate
                for arm,group in groups.items():
                    normalized=[dict(r,record_id=f'{arm}-{i}',phase=arm) for i,r in enumerate(group)]
                    folder=root/f'judge-{arm}';folder.mkdir()
                    summary[arm+'_auxiliary']=await judge(backend,normalized,folder,16)
                    print('judged',arm,flush=True)
            summary.update(memory=recorder.report(),status='COMPLETED_NOT_QUALITY_PASS')
    finally:
        await backend.close();lease.close();save(root/'summary.json',summary)


def run(args):
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.loader_memory import MemoryRecorder,memory_snapshot,GIB
    from echomate_bot.instance import InstanceLease
    from echomate_bot.character_profiles import presets
    root=private_root(args.output);root.mkdir(parents=True,exist_ok=False)
    path=private_root(args.model)
    acquisition=json.loads((path/'acquisition.json').read_text('utf-8'))
    config=json.loads((path/'config.json').read_text('utf-8'))
    if acquisition['model']!='Qwen/Qwen3-8B' or config['model_type']!='qwen3':raise ValueError('Official candidate only')
    health=check_resources()
    if health['free_vram_mib']<10240:raise RuntimeError('Need 10GiB free VRAM')
    weights=sum(p.stat().st_size for p in path.glob('*.safetensors'))
    model_memory_budget(weights,10*GIB)
    # Revalidate downloads instead of trusting folder names or executable code.
    for row in acquisition['files']:
        file=path/row['name'];h=hashlib.sha256()
        with file.open('rb') as stream:
            while block:=stream.read(8*1024**2):h.update(block)
        if h.hexdigest()!=row['sha256']:raise ValueError('Model integrity changed')
    lease=InstanceLease();results=[];model=None;summary=dict(health=health,before=memory_snapshot())
    profiles=presets()
    for p in profiles.values():p['name']='EchoMate'
    save(root/'seal.json',dict(model=acquisition,profiles=profiles,cases=scenarios(),parameters=dict(
        quantization='NF4 double quant BF16 compute',sampling=args.sample,temperature=.7 if args.sample else None,
        top_p=.8 if args.sample else None,top_k=20 if args.sample else None,seed=2026,max_new_tokens=768,enable_thinking=False),
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),real_discord=False))
    try:
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM,BitsAndBytesConfig,StoppingCriteria,StoppingCriteriaList
        class Bound(StoppingCriteria):
            def __init__(self):self.started=time.monotonic();self.steps=0
            def __call__(self,input_ids,scores,**kwargs):
                self.steps+=1
                if self.steps%16==0:check_resources()
                return time.monotonic()-self.started>90
        with MemoryRecorder(interval=1) as recorder,patch('aiohttp.ClientSession._request',side_effect=AssertionError('No external inference')):
            start=time.monotonic()
            tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True,trust_remote_code=False)
            model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,trust_remote_code=False,device_map={'':'cuda:0'},
                dtype=torch.bfloat16,quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
                bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16))
            summary['load_seconds']=time.monotonic()-start
            for case in scenarios():
                for key,profile in profiles.items():
                    check_resources();messages=minimal_messages(profile,case['text'])
                    inputs=tokenizer.apply_chat_template(messages,add_generation_prompt=True,enable_thinking=False,
                        return_tensors='pt',return_dict=True).to('cuda:0')
                    if inputs['input_ids'].shape[-1]>6000:raise ValueError('Input budget')
                    torch.cuda.reset_peak_memory_stats();start=time.monotonic()
                    with torch.inference_mode():
                        torch.manual_seed(2026)
                        generated=model.generate(**inputs,max_new_tokens=768,do_sample=args.sample,
                            **(dict(temperature=.7,top_p=.8,top_k=20) if args.sample else {}),
                            stopping_criteria=StoppingCriteriaList([Bound()]))
                    ids=generated[0,inputs['input_ids'].shape[-1]:].tolist()
                    output=tokenizer.decode(ids,skip_special_tokens=True)
                    if '<think>' in output:raise ValueError('Unexpected thinking channel')
                    results.append(dict(case=case['id'],profile=key,arm='C',output=output,prompt=digest(messages),
                        seconds=time.monotonic()-start,input_tokens=inputs['input_ids'].shape[-1],output_tokens=len(ids),
                        complete=bool(ids and ids[-1]==tokenizer.eos_token_id),peak_allocated_mib=torch.cuda.max_memory_allocated()/1048576,
                        peak_reserved_mib=torch.cuda.max_memory_reserved()/1048576))
                    del inputs,generated
                    save(root/'results-private.json',results);print(json.dumps(dict(done=len(results),case=case['id'],profile=key)),flush=True)
                    if not results[-1]['complete']:raise ValueError('Incomplete output')
            summary['memory']=recorder.report();summary['status']='COMPLETED_NOT_QUALITY_PASS'
    except BaseException as exc:
        summary.update(status='STOPPED',error=type(exc).__name__);raise
    finally:
        model=None;gc.collect()
        if 'torch' in locals() and torch.cuda.is_initialized():
            torch.cuda.empty_cache();summary['after_gpu']=dict(allocated=torch.cuda.memory_allocated(),reserved=torch.cuda.memory_reserved())
        lease.close();summary['after']=memory_snapshot();save(root/'summary.json',summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--output',required=True);p.add_argument('--gemma',action='store_true');p.add_argument('--compare-root');p.add_argument('--sample',action='store_true')
    args=p.parse_args()
    if args.gemma:
        import asyncio
        asyncio.run(gemma_minimal(args))
    else:run(args)
