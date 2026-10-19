"""Offline release paths: one GPU, fake Discord transport, private artifacts."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import secrets
import random
import shutil
import time
from echomate_bot.inference import LocalBackend
from echomate_bot.instance import InstanceLease
from echomate_bot.runtime import Runtime,Event
from echomate_bot.settings import Settings,private_path,atomic_private_json
from verify_parallel_gpu import Borrowed,settle

class Transport:
    bot_id=999
    def __init__(self):self.sent=[]
    async def permissions(self,event):return dict(view=True,send=True,react=True,attach=False,age_restricted=False)
    async def catalog(self,event,cache):return dict(reactions={'👍':'동의','🎉':'축하'},stickers={})
    async def execute(self,event,action,library,fresh):
        if not await fresh():raise ValueError('Stale synthetic output')
        self.sent.append(dict(source=event.response_to or event.id,kind=action.kind.value,asset=action.asset,text=action.text))
        return 9000+len(self.sent)

class Opportunity(random.Random):
    """Force only random opportunity; semantic and permission gates remain real."""
    def random(self):return 0

async def run(root):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend();rows=[]
    for p in Path('src').rglob('*.py'):
        dst=root/'source'/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
    cases=[('program','<@999> Python으로 계산기 프로그램 만들어 줘','TEXT',0),
           ('reaction','<@999> 이 메시지에 👍 달아줘','REACTION',0),
           ('calculation','<@999> 17 더하기 9를 숫자로만 답해 줘','TEXT',None),
           ('autonomous_reaction','드디어 우리 팀 대회 우승했어 다들 축하해','REACTION',None),
           ('autonomous_independent','여러분 오늘 준비하던 프로젝트를 마무리했어 덕분에 잘 끝났어','REACTION',None),
           ('autonomous_other','<@5> 내일 회의 시간은 너한테 따로 말할게','SILENCE',0)]
    try:
        await backend.ready()
        for mode in ('base',):
            for index,(kind,text,expected,calls) in enumerate(cases):
                folder=root/f'{mode}-{kind}';folder.mkdir()
                cfg=Settings(1,secrets.token_hex(32),folder/'settings.json')
                cfg.set_activity_scope(1,2,3,'silent' if kind.startswith('autonomous') else 'mention','autonomous')
                for key,value in dict(enabled=True,reactions=True,model=mode).items():cfg.set(1,key,value)
                transport=Transport();runtime=Runtime(cfg,Borrowed(backend),transport,None,None,ledger_path=folder/'sent.sqlite3',rng=Opportunity())
                runtime.autonomy_idle_since-=1000
                try:
                    before=len(backend.metrics);start=time.monotonic()
                    await runtime.ingest(Event(100+index,2,3,4,text,datetime.now(timezone.utc),member_mentions=(5,) if kind=='autonomous_other' else (999,) if text.startswith('<@999>') else ()))
                    await settle(runtime,backend);metrics=backend.metrics[before:]
                    passed=(not transport.sent if expected=='SILENCE' else len(transport.sent)==1 and transport.sent[0]['kind']==expected) and (calls is None or len(metrics)==calls)
                    if kind=='calculation':passed=passed and '26' in transport.sent[0]['text']
                    row=dict(mode=mode,case=kind,passed=passed,seconds=time.monotonic()-start,gpu_calls=len(metrics),outputs=transport.sent,metrics=metrics,diagnostics=runtime.diagnostics,traces=runtime.traces)
                    rows.append(row);atomic_private_json(root/'responses-private.json',rows)
                    print(json.dumps({k:row[k] for k in ('mode','case','passed','seconds','gpu_calls')}),flush=True)
                finally:await runtime.close()
        summary=dict(real_gpu=True,real_discord=False,cases=len(rows),passed=sum(r['passed'] for r in rows),results=[{k:r[k] for k in ('mode','case','passed','seconds','gpu_calls')} for r in rows],warning='Random opportunity forced; no claim about ordinary reaction frequency or human quality.')
        atomic_private_json(root/'summary.json',summary)
    finally:
        try:await backend.close()
        finally:lease.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);a=parser.parse_args()
    asyncio.run(run(private_path(a.output)))
