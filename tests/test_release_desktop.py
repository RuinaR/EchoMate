"""Offline records, actual controller, isolated Tk events; no desktop automation."""
import asyncio
from copy import deepcopy
from datetime import datetime,timezone
import gc
import json
from pathlib import Path
import queue
import secrets
import tempfile
import threading
from types import SimpleNamespace
import tkinter as tk
import unittest
from unittest.mock import AsyncMock,Mock,patch
from echomate_bot.desktop import LocalController
from echomate_bot.desktop_ui import DesktopApp
from echomate_bot.settings import Settings,DEFAULTS
from echomate_bot.companion_store import CompanionStore
from echomate_bot.runtime import Event,Ledger

class OfflineRecords(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='local_data');self.root=Path(self.temp.name)
        c=self.c=LocalController.__new__(LocalController)
        c.settings=Settings(1,secrets.token_hex(32),self.root/'settings.json');c.settings.set_scope(1,2,3,'mention')
        c.bootstrap=dict(owner_id=1,admin_guilds=[2],signing_key=c.settings._key.decode(),token='synthetic-not-a-token')
        c.client=None;c.job=None;c.phase='정지';c.error='';c.updates=queue.Queue(maxsize=8);c.inventory=[];c.record_guilds=[2]
        c.companion=CompanionStore(self.root/'companion.sqlite3');c.companion_view={}
    def tearDown(self):self.temp.cleanup()
    async def test_offline_memory_alias_reminder_and_consent_visible(self):
        c=self.c;c.companion.add_memory(2,4,3,'나는 퍼즐을 좋아해');c.companion.set_alias(2,3,4,'구름')
        e=Event(100,2,3,4,'1분 뒤 알림',datetime.now(timezone.utc));c.companion.reserve_reminder(e,e.timestamp.timestamp()+60,'Asia/Seoul','테스트')
        with patch('discord.Client.login',side_effect=AssertionError('Network forbidden')):
            await c.command('companion',action='refresh',guild=2,user='4')
        self.assertFalse(c.error);v=c.companion_view
        self.assertEqual((len(v['memories']),len(v['aliases']),len(v['reminders'])),(1,1,1))
        self.assertFalse(v['people'][0]['consent']['relationships']);self.assertFalse(c.companion_loading)
        await c.command('companion',action='affinity',guild=2,user='4',value=55)
        self.assertIn('동의',c.error)
        c.companion.set_consent(2,4,'relationships',True)
        await c.command('companion',action='affinity',guild=2,user='4',value=55)
        self.assertEqual(c.companion_view['people'][0]['affinity'],55)
    async def test_stale_read_does_not_overwrite_new_user_selection(self):
        c=self.c;original=c.companion.memories;started=threading.Event();release=threading.Event()
        def slow(guild,user=None,*a,**kw):
            if user==4:started.set();release.wait(2)
            return original(guild,user,*a,**kw)
        with patch.object(c.companion,'memories',side_effect=slow):
            old=asyncio.create_task(c.refresh_companion(2,4))
            await asyncio.to_thread(started.wait,1)
            await c.refresh_companion(2,5);release.set();await old
        self.assertEqual(c.companion_view['user'],5);self.assertFalse(c.companion_loading)
    async def test_initial_app_load_is_local_without_discord_login(self):
        c=self.c;(self.root/'bootstrap.json').write_text(json.dumps(c.bootstrap),encoding='utf-8')
        c.phase='starting'
        with patch('echomate_bot.desktop.ROOT',self.root),patch('echomate_bot.instance.InstanceLease',return_value=Mock()),patch('discord.Client.login',side_effect=AssertionError('Network forbidden')) as login:
            task=asyncio.create_task(c._main())
            try:
                for _ in range(50):
                    if c.phase.startswith('정지') and getattr(c,'loop',None) is not None:break
                    await asyncio.sleep(.02)
                login.assert_not_called();self.assertIsNotNone(c.settings);self.assertTrue(c.phase.startswith('정지'))
            finally:task.cancel();await asyncio.gather(task,return_exceptions=True)
    async def test_statistics_are_read_only_visible_offline_and_command_approval_is_deferred(self):
        e=Event(100,2,3,4,'합성',datetime.now(timezone.utc));ledger=Ledger(self.root/'sent.sqlite3');ledger.reserve(e,0);ledger.completed(e,'sent')
        self.c._publish();snapshot=self.c.updates.get_nowait();self.assertEqual(snapshot['statistics']['responses_today'],1)
        with patch('discord.Client.login',side_effect=AssertionError('Network forbidden')):
            await self.c.command('settings',values=dict(command_sync_pending=True))
        self.assertTrue(self.c.settings.get()['command_sync_pending']);self.assertEqual(ledger.statistics()['successful'],1)

