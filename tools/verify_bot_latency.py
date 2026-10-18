"""Synthetic text/continuation GPU timing: old multi-call vs compact semantic gate.

Not an independent quality benchmark. Never use real Discord content here.
"""
import argparse
import asyncio
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import time
from echomate_bot.inference import LocalBackend
from echomate_bot.runtime import Runtime,Event
from echomate_bot.settings import Settings,private_path
from echomate_bot.vision import VisualCache


class OldBackend:
    """Preserved JSON assessment + continuity + planner path, same weights/decoding."""
    def __init__(self,backend):self.backend=backend
    def __getattr__(self,key):
        if key in {'fast_text_path','assess_turn'}:raise AttributeError(key)
        return getattr(self.backend,key)
    async def close(self):pass


class Transport:
    bot_id=999
    def __init__(self):self.sent=[]
    async def permissions(self,event):return dict(view=True,send=True,react=True,attach=True)
    async def catalog(self,event,cache):return dict(reactions={},stickers={})
    async def execute(self,event,action,library,fresh):
        if not await fresh():raise ValueError('Stale')
        self.sent.append(dict(kind=action.kind.value,text=action.text))
        return 9000+len(self.sent)


async def run(root,variants=('old','fast'),explicit_reply=False,short_followup=False):
    root.mkdir(parents=True,exist_ok=False)
    sources={}
    for path in [*Path('src/echomate_bot').glob('*.py'),Path('src/echomate_studio/dialogue_state.py'),Path(__file__).resolve().relative_to(Path.cwd())]:
        target=root/'source'/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    (root/'manifest.json').write_text(json.dumps(dict(synthetic=True,source_sha256=sources,seed=2026,explicit_reply=explicit_reply,short_followup=short_followup,decoding='greedy; same loaded weights',note='One sequence per variant, not statistical or quality proof; ledger gap adjusted by 3 seconds to exercise continuation'),indent=2),encoding='utf-8')
    backend=LocalBackend();await backend.ready();rows=[]
    import torch
    torch.manual_seed(2026)
    benchmark_time=datetime.now(timezone.utc)
    try:
        for variant in variants:
            directory=root/variant;directory.mkdir()
            settings=Settings(1,secrets.token_hex(32),directory/'settings.json')
            settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True)
            transport=Transport()
            runtime=Runtime(settings,OldBackend(backend) if variant=='old' else backend,transport,
                VisualCache(directory/'cache.sqlite3'),None,ledger_path=directory/'sent.sqlite3')
            prompts=['<@999> 안녕, 오늘 뭐 하고 있었어?','그럼 파이썬에서 리스트 얕은 복사랑 깊은 복사가 어떻게 달라?']
            if short_followup:prompts[1]='한 문장으로, 방금 우리가 이야기한 주제는 뭐였어?'
            for index,prompt in enumerate(prompts):
                if index:
                    with runtime.ledger.db() as db:db.execute('UPDATE sent SET at=at-3')
                started=time.monotonic();before=len(backend.metrics);sent=len(transport.sent)
                # A follow-up must be newer than the actual completed bot turn.
                timestamp=datetime.now(timezone.utc) if index else benchmark_time
                await runtime.ingest(Event(100+index,2,3,4,prompt,timestamp,reply_to=9001 if index and explicit_reply else None))
                await asyncio.gather(*list(runtime.tasks.values()),return_exceptions=True)
                rows.append(dict(variant=variant,turn=index,seconds=round(time.monotonic()-started,3),sent=len(transport.sent)-sent,
                    metrics=backend.metrics[before:],diagnostics=runtime.diagnostics[-8:],responses=transport.sent[sent:]))
                (root/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
            runtime.stopped=True
    finally:await backend.close()
    print(json.dumps([dict(variant=r['variant'],turn=r['turn'],seconds=r['seconds'],sent=r['sent'],calls=len(r['metrics'])) for r in rows]),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--variant',choices=('both','old','fast'),default='both')
    parser.add_argument('--explicit-reply',action='store_true');parser.add_argument('--short-followup',action='store_true')
    args=parser.parse_args()
    asyncio.run(run(private_path(args.output),('old','fast') if args.variant=='both' else (args.variant,),args.explicit_reply,args.short_followup))
