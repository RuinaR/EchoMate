"""Bounded resident Gemma evaluation: provenance, actual prompt hashes, private HTML.

No Discord access. Final cases are consumed in an append-only ledger BEFORE
generation. Score data never enters the generation prompt. No self-judge score
is treated as a factuality or release certificate.
"""
import argparse
import asyncio
from copy import deepcopy
import hashlib
import json
import subprocess
from pathlib import Path
import time
from unittest.mock import patch

from dialogue_eval_core import (blind_packets, cache_key, digest, inspect_reply,
                               private_root, report_html, save, validate_case, metrics_since)
from dialogue_eval_scenarios import korean_development


def load_cases(args, root):
    if args.suite=='campaign':
        from types import SimpleNamespace
        base=vars(args).copy()
        # Predeclared small campaign, not adaptive selection based on scores.
        standard=load_cases(SimpleNamespace(**dict(base,suite='standard',limit=4,long=False)),root)
        final=load_cases(SimpleNamespace(**dict(base,suite='final',limit=4,long=False)),root)
        selected={'ko-worry','ko-roast','ko-no-record','ko-fiction','ko-turn-a'}
        return [r for r in korean_development() if r['id'] in selected]+standard+final
    if args.suite == 'korean':
        return korean_development()[:args.limit]
    corpus = private_root(args.corpus)
    seal = json.loads((corpus/'seal.json').read_text(encoding='utf-8'))
    path = corpus/f'{args.suite}.json'
    if hashlib.sha256(path.read_bytes()).hexdigest() != seal['files'][path.name]:
        raise ValueError('Corpus seal mismatch')
    rows = json.loads(path.read_text(encoding='utf-8'))
    # Hash order avoids selecting the first emotion/source category only.
    rows.sort(key=lambda r: digest(r['id']))
    if args.long:
        rows=[r for r in rows if r.get('rollout_users')]
    selected=rows[:args.limit]
    if args.suite == 'final':
        if not args.candidate_seal:
            raise ValueError('Frozen candidate seal required for final')
        candidate = json.loads(private_root(args.candidate_seal).read_text(encoding='utf-8'))
        if candidate['sources'] != source_seal():
            raise ValueError('Candidate source changed after freeze')
        if getattr(args,'paired',False) or getattr(args,'evidence_candidate',False):
            current=hashlib.sha256(Path('tools/dialogue_evidence_candidate.py').read_bytes()).hexdigest()
            if candidate.get('evidence_candidate_sha256')!=current:
                raise ValueError('Candidate evidence contract changed after freeze')
        ledger = corpus/'consumed-final.json'
        old=json.loads(ledger.read_text(encoding='utf-8')) if ledger.exists() else []
        seen={i for row in old for i in row['ids']}
        # Never silently pick a different holdout after seeing a failure.
        if seen.intersection(r['id'] for r in selected):
            raise ValueError('Final cases already consumed; these are now regression')
        old.append(dict(ids=[r['id'] for r in selected], run=str(root), candidate=digest(candidate), at=time.time()))
        save(ledger, old)
    return [validate_case(r) for r in selected]


def source_seal():
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('src/echomate_bot').glob('*.py'))}


