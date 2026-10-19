"""Real GPU: same-user 1/2/5s calls, FIFO, explicit supplements and duplicates."""
import argparse
import asyncio
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import random
import secrets
import shutil
import time
from echomate_bot.settings import Settings,private_path,atomic_private_json
from echomate_bot.runtime import Runtime,Event
from echomate_bot.inference import LocalBackend
from echomate_bot.instance import InstanceLease
from echomate_bot.scheduler import request_context
from verify_parallel_gpu import Transport,Borrowed,settle

async def run(root):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend();rows=[]
    for source in Path('src').rglob('*.py'):
        target=root/'source'/source;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    atomic_private_json(root/'manifest.json',dict(real_gpu=True,real_discord=False,synthetic=True,seed=2026,
        intervals=[1,2,5],models=['base'],source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/echomate_bot').glob('*.py')}))
    async def case(mode,interval,kind):
        directory=root/f'{mode}-{kind}-{interval}';directory.mkdir()
        settings=Settings(1,secrets.token_hex(32),directory/'settings.json')
        settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True);settings.set(1,'model',mode)
        settings.change(1,lambda c:c['guilds']['2'].update(name='민랑mk2'))
        transport=Transport();runtime=Runtime(settings,Borrowed(backend),transport,None,None,ledger_path=directory/'sent.sqlite3',rng=random.Random(2026))
        blocker=None
        try:
            if kind=='queued':
                async def occupy():return await backend._job([dict(role='user',content='1부터 40까지 숫자를 빠짐없이 쉼표로 구분해서 적어 줘.')],weight='base',budget=512)
                blocker=asyncio.create_task(occupy());await asyncio.sleep(.3)
            text='<@999> 파이썬 리스트와 튜플의 차이 두 가지를 각각 한 문장으로 설명해 줘.'
            if kind=='supplement':text='<@999> 협동 게임을 두 개 추천하고 각각 한 문장으로 이유를 적어 줘.'
            first=Event(100,2,3,4,text,datetime.now(timezone.utc));await runtime.ingest(first)
            await asyncio.sleep(interval)
            overlap=backend.pending>0
            second=('민랑아, 17 더하기 9의 답을 숫자만 적어 줘.' if kind in ('independent','queued') else
                    '민랑아, 아 무료 게임으로만 부탁해.' if kind=='supplement' else text)
            await runtime.ingest(Event(101,2,3,4,second,datetime.now(timezone.utc)))
            await settle(runtime,backend)
            if blocker:await blocker
            sources=[r['source'] for r in transport.sent]
            expected=[100,101] if kind in ('independent','queued') else [100]
            row=dict(mode=mode,interval=interval,kind=kind,overlap_at_second=overlap,expected=expected,sources=sources,
                passed=sources==expected,duplicates=len(sources)-len(set(sources)),responses=transport.sent,
                traces=runtime.traces,scheduler=backend.scheduler.snapshot())
            rows.append(row);atomic_private_json(root/'responses-private.json',rows)
            print(json.dumps(dict(mode=mode,interval=interval,kind=kind,overlap=overlap,passed=row['passed'],outputs=len(sources))),flush=True)
        finally:
            if blocker and not blocker.done():blocker.cancel();await asyncio.gather(blocker,return_exceptions=True)
            await runtime.close()
    try:
        await backend.ready()
        import torch
        torch.manual_seed(2026)
        for mode in ('base',):
            for interval in (1,2,5):await case(mode,interval,'independent')
            for kind in ('queued','supplement','duplicate'):await case(mode,1,kind)
        summary=dict(real_gpu=True,real_discord=False,cases=len(rows),passed=sum(r['passed'] for r in rows),
            duplicate_sends=sum(r['duplicates'] for r in rows),modes={m:dict(cases=sum(r['mode']==m for r in rows),passed=sum(r['passed'] for r in rows if r['mode']==m)) for m in ('base',)})
        atomic_private_json(root/'summary.json',summary);print(json.dumps(summary),flush=True)
    finally:
        try:await backend.close()
        finally:lease.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    asyncio.run(run(private_path(parser.parse_args().output)))
