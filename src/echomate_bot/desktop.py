"""Native local owner console. Tk stays on main thread, Discord/GPU on workers.

The signed bootstrap and its Windows ACL are the local authorization boundary.
This does not expose an HTTP server or accept remote GUI control requests.
"""
from __future__ import annotations
import asyncio
import json
import logging
import queue
import threading
import time
from pathlib import Path
import tkinter as tk

from .settings import ROOT,Settings,MOODS,ACTIVITY

STAGES={'assessment':'참여·대화 지속 판단','continuity':'대화 지속 판단','visual':'이미지 분석',
        'action':'행동 선택','text':'답변 작성','sending':'Discord 전송'}
MODES={'침묵':'silent','멘션·대화 이어가기':'mention','문맥에 따라 자율 참여':'autonomous'}
ACTIVITIES={'조용함':'quiet','보통':'normal','활발함':'active','매우 활발함':'very_active'}


class LocalController:
    """Every settings mutation and client access runs on the same event loop."""
    def __init__(self):
        self.updates=queue.Queue(maxsize=8);self.loop=None;self.client=None;self.job=None
        self.phase='설정 읽는 중';self.error='';self.lease=None
        self.inventory=[]
        self.thread=threading.Thread(target=self._thread,name='echomate-discord',daemon=True)
        self.thread.start()

    def _thread(self):
        asyncio.run(self._main())

    async def _main(self):
        self.loop=asyncio.get_running_loop()
        try:
            from .instance import InstanceLease
            self.lease=InstanceLease()
            self.bootstrap=json.loads((ROOT/'bootstrap.json').read_text(encoding='utf-8'))
            self.settings=Settings(self.bootstrap['owner_id'],self.bootstrap['signing_key'])
            if not self.bootstrap['admin_guilds']:raise ValueError('No approved guild')
            self.phase='서버와 채널 목록을 불러오고 있어요'
            self._publish()
            await self.refresh_inventory()
            if not self.job or self.job.done():self.phase='정지 — 시작 버튼으로 연결'
        except Exception as exc:
            self.phase='다른 EchoMate 앱이 실행 중이야' if isinstance(exc,RuntimeError) else '로컬 설정 필요 — setup_discord_bot.ps1 확인'
            self.error=type(exc).__name__
            self.settings=None
        while True:
            self._publish()
            await asyncio.sleep(.4)

    def _publish(self):
        cfg=self.settings.get() if self.settings else None
        client=self.client
        servers=[]
        if cfg:
            guild_ids=set(self.bootstrap['admin_guilds'])
            guild_ids.update(g['id'] for g in getattr(self,'inventory',[]))
            if client and client.is_ready():guild_ids.update(g.id for g in client.guilds)
            for gid in sorted(guild_ids):
                guild=client.get_guild(gid) if client and client.is_ready() else None
                g=cfg['guilds'].get(str(gid),dict(enabled=False,channels={},threads={}))
                saved=next((g for g in getattr(self,'inventory',[]) if g['id']==gid),None)
                channels={c['id']:c for c in saved['channels']} if saved else {}
                if guild:
                    import discord
                    for c in [*guild.channels,*guild.threads]:
                        if isinstance(c,(discord.TextChannel,discord.ForumChannel,discord.Thread)):
                            label=(c.parent.name+' / ' if isinstance(c,discord.Thread) and c.parent else '')+c.name
                            channels[c.id]=dict(id=c.id,label=label,thread=isinstance(c,discord.Thread))
                for table in ('channels','threads'):
                    for cid in g[table]:channels.setdefault(int(cid),dict(id=int(cid),label='등록된 '+('스레드' if table=='threads' else '채널'),thread=table=='threads'))
                servers.append(dict(id=gid,label=guild.name if guild else saved['label'] if saved else '등록된 테스트 서버',enabled=g['enabled'],channels=list(channels.values())))
        runtime=client.runtime if client else None
        progress=[]
        if runtime:
            for cid,p in list(runtime.progress.items()):
                channel=client.get_channel(cid)
                progress.append(dict(channel=channel.name if channel else '허용된 채널',stage=STAGES.get(p['stage'],p['stage']),seconds=round(time.time()-p['started'],1)))
        snapshot=dict(phase=self.phase,error=self.error,notice=getattr(self,'notice',''),cfg=cfg,servers=servers,progress=progress,
                      running=bool(self.job and not self.job.done()),
                      connected=bool(client and client.is_ready()),pending=client.backend.pending if client else 0,
                      contexts=len(runtime.states) if runtime else 0,safe_stopped=runtime.stopped if runtime else False,
                      latency=runtime.latencies[-1] if runtime and runtime.latencies else None,
                      gpu_seconds=client.backend.metrics[-1]['seconds'] if client and client.backend.metrics else None)
        if self.updates.full():
            try:self.updates.get_nowait()
            except queue.Empty:pass
        self.updates.put_nowait(snapshot)
        if getattr(self,'lease',None) and time.monotonic()-getattr(self,'_published_at',0)>2:
            from .settings import atomic_private_json
            try:
                atomic_private_json(ROOT/'desktop-status.json',dict(updated=time.time(),phase=self.phase,error=self.error,
                    connected=snapshot['connected'],pending=snapshot['pending'],safe_stopped=snapshot['safe_stopped'],
                    stages=[dict(stage=p['stage'],seconds=p['seconds']) for p in progress],latencies=runtime.latencies if runtime else []))
            except OSError:self.error='StatusWriteError'
            self._published_at=time.monotonic()

    def submit(self,operation,**kwargs):
        if self.loop:asyncio.run_coroutine_threadsafe(self.command(operation,**kwargs),self.loop)

    def known_guild(self,gid):
        return gid in self.bootstrap['admin_guilds'] or any(g['id']==gid for g in getattr(self,'inventory',[])) or bool(self.client and self.client.is_ready() and self.client.get_guild(gid))

    async def refresh_inventory(self):
        """Metadata-only REST, available without loading the model or sending messages."""
        if getattr(self,'refreshing',False):return
        self.refreshing=True
        import discord
        logging.getLogger('discord').setLevel(logging.CRITICAL)
        reader=discord.Client(intents=discord.Intents.none())
        try:
            await reader.login(self.bootstrap['token'])
            inventory=[]
            async for guild in reader.fetch_guilds(limit=200):
                channels=await guild.fetch_channels();parents={c.id:c.name for c in channels}
                entries=[dict(id=c.id,label=c.name,thread=False) for c in channels if isinstance(c,(discord.TextChannel,discord.ForumChannel))]
                entries.extend(dict(id=t.id,label=parents.get(t.parent_id,'')+' / '+t.name,thread=True) for t in await guild.active_threads())
                inventory.append(dict(id=guild.id,label=guild.name,channels=entries))
            self.inventory=inventory
        except Exception as exc:self.error='목록 갱신 실패 · '+type(exc).__name__
        finally:
            await reader.close();self.refreshing=False

    async def command(self,operation,**kwargs):
        try:
            if not self.settings:raise ValueError('Setup required')
            owner=self.bootstrap['owner_id'];self.settings.authorize(owner)
            self.error=''
            if operation=='refresh':await self.refresh_inventory()
            elif operation=='start':
                self.settings.set(owner,'enabled',True)
                if self.job and not self.job.done():return
                self.job=asyncio.create_task(self._run_bot())
            elif operation=='stop':
                self.settings.set(owner,'enabled',False)
                self.phase='종료·GPU 정리 중'
                if self.job and not self.job.done():
                    self.job.cancel()
                    await asyncio.gather(self.job,return_exceptions=True)
                self.phase='정지'
            elif operation=='settings':
                values=kwargs['values']
                allowed={'enabled','text','reactions','vision','stickers','mood','warmth','cuteness','playfulness','activity','cooldown','engagement_seconds','model'}
                if set(values)-allowed:raise ValueError('Unknown GUI setting')
                self.settings.change(owner,lambda cfg:cfg.update(values))
                if self.client:
                    self.client.runtime.cancel_pending()
            elif operation=='guild':
                gid=kwargs['guild']
                if not self.known_guild(gid):raise PermissionError('Guild is not connected')
                def toggle(cfg):
                    g=cfg['guilds'].setdefault(str(gid),dict(enabled=False,channels={},threads={}))
                    g['enabled']=not g['enabled']
                self.settings.change(owner,toggle)
                if self.client:self.client.runtime.invalidate_all()
            elif operation=='scope':
                gid=kwargs['guild'];cid=kwargs['channel']
                if not self.known_guild(gid):raise PermissionError('Guild is not connected')
                self.settings.set_activity_scope(owner,gid,cid,kwargs['text_mode'],kwargs['reaction_mode'],thread=kwargs['thread'],inherit=kwargs['inherit'])
                self.settings.change(owner,lambda cfg:cfg['guilds'][str(gid)].update(enabled=kwargs['enabled']))
                if self.client:
                    self.client.runtime.invalidate(cid)
                    guild=self.client.get_guild(gid)
                    if guild:
                        for thread in guild.threads:
                            if thread.parent_id==cid:self.client.runtime.invalidate(thread.id)
            else:raise ValueError('Unknown operation')
            if operation in {'settings','scope','guild'}:self.notice='설정 저장 완료'
        except Exception as exc:self.error=type(exc).__name__
        self._publish()

    async def _run_bot(self):
        try:
            self.phase='모델 준비 중 — 첫 연결은 약 40초'
            from .inference import LocalBackend
            from .discord_app import EchoClient
            logging.getLogger('discord').setLevel(logging.CRITICAL)
            self.client=EchoClient(self.settings,LocalBackend(),self.bootstrap['admin_guilds'])
            await self.client.backend.ready()
            self.phase='Discord 연결 중'
            task=asyncio.create_task(self.client.start(self.bootstrap['token'],reconnect=True))
            try:
                while not task.done():
                    self.phase='연결됨' if self.client.is_ready() else '연결·재연결 중'
                    await asyncio.sleep(.4)
                await task
            finally:
                task.cancel();await asyncio.gather(task,return_exceptions=True)
        except asyncio.CancelledError:raise
        except Exception as exc:self.error=type(exc).__name__
        finally:
            if self.client:
                from .settings import atomic_private_json
                atomic_private_json(ROOT/'desktop-performance.json',self.client.backend.metrics)
                await self.client.close()
                self.client=None
            self.phase='정지'
            self._published_at=0;self._publish()


from .desktop_ui import DesktopApp


def main():
    import argparse
    import sys
    # pythonw has no standard streams. Keep library progress/errors private.
    ROOT.mkdir(parents=True,exist_ok=True)
    if sys.stderr is None:sys.stderr=(ROOT/'desktop-console.log').open('a',encoding='utf-8')
    if sys.stdout is None:sys.stdout=sys.stderr
    parser=argparse.ArgumentParser();parser.add_argument('--start',action='store_true');args=parser.parse_args()
    root=tk.Tk();controller=LocalController();DesktopApp(root,controller)
    if args.start:
        def start_when_ready():
            if controller.loop and getattr(controller,'settings',None):controller.submit('start')
            else:root.after(400,start_when_ready)
        root.after(400,start_when_ready)
    root.mainloop()


if __name__=='__main__':main()
