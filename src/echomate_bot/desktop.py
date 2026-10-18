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
from tkinter import ttk,messagebox

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
            self.phase='정지 — 시작 버튼으로 연결'
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
            for gid in self.bootstrap['admin_guilds']:
                guild=client.get_guild(gid) if client and client.is_ready() else None
                g=cfg['guilds'].get(str(gid),dict(enabled=False,channels={},threads={}))
                channels={}
                if guild:
                    import discord
                    for c in [*guild.channels,*guild.threads]:
                        if isinstance(c,(discord.TextChannel,discord.ForumChannel,discord.Thread)):
                            channels[c.id]=dict(id=c.id,label=c.name,thread=isinstance(c,discord.Thread))
                for table in ('channels','threads'):
                    for cid in g[table]:channels.setdefault(int(cid),dict(id=int(cid),label='등록된 '+('스레드' if table=='threads' else '채널'),thread=table=='threads'))
                servers.append(dict(id=gid,label=guild.name if guild else '등록된 테스트 서버',enabled=g['enabled'],channels=list(channels.values())))
        runtime=client.runtime if client else None
        progress=[]
        if runtime:
            for cid,p in list(runtime.progress.items()):
                channel=client.get_channel(cid)
                progress.append(dict(channel=channel.name if channel else '허용된 채널',stage=STAGES.get(p['stage'],p['stage']),seconds=round(time.time()-p['started'],1)))
        snapshot=dict(phase=self.phase,error=self.error,notice=getattr(self,'notice',''),cfg=cfg,servers=servers,progress=progress,
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

    async def command(self,operation,**kwargs):
        try:
            if not self.settings:raise ValueError('Setup required')
            owner=self.bootstrap['owner_id'];self.settings.authorize(owner)
            self.error=''
            if operation=='start':
                if self.job and not self.job.done():return
                self.job=asyncio.create_task(self._run_bot())
            elif operation=='stop':
                self.phase='종료·GPU 정리 중'
                if self.job and not self.job.done():
                    self.job.cancel()
                    await asyncio.gather(self.job,return_exceptions=True)
                self.phase='정지'
            elif operation=='settings':
                values=kwargs['values']
                allowed={'enabled','text','reactions','vision','media','stickers','mood','warmth','cuteness','playfulness','activity','cooldown','engagement_seconds','model'}
                if set(values)-allowed:raise ValueError('Unknown GUI setting')
                self.settings.change(owner,lambda cfg:cfg.update(values))
                if self.client:
                    if not values.get('enabled',self.settings.get()['enabled']):self.client.runtime.invalidate_all()
                    else:self.client.runtime.cancel_pending()
            elif operation=='scope':
                gid=kwargs['guild'];cid=kwargs['channel']
                if gid not in self.bootstrap['admin_guilds']:raise PermissionError('Guild not approved locally')
                self.settings.set_activity_scope(owner,gid,cid,kwargs['text_mode'],kwargs['reaction_mode'],thread=kwargs['thread'],inherit=kwargs['inherit'])
                self.settings.change(owner,lambda cfg:cfg['guilds'][str(gid)].update(enabled=kwargs['enabled']))
                if self.client:
                    self.client.runtime.invalidate(cid)
                    guild=self.client.get_guild(gid)
                    if guild:
                        for thread in guild.threads:
                            if thread.parent_id==cid:self.client.runtime.invalidate(thread.id)
            else:raise ValueError('Unknown operation')
            if operation in {'settings','scope'}:self.notice='설정 저장 완료'
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


class DesktopApp:
    def __init__(self,root,controller):
        self.root=root;self.controller=controller;self.snapshot=None;self.servers={};self.channels={};self.loaded=False
        root.title('EchoMate · 로컬 관리');root.geometry('850x760');root.minsize(730,690)
        style=ttk.Style();style.theme_use('vista' if 'vista' in style.theme_names() else 'clam')
        self.status=tk.StringVar(value='시작 준비 중');self.detail=tk.StringVar()
        top=ttk.Frame(root,padding=16);top.pack(fill='both',expand=True)
        ttk.Label(top,text='EchoMate',font=('맑은 고딕',19,'bold')).pack(anchor='w')
        ttk.Label(top,textvariable=self.status,font=('맑은 고딕',11)).pack(anchor='w',pady=5)
        bar=ttk.Frame(top);bar.pack(fill='x',pady=6)
        ttk.Button(bar,text='봇 시작',command=lambda:controller.submit('start')).pack(side='left')
        ttk.Button(bar,text='봇 종료',command=lambda:controller.submit('stop')).pack(side='left',padx=8)
        ttk.Label(bar,textvariable=self.detail).pack(side='left',padx=8)
        tabs=ttk.Notebook(top);tabs.pack(fill='both',expand=True,pady=8)
        settings=ttk.Frame(tabs,padding=14);scopes=ttk.Frame(tabs,padding=14);processing=ttk.Frame(tabs,padding=14)
        tabs.add(settings,text='캐릭터·활동');tabs.add(scopes,text='채팅·이모지 활동 범위');tabs.add(processing,text='처리 상태')
        self.vars={}
        flags=ttk.Frame(settings);flags.grid(row=0,column=0,columnspan=2,sticky='w',pady=8)
        for key,label in [('enabled','활동 활성화'),('text','텍스트'),('reactions','이모지 반응'),('vision','이미지 인식'),('media','등록 미디어'),('stickers','스티커')]:
            self.vars[key]=tk.BooleanVar();ttk.Checkbutton(flags,text=label,variable=self.vars[key]).pack(side='left',padx=3)
        fields=[('mood','기분',sorted(MOODS)),('activity','활동 빈도',list(ACTIVITIES)),('model','모델',['persona','base']),
                ('warmth','다정함 0~100',None),('cuteness','귀여움 0~100',None),('playfulness','장난기 0~100',None),
                ('cooldown','새 대화 참여 간격 (초)',None),('engagement_seconds','대화 유지 시간 (초)',None)]
        for row,(key,label,choices) in enumerate(fields,1):
            ttk.Label(settings,text=label).grid(row=row,column=0,sticky='w',pady=7)
            self.vars[key]=tk.StringVar()
            widget=ttk.Combobox(settings,textvariable=self.vars[key],values=choices,state='readonly',width=25) if choices else ttk.Entry(settings,textvariable=self.vars[key],width=27)
            widget.grid(row=row,column=1,sticky='w',padx=16)
        ttk.Button(settings,text='캐릭터·활동 설정 저장',command=self.save_settings).grid(row=9,column=0,columnspan=2,sticky='w',pady=12)
        ttk.Button(settings,text='저장된 값 다시 읽기',command=self.reload_settings).grid(row=10,column=0,columnspan=2,sticky='w')
        ttk.Label(settings,text='멘션·이어가는 대화는 신규 참여 확률과 별도로 판단해.\n기분·활동 설정 변경은 대화 기록을 유지해. 이미지 분석은 텍스트보다 오래 걸릴 수 있어.',wraplength=700).grid(row=11,column=0,columnspan=2,sticky='w',pady=15)
        self.guild_var=tk.StringVar();self.channel_var=tk.StringVar();self.text_mode=tk.StringVar();self.react_mode=tk.StringVar()
        self.guild_enabled=tk.BooleanVar();self.inherit=tk.BooleanVar()
        self.guild_box=ttk.Combobox(scopes,textvariable=self.guild_var,state='readonly',width=68)
        self.channel_box=ttk.Combobox(scopes,textvariable=self.channel_var,state='readonly',width=68)
        for row,(label,widget) in enumerate([('서버',self.guild_box),('채널·스레드',self.channel_box),
            ('채팅 활동',ttk.Combobox(scopes,textvariable=self.text_mode,values=list(MODES),state='readonly',width=36)),
            ('이모지 활동',ttk.Combobox(scopes,textvariable=self.react_mode,values=list(MODES),state='readonly',width=36))]):
            ttk.Label(scopes,text=label).grid(row=row*2,column=0,sticky='w',pady=(9,3));widget.grid(row=row*2+1,column=0,sticky='w')
        self.guild_box.bind('<<ComboboxSelected>>',lambda e:self.update_channels())
        self.channel_box.bind('<<ComboboxSelected>>',lambda e:self.load_scope())
        ttk.Checkbutton(scopes,text='이 서버 활동 허용',variable=self.guild_enabled).grid(row=8,column=0,sticky='w',pady=10)
        ttk.Checkbutton(scopes,text='상위 채널 규칙을 하위 스레드에 상속',variable=self.inherit).grid(row=9,column=0,sticky='w')
        ttk.Button(scopes,text='선택한 활동 범위 저장',command=self.save_scope).grid(row=10,column=0,sticky='w',pady=15)
        ttk.Label(scopes,text='목록은 연결 후 갱신돼. 채팅과 이모지를 서로 다르게 설정할 수 있어.\n자율 참여를 허용하면 멘션 없이도 문맥에 따라 참여해.\n이미 참여한 대화는 멘션 전용에서도 문맥에 맞으면 이어가.\n등록된 테스트 서버만 표시하며, 나머지는 기본 차단해.',wraplength=700).grid(row=11,column=0,sticky='w',pady=10)
        self.tree=ttk.Treeview(processing,columns=('channel','stage','seconds'),show='headings',height=13)
        for key,label,width in [('channel','채널',200),('stage','처리 단계',280),('seconds','경과(초)',120)]:self.tree.heading(key,text=label);self.tree.column(key,width=width)
        self.tree.pack(fill='both',expand=True)
        self.result=tk.StringVar();ttk.Label(processing,textvariable=self.result,wraplength=700).pack(anchor='w',pady=16)
        ttk.Label(processing,text='대기 작업은 같은 GPU에서 순차 처리해. 새 메시지가 오면 오래된 답변을 취소해.\n대화 본문·토큰은 이 상태 화면에 표시하지 않아.').pack(anchor='w')
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(200,self.poll)

    def reload_settings(self):
        if not self.snapshot or not self.snapshot['cfg']:return
        cfg=self.snapshot['cfg']
        for key,var in self.vars.items():
            value=cfg[key]
            if key=='activity':value=next(k for k,v in ACTIVITIES.items() if v==value)
            var.set(value)
        self.loaded=True

    def save_settings(self):
        try:
            values={k:v.get() for k,v in self.vars.items()}
            values['activity']=ACTIVITIES[values['activity']]
            for key in ('warmth','cuteness','playfulness','cooldown','engagement_seconds'):values[key]=int(values[key])
            self.controller.submit('settings',values=values)
        except (ValueError,KeyError):messagebox.showerror('입력 확인','숫자와 선택값을 확인해 줘.')

    def update_channels(self):
        server=self.servers.get(self.guild_var.get())
        if not server:return
        self.channels={(('스레드 · ' if c['thread'] else '# ')+c['label']+' · '+str(c['id'])):c for c in server['channels']}
        self.channel_box['values']=list(self.channels)
        if self.channel_var.get() not in self.channels:self.channel_var.set(next(iter(self.channels),''))
        self.load_scope()

    def load_scope(self):
        if not self.snapshot or not self.snapshot['cfg']:return
        server=self.servers.get(self.guild_var.get());channel=self.channels.get(self.channel_var.get())
        if not server or not channel:return
        g=self.snapshot['cfg']['guilds'].get(str(server['id']),dict(enabled=False,channels={},threads={}))
        rule=g['threads' if channel['thread'] else 'channels'].get(str(channel['id']),dict(mode='silent',inherit=False))
        reverse={v:k for k,v in MODES.items()}
        self.text_mode.set(reverse.get(rule['mode'],'침묵'))
        self.react_mode.set(reverse.get(rule.get('reaction_mode',rule['mode']),'문맥에 따라 자율 참여' if rule['mode']=='reaction' else '침묵'))
        self.inherit.set(rule['inherit']);self.guild_enabled.set(g['enabled'])

    def save_scope(self):
        server=self.servers.get(self.guild_var.get());channel=self.channels.get(self.channel_var.get())
        if not server or not channel:return
        self.controller.submit('scope',guild=server['id'],channel=channel['id'],thread=channel['thread'],
            text_mode=MODES[self.text_mode.get()],reaction_mode=MODES[self.react_mode.get()],enabled=self.guild_enabled.get(),inherit=False if channel['thread'] else self.inherit.get())

    def poll(self):
        try:
            while True:self.snapshot=self.controller.updates.get_nowait()
        except queue.Empty:pass
        s=self.snapshot
        if s:
            self.status.set(s['phase']+(' · 안전 중단' if s['safe_stopped'] else '')+(' · 오류 '+s['error'] if s['error'] else ''))
            self.detail.set(f"활동 {'켜짐' if s['cfg'] and s['cfg']['enabled'] else '꺼짐'} · GPU 작업 {s['pending']} · 유지 채널 {s['contexts']} · {s.get('notice','')}")
            if not self.loaded:self.reload_settings()
            new={g['label']+' · '+str(g['id']):g for g in s['servers']}
            if new!=self.servers:
                self.servers=new;self.guild_box['values']=list(new)
                if self.guild_var.get() not in new:self.guild_var.set(next(iter(new),''))
                self.update_channels()
            for item in self.tree.get_children():self.tree.delete(item)
            for p in s['progress']:self.tree.insert('',tk.END,values=(p['channel'],p['stage'],p['seconds']))
            self.result.set(f"최근 전체 응답 시간: {s['latency'] if s['latency'] is not None else '아직 없음'}초\n최근 GPU 생성: {s['gpu_seconds'] if s['gpu_seconds'] is not None else '아직 없음'}초")
        self.root.after(400,self.poll)

    def close(self):
        self.controller.submit('stop');self.status.set('안전하게 종료 중…')
        def wait():
            if self.controller.client is None and (self.controller.job is None or self.controller.job.done()):self.root.destroy()
            else:self.root.after(200,wait)
        self.root.after(200,wait)


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
