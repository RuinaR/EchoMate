"""Real local GPU inference through synthetic Discord events; no Gateway login."""
import asyncio
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import time
from unittest.mock import patch
from echomate_bot.settings import Settings
from echomate_bot.inference import LocalBackend
from echomate_bot.runtime import Runtime,Event
from echomate_bot.media import MediaLibrary
from echomate_bot.vision import VisualCache


class Transport:
    bot_id=999
    def __init__(self):self.results=[]
    async def permissions(self,event):return dict(view=True,send=True,react=True,attach=True)
    async def catalog(self,event,cache):return dict(reactions={},stickers={})
    async def execute(self,event,action,library,fresh):
        if not await fresh():raise ValueError('stale')
        self.results.append(dict(kind=action.kind.value,text=action.text,asset=action.asset))
        return 10000


async def run(root):
    root.mkdir(exist_ok=False,parents=True)
    source={}
    for path in [*Path('src/echomate_bot').glob('*.py'),Path(__file__)]:
        path=path.resolve().relative_to(Path.cwd().resolve())
        source[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        target=root/'source'/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    (root/'manifest.json').write_text(json.dumps(dict(synthetic=True,network='mock only',source_sha256=source),indent=2),encoding='utf-8')
    settings=Settings(1,secrets.token_hex(32),root/'settings.json')
    settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True);settings.set(1,'vision',True)
    backend=LocalBackend();transport=Transport()
    runtime=Runtime(settings,backend,transport,VisualCache(root/'cache.sqlite3'),MediaLibrary(settings,root/'library'),ledger_path=root/'sent.sqlite3')
    cold_started=time.monotonic();await backend.ready();startup_seconds=round(time.monotonic()-cold_started,1)
    ticks=0;running=True;max_gap=0
    async def heartbeat():
        nonlocal ticks,max_gap
        previous=time.monotonic()
        while running:
            current=time.monotonic();max_gap=max(max_gap,current-previous);previous=current
            ticks+=1;await asyncio.sleep(.05)
    heartbeat_task=asyncio.create_task(heartbeat());started=time.monotonic()
    image=Path('local_data/discord-integration-20261019/gpu-smoke-2/static.png').read_bytes()
    async def local_download(url):return image
    try:
        event=Event(100,2,3,4,'<@999> 이미지의 왼쪽 도형과 오른쪽 도형 색깔을 간단히 알려줘.',datetime.now(timezone.utc),assets=(('attachment:synthetic','https://cdn.discordapp.com/attachments/1/synthetic.png'),))
        with patch('echomate_bot.runtime.download',local_download):
            await runtime.ingest(event)
            await asyncio.gather(*list(runtime.tasks.values()))
        summary=dict(status='finished' if transport.results else 'failed_closed',seconds=round(time.monotonic()-started,1),
            startup_seconds=startup_seconds,heartbeat_ticks=ticks,max_heartbeat_gap_seconds=round(max_gap,3),actions=transport.results,metrics=backend.metrics,diagnostics=runtime.diagnostics,
            real_discord=False,processor=getattr(backend,'processor_origin','not loaded'))
        (root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Synthetic-event GPU pipeline:',summary['status'],'actions',len(transport.results),flush=True)
    finally:
        running=False;await heartbeat_task;await runtime.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    from echomate_bot.settings import private_path
    asyncio.run(run(private_path(parser.parse_args().output)))
