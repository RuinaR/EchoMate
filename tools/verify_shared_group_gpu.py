"""Final-source GPU smoke: explicit shared flow, queued reply and latest update."""
import argparse
import asyncio
from datetime import datetime,timezone
from pathlib import Path
import random
import secrets
import shutil
from echomate_bot.settings import Settings,private_path,atomic_private_json
from echomate_bot.runtime import Runtime,Event
from echomate_bot.inference import LocalBackend
from echomate_bot.instance import InstanceLease
from verify_parallel_gpu import Transport,Borrowed,settle

async def run(root,independent=False):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend();rows=[]
    for p in Path('src').rglob('*.py'):
        target=root/'source'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    try:
        await backend.ready()
        for mode in ('base',):
            settings=Settings(1,secrets.token_hex(32),root/f'{mode}-settings.json')
            settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True);settings.set(1,'model',mode)
            transport=Transport();runtime=Runtime(settings,Borrowed(backend),transport,None,None,ledger_path=root/f'{mode}-sent.sqlite3',rng=random.Random(2026))
            def event(number,user,text,reply=None):return Event(number,2,3,user,text,datetime.now(timezone.utc),reply_to=reply)
            try:
                name,initial,updated=('이슬','초록','주황') if independent else ('하늘','보라','노랑')
                await runtime.ingest(event(100,4,f'<@999> 프로젝트 이름은 {name}이고 색은 {initial}이야. 확인하고 리스트와 튜플의 차이 두 가지를 설명해 줘.'))
                await asyncio.sleep(1)
                await runtime.ingest(event(101,5,'<@999> 그 프로젝트의 이름과 색만 알려 줘.',100))
                await settle(runtime,backend)
                targets=[r['source'] for r in transport.sent]
                second=next((r['text'] for r in transport.sent if r['source']==101),'')
                last=9000+len(transport.sent)
                await runtime.ingest(event(102,6,f'색은 {updated}으로 변경했어. 한 문장으로 확인해 줘.',last));await settle(runtime,backend)
                await runtime.ingest(event(103,4,'최종 색은 뭐였지? 한 단어로 알려 줘.'));await settle(runtime,backend)
                final=next((r['text'] for r in transport.sent if r['source']==103),'')
                row=dict(mode=mode,targets=[r['source'] for r in transport.sent],initial_order=targets==[100,101],shared_fact=(name in second and initial in second),
                    latest_fact=updated in final,conversation_ids=len({f.conversation_id for f in runtime.conversations.flows.values()}),
                    responses=transport.sent,traces=runtime.traces)
                rows.append(row);atomic_private_json(root/'responses-private.json',rows)
                print(str({k:v for k,v in row.items() if k not in ('responses','traces')}),flush=True)
            finally:await runtime.close()
        atomic_private_json(root/'summary.json',dict(real_gpu=True,real_discord=False,modes=[{k:v for k,v in r.items() if k not in ('responses','traces')} for r in rows]))
    finally:
        try:await backend.close()
        finally:lease.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--independent',action='store_true');args=parser.parse_args()
    asyncio.run(run(private_path(args.output),args.independent))
