"""Synthetic commit-to-send races. No operating data or live network."""
import unittest
from unittest.mock import patch
from echomate_bot.companion_store import CompanionStore
import test_bot_integration as base


class OperationRaces(unittest.IsolatedAsyncioTestCase):
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle
    asyncTearDown=base.BotIntegration.asyncTearDown

    def setUp(self):
        base.BotIntegration.setUp(self)
        self.store=self.runtime.companion=CompanionStore(self.root/'private.sqlite3')
        self.runtime.direct_cooldown=0

    async def test_deleted_memory_must_not_send_stored_ack(self):
        self.store.set_consent(2,4,'memory',True)
        original=self.transport.execute
        async def changed(event,action,library,fresh):
            self.assertIn('저장했어',action.text)
            self.store.forget_memories(2,4)
            return await original(event,action,library,fresh)
        self.transport.execute=changed
        await self.runtime.ingest(self.event(content='<@999> 나는 레몬을 좋아해. 기억해 줘'))
        await self.settle()
        self.assertFalse(self.transport.sent)
        self.assertEqual(self.runtime.traces[-1]['outcome'],'cancelled')
        self.assertEqual(self.runtime.failures,0)

    async def test_cancelled_reminder_must_not_send_scheduled_ack(self):
        original=self.transport.execute
        async def changed(event,action,library,fresh):
            row=self.store.reminders(2,4,active=True)[0]
            self.store.change_reminder(2,4,row['reminder_id'],cancel=True)
            return await original(event,action,library,fresh)
        self.transport.execute=changed
        await self.runtime.ingest(self.event(content='<@999> 20분 뒤에 물 마시라고 알려줘'))
        await self.settle()
        self.assertFalse(self.transport.sent)

    async def test_revoked_relationship_must_not_send_generated_old_context(self):
        self.store.set_consent(2,4,'relationships',True)
        async def text(context,cfg):
            self.assertIsNotNone(cfg['_familiarity'])
            self.store.set_consent(2,4,'relationships',False)
            return '응, 잠깐 쉬면서 얘기하자.'
        self.backend.text=text
        await self.runtime.ingest(self.event(content='<@999> 오늘은 조금 쉬어볼까?'))
        await self.settle()
        self.assertFalse(self.transport.sent)

    async def test_unchanged_writes_preserve_ack_without_generation(self):
        self.store.set_consent(2,4,'memory',True)
        await self.runtime.ingest(self.event(content='<@999> 나는 레몬을 좋아해. 기억해 줘'))
        await self.settle()
        await self.runtime.ingest(self.event(id=11,content='<@999> 20분 뒤에 물 마시라고 알려줘'))
        await self.settle()
        self.assertEqual(len(self.transport.sent),2)
        self.assertIn('저장했어',self.transport.sent[0][1].text)
        self.assertIn('예약',self.transport.sent[1][1].text)
        self.assertFalse(self.backend.calls)
        self.assertEqual(self.runtime.failures,0)

    async def test_reconsent_same_boolean_does_not_reauthorize_old_generation(self):
        self.store.set_consent(2,4,'relationships',True)
        async def text(context,cfg):
            self.store.set_consent(2,4,'relationships',False)
            self.store.set_consent(2,4,'relationships',True)
            return '오늘은 천천히 얘기하자.'
        self.backend.text=text
        await self.runtime.ingest(self.event());await self.settle()
        self.assertFalse(self.transport.sent)
        self.assertEqual(self.runtime.failures,0)
        self.assertIn('subject_evidence_changed',[d['code'] for d in self.runtime.diagnostics])

    async def test_other_subject_change_does_not_cancel_ordinary_answer(self):
        self.store.set_consent(2,4,'relationships',True)
        async def text(context,cfg):
            self.store.delete_personal(2,5,'relationships')
            return '오늘은 천천히 얘기하자.'
        self.backend.text=text
        await self.runtime.ingest(self.event());await self.settle()
        self.assertEqual(len(self.transport.sent),1)

    async def test_affinity_change_invalidates_old_relationship_style(self):
        self.store.set_consent(2,4,'relationships',True)
        async def text(context,cfg):
            self.store.set_affinity(2,4,80)
            return '우리 친하니까 편하게 얘기하자.'
        self.backend.text=text
        await self.runtime.ingest(self.event());await self.settle()
        self.assertFalse(self.transport.sent)

    async def test_transient_initial_snapshot_error_cannot_remove_final_guard(self):
        self.store.set_consent(2,4,'relationships',True)
        snapshot=self.store.subject_snapshot;calls=[]
        def temporary(*args,**kwargs):
            calls.append(1)
            if len(calls)==1:raise OSError('Synthetic transient read error')
            return snapshot(*args,**kwargs)
        async def text(context,cfg):
            self.store.set_consent(2,4,'relationships',False)
            return '우리 편하게 얘기하자.'
        self.backend.text=text
        with patch.object(self.store,'subject_snapshot',side_effect=temporary):
            await self.runtime.ingest(self.event());await self.settle()
        self.assertFalse(self.transport.sent)

    async def test_rescheduled_receipt_cannot_send_old_time(self):
        original=self.transport.execute
        async def changed(event,action,library,fresh):
            row=self.store.reminders(2,4,active=True)[0]
            self.store.change_reminder(2,4,row['reminder_id'],due=row['due_at']+3600)
            return await original(event,action,library,fresh)
        self.transport.execute=changed
        await self.runtime.ingest(self.event(content='<@999> 20분 뒤에 물 마시라고 알려줘'))
        await self.settle();self.assertFalse(self.transport.sent)
        self.assertEqual(self.runtime.failures,0)

    async def test_internal_preflight_metadata_does_not_invalidate_receipt(self):
        original=self.transport.execute
        async def changed(event,action,library,fresh):
            row=self.store.reminders(2,4,active=True)[0]
            self.store.defer_preflight(row['reminder_id'],'synthetic_backoff')
            return await original(event,action,library,fresh)
        self.transport.execute=changed
        await self.runtime.ingest(self.event(content='<@999> 20분 뒤에 물 마시라고 알려줘'))
        await self.settle();self.assertEqual(len(self.transport.sent),1)

    async def test_storage_failure_after_receipt_never_sends_success(self):
        original=self.transport.execute
        async def changed(event,action,library,fresh):
            self.store.error='Synthetic storage failure'
            return await original(event,action,library,fresh)
        self.transport.execute=changed
        await self.runtime.ingest(self.event(content='<@999> 20분 뒤에 물 마시라고 알려줘'))
        await self.settle();self.assertFalse(self.transport.sent)
        self.assertIn('delivery_evidence_unavailable',[d['code'] for d in self.runtime.diagnostics])

    async def test_rolled_back_write_cannot_leave_a_success_receipt(self):
        from contextlib import contextmanager
        original=self.store.db
        @contextmanager
        def rollback_reservation():
            with original() as db:
                yield db
                # Only interrupt the transaction which actually inserted a row.
                if db.in_transaction and db.execute('SELECT 1 FROM reminders').fetchone():
                    db.rollback();raise OSError('Synthetic commit failure')
        with patch.object(self.store,'db',rollback_reservation):
            await self.runtime.ingest(self.event(content='<@999> 20분 뒤에 물 마시라고 알려줘'))
            await self.settle()
        self.assertFalse(self.store.reminders(2,4))
        self.assertEqual(len(self.transport.sent),1)
        self.assertIn('확인할 수 없어',self.transport.sent[0][1].text)

    async def test_memory_list_deleted_after_read_must_not_publish_old_content(self):
        self.store.set_consent(2,4,'memory',True)
        key=self.store.add_memory(2,4,3,'나는 레몬을 좋아해')
        original=self.transport.execute
        async def changed(event,action,library,fresh):
            self.assertIn('레몬',action.text)
            self.store.delete_memory(2,key)
            return await original(event,action,library,fresh)
        self.transport.execute=changed
        await self.runtime.ingest(self.event(content='<@999> 내 기억 목록을 보여줘'))
        await self.settle();self.assertFalse(self.transport.sent)

    async def test_unchanged_memory_list_can_show_own_retained_data_after_optout(self):
        self.store.add_memory(2,4,3,'나는 레몬을 좋아해')
        await self.runtime.ingest(self.event(content='<@999> 내 기억 목록을 보여줘'))
        await self.settle();self.assertEqual(len(self.transport.sent),1)
        self.assertIn('레몬',self.transport.sent[0][1].text)
        self.assertFalse(self.backend.calls)

    async def test_unrelated_consent_does_not_cancel_memory_list(self):
        self.store.add_memory(2,4,3,'나는 레몬을 좋아해')
        original=self.transport.execute
        async def changed(event,action,library,fresh):
            self.store.set_consent(2,4,'summaries',False)
            self.store.set_consent(9,4,'memory',False)
            return await original(event,action,library,fresh)
        self.transport.execute=changed
        await self.runtime.ingest(self.event(content='<@999> 내 기억 목록을 보여줘'))
        await self.settle();self.assertEqual(len(self.transport.sent),1)

    async def test_sdk_final_source_read_can_invalidate_an_empty_list(self):
        from verify_utterance_gpu import Transport
        sdk=Transport();await sdk.start_sdk();self.runtime.transport=sdk
        original=sdk.http.get_message;changed=[]
        async def read(channel,mid):
            value=await original(channel,mid)
            if not changed:
                changed.append(True);self.store.add_memory(2,4,3,'나는 레몬을 좋아해')
            return value
        sdk.http.get_message=read
        event=self.event(content='<@999> 내 기억 목록을 보여줘');sdk.register(event)
        try:
            with patch('discord.http.HTTPClient.request',side_effect=AssertionError('No live HTTP')),patch('aiohttp.ClientSession._request',side_effect=AssertionError('No external HTTP')):
                await self.runtime.ingest(event);await self.settle()
            self.assertFalse(sdk.http.sends);self.assertFalse(sdk.sent)
            self.assertTrue(changed);self.assertFalse(self.backend.calls)
            self.assertIn('operation_receipt_changed',[d['code'] for d in self.runtime.diagnostics])
        finally:await sdk.sdk_client.close()

    async def test_deleted_reminder_and_summary_lists_do_not_publish_cached_content(self):
        row=self.store.reserve_reminder(self.event(id=91),self.store.clock()+1200,'UTC','합성 알림')
        self.store.set_consent(2,4,'summaries',True)
        with self.store.db() as db:
            db.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?,?)',
                ('2','4','3','92','fixture','나는 오늘 작은 모임을 준비했다','["4"]',self.store.clock(),self.store.clock()+3600))
        original=self.transport.execute
        async def changed(event,action,library,fresh):
            if event.id==10:self.store.change_reminder(2,4,row['reminder_id'],cancel=True)
            else:self.store.delete_personal(2,4,'summaries')
            return await original(event,action,library,fresh)
        self.transport.execute=changed
        await self.runtime.ingest(self.event(content='<@999> 내 알림 목록 보여줘'));await self.settle()
        await self.runtime.ingest(self.event(id=11,content='<@999> 내 대화 요약 보여줘'));await self.settle()
        self.assertFalse(self.transport.sent);self.assertFalse(self.backend.calls)

    async def test_partial_text_reaction_is_uncertain_not_a_no_send_cancellation(self):
        self.settings.set(1,'reactions',True)
        self.store.set_consent(2,4,'relationships',True);self.backend.action='TEXT_REACTION'
        async def propose(context,catalog):return '{"kind":"TEXT_REACTION","text":"","asset":"👍"}'
        self.backend.propose=propose
        async def partial(event,action,library,fresh):
            self.assertTrue(await fresh())
            self.transport.sent.append((event,action))  # text already reached mock transport
            self.store.set_consent(2,4,'relationships',False)
            self.assertFalse(await fresh())  # reaction's separate final check
            raise ValueError('Synthetic partial text/reaction delivery')
        self.transport.execute=partial
        await self.runtime.ingest(self.event());await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        self.assertEqual(self.runtime.traces[-1]['outcome'],'failed')
        self.assertIn('send_failed',[d['code'] for d in self.runtime.diagnostics])


if __name__=='__main__':unittest.main()
