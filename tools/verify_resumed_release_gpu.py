"""Offline resumed release QA. One resident model, synthetic Discord only.

Shared workers avoid repeated 12B loads between independent protocols. Protocols,
responses, local hard-linked model fixtures and traces stay below local_data.
"""
import argparse
import asyncio
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

from echomate_bot.inference import LocalBackend,ADAPTER
from echomate_bot.instance import InstanceLease
from echomate_bot.settings import Settings,private_path,atomic_private_json
from echomate_bot.model_registry import ModelRegistry,ModelValidator
from echomate_bot.runtime import Runtime,Event
from echomate_bot.loader_memory import memory_snapshot
from echomate_bot.telemetry import summarize as report,distribution
from verify_parallel_gpu import Borrowed,settle
import verify_social_gpu as social
import verify_social_fairness_gpu as fairness


class LeaseBorrow:
    def close(self):pass


def gpu_memory():
    row=memory_snapshot();torch=sys.modules.get('torch')
    if torch is not None and torch.cuda.is_initialized():
        row.update(allocated=torch.cuda.memory_allocated(),reserved=torch.cuda.memory_reserved(),
                   inactive_split=torch.cuda.memory_stats().get('inactive_split_bytes.all.current',0))
    return row


async def lifecycle(backend,root):
    """Actual reload/rollback of same weights at independent local paths."""
    root.mkdir();original=ModelRegistry().resolve('base')
    installed=root/'models';installed.mkdir();candidate=installed/'same-weights';candidate.mkdir()
    # No source write, copy or deletion: hard links reference immutable weights.
    for source in Path(original.path).iterdir():
        if source.is_file():os.link(source.resolve(),candidate/source.name)
    entry=ModelValidator().validate(candidate)
    if not entry.compatible:raise ValueError('Local fixture incompatible')
    backend.model_roots=[installed]
    settings=Settings(1,secrets.token_hex(32),root/'settings.json')
    settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True)
    transport=social.SocialTransport();runtime=Runtime(settings,Borrowed(backend),transport,None,None,ledger_path=root/'sent.sqlite3')
    original_resolve=ModelRegistry.resolve;bad='local:'+'f'*24;original_load=backend._load_impl
    started=time.monotonic();before=hashlib.sha256(settings.path.read_bytes()).hexdigest()
    try:
        await runtime.switch_model(1,entry.id)
        switched=backend.model_id==entry.id and backend.capabilities_verified and settings.get()['model']==entry.id
        selected_hash=hashlib.sha256(settings.path.read_bytes()).hexdigest()
        def resolve(registry,key):
            if key==bad:return replace(entry,id=bad,path=str(root/'injected-missing'))
            return original_resolve(registry,key)
        def load():
            if backend.model_id==bad:raise OSError('Injected preparation failure after old model unload')
            return original_load()
        backend._load_impl=load
        with patch.object(ModelRegistry,'resolve',resolve):
            try:await runtime.switch_model(1,bad)
            except OSError:pass
            else:raise AssertionError('Expected injected switch failure')
        restored=backend.model_id==entry.id and backend.capabilities_verified
        unchanged=selected_hash==hashlib.sha256(settings.path.read_bytes()).hexdigest()
        from datetime import datetime,timezone
        await runtime.ingest(Event(900,2,3,4,'<@999> 7 더하기 8을 숫자로만 알려줘',datetime.now(timezone.utc),member_mentions=(999,)))
        await settle(runtime,backend)
        reply_ok=len(transport.sent)==1 and transport.sent[0]['source']==900 and '15' in transport.sent[0]['text']
        runtime.direct_cooldown=0;runtime.direct_spam_window=0
        await runtime.ingest(Event(901,2,3,4,'<@999> 1부터 40까지 숫자를 빠짐없이 쉼표로 적어 줘',datetime.now(timezone.utc),member_mentions=(999,)))
        await asyncio.sleep(.5)
        await runtime.ingest(Event(902,2,3,5,'<@999> 9 곱하기 9를 숫자로만 알려줘',datetime.now(timezone.utc),member_mentions=(999,)))
        switch_busy=backend.pending>0
        await runtime.switch_model(1,'base');await settle(runtime,backend)
        targets=[x['source'] for x in transport.sent if x['source'] in (901,902)]
        pending_preserved=targets==[901,902] and '81' in next((x['text'] for x in transport.sent if x['source']==902),'')
        result=dict(switched=switched,restored_after_injected_failure=restored,failed_selection_not_saved=unchanged,
                    answered_after_restore=reply_ok,seconds=time.monotonic()-started,
                    switch_while_busy=switch_busy,pending_targets_preserved=pending_preserved,
                    fixture='same original weights via hard links; not a different-model quality test',passed=switched and restored and unchanged and reply_ok and switch_busy and pending_preserved,
                    memory=gpu_memory(),traces=runtime.traces,outputs=transport.sent)
        atomic_private_json(root/'results-private.json',result)
        return {k:result[k] for k in ('switched','restored_after_injected_failure','failed_selection_not_saved','answered_after_restore','switch_while_busy','pending_targets_preserved','seconds','passed')}
    finally:
        backend._load_impl=original_load
        await runtime.close()


