"""Owned Tk events -> actual Controller -> temporary signed settings/SQLite.

Native file dialogs and GPU/network preparation are injected boundaries, not
certified Windows/Discord interactions. No operating installation is opened.
"""
import asyncio
from copy import deepcopy
import gc
import queue
import re
import time
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
import unittest
from unittest.mock import AsyncMock,patch

import test_release_desktop as fixtures
from test_dialog_layout import invoke
from echomate_bot.desktop_ui import DesktopApp
from echomate_bot.character_profiles import DEFAULT_PROFILE,ProfileStore


class UIWorkflows(unittest.IsolatedAsyncioTestCase):
    async def test_departed_guild_hidden_from_joined_list_but_local_records_preserved(self):
        self.c.settings.set_scope(1,9,90,'mention')
        self.c.bootstrap['admin_guilds'].append(9)
        self.c.record_guilds.append(9)
        await self.sync()
        self.assertEqual([s['id'] for s in self.app.server_list.items],[2])
        self.assertIn(9,[s['id'] for s in self.app.snapshot['servers']])
        self.assertIn('9',self.c.settings.get()['guilds'])
        # A known departure also overrides stale cached membership.
        self.app.snapshot['servers'][0]['joined']=False
        self.app.refresh_lists()
        self.assertFalse(self.app.server_list.items)
        self.assertIsNone(self.app.guild_id)
        self.assertFalse(self.app.channel_ids)

    async def asyncSetUp(self):
        self.fixture=fixtures.OfflineRecords();self.fixture.setUp();self.c=self.fixture.c
        self.patch=patch('echomate_bot.desktop.ROOT',self.fixture.root);self.patch.start()
        self.network=patch('aiohttp.ClientSession._request',new=AsyncMock(side_effect=AssertionError('Network forbidden in UI test')));self.outbound=self.network.start()
        self.c.models=[];self.c.notice='';self.c.profiles_view={'default':dict(DEFAULT_PROFILE)}
        self.c.inventory=[dict(id=2,label='Synthetic guild',channels=[dict(id=3,label='text',thread=False),dict(id=7,label='thread',thread=True,parent=3)])]
        self.tasks=[];self.commands=[]
        def submit(op,**values):
            self.commands.append((op,deepcopy(values)))
            task=asyncio.create_task(self.c.command(op,**values));self.tasks.append(task)
            self.c.last_submission=task
            return task
        self.c.submit=submit
        self.root=tk.Tk();self.root.withdraw();self.errors=[]
        self.root.report_callback_exception=lambda kind,value,tb:self.errors.append(kind.__name__)
        self.app=DesktopApp(self.root,self.c);self.app.canvas.pack_forget()
        self.app.canvas.place(x=0,y=0,width=1180,height=820)
        self.root.update_idletasks();self.app.guild_id=2;self.app.channel_ids={3}
        await self.sync()

    async def sync(self):
        for _ in range(12):
            tasks=[t for t in self.tasks if not t.done()]
            if tasks:await asyncio.gather(*tasks)
            if not any(not t.done() for t in self.tasks):break
        self.c._publish()
        while not self.c.updates.empty():self.app.snapshot=self.c.updates.get_nowait()
        self.app.refresh_lists();self.app.render();self.root.update_idletasks()

    async def asyncTearDown(self):
        for w in self.root.winfo_children():
            if isinstance(w,tk.Toplevel):w.destroy()
        for t in self.tasks:
            if not t.done():t.cancel()
        await asyncio.gather(*self.tasks,return_exceptions=True)
        if self.c.job and not self.c.job.done():self.c.job.cancel();await asyncio.gather(self.c.job,return_exceptions=True)
        self.app.destroy();self.app=None;self.root=None;gc.collect()
        self.outbound.assert_not_awaited();self.network.stop()
        self.patch.stop();self.fixture.tearDown();self.assertFalse(self.errors)

    def dialog(self):
        return next(w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel))

    def fill(self,dialog,values):
        fields=dialog._form_values
        self.assertEqual(len(fields),len(values))
        for variable,value in zip(fields.values(),values):variable.set(str(value))
        invoke(dialog,'<Control-Return>')

    async def test_all_character_choices_numbers_and_output_toggles_reach_signed_settings(self):
        app=self.app;app.page='character';app.render()
        # Invoke the actual Canvas click dispatcher at each generated setting
        # button, then verify the command reached the signed store.
        targets=[]
        for x,y,w,h,callback in app.hits:
            if x>=240 and (y in (194,236,321) or x in (595,637) and 370<=y<=520):targets.append((x,y,w,h))
        self.assertTrue(targets)
        for x,y,w,h in targets:
            app.render();before=len(self.commands)
            app.click(SimpleNamespace(x=x+w/2,y=y+h/2))
            await self.sync()
            self.assertEqual(len(self.commands),before+1)
            op,kw=self.commands[-1];self.assertEqual(op,'settings')
            for k,v in kw['values'].items():self.assertEqual(self.c.settings.get()[k],v)
        # Every generated toggle on the output page, including the opt-in
        # command cleanup flag, is local only: no SDK sync is called.
        app.page='outputs';app.render()
        for y in (285,375,465):
            n=len(self.commands);app.click(SimpleNamespace(x=260,y=y+10));await self.sync()
            self.assertEqual(len(self.commands),n+1);self.assertEqual(self.commands[-1][0],'settings')
            for k,v in self.commands[-1][1]['values'].items():self.assertEqual(self.c.settings.get()[k],v)

    async def test_profile_edit_export_import_and_cancel_persist_exactly(self):
        app=self.app;app.page='character';app.edit_profile();d=self.dialog()
        self.fill(d,['Synthetic profile','Display only','존댓말','35','20','자세히']);await self.sync()
        self.assertFalse(self.c.error)
        cfg=self.c.settings.get();self.assertEqual(cfg['character_profile']['speech'],'polite')
        key=next(k for k in self.c.profiles_view if k!='default')
        export=self.fixture.root/'profile-export.json'
        with patch('tkinter.filedialog.asksaveasfilename',return_value=str(export)):
            app.profile_files();self.fill(self.dialog(),['내보내기']);await self.sync()
        self.assertTrue(export.is_file());self.assertNotIn('token',export.read_text(encoding='utf-8'))
        keys=set(self.c.profiles_view)
        with patch('tkinter.filedialog.askopenfilename',return_value=str(export)):
            app.profile_files();self.fill(self.dialog(),['가져오기']);await self.sync()
        self.assertEqual(len(set(self.c.profiles_view)-keys),1)
        self.assertEqual(self.c.settings.get()['character_profile'],cfg['character_profile'])
        self.assertEqual(__import__('json').loads(export.read_text(encoding='utf-8')),cfg['character_profile'])
        before=deepcopy(self.c.settings.get());n=len(self.commands)
        app.advanced_profile();invoke(self.dialog(),'<Escape>');await self.sync()
        self.assertEqual(self.c.settings.get(),before);self.assertEqual(len(self.commands),n)
        keys=set(self.c.profiles_view)
        with patch('tkinter.filedialog.askopenfilename',return_value=''):
            app.profile_files();self.fill(self.dialog(),['가져오기']);await self.sync()
        self.assertEqual(set(self.c.profiles_view),keys)

    async def test_advanced_typed_controls_persist_reopen_cancel_and_failed_write(self):
        app=self.app;app.page='character';original=deepcopy(self.c.settings.get())
        app.advanced_profile();d=self.dialog()
        self.fill(d,['80','90','15','0','짧게','가벼운 감탄만']);await self.sync()
        self.assertFalse(self.c.error);p=self.c.settings.get()['character_profile']
        self.assertEqual((p['calmness'],p['honesty'],p['emoji'],p['length'],p['swearing']),(80,90,0,'short',True))
        from echomate_bot.settings import Settings
        restored=Settings(1,self.c.bootstrap['signing_key'],self.c.settings.path).get()
        self.assertEqual(restored['character_profile'],p)
        app.advanced_profile();d=self.dialog();self.assertEqual(d._form_controls['calmness'].value(),80)
        d._form_controls['calmness'].set(0);invoke(d,'<Escape>');await self.sync()
        self.assertEqual(self.c.settings.get()['character_profile'],p)
        app.advanced_profile();d=self.dialog();d._form_controls['calmness'].set(20)
        with patch('echomate_bot.settings.atomic_private_json',side_effect=OSError('Synthetic locked write')):
            invoke(d,'<Control-Return>');await self.sync()
        self.assertTrue(d.winfo_exists());self.assertEqual(d._form_controls['calmness'].value(),20)
        self.assertEqual(self.c.settings.get()['character_profile'],p)
        self.assertEqual(self.c.settings.get()['model'],original['model'])

    async def test_memory_form_crud_and_revoked_consent_reach_actual_sqlite(self):
        app=self.app;app.page='memories';app.record_user='4'
        self.c.companion.set_consent(2,4,'memory',True)
        app.edit_record(True);self.fill(self.dialog(),['4','3','직접 기억','주말에 도예를 배우는 중','']);await self.sync()
        self.assertFalse(self.c.error);rows=self.c.companion.memories(2,4)
        self.assertEqual(len(rows),1);key=rows[0]['memory_id']
        app.record_key=key;app.edit_record();self.fill(self.dialog(),['주말에 도예 수업을 듣는 중','','사용']);await self.sync()
        self.assertEqual(self.c.companion.memories(2,4)[0]['summary'],'주말에 도예 수업을 듣는 중')
        # The popup must not silently retarget when its user changes.
        app.record_key=key;app.edit_record();d=self.dialog();app.record_user='5'
        self.fill(d,['다른 대상에게 쓰이면 안 되는 내용','','사용']);await self.sync()
        self.assertTrue(d.winfo_exists());self.assertNotEqual(self.c.companion.memories(2,4)[0]['summary'],'다른 대상에게 쓰이면 안 되는 내용');d.destroy()
        app.record_user='4';self.c.companion.set_consent(2,4,'memory',False)
        app.edit_record(True);self.fill(self.dialog(),['4','3','직접 기억','새 수업을 계획 중','']);await self.sync()
        self.assertTrue(self.c.error);self.assertEqual(len(self.c.companion.memories(2,4)),1)

    async def test_invalid_profile_write_error_and_old_record_delete_are_not_success(self):
        app=self.app;app.page='character';before=deepcopy(self.c.settings.get())
        app.edit_profile();d=self.dialog();self.fill(d,['','Display','반말','999','20','균형'])
        self.assertTrue(d.winfo_exists());self.assertEqual(self.c.settings.get(),before);d.destroy()
        with patch.object(ProfileStore,'save',side_effect=OSError('synthetic private path')):
            app.edit_profile();self.fill(self.dialog(),['Synthetic','Display','반말','30','20','균형']);await self.sync()
        self.assertEqual(self.c.error,'OSError');self.assertEqual(self.c.settings.get(),before)
        self.assertNotIn('synthetic private path',str(app.snapshot))

    async def test_summary_delete_invalid_confirmation_and_selection_change_stay_open(self):
        app=self.app;app.page='memories';app.record_user='4';app.record_key='digest:synthetic'
        n=len(self.commands);app.remove_record();d=self.dialog()
        self.fill(d,['아니오']);self.assertTrue(d.winfo_exists());self.assertEqual(len(self.commands),n)
        app.guild_id=9;self.fill(d,['삭제']);self.assertTrue(d.winfo_exists());self.assertEqual(len(self.commands),n)
        invoke(d,'<Escape>');self.assertFalse(d.winfo_exists())

    async def test_memory_delete_and_reset_confirmations_only_mutate_selected_scope(self):
        app=self.app;app.page='memories';app.record_user='4'
        store=self.c.companion;store.set_consent(2,4,'memory',True)
        key=store.add_memory(2,4,3,'주말에 도예 수업',require_consent=True)
        other=store.add_memory(2,5,3,'평일에 음악 수업')
        await self.c.refresh_companion(2,'4');await self.sync();app.record_key=key
        app.remove_record();self.fill(self.dialog(),['삭제']);await self.sync()
        self.assertFalse(store.memories(2,4));self.assertEqual(len(store.memories(2,5)),1)
        app.record_user='5';app.reset_records(False);self.fill(self.dialog(),['취소'])
        self.assertTrue(self.dialog().winfo_exists());self.assertEqual(len(store.memories(2,5)),1)
        self.fill(self.dialog(),['삭제']);await self.sync();self.assertFalse(store.memories(2,5))

    async def test_channel_and_thread_save_then_restart_configuration(self):
        app=self.app;app.page='spaces';app.channel_ids={3,7};app.text_mode='autonomous';app.react_mode='mention';app.inherit=True
        app.save_scope();await self.sync();cfg=self.c.settings.get()
        self.assertEqual(cfg['guilds']['2']['channels']['3']['mode'],'autonomous')
        self.assertTrue(cfg['guilds']['2']['channels']['3']['inherit'])
        self.assertFalse(cfg['guilds']['2']['threads']['7']['inherit'])
        from echomate_bot.settings import Settings
        restored=Settings(1,self.c.settings._key.decode(),self.fixture.root/'settings.json').get()
        self.assertEqual(restored,cfg)

    async def test_name_alias_timezone_memory_defaults_and_search(self):
        app=self.app;app.page='spaces';app.edit_name();d=self.dialog()
        self.fill(d,['']);self.assertTrue(d.winfo_exists())
        self.fill(d,['테스트봇']);await self.sync()
        self.assertEqual(self.c.settings.get()['guilds']['2']['name'],'테스트봇')
        app.server_options();self.fill(self.dialog(),['테스트,별칭','UTC','끄기']);await self.sync()
        g=self.c.settings.get()['guilds']['2'];self.assertEqual(g['timezone'],'UTC');self.assertFalse(g['partial_names'])
        app.page='memories';app.memory_defaults(self.c.settings.get());self.fill(self.dialog(),['10','20','5','켜기']);await self.sync()
        cfg=self.c.settings.get();self.assertEqual(cfg['memory_plan_grace'],600);self.assertTrue(cfg['summaries_auto'])
        app.form('기억·요약 검색',[('query','검색어',''),('kind','종류','전체')],app.search_records)
        self.fill(self.dialog(),['도예','직접 기억']);await self.sync()
        self.assertEqual(app.record_search,'도예');self.assertEqual(app.record_kind,'explicit')
        for _ in range(6):app.cycle_record_status()
        self.assertEqual(app.record_status,'전체')

    async def test_relationship_alias_and_reminder_edit_cancel_use_real_rows(self):
        app=self.app;store=self.c.companion;app.page='relations';app.record_user='4'
        store.set_consent(2,4,'relationships',True);store.set_affinity(2,4,50)
        await self.c.refresh_companion(2,'4');await self.sync()
        app.edit_record();self.fill(self.dialog(),['72']);await self.sync()
        self.assertEqual(store.users(2)[0]['affinity'],72)
        app.member_alias_editor();self.fill(self.dialog(),['3','가온','확정']);await self.sync();self.assertFalse(self.c.error)
        from echomate_bot.runtime import Event
        from datetime import datetime,timezone
        event=Event(810,2,3,4,'synthetic reminder',datetime.now(timezone.utc))
        store.reserve_reminder(event,time.time()+3600,'Asia/Seoul','도예 준비하기')
        app.page='reminders';await self.c.refresh_companion(2,'4');await self.sync()
        app.record_key=store.reminders(2,4)[0]['reminder_id'];app.edit_record();d=self.dialog()
        canvas=next(w for w in d.winfo_children() if isinstance(w,tk.Canvas))
        values=[w.get() for w in canvas.winfo_children() if isinstance(w,tk.Entry)]
        self.fill(d,[values[0],'도예 준비물 챙기기']);await self.sync()
        self.assertEqual(store.reminders(2,4)[0]['text'],'도예 준비물 챙기기')
        app.record_key=store.reminders(2,4)[0]['reminder_id'];app.remove_record();self.fill(self.dialog(),['삭제']);await self.sync()
        self.assertEqual(store.reminders(2,4)[0]['status'],'cancelled')

    async def test_profile_library_actual_apply_delete_restore_and_broken_import(self):
        app=self.app;app.page='character'
        await self.c.command('profiles',action='save',key='custom',value=dict(DEFAULT_PROFILE,name='Synthetic'))
        await self.sync();app.profile_library();d=self.dialog()
        from echomate_bot.desktop_ui import SelectionList
        listing=next(w for w in d.winfo_children()[0].winfo_children() if isinstance(w,SelectionList))
        listing.callback({'custom'});listing.selected={'custom'}
        canvas=d.winfo_children()[0]
        command=re.search(r'\[([^ ]+) ',canvas.bind('<Button-1>'))[1]
        def click(x):
            for sequence,kind in (('<Button-1>','4'),('<ButtonRelease-1>','5')):
                for binding in re.findall(r'\[([^ ]+) ',canvas.bind(sequence)):
                    canvas.tk.call(binding,'0','1','0','0','0','0','0','0',str(x),'380','','0','','0',str(canvas),kind,'0','0','0')
        click(80);await self.sync();self.assertEqual(self.c.settings.get()['character_profile']['name'],'Synthetic')
        app.profile_library();d=self.dialog();canvas=d.winfo_children()[0]
        listing=next(w for w in canvas.winfo_children() if isinstance(w,SelectionList));listing.callback({'custom'})
        command=re.search(r'\[([^ ]+) ',canvas.bind('<Button-1>'))[1];click(220)
        confirmation=next(w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel) and w is not d)
        self.fill(confirmation,['아니오']);await self.sync();self.assertIn('custom',self.c.profiles_view)
        self.fill(confirmation,['삭제']);await self.sync();self.assertNotIn('custom',self.c.profiles_view)
        invoke(d,'<Escape>');await self.sync()
        app.profile_library();d=self.dialog();canvas=d.winfo_children()[0]
        command=re.search(r'\[([^ ]+) ',canvas.bind('<Button-1>'))[1];click(400);await self.sync()
        self.assertEqual(self.c.settings.get()['character_profile'],DEFAULT_PROFILE)
        broken=self.fixture.root/'broken.json';broken.write_text('{',encoding='utf-8')
        with patch('tkinter.filedialog.askopenfilename',return_value=str(broken)):
            app.profile_files();self.fill(self.dialog(),['가져오기']);await self.sync()
        self.assertTrue(self.c.error);self.assertNotIn('bad',self.c.profiles_view)

    async def test_scope_selection_cancel_file_picker_and_command_approval_do_not_connect(self):
        app=self.app;app.page='models';n=len(self.commands)
        with patch('tkinter.filedialog.askdirectory',return_value=''):app.choose_model_folder()
        self.assertEqual(len(self.commands),n)
        app.page='outputs';app.approve_commands();await self.sync()
        self.assertEqual(self.commands[-1][0],'command_review')
        self.assertFalse(self.c.settings.get()['command_sync_pending'])
        self.c.command_review=dict(application='42',global_before=[dict(id='1',name='old',type=1)],guilds={'2':[]},fingerprint='synthetic')
        await self.sync();app.approve_commands();d=self.dialog();self.fill(d,['아니오'])
        self.assertTrue(d.winfo_exists());self.assertFalse(self.c.settings.get()['command_sync_pending'])
        self.fill(d,['동의로 교체']);await self.sync();self.assertFalse(self.c.settings.get()['command_sync_pending'])
        self.assertEqual(self.commands[-1][0],'command_apply')
        self.assertTrue(d.winfo_exists())
        self.assertIsNone(self.c.client)

    async def test_command_read_and_change_are_separate_release_actions(self):
        app=self.app;app.page='outputs';app.render()
        query=next(region for region in app.feedback.regions if region['box'][0]==250 and region['box'][1]==615)
        # The fixture is 1180x820; this is the real row, not a direct callback.
        before=len(self.commands);event=SimpleNamespace(x=260,y=625)
        app.press(event);self.assertEqual(len(self.commands),before)
        app.feedback.release(event);await self.sync()
        self.assertEqual(self.commands[-1][0],'command_review')
        self.assertFalse(self.c.settings.get()['command_sync_pending'])
        self.assertFalse(any(x==446 and y==615 for x,y,w,h,cb in app.hits))
        self.c.command_review=dict(application='42',global_before=[],guilds={'2':[]},fingerprint='synthetic')
        await self.sync();self.assertTrue(any(x==446 and y==615 for x,y,w,h,cb in app.hits))
        app.approve_commands();dialog=self.dialog();invoke(dialog,'<Escape>');await self.sync()
        self.assertFalse(self.c.settings.get()['command_sync_pending'])

    async def test_command_http_errors_are_safe_and_invalidate_ui_review(self):
        import discord
        for status in (403,404):
            failure=discord.HTTPException(SimpleNamespace(status=status,reason='synthetic'),dict(code=50001,message='private response text'))
            client=SimpleNamespace(is_ready=lambda:True,review_commands=AsyncMock(side_effect=failure),command_review=None)
            self.c.command_review=dict(fingerprint='stale');self.c.client=client
            try:
                with patch.object(self.c,'_publish'):
                    result=await self.c.command('command_review')
                self.assertFalse(result['ok']);self.assertIsNone(self.c.command_review)
                self.assertNotIn('private',result['error']);self.assertIn('권한' if status==403 else '대상',result['error'])
            finally:self.c.client=None
    async def test_concurrent_deleted_memory_reports_failure_and_keeps_editor_input(self):
        app=self.app;app.page='memories';app.record_user='4'
        key=self.c.companion.add_memory(2,4,3,'합성 보존 내용')
        await self.c.refresh_companion(2,'4');await self.sync();app.record_key=key;app.edit_record();d=self.dialog()
        self.c.companion.delete_memory(2,key)
        self.fill(d,['변경하려던 입력','','사용']);await self.sync()
        self.assertTrue(d.winfo_exists());self.assertFalse(d._pending_save)
        self.assertTrue(self.c.error);self.assertFalse(self.c.companion.memories(2,4))
        entry=next(w for w in d.winfo_children()[0].winfo_children() if isinstance(w,tk.Entry))
        self.assertEqual(entry.get(),'변경하려던 입력')

    async def test_blank_installation_gui_encrypts_dummy_credentials_and_offline_start_is_blocked(self):
        from echomate_bot.user_check import controller_type
        from echomate_bot.desktop import LocalController
        from echomate_bot.onboarding import load_bootstrap
        self.c.settings=None;self.c.lease=SimpleNamespace(close=lambda:None)
        path=self.fixture.root/'settings.json'
        self.assertTrue(path.resolve().is_relative_to(self.fixture.root.resolve()));path.unlink()
        self.c.__class__=controller_type(LocalController)
        app=self.app;app.page='setup';app.setup_credentials()
        self.fill(self.dialog(),['1','offline-synthetic-token-not-for-discord']);await self.sync()
        self.assertIsNotNone(self.c.settings);self.assertFalse(self.c.error)
        bootstrap=self.fixture.root/'bootstrap.json'
        self.assertNotIn('offline-synthetic-token-not-for-discord',bootstrap.read_text(encoding='utf-8'))
        self.assertEqual(load_bootstrap(bootstrap)['owner_id'],1)
        result=await self.c.command('start');self.assertFalse(result['ok']);self.assertIsNone(self.c.client)
        self.assertFalse(self.c.settings.get()['enabled'])

    async def test_real_sqlite_lock_preserves_editor_then_retry_succeeds(self):
        import sqlite3
        app=self.app;app.page='relations';app.record_user='4'
        self.c.companion.set_consent(2,4,'relationships',True);self.c.companion.set_affinity(2,4,50)
        await self.c.refresh_companion(2,'4');await self.sync()
        blocker=sqlite3.connect(self.c.companion.path);blocker.execute('BEGIN IMMEDIATE')
        try:
            app.edit_record();d=self.dialog();self.fill(d,['65']);await self.sync()
            self.assertTrue(d.winfo_exists());self.assertFalse(d._pending_save)
            self.assertEqual(self.c.error,'OperationalError')
        finally:blocker.rollback();blocker.close()
        self.assertEqual(self.c.companion.users(2)[0]['affinity'],50)
        self.fill(d,['65']);await self.sync()
        self.assertFalse(d.winfo_exists());self.assertEqual(self.c.companion.users(2)[0]['affinity'],65)

    async def test_repeated_start_clicks_create_one_job_and_stop_releases_it(self):
        async def wait():await asyncio.Event().wait()
        self.c._run_bot=AsyncMock(side_effect=wait)
        self.c.submit('start');self.c.submit('start');await self.sync();await asyncio.sleep(0)
        self.assertEqual(self.c._run_bot.await_count,1);self.assertFalse(self.c.job.done())
        self.c.submit('stop');await self.sync()
        self.assertTrue(self.c.job.done());self.assertFalse(self.c.settings.get()['enabled'])

    async def test_inventory_refresh_uses_actual_sdk_with_http_mock_only(self):
        from verify_ui_actions import offline_discord_request
        with patch('discord.http.HTTPClient.request',new=AsyncMock(side_effect=offline_discord_request)) as http:
            self.c.submit('refresh');await self.sync()
        self.assertFalse(self.c.error);self.assertGreaterEqual(http.await_count,4)
        self.assertEqual(self.c.inventory[0]['id'],2)
        self.assertEqual(self.c.inventory[0]['channels'][0]['id'],3)
        self.outbound.assert_not_awaited()

    async def test_summary_readonly_delete_and_no_resurrection_use_consented_sources(self):
        from datetime import datetime,timezone
        from echomate_studio.dialogue_state import Turn
        store=self.c.companion;store.set_consent(2,4,'summaries',True)
        turns=[Turn('701','4','합성 수업 문의',datetime.now(timezone.utc)),Turn('702','999','합성 안내 답변',datetime.now(timezone.utc),True,'701')]
        body=dict(items=[dict(kind='question',source='701',text='도예 수업을 문의함'),dict(kind='answer',source='702',text='준비 과정을 안내함')])
        versions=store.digest_consent(2,['4']);key=store.save_digest(2,3,'synthetic-flow',body,turns,versions)
        self.assertIsNotNone(key)
        app=self.app;app.page='relations';app.record_user='4';app.show_summaries();await self.sync()
        app.record_key='digest:'+key;app.show_digest();d=self.dialog()
        entries=[w for w in d.winfo_children()[0].winfo_children() if isinstance(w,tk.Entry)]
        self.assertTrue(entries);self.assertTrue(all(w.cget('state')=='readonly' for w in entries))
        invoke(d,'<Control-Return>');app.remove_record();self.fill(self.dialog(),['삭제']);await self.sync()
        self.assertFalse(store.digests(2,4,include_expired=True));self.assertIsNone(app.record_key)
        self.assertIsNone(store.save_digest(2,3,'synthetic-flow',body,turns,versions))
        before=len(self.commands);app.show_legacy_summaries();invoke(self.dialog(),'<Control-Return>')
        self.assertEqual(len(self.commands),before)
