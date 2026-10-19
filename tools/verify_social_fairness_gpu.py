"""Real single-GPU fair admission, four synthetic requests across two channels."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import secrets
import shutil
from echomate_bot.instance import InstanceLease
from echomate_bot.inference import LocalBackend
from echomate_bot.runtime import Runtime,Event
from echomate_bot.settings import Settings,private_path,atomic_private_json
from verify_parallel_gpu import Borrowed,Transport,settle

async def run(root):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend();rows=[]
    for p in Path('src').rglob('*.py'):
        target=root/'source'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    try:
        await backend.ready()
        for mode in ('base','persona','adult'):
            folder=root/mode;folder.mkdir();cfg=Settings(1,secrets.token_hex(32),folder/'settings.json')
            cfg.set_scope(1,2,3,'mention');cfg.set_scope(1,2,8,'mention',thread=True);cfg.set(1,'enabled',True);cfg.set(1,'model',mode)
            transport=Transport();runtime=Runtime(cfg,Borrowed(backend),transport,None,None,ledger_path=folder/'sent.sqlite3')
            runtime.direct_cooldown=0
            blocker=asyncio.create_task(backend._job([dict(role='user',content='1부터 25까지 숫자를 쉼표로 빠짐없이 적어 줘')],budget=256,weight='base'))
            try:
                await asyncio.sleep(.3)
                for source,user,channel,text in ((100,4,3,'<@999> 13 더하기 8을 숫자로만'),(101,5,3,'<@999> 12 더하기 6을 숫자로만'),(102,6,8,'<@999> 15 더하기 4를 숫자로만'),(103,4,3,'<@999> 그리고 별개 질문이야 6 더하기 7을 숫자로만')):
                    await runtime.ingest(Event(source,2,channel,user,text,datetime.now(timezone.utc),parent=3 if channel==8 else None,member_mentions=(999,)))
                    if source==100:
                        await asyncio.sleep(.03)
                        await runtime.ingest(Event(104,2,3,4,'<@5> 이 방식으로 해줘',datetime.now(timezone.utc),member_mentions=(5,)))
                await asyncio.sleep(.1);queued=backend.scheduler.details()
                await blocker;await settle(runtime,backend)
                targets=[r['source'] for r in transport.sent]
                cancelled=sum(t['outcome']=='cancelled' for t in runtime.traces)
                correct=targets==[100,101,102,103] and cancelled==0 and all(answer in next((r['text'] for r in transport.sent if r['source']==source),'') for source,answer in ((100,'21'),(101,'18'),(102,'19'),(103,'13')))
                row=dict(mode=mode,passed=correct,targets=targets,duplicates=len(targets)-len(set(targets)),queued=queued,
                    cancelled=cancelled,traces=runtime.traces,outputs=transport.sent,scheduler=backend.scheduler.snapshot())
                rows.append(row);atomic_private_json(root/'results-private.json',rows)
            finally:
                if not blocker.done():blocker.cancel()
                await asyncio.gather(blocker,return_exceptions=True);await runtime.close()
        result=dict(real_gpu=True,real_discord=False,cases=len(rows),passed=sum(r['passed'] for r in rows),wrong_order=sum(not r['passed'] for r in rows),duplicate_sends=sum(r['duplicates'] for r in rows))
        atomic_private_json(root/'summary.json',result);print(json.dumps(result))
    finally:await backend.close();lease.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);asyncio.run(run(private_path(p.parse_args().output)))