async def wrapper_ab(backend,root,protocol):
    """Counterbalanced bare weights vs disabled PEFT, shared GPU, same inputs.

    Native PEFT unload removes adapter layers without merging the adapter.
    Adapter transition/synchronization is outside request timing. One warmup
    pair per prompt is excluded; three measured pairs per prompt are retained.
    """
    from datetime import datetime,timezone
    import torch
    from peft import PeftModel
    root.mkdir();data=json.loads(private_path(protocol).read_text(encoding='utf-8'))
    cases=list({c['event']['text']:c for c in reversed(data['cases'])}.values())
    rows=[];transitions=[]
    def select(legacy):
        started=time.monotonic()
        if backend.adapter is not None:
            backend.model=backend.model.unload();backend.adapter=None
        if legacy:
            backend.model=PeftModel.from_pretrained(backend.model,str(ADAPTER),is_trainable=False,local_files_only=True).eval()
            backend.adapter=ADAPTER
        torch.cuda.synchronize()
        transitions.append(time.monotonic()-started)
    try:
        for repeat in range(-1,3):
            for i,case in enumerate(cases):
                for variant in (('bare','peft_disabled') if repeat%2==0 else ('peft_disabled','bare')):
                    select(variant=='peft_disabled');folder=root/f'{repeat+1}-{i}-{variant}';folder.mkdir()
                    cfg=Settings(1,secrets.token_hex(32),folder/'settings.json')
                    cfg.set_scope(1,2,3,'mention');cfg.set(1,'enabled',True)
                    cfg.change(1,lambda c:c['guilds']['2'].update(name=data['bot_name']))
                    transport=social.SocialTransport();runtime=Runtime(cfg,Borrowed(backend),transport,None,None,ledger_path=folder/'sent.sqlite3')
                    try:
                        started=time.monotonic()
                        await runtime.ingest(Event(200,2,3,4,case['event']['text'],datetime.now(timezone.utc)))
                        await settle(runtime,backend)
                        row=dict(prompt=i,repeat=repeat,variant=variant,seconds=time.monotonic()-started,
                                 prompt_sha256=hashlib.sha256(case['event']['text'].encode()).hexdigest(),
                                 sent=transport.sent,traces=runtime.traces,
                                 passed=len(transport.sent)==1 and transport.sent[0]['source']==200)
                        rows.append(row);atomic_private_json(root/'results-private.json',rows)
                        atomic_private_json(root/'progress.json',dict(completed=len(rows),total=24))
                    finally:await runtime.close()
        measured=[r for r in rows if r['repeat']>=0]
        comparisons=[]
        for repeat in range(3):
            for i in range(len(cases)):
                pair=[r for r in measured if r['repeat']==repeat and r['prompt']==i]
                comparisons.append(all(r['passed'] for r in pair) and pair[0]['sent'][0]['text']==pair[1]['sent'][0]['text'])
        result=dict(cases=len(measured),passed=sum(r['passed'] for r in measured),warmup_cases=len(rows)-len(measured),
                    output_equal_pairs=sum(comparisons),pairs=len(comparisons),transition_seconds=distribution(transitions),
                    variants={v:report([t for r in measured if r['variant']==v for t in r['traces']]) for v in ('bare','peft_disabled')})
        atomic_private_json(root/'summary.json',result);return result
    finally:
        if backend.adapter is not None:backend.model=backend.model.unload();backend.adapter=None