async def run(args):
    from echomate_bot.character import effective_character, instruction
    from echomate_bot.character_profiles import presets, SHARED_FIELDS, applied_profile
    from echomate_bot.character_card import augment, select_material
    from echomate_bot.settings import DEFAULTS
    from echomate_bot.inference import LocalBackend
    from echomate_bot.instance import InstanceLease
    from echomate_bot.model_registry import ModelValidator, ModelRegistry
    from echomate_bot.loader_memory import MemoryRecorder, memory_snapshot, loading_reserve
    from echomate_bot.processes import check_resources, model_memory_budget
    from echomate_bot.telemetry import distribution
    root=private_root(args.output);root.mkdir(parents=True, exist_ok=False)
    if not 1<=args.limit<=100:
        raise ValueError('Use explicit bounded batches of 1..100 cases')
    if not 0<args.max_seconds<=7200:
        raise ValueError('Use an explicit time budget of at most two hours')
    rows=load_cases(args, root)
    sources=source_seal()
    profiles=presets()
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:
        raise ValueError('Incompatible model')
    health=check_resources()
    if health['free_vram_mib'] < 10240:
        raise RuntimeError('Need at least 10GiB free VRAM before one model load')
    model_memory_budget(*loading_reserve(entry))
    model_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(entry.path).glob('*.json') if p.name in ('config.json','tokenizer_config.json','model.safetensors.index.json')}
    import importlib.metadata
    seal=dict(sources=sources, cases=digest(rows), model=model_files, profiles=digest(profiles),
              git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              versions={name:importlib.metadata.version(name) for name in ('torch','transformers','safetensors','bitsandbytes')},
              tools={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('tools').glob('*dialogue_*.py')},
              phase=args.phase, health=health, parameters=dict(sampling=False,max_new_tokens=768,evidence_candidate=args.evidence_candidate,paired=args.paired),
              note='Existing LocalBackend output policy/retry, tokenizer and single-worker retained')
    save(root/'seal.json', seal)
    lease=InstanceLease();backend=LocalBackend(adapter=None)
    results=[];summary=dict(status='RUNNING', actual_discord=False)
    active={};material=[]
    def tracked_augment(messages, profile, familiarity, tokenizer, **kwargs):
        output, metric=augment(messages, profile, familiarity, tokenizer, **kwargs)
        selected,_=select_material(profile['card'], messages, familiarity, kwargs.get('current_text'))
        material.append(dict(prompt_sha256=digest(output), input_sha256=digest(messages),
            lore=[r['id'] for r in selected['lore'][:metric['lore']]],
            examples=[r['id'] for r in selected['examples'][:metric['examples']]], extra_tokens=metric['tokens']))
        return output, metric
    resolve=ModelRegistry.resolve
    started=time.monotonic()
    def snapshot():
        import sys
        value=memory_snapshot();torch=sys.modules.get('torch')
        if torch and torch.cuda.is_initialized():
            value.update(gpu_allocated=torch.cuda.memory_allocated(),gpu_reserved=torch.cuda.memory_reserved())
        return value
    try:
        with MemoryRecorder(interval=.5) as recorder, patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)), patch('echomate_bot.character_card.augment',side_effect=tracked_augment):
            summary['before']=snapshot();loading=time.monotonic();await backend.ready();await backend.probe()
            summary['load_seconds']=time.monotonic()-loading
            summary['probe_calls']=len(backend.metrics)
            summary['ready']=snapshot()
            for case in rows:
                for key, profile in profiles.items():
                    arms=[('baseline',False),('evidence-candidate',True)] if args.paired else [(args.phase,args.evidence_candidate)]
                    for arm_phase,arm_candidate in arms:
                        context=[]
                        users=case.get('rollout_users') if args.long else None
                        users=users or [case['context'][-1]['content']]
                        if not args.long:
                            context=deepcopy(case['context'][:-1])
                        for turn, text in enumerate(users):
                            if time.monotonic()-started>args.max_seconds:
                                raise TimeoutError('Bounded evaluation time expired')
                            # Existing per-job health checks also remain active.
                            check_resources()
                            cfg=deepcopy(DEFAULTS);cfg.update(character_profile=dict(deepcopy(profile),name='EchoMate'), **{k:profile[k] for k in SHARED_FIELDS})
                            cfg['mood']=case.get('mood',cfg['mood'])
                            cfg=effective_character(cfg,text);cfg['_current_utterance']=text
                            cfg['_familiarity']=case.get('familiarity')
                            context.append(dict(role='user',content=text))
                            generation_context=deepcopy(context)
                            if arm_candidate:
                                from dialogue_evidence_candidate import evidence_context
                                generation_context=evidence_context(generation_context)
                            cursor=backend.metrics[-1] if backend.metrics else None
                            material.clear();t=time.monotonic()
                            output=await backend.text(generation_context,cfg)
                            metrics=deepcopy(metrics_since(backend.metrics,cursor));seconds=time.monotonic()-t
                            record=dict(record_id=f'{case["id"]}:{key}:{arm_phase}:{turn}',case=case['id'],source=case['source'],group=case['group'],
                                 category=case['category'],split=case['split'],phase=arm_phase,profile=key,turn=turn,
                                 context=deepcopy(context),generation_context=generation_context,output=output,seconds=seconds,metrics=metrics,material=deepcopy(material),
                                 checks=inspect_reply(output,case),facts=case['facts'],
                                 prompt_base_sha256=digest(instruction(cfg)),profile_sha256=digest(applied_profile(cfg)),
                                 cache_key=cache_key(case,profile,seal,dict(turn=turn,context=context,evidence_candidate=arm_candidate)), memory=snapshot(),
                                 path='gpu_generation' if metrics else 'deterministic_reality_boundary')
                            results.append(record);context.append(dict(role='assistant',content=output))
                            save(root/'results-private.json',results)
                            save(root/'progress.json',dict(completed=len(results),case=case['id'],profile=key,turn=turn))
            if source_seal()!=sources:
                raise RuntimeError('Runtime source changed during evaluation')
            if args.judge_limit:
                from dialogue_eval_judge import judge
                summary['auxiliary_judge']=await judge(backend,results,root,args.judge_limit)
            summary.update(status='COMPLETED_NOT_QUALITY_PASS',cases=len(rows),responses=len(results),
                actual_generation_calls=sum(len(r['metrics']) for r in results),
                deterministic=sum(not r['metrics'] for r in results),
                response_seconds=distribution([r['seconds'] for r in results]),
                gpu_response_seconds=distribution([r['seconds'] for r in results if r['metrics']]),
                ttft=distribution([m['ttft_seconds'] for r in results for m in r['metrics'] if m.get('ttft_seconds') is not None]),
                memory=recorder.report(),quality='HUMAN_AND_CLAIM_REVIEW_REQUIRED')
    except BaseException as error:
        summary.update(status='STOPPED',error_type=type(error).__name__,responses=len(results))
        raise
    finally:
        try:
            await backend.close();summary['closed']=snapshot()
        finally:
            lease.close();save(root/'summary.json',summary)
            packets,key,excluded=blind_packets(results,seed=24026,forbidden_names=['EchoMate','은빛항','달빛 정거장','고요궤도','녹슨골목'])
            save(root/'blind-responses.json',packets);save(root/'blind-key.json',key)
            save(root/'blind-excluded.json',excluded)
            report_html(root/'report.html',results,summary)
    print(json.dumps({k:v for k,v in summary.items() if k in ('status','cases','responses','actual_generation_calls','deterministic','response_seconds','gpu_response_seconds','load_seconds')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--suite',choices=['korean','development','standard','final','campaign'],required=True)
    parser.add_argument('--corpus',default='local_data/evaluation-20261024/corpus')
    parser.add_argument('--candidate-seal')
    parser.add_argument('--phase',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--model',required=True)
    parser.add_argument('--limit',type=int,default=8)
    parser.add_argument('--max-seconds',type=int,default=1800)
    parser.add_argument('--long',action='store_true')
    parser.add_argument('--judge-limit',type=int,choices=range(0,33),default=0)
    parser.add_argument('--evidence-candidate',action='store_true')
    parser.add_argument('--paired',action='store_true')
    args=parser.parse_args()
    with patch('discord.http.HTTPClient.request',side_effect=AssertionError('Live Discord forbidden')), patch('aiohttp.ClientSession._request',side_effect=AssertionError('External network forbidden')):
        asyncio.run(run(args))
