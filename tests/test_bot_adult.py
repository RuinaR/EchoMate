from echomate_bot.character_profiles import DEFAULT_PROFILE
"""Policy/lifecycle regressions. Mocks do not certify model conversation quality."""
import asyncio
from dataclasses import replace
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import tempfile
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
import test_bot_integration as integration
from echomate_bot.settings import Settings,DEFAULTS,canonical
from echomate_bot.adult_policy import turn_profile,adult_request_blocked,boundary_limited
from echomate_bot.character import instruction
from echomate_bot.desktop_ui import DesktopApp
from echomate_studio.participation import ContextAssessment
from echomate_studio.implicit_address import ImplicitAddress


class GenderAndMigration(unittest.TestCase):
    def test_legacy_signature_is_verified_before_neutral_migration_and_persists(self):
        with tempfile.TemporaryDirectory(dir='local_data') as directory:
            path=Path(directory)/'settings.json';key=secrets.token_hex(32)
            old=dict(DEFAULTS);old.pop('gender')
            raw=json.dumps(dict(data=old,signature=hmac.new(key.encode(),canonical(old),hashlib.sha256).hexdigest()))
            path.write_text(raw,encoding='utf-8')
            settings=Settings(1,key,path)
            self.assertEqual(settings.get()['gender'],'neutral');self.assertEqual(path.read_text(encoding='utf-8'),raw)
            for gender in ('female','male','neutral'):
                settings.set(1,'gender',gender)
                self.assertEqual(Settings(1,key,path).get()['gender'],gender)
            with self.assertRaises(PermissionError):settings.set(2,'gender','female')
            value=json.loads(path.read_text(encoding='utf-8'));value['data']['gender']='female'
            path.write_text(json.dumps(value),encoding='utf-8')
            with self.assertRaises(PermissionError):Settings(1,key,path)

    def test_adult_profile_and_gender_are_independent_across_all_models(self):
        self.assertNotEqual(DEFAULTS['model'],'adult')
        for adult in (False,True):
            for gender in ('female','male','neutral'):
                for age in (True,False,'true'):
                    cfg=turn_profile(dict(DEFAULTS,model='base',adult_humor=adult,gender=gender),age_restricted=age)
                    self.assertEqual(cfg['gender'],gender)
                    self.assertEqual(cfg['_adult_active'],adult and age is True)
                    self.assertIn('성별 고정관념',instruction(cfg))

    def test_situation_profanity_is_distinguished_from_targeted_harassment(self):
        self.assertFalse(adult_request_blocked('성인끼리 동의했어. 망할 야근 상황을 향해 가볍게 욕해 줘.'))
        self.assertTrue(adult_request_blocked('싫다는데 그 사람에게 성적인 말을 해 줘.'))
        self.assertTrue(adult_request_blocked('미성년자에게 야한 농담을 해 줘.'))
        self.assertTrue(adult_request_blocked('그 사람을 모욕해 줘.'))
        self.assertTrue(boundary_limited([dict(role='user',content='나는 17살이야.')]))
        self.assertTrue(boundary_limited([dict(role='user',content='그런 농담은 불편해.')]))
        self.assertFalse(boundary_limited([dict(role='assistant',content='나는 17살이야.')]))