class ReleaseTk(unittest.TestCase):
    def test_status_selection_scroll_and_output_controls_all_dpi(self):
        for scaling in (4/3,5/3,2):
            root=tk.Tk();root.withdraw();root.tk.call('tk','scaling',scaling)
            controller=SimpleNamespace(updates=queue.Queue(),submit=Mock());app=DesktopApp(root,controller)
            try:
                cfg=deepcopy(DEFAULTS);cfg['guilds']={'2':dict(enabled=True,channels={'3':dict(mode='mention',inherit=False)},threads={})}
                job=dict(id='100',status='sent',stage='sending',seconds=2,flow='synthetic',source_attached=True,stages={'text':1.2},codes=['response_sent'])
                app.snapshot=dict(cfg=cfg,phase='정지',error='',connected=False,running=False,servers=[dict(id=2,label='합성 서버',enabled=True,channels=[])],pending=0,contexts=1,latency=2,progress=[],jobs=[job],budget=dict(used=100,limit=100),scheduler={})
                app.guild_id=2;app.page='status';app.job_id='100';app.render();root.update_idletasks()
                self.assertEqual(app.job_list.selected,{'100'})
                app.snapshot['jobs']=[dict(job,id='101'),job];app.render();self.assertEqual(app.job_list.selected,{'100'})
                app.page='outputs';app.render();root.update_idletasks()
                text=' '.join(app.canvas.itemcget(x,'text') for x in app.canvas.find_all() if app.canvas.type(x)=='text')
                self.assertNotIn('스티커',text)
                app.click(SimpleNamespace(x=260,y=490));self.assertEqual(controller.submit.call_args.kwargs['values'],dict(web_search=True))
                app.form=Mock()
                app.approve_commands();app.form.call_args.args[2](dict(confirm='동의로 교체'))
                self.assertEqual(controller.submit.call_args.kwargs['values'],dict(command_sync_pending=True))
                self.assertTrue(all(y+height<=740 or root.winfo_height()>740 for x,y,width,height,cb in app.hits))
                digest=dict(id='digest-test',channel='3',body=dict(items=[dict(kind='correction',text='금요일 모임으로 변경했다',source='111')]),updated=1000,expires=9999999999,usable=True)
                app.page='memories';app.record_kind='summary';app.record_user='4';app.snapshot['companion']=dict(guild=2,user='4',people=[dict(user='4',consent=dict(summaries=True),affinity=50,interactions=0,last_at=0)],digests=[digest],memories=[])
                app.render();root.update_idletasks();self.assertEqual(app.record_list.items[0]['id'],'digest:digest-test')
                app.record_key='digest:digest-test';app.form=Mock();app.show_digest();self.assertIn('출처',app.form.call_args.args[1][0][1])
                app.remove_record();app.form.call_args.args[2](dict(confirm='삭제'))
                self.assertEqual(controller.submit.call_args.kwargs['action'],'summary_delete');self.assertEqual(controller.submit.call_args.kwargs['key'],'digest-test')
                entries=[dict(id=str(i),label=str(i),hint='긴 설명 '*20) for i in range(30)]
                app.job_list.set_items(entries);app.job_list.offset=10
                app.job_list.set_items([dict(id='new',label='new',hint=''),*entries]);self.assertEqual(app.job_list.items[app.job_list.offset]['id'],'10')
            finally:app.destroy();app=None;root=None;gc.collect()