async def cache_ab(backend,root):
    """Matched resident-GPU classification A/B, not end-to-end Discord latency."""
    from dataclasses import asdict
    root.mkdir();rows=[];original=backend.choice_cache
    packets=[]
    for text in ('그건 왜 그렇게 하는 거야','그 순서는 이해했어','다들 준비됐으면 시작하자'):
        packets.append(dict(bot_id='999',current=dict(id='200',speaker='4',text=text,reply=None,roles={}),
            frames=[dict(index='0',participants=['4'],current_peers=['4'],last_recipient='4',turns=[dict(id='100',speaker='4',bot=False,reply=None,text='준비 순서를 설명해 줘'),dict(id='101',speaker='999',bot=True,reply='100',text='목표를 정하고 필요한 자료를 모은 뒤 확인하면 돼.')])],
            surrounding=[],current_peer_frames=['0'],pending_human_exchange=None,candidates_truncated=False,reaction_available=False))
    try:
        for repeat in range(-1,5):
            for index,packet in enumerate(packets):
                for cached in ((False,True) if (repeat+index)%2 else (True,False)):
                    backend.choice_cache=cached;started=time.monotonic();decision=await backend.assess_social(packet)
                    rows.append(dict(repeat=repeat,prompt=index,cached=cached,seconds=time.monotonic()-started,decision=asdict(decision),metric=dict(backend.metrics[-1])))
        measured=[r for r in rows if r['repeat']>=0]
        equal=all([r['decision'] for r in measured if r['repeat']==repeat and r['prompt']==i][0]==[r['decision'] for r in measured if r['repeat']==repeat and r['prompt']==i][1] for repeat in range(5) for i in range(3))
        result=dict(equal_pairs=15 if equal else None,pairs=15,warmup_calls=6,
            variants={str(c):distribution([r['seconds'] for r in measured if r['cached']==c]) for c in (False,True)},
            criterion='>=5% lower median, no >3% p95 regression, all outputs equal; descriptive small-sample evidence')
        a=result['variants']['False'];b=result['variants']['True']
        result['adopt']=equal and b['p50']<=a['p50']*.95 and b['p95']<=a['p95']*1.03
        atomic_private_json(root/'results-private.json',rows);atomic_private_json(root/'summary.json',result);return result
    finally:backend.choice_cache=original