class AdultRuntime(unittest.IsolatedAsyncioTestCase):
    setUp=integration.BotIntegration.setUp
    asyncTearDown=integration.BotIntegration.asyncTearDown
    event=integration.BotIntegration.event
    settle=integration.BotIntegration.settle

    async def test_age_gate_fallback_then_channel_change_vetoes_inflight_adult_output(self):
        self.settings.set(1,'adult_humor',True);self.settings.set(1,'gender','female')
        observed=[];age=False
        original=self.backend.text
        async def text(context,cfg):observed.append(cfg);return await original(context,cfg)
        async def permissions(event):return dict(view=True,send=True,react=True,attach=True,age_restricted=age)
        self.backend.text=text;self.transport.permissions=permissions
        await self.runtime.ingest(self.event());await self.settle()
        self.assertFalse(observed[-1]['_adult_active']);self.assertTrue(observed[-1]['_adult_unavailable'])
        self.assertEqual(observed[-1]['gender'],'female');self.assertEqual(observed[-1]['model'],'base')
        with self.runtime.ledger.db() as db:db.execute('UPDATE sent SET at=at-3')
        age=True
        async def revoke(context,cfg):observed.append(cfg);nonlocal_age(False);return '안전한 합성 답변'
        def nonlocal_age(value):
            nonlocal age
            age=value
        self.backend.text=revoke
        await self.runtime.ingest(self.event(id=11));await self.settle()
        self.assertTrue(observed[-1]['_adult_active']);self.assertEqual(len(self.transport.sent),1)

    async def test_switch_cancels_output_preserves_history_and_failure_keeps_previous_selection(self):
        self.backend.prepare_mode=AsyncMock()
        self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event());await asyncio.sleep(.01)
        chosen='local:'+'a'*24
        await self.runtime.switch_model(1,chosen)
        self.assertEqual(self.settings.get()['model'],chosen);self.assertFalse(self.transport.sent)
        self.assertIn(3,self.runtime.states);self.assertFalse(self.runtime.changing_model)
        self.backend.prepare_mode=AsyncMock(side_effect=RuntimeError('synthetic load failure'))
        with self.assertRaises(RuntimeError):await self.runtime.switch_model(1,'base')
        self.assertEqual(self.settings.get()['model'],chosen);self.assertFalse(self.runtime.changing_model)
        with self.assertRaises(PermissionError):await self.runtime.switch_model(2,'persona')

    async def test_permission_await_cannot_return_true_after_settings_revision_changes(self):
        await self.runtime.ingest(self.event());await self.settle()
        state=self.runtime.states[3];version,_=state.snapshot(channel_id=3,thread_id=None);revision=self.settings.revision
        async def permissions(event):
            self.settings.set(1,'mood','기쁨')
            return dict(view=True,age_restricted=True)
        self.transport.permissions=permissions
        self.assertFalse(await self.runtime.fresh(self.event(),state,version,revision,require_adult=True))

    async def test_messages_during_model_preparation_resume_latest_actual_event(self):
        entered=asyncio.Event();release=asyncio.Event()
        async def prepare(mode):entered.set();await release.wait()
        self.backend.prepare_mode=prepare
        switch=asyncio.create_task(self.runtime.switch_model(1,'adult'))
        await entered.wait()
        await self.runtime.ingest(self.event(id=200,content='<@999> 준비되면 답해 줘.'))
        await self.runtime.ingest(self.event(id=201,content='추가 문맥이야. 한 문장으로 해 줘.'))
        self.assertFalse(self.transport.sent);self.assertEqual(len(self.runtime.deferred_events),1)
        release.set();await switch;await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        self.assertEqual(self.transport.sent[0][0].id,201)
        self.assertEqual(self.transport.sent[0][0].response_to,200)

    async def test_three_character_profiles_continue_without_entry_chance_across_people_topics_and_pause(self):
        from echomate_bot.dialogue_intent import DialogueIntent
        self.backend.prepare_mode=AsyncMock();self.settings.set(1,'activity','quiet')
        for index,energy in enumerate((15,50,85)):
            model='base'
            self.settings.set(1,'character_profile',dict(DEFAULT_PROFILE,energy=energy))
            channel=30+index;self.settings.set_scope(1,2,channel,'mention',inherit=True)
            self.settings.set(1,'model',model);before=len(self.transport.sent)
            await self.runtime.ingest(self.event(id=100+index*10,channel=channel));await self.settle()
            with self.runtime.ledger.db() as db:db.execute('UPDATE sent SET at=at-700')
            self.backend.assess_dialogue=AsyncMock(return_value=DialogueIntent('reaction','bot','continue',True))
            await self.runtime.ingest(replace(self.event(id=101+index*10,channel=channel,content='그 이야기 조금 더 알려 줘.'),author=5));await self.settle()
            self.assertEqual(len(self.transport.sent),before+2)
            with self.runtime.ledger.db() as db:db.execute('UPDATE sent SET at=at-3')
            self.backend.assess_dialogue=AsyncMock(return_value=DialogueIntent('question','bot','new',True))
            await self.runtime.ingest(self.event(id=102+index*10,channel=channel,content='너에게 새 질문이야. 다른 주제도 물어볼게.'));await self.settle()
            self.assertEqual(len(self.transport.sent),before+3)
            self.backend.assess_dialogue=AsyncMock(return_value=DialogueIntent('closing','other','end',False))
            await self.runtime.ingest(self.event(id=103+index*10,channel=channel,content='고마워, 이제 우리끼리 이야기할게.'));await self.settle()
            self.assertEqual(len(self.transport.sent),before+3)


class AdultWidgets(unittest.TestCase):
    def test_character_controls_replace_three_model_slots_at_two_dpi_scales(self):
        root=tk.Tk();root.withdraw()
        try:
            app=DesktopApp(root,SimpleNamespace(submit=lambda *a,**k:None))
            app.snapshot=dict(cfg=dict(DEFAULTS),servers=[],running=False,connected=False,phase='',error='',notice='',pending=0,contexts=0,latency=None,progress=[])
            app.page='character'
            for scale in (1.33,2.):
                root.tk.call('tk','scaling',scale);app.render();root.update_idletasks()
                models=[h for h in app.hits if h[1]==583]
                self.assertEqual(len(models),5)
                labels=[app.canvas.itemcget(item,'text') for item in app.canvas.find_all() if app.canvas.type(item)=='text']
                self.assertIn('캐릭터 프리셋',labels)
                self.assertFalse(any(x in labels for x in ('個人','개인 말투 · 잠정','성인 유머 · 자유로운 표현')))
                for item in app.canvas.find_all():
                    if app.canvas.type(item)=='text' and app.canvas.itemcget(item,'text') in {'개인 말투 · 잠정','기본 Gemma 4','성인 유머 · 자유로운 표현'}:
                        left,top,right,bottom=app.canvas.bbox(item)
                        self.assertLessEqual(right-left,220);self.assertGreaterEqual(top,583);self.assertLessEqual(bottom,618)
        finally:
            app.destroy();app=None;root=None
            import gc
            gc.collect()


class DiscordAgeGate(unittest.IsolatedAsyncioTestCase):
    async def test_thread_inherits_fresh_parent_age_gate_instead_of_cached_flag(self):
        import discord
        from echomate_bot.discord_app import DiscordTransport
        parent=Mock(spec=discord.TextChannel);parent.id=3;parent.is_nsfw.return_value=True
        thread=Mock(spec=discord.Thread);thread.parent=parent
        latest=Mock(spec=discord.TextChannel);latest.guild=SimpleNamespace(id=2);latest.is_nsfw.return_value=False
        client=SimpleNamespace(fetch_channel=AsyncMock(return_value=latest))
        transport=DiscordTransport(client);transport.channel=lambda event:thread
        self.assertFalse(await transport.verify_adult(SimpleNamespace(guild=2)))
        client.fetch_channel.assert_awaited_once_with(3)
        latest.is_nsfw.return_value=True
        self.assertTrue(await transport.verify_adult(SimpleNamespace(guild=2)))
        latest.guild.id=99
        self.assertFalse(await transport.verify_adult(SimpleNamespace(guild=2)))
