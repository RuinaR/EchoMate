"""Real one-GPU release probe. Synthetic events only, never logs responses publicly."""
import argparse
import asyncio
from datetime import datetime,timedelta,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import secrets
import shutil
import subprocess
import time
from echomate_bot.settings import Settings,private_path,atomic_private_json
from echomate_bot.runtime import Runtime,Event
from echomate_bot.inference import LocalBackend
from echomate_bot.instance import InstanceLease
from echomate_bot.character import instruction
from echomate_bot.telemetry import distribution
from echomate_studio.dialogue_state import DialogueState,Turn

class Transport:
    bot_id=999
    def __init__(self):self.sent=[]
    async def permissions(self,event):return dict(view=True,send=True,react=True,attach=False,age_restricted=False)
    async def catalog(self,event,cache):return dict(reactions={},stickers={})
    async def execute(self,event,action,library,fresh):
        if not await fresh():raise ValueError('Stale synthetic send')
        self.sent.append(dict(source=event.response_to or event.id,author=event.author,text=action.text,seconds=time.monotonic()-event.received_at))
        return 9000+len(self.sent)

class Borrowed:
    def __init__(self,backend):self.backend=backend
    def __getattr__(self,key):return getattr(self.backend,key)
    async def close(self):pass

async def settle(runtime,backend):
    while runtime.tasks:await asyncio.gather(*list(runtime.tasks.values()),return_exceptions=True)
    deadline=time.monotonic()+100
    while backend.pending:
        if time.monotonic()>deadline:raise TimeoutError('GPU did not drain')
        await asyncio.sleep(.02)