async def run(args):
    root=private_path(args.output);root.mkdir(parents=True,exist_ok=False)
    lease=InstanceLease();backend=LocalBackend(adapter=ADAPTER if args.legacy_adapter else None,choice_cache=getattr(args,'cache_choices',False))
    original_close=backend.close;summary={};before=[]
    from echomate_bot import social as social_policy
    original_prompt=social_policy.PROMPT
    async def borrowed_close():pass
    backend.close=borrowed_close
    async def protocol(name,path):
        a=SimpleNamespace(output=str(root/name),protocol=path,modes='base',generate=False,legacy_adapter=args.legacy_adapter,cache_choices=False)
        with patch.object(social,'LocalBackend',lambda **kw:backend),patch.object(social,'InstanceLease',LeaseBorrow):await social.run(a)
        result=json.loads((root/name/'summary.json').read_text(encoding='utf-8'))
        rows=json.loads((root/name/'results-private.json').read_text(encoding='utf-8'))
        result['pipeline']=report([t for r in rows for t in r['traces']])
        atomic_private_json(root/name/'summary.json',result)
        return {k:v for k,v in result.items() if k not in ('scheduler',)}
    try:
        if args.social_system:
            path=private_path(args.social_system)
            if path.stat().st_size>32*1024:raise ValueError('QA prompt too large')
            social_policy.PROMPT=path.read_text(encoding='utf-8')
        import shutil
        for source in [*Path('src').rglob('*.py'),Path(__file__),Path('tools/verify_social_gpu.py'),Path('tools/verify_stability_soak.py')]:
            relative=source.resolve().relative_to(Path.cwd().resolve())
            target=root/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        atomic_private_json(root/'manifest.json',dict(code_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            real_gpu=True,real_discord=False,legacy_adapter=args.legacy_adapter,shared_model=True,
            social_prompt_sha256=hashlib.sha256(social_policy.PROMPT.encode()).hexdigest(),cache_choices=backend.choice_cache,
            source_hashes={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src').rglob('*.py')}))
        await backend.ready();await backend.probe();before.append(gpu_memory())
        if args.social:summary['social']=await protocol('social',args.social)
        if args.social_regression:summary['social_regression']=await protocol('social-regression',args.social_regression)
        if args.characters:summary['characters']=await protocol('characters',args.characters)
        if args.pipeline:summary['pipeline']=await protocol('pipeline',args.pipeline)
        if getattr(args,'cache_ab',False):summary['cache_ab']=await cache_ab(backend,root/'cache-ab')
        if args.wrapper_ab:summary['wrapper_ab']=await wrapper_ab(backend,root/'wrapper-ab',args.wrapper_ab)
        if args.fairness:
            with patch.object(fairness,'LocalBackend',lambda:backend),patch.object(fairness,'InstanceLease',LeaseBorrow):await fairness.run(root/'fairness')
            summary['fairness']=json.loads((root/'fairness/summary.json').read_text())
        if args.lifecycle:summary['lifecycle']=await lifecycle(backend,root/'lifecycle')
        if getattr(args,'capacity',False):
            from verify_stability_soak import capacity_probe
            summary['capacity']=await capacity_probe(root/'capacity',backend)
        if getattr(args,'soak_seconds',0):
            from verify_stability_soak import run as soak
            summary['soak']=await soak(root/'soak',args.soak_seconds,backend,restart_interval=max(60,args.soak_seconds/2))
        summary['memory_before_after_workloads']=[*before,gpu_memory()]
    except BaseException as exc:
        summary['failure']=dict(type=type(exc).__name__,reason=getattr(exc,'reason',None),status='BLOCKED')
        raise
    finally:
        backend.close=original_close
        try:await backend.close();summary['memory_after_close']=gpu_memory()
        finally:
            social_policy.PROMPT=original_prompt
            lease.close();atomic_private_json(root/'summary.json',summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--characters');p.add_argument('--pipeline');p.add_argument('--social')
    p.add_argument('--wrapper-ab')
    p.add_argument('--social-regression')
    p.add_argument('--cache-choices',action='store_true')
    p.add_argument('--cache-ab',action='store_true')
    p.add_argument('--soak-seconds',type=float,default=0)
    p.add_argument('--capacity',action='store_true')
    p.add_argument('--social-system',help='Offline QA-only system prompt below local_data')
    p.add_argument('--fairness',action='store_true');p.add_argument('--lifecycle',action='store_true');p.add_argument('--legacy-adapter',action='store_true')
    args=p.parse_args()
    try:asyncio.run(run(args))
    finally:
        import threading
        root=private_path(args.output)
        if root.exists():atomic_private_json(root/'shutdown.json',dict(python_threads=threading.active_count(),worker_threads=sum(t.name.startswith(('echomate-gpu','asyncio_','ThreadPoolExecutor')) for t in threading.enumerate()),memory=memory_snapshot()))
