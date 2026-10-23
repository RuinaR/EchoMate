"""Anonymized server failures. No real credentials, IDs or network."""
import asyncio
from dataclasses import replace
import json
import sqlite3
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,patch
import discord
from discord import app_commands
import test_bot_integration as base
from echomate_bot.capabilities import public_state,describe,visual_guard
from echomate_bot.companion_store import CompanionStore
from echomate_bot.discord_app import EchoClient
from echomate_bot.social import SocialDecision

class LiveFailures(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle

    def social(self):
        self.runtime.direct_cooldown=0
        self.backend.fast_text_path=True
        self.backend.assess_social=AsyncMock(return_value=SocialDecision('bot','continue','0','question',True))
        self.settings.change(1,lambda c:c['guilds']['2'].update(name='다온봇'))

    async def test_name_then_question_before_ack_is_one_source_chain(self):
        self.social();self.runtime.utterances.attention_wait=.15
        await self.runtime.ingest(self.event(content='다온아'))
        await asyncio.sleep(.03)
        await self.runtime.ingest(self.event(id=11,content='뭐해'))
        await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        self.assertEqual([p.id for p in self.transport.sent[0][0].raw_parts],[10,11])
        self.assertEqual(self.transport.sent[0][0].response_to,10)

    async def test_after_sent_attention_keeps_conversation_not_old_reply(self):
        self.social();self.runtime.utterances.attention_wait=.01
        await self.runtime.ingest(self.event(content='다온아'));await self.settle()
        first=self.transport.sent[0][0]
        await self.runtime.ingest(self.event(id=11,content='뭐해'));await self.settle()
        self.assertEqual(len(self.transport.sent),2)
        second=self.transport.sent[1][0]
        self.assertEqual(first.conversation_id,second.conversation_id)
        self.assertEqual(second.response_to or second.id,11)
        self.backend.assess_social.assert_awaited_once()

    async def test_attention_never_invites_other_person_or_independent_question(self):
        self.social();self.runtime.utterances.attention_wait=.01
        await self.runtime.ingest(self.event(content='다온아'));await self.settle()
        await self.runtime.ingest(replace(self.event(id=11,content='<@5> 너는 뭐해'),member_mentions=(5,)))
        await self.settle();self.assertEqual(len(self.transport.sent),1)
        self.assertTrue(all(f.attention_source is None for f in self.runtime.conversations.flows.values()))

    async def test_reactive_pieces_over_old_window_do_not_each_generate(self):
        self.social();await self.runtime.ingest(self.event(content='다온아 짧게 인사해줘'));await self.settle();self.transport.sent.clear()
        await self.runtime.ingest(self.event(id=11,content='잘 안 맞네.'))
        await asyncio.sleep(.4)
        self.assertFalse(self.transport.sent)
        await self.runtime.ingest(self.event(id=12,content='좀 실망인데!'))
        await self.settle();self.assertEqual(len(self.transport.sent),1)
        self.assertEqual([p.id for p in self.transport.sent[0][0].raw_parts],[11,12])

    async def test_first_attachment_survives_assembly_and_is_never_invented(self):
        self.social()
        await self.runtime.ingest(self.event(content='다온아'))
        await self.runtime.ingest(replace(self.event(id=11,content='이게 누군지 알겠니'),assets=(('attachment:11','https://invalid.example/picture.png'),)))
        await self.runtime.ingest(self.event(id=12,content='사진 좀 봐줘'))
        with patch('echomate_bot.runtime.download',new=AsyncMock(side_effect=AssertionError('No image download'))) as download:
            await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        event,action=self.transport.sent[0]
        self.assertEqual(len(event.assets),1);self.assertIn('확인할 수 없어',action.text)
        self.assertFalse(self.backend.calls);download.assert_not_awaited()

    async def test_current_settings_and_only_self_consent_no_generation(self):
        self.runtime.companion=CompanionStore(self.root/'private.sqlite3')
        self.settings.set(1,'memory_auto',True)
        e=self.event(content='<@999> 너 기억력 있어?')
        view=await public_state(self.runtime,e,await self.transport.permissions(e))
        self.assertEqual(view['features']['memory']['state'],'consent_required')
        self.runtime.companion.set_consent(2,4,'memory',True)
        view=await public_state(self.runtime,e,await self.transport.permissions(e))
        self.assertEqual(view['features']['memory']['state'],'ready')
        self.assertNotIn('path',json.dumps(view))
        await self.runtime.ingest(e);await self.settle()
        self.assertIn('사용할 수 있어',self.transport.sent[-1][1].text);self.assertFalse(self.backend.calls)
        other=replace(e,member_mentions=(5,))
        self.assertIn('알려줄 수 없어',describe('다른 사람의 동의 상태는 어때',view,other,999))
        self.runtime.companion.set_consent(2,4,'memory',False)
        self.assertEqual((await public_state(self.runtime,e,await self.transport.permissions(e)))['features']['memory']['state'],'consent_required')

    async def test_state_change_during_send_blocks_stale_capability_answer(self):
        self.runtime.companion=CompanionStore(self.root/'private.sqlite3')
        original=self.transport.execute
        async def changed(event,action,library,fresh):
            self.settings.set(1,'web_search',True)
            return await original(event,action,library,fresh)
        self.transport.execute=changed
        await self.runtime.ingest(self.event(content='<@999> 너 검색 가능해?'));await self.settle()
        self.assertFalse(self.transport.sent)

    async def test_expired_lease_and_done_task_not_perpetually_active(self):
        self.social();await self.runtime.ingest(self.event(content='다온아 안녕'));await self.settle()
        flow=next(f for f in self.runtime.conversations.flows.values() if f.last_bot)
        flow.last_at=self.runtime.activity_clock()-1000
        task=asyncio.create_task(asyncio.sleep(0));await task
        self.runtime.tasks[flow.key]=task
        self.assertEqual(self.runtime.activity_changed(),0)
        self.assertEqual(self.runtime.social_monitor()[0]['status'],'idle')
        self.assertFalse(flow.engaged);self.assertIn(flow.key,self.runtime.states)
        self.runtime.tasks.pop(flow.key)

    async def test_report_pseudonyms_no_bodies_or_actual_ids(self):
        await self.runtime.ingest(self.event(id=123456789,content='<@999>'))
        serialized=json.dumps(self.runtime.utterances.report())
        self.assertNotIn('123456789',serialized);self.assertNotIn('<@999>',serialized)

    async def test_capability_flags_model_scope_and_failures_are_not_claimed_ready(self):
        e=self.event();p=await self.transport.permissions(e)
        self.backend.model=None
        view=await public_state(self.runtime,e,p)
        self.assertEqual(view['model'],'not_ready')
        self.backend.failed=True
        self.assertEqual((await public_state(self.runtime,e,p))['model'],'failed')
        self.backend.failed=False;self.backend.model=object()
        self.settings.set(1,'web_search',True)
        self.runtime.feature_outcomes={(2,3,4,'web'):'failed'}
        self.assertEqual((await public_state(self.runtime,e,p))['features']['web']['state'],'failed')
        other=replace(e,author=5)
        self.assertEqual((await public_state(self.runtime,other,p))['features']['web']['state'],'ready')
        self.settings.set(1,'web_search',False)
        self.assertEqual((await public_state(self.runtime,e,p))['features']['web']['state'],'off')
        denied=await public_state(self.runtime,e,dict(view=False,send=False,react=False))
        self.assertFalse(denied['text_enabled']);self.assertNotIn('private.sqlite3',json.dumps(denied))

    async def test_visual_guard_needs_real_observation_not_filename_or_text(self):
        e=self.event(content='이게 누군지 알겠니');p=await self.transport.permissions(e)
        view=await public_state(self.runtime,e,p)
        for status in ('not_provided','present_not_analyzed','analysis_failed'):
            view['visual_observation']=status
            self.assertNotEqual(visual_guard('사진 속에는 누군가 서 있어.',view,e),'사진 속에는 누군가 서 있어.')
        view['visual_observation']='verified_observation'
        self.assertEqual(visual_guard('관찰 결과의 설명',view,e),'관찰 결과의 설명')
        from echomate_bot.capabilities import question
        self.assertFalse(question('이미지 분류 알고리즘의 원리를 설명해줘'))
        self.assertFalse(question('이 함수의 기능을 설명해줘'))
        self.assertFalse(question('너는 창문 없는 방에서도 가능하다고 생각해?'))
        self.assertFalse(question('너는 그 규칙을 지킬 수 있다고 생각해?'))
        self.assertTrue(question('너는 순간이동 가능해?'))
        self.assertIn('그 기능은 지원하지 않아',describe('영상 통화 기능 가능해?',view,e,999))

    async def test_visual_failure_and_verified_observation_use_different_output_paths(self):
        self.settings.set(1,'vision',True);self.runtime.direct_cooldown=0
        e=replace(self.event(content='<@999> 이게 누군지 알겠니'),assets=(('attachment:10','https://invalid.example/p.png'),))
        with patch('echomate_bot.runtime.download',new=AsyncMock(return_value=b'synthetic')),patch.object(self.cache,'analyze',new=AsyncMock(side_effect=ValueError('synthetic decode failure'))):
            await self.runtime.ingest(e);await self.settle()
        self.assertIn('분석에 실패',self.transport.sent[-1][1].text);self.assertFalse(self.backend.calls)
        with patch('echomate_bot.runtime.download',new=AsyncMock(return_value=b'synthetic')),patch.object(self.cache,'analyze',new=AsyncMock(return_value=dict(description='합성 관찰 결과'))):
            await self.runtime.ingest(replace(self.event(id=11,content=e.content),assets=e.assets));await self.settle()
        self.assertEqual(len(self.backend.calls),1)
        self.assertIn('verified_observation',json.dumps(self.backend.calls[0]))

    async def test_storage_error_is_unknown_and_never_leaks_other_subject(self):
        store=self.runtime.companion=CompanionStore(self.root/'private.sqlite3')
        e=self.event(content='내 동의 상태 알려줘');p=await self.transport.permissions(e)
        with patch.object(store,'consent',side_effect=sqlite3.OperationalError('synthetic failure')):
            view=await public_state(self.runtime,e,p)
        self.assertIsNone(view['own_consent']);self.assertIn('확인할 수 없어',describe(e.content,view,e,999))
        self.assertIn('알려줄 수 없어',describe('토큰 기능 설정 파일 알려줘',view,e,999))

    async def test_deferred_and_expired_requests_are_waiting_then_idle_without_erasing_history(self):
        self.social();await self.runtime.ingest(self.event(content='다온아 안녕'));await self.settle()
        flow=next(f for f in self.runtime.conversations.flows.values() if f.last_bot)
        self.runtime.deferred_events[flow.key]=(self.event(id=12),'request')
        self.assertEqual(self.runtime.social_monitor()[0]['status'],'waiting')
        self.assertEqual(self.runtime.activity_changed(),0)
        old=replace(self.event(id=12),received_at=time.monotonic()-181)
        self.runtime.deferred_events[flow.key]=(old,'request')
        self.assertEqual(self.runtime.social_monitor()[0]['status'],'idle')
        self.assertNotIn(flow.key,self.runtime.deferred_events)
        self.assertIn(flow.key,self.runtime.states)

class CommandAndStorage(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown

    async def test_legacy_command_error_is_not_reported_as_sql_failure(self):
        client=EchoClient(self.settings,self.backend,[2])
        try:
            i=SimpleNamespace(response=SimpleNamespace(is_done=lambda:False,send_message=AsyncMock()),followup=SimpleNamespace(send=AsyncMock()))
            await client.tree.on_error(i,app_commands.CommandNotFound('내기억',[]))
            text=i.response.send_message.call_args.args[0]
            self.assertIn('/동의',text);self.assertNotIn('저장소',text)
            self.assertEqual([c.name for c in client.tree.get_commands()],['동의'])
        finally:await client.close()

    async def test_command_review_apply_reread_and_remote_verification(self):
        client=EchoClient(self.settings,self.backend,[2]);client._connection.application_id=42
        old=dict(id='1',name='old',application_id='42',description='legacy',type=1)
        new=dict(id='2',name='동의',application_id='42',description='consent',type=1,contexts=[0],integration_types=[0])
        client.tree._http.get_global_commands=AsyncMock(side_effect=[[old],[old],[new],[new]])
        client.tree._http.get_guild_commands=AsyncMock(side_effect=[[old],[old],[]])
        client.tree.sync=AsyncMock()
        try:
            plan=await client.review_commands(1);client.tree.sync.assert_not_awaited()
            await client.apply_commands(1,plan['fingerprint'])
            self.assertEqual(client.tree.sync.await_count,2)
            self.assertFalse(self.settings.get()['command_sync_pending'])
            self.assertEqual(json.loads((self.settings.path.parent/'command-audit.json').read_text(encoding='utf-8'))['status'],'verified')
        finally:await client.close()

    async def test_changed_or_foreign_command_list_never_writes(self):
        client=EchoClient(self.settings,self.backend,[2]);client._connection.application_id=42
        old=dict(id='1',name='old',application_id='42',description='legacy',type=1)
        new=dict(id='2',name='changed',application_id='42',description='changed',type=1)
        client.tree._http.get_global_commands=AsyncMock(side_effect=[[old],[new]])
        client.tree._http.get_guild_commands=AsyncMock(return_value=[]);client.tree.sync=AsyncMock()
        try:
            plan=await client.review_commands(1)
            with self.assertRaises(ValueError):await client.apply_commands(1,plan['fingerprint'])
            client.tree.sync.assert_not_awaited()
            client.tree._http.get_global_commands=AsyncMock(return_value=[dict(id='4',name='other',application_id='43',description='foreign',type=1)])
            with self.assertRaises(ValueError):await client.review_commands(1)
            with self.assertRaises(PermissionError):await client.review_commands(5)
        finally:await client.close()

    async def test_partial_command_sync_failure_keeps_pending_and_retry_review(self):
        client=EchoClient(self.settings,self.backend,[2]);client._connection.application_id=42
        old=dict(id='1',name='old',application_id='42',description='legacy',type=1)
        new=dict(id='2',name='동의',application_id='42',description='consent',type=1,contexts=[0],integration_types=[0])
        client.tree._http.get_global_commands=AsyncMock(side_effect=[[old],[old],[new]])
        client.tree._http.get_guild_commands=AsyncMock(return_value=[])
        client.tree.sync=AsyncMock(side_effect=[None,OSError('synthetic failure')])
        try:
            plan=await client.review_commands(1)
            with self.assertRaises(OSError):await client.apply_commands(1,plan['fingerprint'])
            self.assertTrue(self.settings.get()['command_sync_pending'])
            audit=json.loads((self.settings.path.parent/'command-audit.json').read_text(encoding='utf-8'))
            self.assertEqual(audit['status'],'failed');self.assertEqual(audit['error'],'OSError')
            self.assertIsNone(client.command_review)  # A partial write requires a fresh review/approval.
        finally:await client.close()

    async def test_legacy_consent_schema_upgrade_preserves_explicit_optouts_and_restart(self):
        path=self.root/'legacy.sqlite3'
        with sqlite3.connect(path) as db:
            db.executescript("CREATE TABLE subject_consents(guild TEXT,user TEXT,at REAL,PRIMARY KEY(guild,user));CREATE TABLE optouts(guild TEXT,user TEXT,PRIMARY KEY(guild,user));INSERT INTO subject_consents VALUES('2','4',1);INSERT INTO subject_consents VALUES('2','5',1);INSERT INTO optouts VALUES('2','5');PRAGMA user_version=1;")
        store=CompanionStore(path)
        self.assertIsNone(store.error);self.assertTrue(store.consent(2,4)['memory']);self.assertFalse(any(store.consent(2,5).values()))
        store.set_consent(2,4,'memory',False);store=CompanionStore(path)
        self.assertFalse(store.consent(2,4)['memory']);self.assertTrue(store.consent(2,4)['relationships'])
        self.assertFalse(store.consent(3,4)['relationships']);self.assertFalse(store.consent(2,6)['memory'])
        with sqlite3.connect(path,timeout=.01) as db:
            db.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError):store.set_consent(2,4,'summaries',True)
        self.assertFalse(store.consent(2,4)['summaries']);self.assertIsNone(store.last_error)

    async def test_real_sdk_interaction_ephemeral_consent_and_withdrawal(self):
        from datetime import datetime,timezone
        from discord.webhook.async_ import async_context
        from echomate_bot.consent_ui import open_consent,ConsentPanel
        from test_discord_simulator import payload,user
        client=EchoClient(self.settings,self.backend,[2]);await client._async_setup_hook()
        client._connection.user=discord.ClientUser(state=client._connection,data=user(999))
        adapter=SimpleNamespace(create_interaction_response=AsyncMock(return_value={'interaction':{'id':'100'}}),
            execute_webhook=AsyncMock(return_value=payload(9001,content='synthetic',author=999)),
            edit_original_interaction_response=AsyncMock(return_value=payload(9001,content='synthetic',author=999)))
        token=async_context.set(adapter);panels=[]
        def make(*args):
            panel=ConsentPanel(*args);panels.append(panel);return panel
        def interaction(uid=4,component=False):
            mid=discord.utils.time_snowflake(datetime.now(timezone.utc))
            data=dict(id=str(mid),application_id='42',type=3 if component else 2,token='synthetic-only',version=1,guild_id='2',channel_id='3',attachment_size_limit=10485760,
                channel=dict(id='3',type=0,name='synthetic',position=0,permission_overwrites=[]),
                member=dict(user=user(uid),roles=[],flags=0,permissions='0'),data=dict(custom_id='consent:memory',component_type=2) if component else dict(id='77',name='동의',type=1))
            if component:data['message']=payload(9001,content='synthetic',author=999)
            return discord.Interaction(data=data,state=client._connection)
        try:
            with patch('echomate_bot.consent_ui.ConsentPanel',side_effect=make),patch('discord.http.HTTPClient.request',side_effect=AssertionError('No network')),patch('aiohttp.ClientSession._request',side_effect=AssertionError('No network')):
                await open_consent(client,interaction())
                self.assertEqual(adapter.create_interaction_response.call_args.kwargs['params'].payload['data']['flags'],64)
                self.assertTrue(adapter.execute_webhook.call_args.kwargs['payload']['flags']&64)
                panel=panels[0]
                await panel.memory.callback(interaction(component=True));self.assertTrue(client.companion.consent(2,4)['memory'])
                await panel.memory.callback(interaction(component=True));self.assertFalse(client.companion.consent(2,4)['memory'])
                self.assertFalse(await panel.interaction_check(interaction(5,True)))
                panel.selected='memory';panel.confirm=True
                await panel.delete.callback(interaction(component=True));self.assertFalse(client.companion.consent(2,4)['memory'])
                restarted=CompanionStore(client.companion.path);self.assertFalse(restarted.consent(2,4)['memory'])
        finally:
            for panel in panels:panel.stop()
            async_context.reset(token);await client.close()

    async def test_transient_initialization_lock_recovers_readonly_without_migration(self):
        path=self.root/'retry.sqlite3';store=CompanionStore(path)
        store.set_consent(2,4,'memory',True)
        with sqlite3.connect(path) as writer:
            writer.execute('BEGIN IMMEDIATE')
            failed=CompanionStore(path)
            self.assertEqual(failed.error,'OperationalError')
        self.assertTrue(failed.recover_readonly())
        self.assertTrue(failed.consent(2,4)['memory']);self.assertIsNone(failed.error)
        failed.error='DatabaseError'
        self.assertFalse(failed.recover_readonly())
        client=EchoClient(self.settings,self.backend,[2],companion=store)
        try:self.assertIs(client.runtime.companion,store)
        finally:await client.close()
