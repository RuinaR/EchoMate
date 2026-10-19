"""Shared runtime/Discord SDK mocks; never send to an actual guild."""
import asyncio
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
import unittest
import test_bot_integration as integration
from echomate_studio.participation import ContextAssessment
from echomate_studio.implicit_address import ImplicitAddress
from echomate_bot.companion_store import CompanionStore
from echomate_bot.discord_app import DiscordTransport


class CommonRuntime(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        integration.BotIntegration.setUp(self)
        self.store=CompanionStore(self.root/'companion.sqlite3');self.runtime.companion=self.store
        self.store.resume_subject(2,4);self.store.resume_subject(2,5)
    asyncTearDown=integration.BotIntegration.asyncTearDown
    event=integration.BotIntegration.event
    settle=integration.BotIntegration.settle

    async def test_three_modes_save_and_ack_without_text_generation(self):
        for i,mode in enumerate(('base','persona','adult')):
            self.settings.set(1,'model',mode)
            with self.runtime.ledger.db() as db:db.execute('UPDATE sent SET at=at-3')
            await self.runtime.ingest(self.event(id=10+i,content='<@999> 20분 뒤에 물 마시라고 알려줘'))
            await self.settle()
            self.assertIn('예약',self.transport.sent[-1][1].text)
        self.assertEqual(len(self.store.reminders(2,4,active=True)),3)
        self.assertFalse(self.backend.calls)

    async def test_scheduler_independent_of_generation_and_ambiguous_error_not_replayed(self):
        event=self.event();now=self.store.clock();row=self.store.reserve_reminder(event,now+1,'UTC','물 마시기')
        self.store.clock=lambda:now+2
        self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event(id=11));await asyncio.sleep(.02)
        self.transport.deliver_reminder=AsyncMock(side_effect=OSError('Synthetic uncertain delivery'))
        await self.runtime.deliver_reminders();await self.runtime.deliver_reminders()
        self.assertEqual(self.transport.deliver_reminder.await_count,1)
        self.assertEqual(self.store.reminders(2,4)[0]['status'],'failed')
        self.assertTrue(self.runtime.tasks)

    async def test_permissions_pause_cancel_and_expiry_prevent_mentions(self):
        now=self.store.clock();e=self.event();row=self.store.reserve_reminder(e,now+1,'UTC','물 마시기');self.store.clock=lambda:now+2
        self.transport.deliver_reminder=AsyncMock();self.transport.allow=False
        await self.runtime.deliver_reminders();self.transport.deliver_reminder.assert_not_awaited()
        self.transport.allow=True;self.settings.set(1,'enabled',False)
        await self.runtime.deliver_reminders();self.transport.deliver_reminder.assert_not_awaited()
        self.settings.set(1,'enabled',True);self.store.change_reminder(2,4,row['reminder_id'],cancel=True)
        await self.runtime.deliver_reminders();self.transport.deliver_reminder.assert_not_awaited()

    async def test_edit_delete_revoke_sources_without_erasing_unrelated_history(self):
        e=self.event(content='나는 RPG를 좋아해');self.store.extract(e,'Asia/Seoul')
        await self.runtime.ingest(e);await self.settle()
        await self.runtime.ingest(self.event(id=11));await self.settle()
        await self.runtime.message_changed(2,3,10,'나는 퍼즐을 좋아해')
        _,turns=self.runtime.states[3].snapshot(channel_id=3,thread_id=None)
        self.assertTrue(any(t.message_id=='11' for t in turns));self.assertFalse(self.store.memories(2,4))
        self.assertTrue(any(t.content=='나는 퍼즐을 좋아해' for t in turns))
        await self.runtime.message_changed(2,3,10)
        self.assertFalse(any(t.message_id=='10' for t in self.runtime.states[3].snapshot(channel_id=3,thread_id=None)[1]))

    async def test_memory_store_failure_does_not_disable_normal_conversation(self):
        self.store.memories=Mock(side_effect=RuntimeError('Synthetic DB failure'))
        await self.runtime.ingest(self.event());await self.settle()
        self.assertTrue(self.transport.sent);self.assertFalse(self.runtime.stopped);self.assertEqual(self.runtime.failures,0)

    async def test_unicode_reaction_remove_and_cross_guild_are_isolated(self):
        await self.runtime.ingest(self.event());await self.settle()
        await self.runtime.reaction_event(2,3,5,9001,'👍')
        self.assertEqual(len(self.store.users(2)),2)
        await self.runtime.reaction_event(9,3,6,9001,'👍')
        self.assertFalse(self.store.users(9))
        await self.runtime.reaction_event(2,3,5,9001,'👍',remove=True)
        self.assertEqual(self.store.familiarity(2,5),50)

    async def test_single_partner_semantic_request_and_ending_are_distinguished(self):
        from echomate_bot.dialogue_intent import DialogueIntent
        self.backend.assess_dialogue=AsyncMock(return_value=DialogueIntent('request','bot','continue',True))
        self.backend.fast_text_path=True
        await self.runtime.ingest(self.event());await self.settle()
        self.backend.classify=AsyncMock(return_value=ContextAssessment(False,False,False))
        self.backend.continuity=AsyncMock(return_value=ImplicitAddress(False,False))
        with self.runtime.ledger.db() as db:db.execute('UPDATE sent SET at=at-3')
        await self.runtime.ingest(self.event(id=11,content='그럼 3 더하기 4의 답만 알려줘'));await self.settle()
        self.backend.classify.assert_not_awaited();self.assertEqual(len(self.transport.sent),2)
        self.backend.assess_dialogue.return_value=DialogueIntent('closing','bot','end',False)
        await self.runtime.ingest(self.event(id=12,content='고마워, 여기까지면 충분해. 이제 다른 친구랑 이야기할게.'));await self.settle()
        await self.runtime.ingest(self.event(id=13,content='다음 질문은 7 더하기 8이야?'));await self.settle()
        self.assertEqual(len(self.transport.sent),2)

    async def test_sensitive_moment_veto_is_for_uninvited_entry_not_requested_support(self):
        self.backend.classify=AsyncMock(return_value=ContextAssessment(True,True,True))
        await self.runtime.ingest(self.event(content='<@999> 발표에서 실수해서 속상해. 짧게 위로해줘'));await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        self.settings.set_scope(1,2,7,'autonomous')
        await self.runtime.ingest(self.event(id=11,channel=7,content='우리 둘이 진지하게 이야기하는 중이야.'));await self.settle()
        self.assertEqual(len(self.transport.sent),1)

    async def test_failed_reservation_never_claims_success(self):
        self.store.reserve_reminder=Mock(side_effect=OSError('Synthetic disk failure'))
        await self.runtime.ingest(self.event(content='<@999> 20분 뒤에 불러줘'));await self.settle()
        self.assertIn('확인할 수 없어',self.transport.sent[-1][1].text)
        self.assertFalse(self.store.reminders(2));self.assertFalse(self.backend.calls)
    async def test_preflight_network_error_is_backed_off_without_killing_scheduler(self):
        event=self.event();now=self.store.clock();self.store.reserve_reminder(event,now+1,'UTC','물 마시기');self.store.clock=lambda:now+2
        self.transport.permissions=AsyncMock(side_effect=ConnectionError('Synthetic preflight outage'))
        self.transport.deliver_reminder=AsyncMock()
        await self.runtime.deliver_reminders();await self.runtime.deliver_reminders()
        self.assertEqual(self.transport.permissions.await_count,1);self.transport.deliver_reminder.assert_not_awaited()
        self.assertFalse(self.runtime.stopped);self.assertEqual(self.store.reminders(2)[0]['status'],'scheduled')


class ReminderTransport(unittest.IsolatedAsyncioTestCase):
    async def test_sdk_send_allows_only_one_saved_target_and_nonce(self):
        import discord
        channel=Mock(spec=discord.TextChannel);channel.guild=SimpleNamespace(id=2,fetch_member=AsyncMock(return_value=SimpleNamespace(id=4,bot=False)))
        channel.send=AsyncMock(return_value=SimpleNamespace(id=99))
        client=SimpleNamespace(is_ready=lambda:True,fetch_channel=AsyncMock(return_value=channel))
        transport=DiscordTransport(client)
        row=dict(guild='2',channel='3',requester='4',target='4',text='물 마시기',reminder_id='a'*24)
        await transport.deliver_reminder(row,AsyncMock(return_value=True))
        data=channel.send.call_args.kwargs;allowed=data['allowed_mentions'].to_dict()
        self.assertEqual(allowed['users'],[4]);self.assertNotIn('everyone',allowed['parse']);self.assertNotIn('roles',allowed['parse']);self.assertEqual(data['nonce'],'a'*24)
        row['target']='5'
        with self.assertRaises(ValueError):await transport.deliver_reminder(row,AsyncMock(return_value=True))
