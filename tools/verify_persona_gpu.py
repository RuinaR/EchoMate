"""One resident model: frozen old prompts, candidate personas, blind review.

All protocols/outputs must stay under ignored local_data. No live Discord.
Automated completion/format checks are not a human persona-quality PASS.
"""
import argparse,asyncio,hashlib,json,random,time
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from echomate_bot.character_profiles import presets,SHARED_FIELDS
from echomate_bot.character import instruction,effective_character
from echomate_bot.settings import DEFAULTS,atomic_private_json,private_path
from echomate_bot.inference import LocalBackend
from echomate_bot.instance import InstanceLease
from echomate_bot.model_registry import ModelValidator,ModelRegistry
from echomate_bot.loader_memory import MemoryRecorder,loading_reserve,memory_snapshot
from echomate_bot.processes import check_resources,model_memory_budget
from echomate_bot.output_policy import contains_code
from echomate_bot.telemetry import distribution


async def run(args):
    root=private_path(args.output);root.mkdir(parents=True,exist_ok=False)
    protocol=json.loads(private_path(args.protocol).read_text(encoding='utf-8'))
    baseline=json.loads(private_path(args.baseline).read_text(encoding='utf-8'))
    if not isinstance(protocol,list) or not 1<=len(protocol)<=12:raise ValueError('Bounded protocol required')
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:raise ValueError('Model incompatible')
    health=check_resources()
    if health['free_vram_mib']<10240:raise RuntimeError('GPU probe needs 10GiB headroom')
    model_memory_budget(*loading_reserve(entry))
    atomic_private_json(root/'seal.json',dict(protocol_sha256=hashlib.sha256(private_path(args.protocol).read_bytes()).hexdigest(),
        baseline_sha256=hashlib.sha256(private_path(args.baseline).read_bytes()).hexdigest(),
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/echomate_bot').glob('*.py')},health=health))
    lease=InstanceLease();backend=LocalBackend(adapter=None);resolve=ModelRegistry.resolve;results=[];summary={}
    def snapshot():
        import sys
        row=memory_snapshot();torch=sys.modules.get('torch')
        if torch and torch.cuda.is_initialized():row.update(allocated=torch.cuda.memory_allocated(),reserved=torch.cuda.memory_reserved())
        return row
    try:
        with MemoryRecorder(interval=.25) as recorder,patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)):
            summary['before']=snapshot();started=time.monotonic();await backend.ready();await backend.probe()
            summary.update(load_seconds=time.monotonic()-started,ready=snapshot())
            for phase in ('baseline','candidate'):
                if phase=='baseline' and args.candidate_only:continue
                for key,p in presets().items():
                    prior={}
                    for case in protocol:
                        if phase=='baseline' and not case.get('baseline'):continue
                        cfg=deepcopy(DEFAULTS);cfg.update(character_profile=dict(p,name='EchoMate'),**{k:p[k] for k in SHARED_FIELDS})
                        cfg['mood']=case.get('mood','평온');cfg=effective_character(cfg,case['text']);cfg['_familiarity']=None
                        context=[]
                        if case.get('follow'):
                            previous=prior[case['follow']];context=[dict(role='user',content=previous['question']),dict(role='assistant',content=previous['output'])]
                        context.append(dict(role='user',content=case['text']))
                        before=len(backend.metrics);start=time.monotonic()
                        if phase=='baseline':
                            with patch('echomate_bot.inference.instruction',return_value=baseline[key]['instruction']):output=await backend.text(context,cfg)
                            prompt=baseline[key]['instruction']
                        else:output=await backend.text(context,cfg);prompt=instruction(cfg)
                        result=dict(phase=phase,profile=key,case=case['id'],question=case['text'],output=output,seconds=time.monotonic()-start,
                            metrics=deepcopy(backend.metrics[before:]),system_tokens=len(backend.processor.tokenizer.encode(prompt,add_special_tokens=False)),
                            complete=bool(output.strip()),code=contains_code(output),mood=cfg['mood'])
                        results.append(result);prior[case['id']]=result
                        atomic_private_json(root/'results-private.json',results)
                        atomic_private_json(root/'progress.json',dict(completed=len(results),phase=phase,profile=key,case=case['id']))
                        await asyncio.sleep(.1)
            # Produce blinded packets before a reviewer sees the profile key.
            packets=[];key_rows=[];rng=random.Random(29024)
            for case in protocol:
                group=[r for r in results if r['phase']=='candidate' and r['case']==case['id']];rng.shuffle(group)
                answers=[]
                for i,row in enumerate(group):
                    label=chr(65+i);answers.append(dict(label=label,text=row['output']));key_rows.append(dict(case=case['id'],label=label,profile=row['profile']))
                packets.append(dict(case=case['id'],question=case['text'],answers=answers))
            atomic_private_json(root/'blind-review.json',packets);atomic_private_json(root/'blind-key.json',key_rows)
            if args.runtime_protocol:
                import verify_utterance_gpu as runtime_qa
                class Borrow:
                    def __getattr__(self,name):return getattr(backend,name)
                    async def ready(self):pass
                    async def probe(self):pass
                    async def close(self):pass
                class LeaseBorrow:
                    def close(self):pass
                # Outer real lease and backend stay owned until this finally.
                with patch.object(runtime_qa,'LocalBackend',return_value=Borrow()),patch.object(runtime_qa,'InstanceLease',return_value=LeaseBorrow()):
                    await runtime_qa.run(SimpleNamespace(model=args.model,protocol=args.runtime_protocol,output=str(root/'runtime'),sdk_mock=True))
            summary.update(after=snapshot(),outputs=len(results),format_ok=all(r['complete'] and not r['code'] for r in results),
                phases={phase:dict(n=sum(r['phase']==phase for r in results),seconds=distribution([r['seconds'] for r in results if r['phase']==phase]),
                    mean_system_tokens=sum(r['system_tokens'] for r in results if r['phase']==phase)/max(1,sum(r['phase']==phase for r in results))) for phase in ('baseline','candidate')},
                actual_discord=False,persona_quality='REQUIRES_RUBRIC_REVIEW')
            summary['memory']=recorder.report()
    finally:
        try:await backend.close();summary['closed']=snapshot()
        finally:lease.close();atomic_private_json(root/'summary.json',summary)
    print(json.dumps(dict(outputs=summary['outputs'],format_ok=summary['format_ok'],persona_quality=summary['persona_quality'])))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--model',required=True);parser.add_argument('--protocol',required=True);parser.add_argument('--baseline',required=True);parser.add_argument('--output',required=True);parser.add_argument('--runtime-protocol');parser.add_argument('--candidate-only',action='store_true');args=parser.parse_args()
    with patch('discord.http.HTTPClient.request',side_effect=AssertionError('Live Discord forbidden')),patch('aiohttp.ClientSession._request',side_effect=AssertionError('External network forbidden')):
        asyncio.run(run(args))
