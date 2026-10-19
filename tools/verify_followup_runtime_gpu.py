"""Actual local semantic recall routing against copied synthetic digest stores."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import secrets
import sqlite3
import time
from echomate_bot.runtime import Runtime,Event
from echomate_bot.inference import LocalBackend
from echomate_bot.settings import Settings,private_path,atomic_private_json
from echomate_bot.instance import InstanceLease
from echomate_bot.companion_store import CompanionStore
from echomate_studio.dialogue_state import DialogueState,Turn
from verify_parallel_gpu import Transport,Borrowed,settle

async def run(root,previous):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend();rows=[]
    try:
        await backend.ready()
        for mode in ('base','persona','adult'):
            folder=root/mode;folder.mkdir();dbpath=folder/'companion.sqlite3'
            source=sqlite3.connect((previous/mode/'companion.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);target=sqlite3.connect(dbpath)
            try:source.backup(target)
            finally:source.close();target.close()
            store=CompanionStore(dbpath);cfg=Settings(1,secrets.token_hex(32),folder/'settings.json')
            cfg.set_scope(1,2,3,'mention');cfg.set_scope(1,2,8,'mention');cfg.set(1,'enabled',True);cfg.set(1,'model',mode)
            transport=Transport();runtime=Runtime(cfg,Borrowed(backend),transport,None,None,ledger_path=folder/'sent.sqlite3',companion=store);runtime.direct_cooldown=0
            try:
                for channel in (3,8):
                    e=Event(30+channel,2,channel,4,'<@999> 지난번에 모임을 언제 하기로 정했지',datetime.now(timezone.utc))
                    start=time.monotonic();await runtime.ingest(e);await settle(runtime,backend)
                    sent=[r for r in transport.sent if r['source']==e.id]
                    passed=len(sent)==1 and (('금요일' in sent[0]['text'] and '9' in sent[0]['text']) if channel==3 else '확인할 수 있는' in sent[0]['text'])
                    rows.append(dict(mode=mode,case='stored_recall' if channel==3 else 'channel_isolation',passed=passed,seconds=time.monotonic()-start,outputs=sent,traces=runtime.traces,diagnostics=runtime.diagnostics))
                    print(json.dumps({k:rows[-1][k] for k in ('mode','case','passed','seconds')}),flush=True)
                    atomic_private_json(root/'responses-private.json',rows)
            finally:await runtime.close()
        atomic_private_json(root/'summary.json',dict(real_gpu=True,real_discord=False,cases=len(rows),passed=sum(r['passed'] for r in rows),results=[{k:r[k] for k in ('mode','case','passed','seconds')} for r in rows]))
    finally:
        try:await backend.close()
        finally:lease.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--previous',required=True);a=p.parse_args()
    asyncio.run(run(private_path(a.output),private_path(a.previous)))
