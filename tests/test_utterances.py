"""Event sequences with real Runtime/SQLite, synthetic people and no network."""
import asyncio
from dataclasses import replace
import unittest
from unittest.mock import AsyncMock
from types import SimpleNamespace

import test_bot_integration as base
from echomate_bot.utterances import Utterances
from echomate_bot.discord_app import DiscordTransport
from echomate_bot.actions import Action,Kind


class FragmentSequences(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle

    async def sequence(self,texts,interleave=False):
        self.runtime.direct_cooldown=0
        for i,text in enumerate(texts):
            await self.runtime.ingest(self.event(id=100+i,content=text))
            if interleave and i<len(texts)-1:
                await self.runtime.ingest(replace(self.event(id=200+i,content='<@6> 같이 얘기하자'),author=5,member_mentions=(6,)))

    async def test_eleven_parts_interleaved_preserve_actual_history_and_root(self):
        texts=['<@999>']+['이 조건을 포함해서']*9+['장단점을 짧게 설명해줘']
        await self.sequence(texts,True);await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        event,_=self.transport.sent[0]
        self.assertEqual(event.response_to,100)
        self.assertEqual([p.id for p in event.raw_parts],list(range(100,111)))
        self.assertTrue(event.utterance_id.startswith('utt:'))
        turns=self.runtime.states[event.flow_key].snapshot(channel_id=3,thread_id=None)[1]
        self.assertEqual([t.content for t in turns if not t.is_bot],texts)
        self.assertTrue(all(t.author_id=='4' for t in turns if not t.is_bot))

    async def test_complete_question_has_no_fixed_wait_and_independent_question_kept(self):
        self.backend.wait=asyncio.Event();self.runtime.direct_cooldown=0
        await self.runtime.ingest(self.event(content='<@999> 협동 게임 추천해줘'))
        self.assertFalse(self.runtime.utterances.pending)
        await self.runtime.ingest(self.event(id=11,content='<@999> 그리고 내일 날씨 알려줘'))
        self.assertEqual(len(self.runtime.tasks),2)
        self.backend.wait.set();await self.settle()
        self.assertEqual([e.response_to or e.id for e,a in self.transport.sent],[10,11])

    async def test_same_author_actual_reply_change_does_not_merge(self):
        await self.runtime.ingest(self.event(content='<@999>'))
        await self.runtime.ingest(replace(self.event(id=11,content='<@5> 너에게 묻는 건데'),reply_to=55,reply_author=5,member_mentions=(5,)))
        await self.settle()
        self.assertEqual([e.response_to or e.id for e,a in self.transport.sent],[10])
        self.assertEqual([p.id for p in self.transport.sent[0][0].raw_parts],[10])

    async def test_middle_edit_invalidates_waiting_utterance_not_other_user(self):
        await self.sequence(['<@999>','우선 이 조건을 포함해서'])
        await self.runtime.message_changed(2,3,101,'완전히 다른 조건')
        await self.runtime.ingest(replace(self.event(id=300,content='<@999> 안녕'),author=7))
        await self.settle()
        self.assertEqual([e.author for e,a in self.transport.sent],[7])
        self.assertFalse(self.runtime.utterances.pending)

    async def test_middle_delete_during_generation_vetoes_stale_result(self):
        self.backend.wait=asyncio.Event()
        await self.sequence(['<@999>','그 조건을 포함해서','설명해줘'])
        await asyncio.sleep(.01)
        await self.runtime.message_changed(2,3,101)
        self.backend.wait.set();await self.settle()
        self.assertFalse(self.transport.sent)

    async def test_supplement_during_generation_carries_all_sources_once(self):
        self.runtime.direct_cooldown=0;self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event(content='<@999> 게임 추천해줘'))
        await asyncio.sleep(.01)
        await self.runtime.ingest(self.event(id=11,content='아 근데'))
        await self.runtime.ingest(self.event(id=12,content='혼자 할 수 있는 걸로'))
        await self.runtime.ingest(self.event(id=13,content='너무 어렵지 않게 해줘'))
        self.backend.wait.set();await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        event=self.transport.sent[0][0]
        self.assertEqual(event.response_to,10)
        self.assertEqual([p.id for p in event.raw_parts],[10,11,12,13])

    async def test_wait_deadline_does_not_extend_and_close_releases_tasks(self):
        self.runtime.utterances.idle=.015;self.runtime.utterances.maximum=.025
        await self.runtime.ingest(self.event(content='<@999>'))
        await asyncio.sleep(.01)
        await self.runtime.ingest(self.event(id=11,content='이 조건을 포함해서'))
        await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        await self.runtime.ingest(self.event(id=12,content='<@999>'))
        await self.runtime.close()
        self.assertFalse(self.runtime.utterances.pending)
        self.assertFalse(self.runtime.utterances.emitting)

    async def test_privacy_and_scope_clear_pending_parts(self):
        await self.runtime.ingest(self.event(content='<@999>'))
        self.runtime.privacy_changed(2,4,'memory',True)
        self.assertFalse(self.runtime.utterances.pending)
        await self.runtime.ingest(self.event(id=11,content='<@999>'))
        self.runtime.invalidate(3)
        self.assertFalse(self.runtime.utterances.pending)

    async def test_source_chain_sdk_mock_checks_middle_and_actual_author(self):
        parts=[self.event(id=100+i,content=t) for i,t in enumerate(['<@999>','그 조건을 포함해서','설명해줘'])]
        event=Utterances.compose(parts,'utt:test')
        originals={p.id:SimpleNamespace(id=p.id,content=p.content,author=SimpleNamespace(id=4),channel=SimpleNamespace(id=3),reply=AsyncMock()) for p in parts}
        originals[101].content='수정된 중간 조각'
        channel=SimpleNamespace(fetch_message=AsyncMock(side_effect=lambda mid:originals[mid]))
        transport=DiscordTransport(SimpleNamespace(user=SimpleNamespace(id=999)))
        transport._permissions=AsyncMock(return_value=dict(view=True,send=True,react=True));transport.channel=lambda e:channel
        with self.assertRaises(ValueError):await transport.execute(event,Action(Kind.TEXT,'설명'),None,AsyncMock(return_value=True))
        originals[100].reply.assert_not_awaited()

    async def test_budget_splits_without_losing_ids_and_duplicate_pending_is_ignored(self):
        self.runtime.utterances.budget=300
        first=self.event(content='<@999>');await self.runtime.ingest(first);await self.runtime.ingest(first)
        await self.runtime.ingest(self.event(id=11,content='이 조건을 포함해서'))
        await self.runtime.ingest(self.event(id=12,content='설명해줘'))
        await self.settle()
        ids=[p.id for e,a in self.transport.sent for p in e.raw_parts]
        self.assertEqual(ids.count(10),1)
        self.assertLessEqual(len(self.runtime.utterances.pending),64)

    async def test_direct_nominal_fragment_and_repeated_call_complete_one_utterance(self):
        await self.sequence(['<@999> 나 그 게임','어제 설치했거든','그런데 실행이 안 돼'])
        await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        self.assertEqual(self.transport.sent[0][0].response_to,100)
        await self.runtime.ingest(self.event(id=200,content='<@999>'))
        await self.runtime.ingest(self.event(id=201,content='<@999> 안녕'))
        await self.settle()
        self.assertEqual(len(self.transport.sent),2)
        self.assertEqual(self.transport.sent[-1][0].response_to,200)

    async def test_two_speakers_and_two_threads_do_not_share_buffers(self):
        self.runtime.direct_cooldown=0
        await self.runtime.ingest(self.event(content='<@999>'))
        await self.runtime.ingest(replace(self.event(id=11,content='<@999>'),author=5))
        await self.runtime.ingest(replace(self.event(id=12,content='계산 원리를 설명해줘'),author=5))
        await self.runtime.ingest(self.event(id=13,content='게임 추천해줘'))
        await self.settle()
        self.assertEqual({(e.author,e.response_to) for e,a in self.transport.sent},{(4,10),(5,11)})
        self.assertEqual({tuple(p.id for p in e.raw_parts) for e,a in self.transport.sent},{(10,13),(11,12)})
        self.assertEqual(len({e.conversation_id for e,a in self.transport.sent}),2)

    async def test_generation_finishes_while_supplement_waits_no_old_or_duplicate_send(self):
        self.backend.wait=asyncio.Event();self.runtime.direct_cooldown=0
        await self.runtime.ingest(self.event(content='<@999> 게임 추천해줘'))
        await asyncio.sleep(.01)
        await self.runtime.ingest(self.event(id=11,content='아 근데'))
        self.backend.wait.set();await asyncio.sleep(.015)
        self.assertFalse(self.transport.sent)
        await self.runtime.ingest(self.event(id=12,content='혼자 할 게임으로 설명해줘'))
        await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        self.assertEqual(self.transport.sent[0][0].response_to,10)
        self.assertEqual([p.id for p in self.transport.sent[0][0].raw_parts],[10,11,12])

    async def test_instrumental_modifier_during_generation_does_not_finalize_early(self):
        self.backend.wait=asyncio.Event();self.runtime.direct_cooldown=0
        await self.runtime.ingest(self.event(content='<@999> 모임 준비 방법을 설명해줘'))
        await asyncio.sleep(.01)
        for mid,text in [(11,'아 근데'),(12,'이름표가 없는 상태로'),(13,'한 문장으로 말해줘')]:
            await self.runtime.ingest(self.event(id=mid,content=text))
        self.backend.wait.set();await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        self.assertEqual([p.id for p in self.transport.sent[0][0].raw_parts],[10,11,12,13])

    async def test_supplement_after_thirty_seconds_keeps_unexpired_original_request(self):
        from datetime import timedelta
        self.backend.wait=asyncio.Event();self.runtime.direct_cooldown=0
        root=self.event(content='<@999> 추천해줘')
        root=replace(root,timestamp=root.timestamp-timedelta(seconds=40),received_at=root.received_at-40)
        await self.runtime.ingest(root);await asyncio.sleep(.01)
        await self.runtime.ingest(self.event(id=11,content='아, 짧게 해줘'))
        self.backend.wait.set();await self.settle()
        self.assertEqual([e.response_to for e,a in self.transport.sent],[10])
        self.assertEqual(self.transport.sent[0][0].received_at,root.received_at)

    async def test_cross_window_budget_segments_preserve_both_pending_requests(self):
        self.backend.wait=asyncio.Event();self.runtime.direct_cooldown=0
        self.runtime.utterances.budget=700
        await self.runtime.ingest(self.event(content='<@999> 모임 준비를 설명해줘'))
        for mid in (11,12,13):
            await asyncio.sleep(.01)
            await self.runtime.ingest(self.event(id=mid,content='아, '+('조건 '*35)+'포함해서 해줘'))
        self.assertGreaterEqual(len(self.runtime.tasks),2)
        self.backend.wait.set();await self.settle()
        sources=[p.id for e,a in self.transport.sent for p in e.raw_parts]
        self.assertEqual(sorted(sources),[10,11,12,13])
        self.assertEqual(len(sources),len(set(sources)))

    async def test_pending_monitor_has_counts_without_message_content(self):
        await self.runtime.ingest(self.event(content='<@999>'))
        rows=self.runtime.monitor()
        self.assertEqual(rows[0]['stage'],'utterance_wait')
        self.assertEqual(rows[0]['source_count'],1)
        self.assertNotIn('<@999>',str(rows))
        self.runtime.invalidate_guild(2)
        self.assertFalse(self.runtime.utterances.pending)

    async def test_long_utterance_keeps_current_tail_and_marks_omitted_middle(self):
        from echomate_bot.social import SocialRouter
        from echomate_bot.sessions import Conversations
        parts=[self.event(id=100,content='처음의 실제 화제 '+('설명을 '*600)),self.event(id=101,content='이 조건에서도 가능한지 어떻게 생각해')]
        event=Utterances.compose(parts,'utt:long')
        packet,_=SocialRouter().packet(event,Conversations(),{},999)
        current=packet['current']
        self.assertIn(parts[-1].content,current['text'])
        self.assertIn('처음의 실제 화제',current['text'])
        self.assertTrue(current['text_clipped'])
        self.assertLessEqual(len(current['text']),2000)
        self.assertEqual([p['id'] for p in current['sources']],['100','101'])

    async def test_many_sources_keep_raw_dedupe_registry_at_existing_bound(self):
        import time
        self.runtime.seen={n:time.time() for n in range(5000)}
        await self.runtime.ingest(self.event(id=6000,content='<@999>'))
        await self.runtime.ingest(self.event(id=6001,content='짧게 답해줘'))
        await self.settle()
        self.assertEqual(len(self.runtime.seen),5000)
        self.assertIn(6000,self.runtime.seen);self.assertIn(6001,self.runtime.seen)

    async def test_gateway_pause_defers_one_complete_source_chain_and_resume_once(self):
        self.runtime.pause_gateway()
        await self.sequence(['<@999>','이 조건을 포함해서','설명해줘'])
        self.assertFalse(self.transport.sent)
        self.assertEqual(len(self.runtime.deferred_events),1)
        await self.runtime.resume_gateway();await self.settle()
        self.assertEqual([e.response_to for e,a in self.transport.sent],[100])

    async def test_channels_and_threads_keep_separate_raw_sources(self):
        self.settings.set_scope(1,2,8,'mention',thread=True)
        self.runtime.direct_cooldown=0
        await self.runtime.ingest(self.event(content='<@999>'))
        await self.runtime.ingest(self.event(id=11,channel=8,parent=3,content='<@999>'))
        await self.runtime.ingest(self.event(id=12,content='게임 추천해줘'))
        await self.runtime.ingest(self.event(id=13,channel=8,parent=3,content='독서 방법 설명해줘'))
        await self.settle()
        self.assertEqual({(e.channel,e.response_to) for e,a in self.transport.sent},{(3,10),(8,11)})

    async def test_persisted_memory_dependency_survives_restart_and_middle_delete(self):
        from echomate_bot.companion_store import CompanionStore
        path=self.root/'parts.sqlite3';store=CompanionStore(path,clock=lambda:1000.)
        store.set_consent(2,4,'memory',True)
        parts=[self.event(id=100+i,content=t) for i,t in enumerate(['나는','퍼즐을','좋아해'])]
        event=Utterances.compose(parts,'utt:memory')
        self.assertTrue(store.extract(event,'Asia/Seoul'))
        store=CompanionStore(path,clock=lambda:1001.)
        store.delete_source(2,101,known=False)
        self.assertFalse(store.memories(2,4))
        self.assertIsNone(store.extract(event,'Asia/Seoul'))

    async def test_reminder_middle_delete_cancels_only_dependent_source(self):
        from echomate_bot.companion_store import CompanionStore
        store=CompanionStore(self.root/'parts.sqlite3',clock=lambda:1000.)
        parts=[self.event(id=100+i,content=t) for i,t in enumerate(['내일','알림을','예약해줘'])]
        event=Utterances.compose(parts,'utt:reminder')
        row=store.reserve_reminder(event,1060.,'Asia/Seoul','알림 확인')
        store.reserve_reminder(replace(self.event(id=200),author=5),1070.,'Asia/Seoul','다른 사람 알림')
        store.delete_source(2,101,known=False)
        rows=store.reminders(2)
        self.assertEqual(next(r for r in rows if r['reminder_id']==row['reminder_id'])['status'],'cancelled')
        self.assertEqual(next(r for r in rows if r['requester']=='5')['status'],'scheduled')
        with self.assertRaises(ValueError):store.reserve_reminder(event,1080.,'Asia/Seoul','재생성 금지')

    async def test_consent_after_first_fragment_does_not_authorize_earlier_content(self):
        from datetime import datetime,timezone
        from echomate_bot.companion_store import CompanionStore
        store=CompanionStore(self.root/'parts.sqlite3',clock=lambda:1000.)
        store.set_consent(2,4,'memory',True)
        first=replace(self.event(id=100,content='나는 퍼즐을'),timestamp=datetime.fromtimestamp(999,timezone.utc))
        last=replace(self.event(id=101,content='좋아해'),timestamp=datetime.fromtimestamp(1001,timezone.utc))
        self.assertIsNone(store.extract(Utterances.compose([first,last],'utt:consent'),'Asia/Seoul'))
        self.assertFalse(store.memories(2,4))