async def run(root,repeats,concurrency_only=False):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend();rows=[];prompt_hashes=[]
    source=root/'baseline-runtime.py';source.write_bytes(subprocess.check_output(['git','show','eaf1d1e:src/echomate_bot/runtime.py']))
    spec=importlib.util.spec_from_file_location('echomate_bot._qa_previous_runtime',source);module=importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name]=module;spec.loader.exec_module(module)
    for p in Path('src').rglob('*.py'):
        target=root/'source'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    original_text=backend.text
    async def recorded_text(context,cfg):
        serialized=json.dumps([dict(role='system',content=instruction(cfg)),*context],ensure_ascii=False,sort_keys=True)
        prompt_hashes.append(hashlib.sha256(serialized.encode()).hexdigest())
        return await original_text(context,cfg)
    backend.text=recorded_text
    atomic_private_json(root/'manifest.json',dict(real_gpu=True,real_discord=False,baseline='eaf1d1e runtime + same current GPU backend',
        head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),dirty_sha256=hashlib.sha256(subprocess.check_output(['git','diff'])).hexdigest(),
        seed=2026,repeats=repeats,warmup_pairs=1,warning='Concurrency changes outputs/context; not a matched speedup claim'))
    async def case(variant,mode,label,index,second=None,turns=None):
        directory=root/f'{mode}-{label}-{index}-{variant}';directory.mkdir()
        settings=Settings(1,secrets.token_hex(32),directory/'settings.json')
        settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True);settings.set(1,'model',mode)
        transport=Transport();cls=module.Runtime if variant=='baseline' else Runtime
        runtime=cls(settings,Borrowed(backend),transport,None,None,ledger_path=directory/'sent.sqlite3',rng=random.Random(2026))
        runtime.direct_spam_window=0
        now=datetime.now(timezone.utc)
        if turns:
            state=DialogueState(limit=100)
            for n in range(turns):
                content='새 연습 라운드에 관한 짧은 잡담이야.'
                if n==1:content='청록 프로젝트의 최종 색은 파랑으로 정했어.'
                if n==14:content='청록 프로젝트의 최종 색은 보라로 변경했어. 파랑은 취소야.'
                state.append(channel_id=3,thread_id=None,turn=Turn(str(n+1),'4',content,now-timedelta(seconds=100-n)))
            runtime.states[3]=state
        text=('<@999> 청록 프로젝트의 최종 색만 알려줘.' if turns else
              '<@999> 파이썬 리스트와 튜플의 차이 두 가지를 각각 한 문장으로 설명해 줘.' if second else
              '<@999> 13 더하기 8의 답을 숫자만 적어 줘.')
        start=len(prompt_hashes);started=time.monotonic()
        await runtime.ingest(Event(100,2,3,4,text,now))
        if second:
            await asyncio.sleep(1)
            overlapping=backend.pending>0
            await runtime.ingest(Event(101,2,3,5,second,datetime.now(timezone.utc)))
        await settle(runtime,backend)
        row=dict(variant=variant,mode=mode,label=label,index=index,warmup=index==0,turns=turns,
            seconds=time.monotonic()-started,sent=transport.sent,traces=runtime.traces,prompt_hashes=prompt_hashes[start:],
            overlap_at_second=overlapping if second else None,scheduler=backend.scheduler.snapshot(),missing=len({100,101} if second else {100})-len({s['source'] for s in transport.sent}),
            wrong_targets=sum(s['source'] not in ({100,101} if second else {100}) for s in transport.sent),
            duplicates=len(transport.sent)-len({s['source'] for s in transport.sent}))
        rows.append(row);atomic_private_json(root/'responses-private.json',rows)
        print(json.dumps(dict(phase=label,variant=variant,mode=mode,index=index,outputs=len(transport.sent),missing=row['missing'])),flush=True)
        await runtime.close()
    try:
        await backend.ready()
        import torch
        torch.manual_seed(2026)
        for mode in ('base',):
            for i in range(0 if concurrency_only else repeats+1):
                for variant in (('baseline','candidate') if i%2==0 else ('candidate','baseline')):await case(variant,mode,'single',i)
            for i in range(1,4):
                for variant in (('baseline','candidate') if i%2 else ('candidate','baseline')):
                    await case(variant,mode,'parallel',i,second='EchoMate, 6 곱하기 7의 답을 숫자만 적어 줘.' if i==2 else '<@999> 6 곱하기 7의 답을 숫자만 적어 줘.')
            if not concurrency_only:
                for n in (5,10,20,50):await case('candidate',mode,'context',n,turns=n)
        summary=dict(real_gpu=True,real_discord=False,modes={})
        for mode in ('base',):
            r=[x for x in rows if x['mode']==mode];single={}
            for variant in ('baseline','candidate'):
                q=[x for x in r if x['variant']==variant and x['label']=='single' and not x['warmup']]
                single[variant]=distribution([x['seconds'] for x in q])
            paired=[] if concurrency_only else [(next(x for x in r if x['label']=='single' and x['index']==i and x['variant']=='baseline'),next(x for x in r if x['label']=='single' and x['index']==i and x['variant']=='candidate')) for i in range(1,repeats+1)]
            concurrent={v:dict(outputs=sum(len(x['sent']) for x in r if x['label']=='parallel' and x['variant']==v),overlap_waves=sum(x['overlap_at_second'] for x in r if x['label']=='parallel' and x['variant']==v),missing=sum(x['missing'] for x in r if x['label']=='parallel' and x['variant']==v),wrong_targets=sum(x['wrong_targets'] for x in r if x['label']=='parallel' and x['variant']==v)) for v in ('baseline','candidate')}
            calls=[c for x in r if x['variant']=='candidate' for t in x['traces'] for c in t['calls']]
            summary['modes'][mode]=dict(single=single,matched_prompt_pairs=sum(a['prompt_hashes']==b['prompt_hashes'] and bool(a['prompt_hashes']) for a,b in paired),
                matched_response_pairs=sum([s['text'] for s in a['sent']]==[s['text'] for s in b['sent']] and bool(a['sent']) for a,b in paired),
                concurrent=concurrent,context_checks=[dict(turns=x['turns'],passed=bool(x['sent'] and ('보라' if x['turns']>=15 else '파랑') in x['sent'][0]['text'])) for x in r if x['label']=='context'],
                queue_seconds=distribution([c['queue_seconds'] for c in calls]),peak_allocated_mib=max((c.get('peak_allocated_mib',0) for c in calls),default=0),
                max_ram_mib=max((c.get('ram_mib',0) or 0 for c in calls),default=0),regenerations=sum(t['regenerations'] for x in r if x['variant']=='candidate' for t in x['traces']))
        atomic_private_json(root/'summary.json',summary);print(json.dumps(summary),flush=True)
    finally:
        try:await backend.close()
        finally:lease.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--repeats',type=int,default=5)
    parser.add_argument('--concurrency-only',action='store_true')
    args=parser.parse_args();asyncio.run(run(private_path(args.output),args.repeats,args.concurrency_only))
