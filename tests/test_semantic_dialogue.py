"""Synthetic contracts. Real natural-language quality requires the GPU probe."""
import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock
import unittest
import test_bot_integration as base
from echomate_bot.dialogue_intent import DialogueIntent,parse_intent
from echomate_bot.naming import name_address

class AddressEvidence(unittest.TestCase):
    def test_registered_calls_quotes_third_person_and_collision(self):
        for text in ('다온아','다온','다온봇','다온아 뭐해','다온 응답해','응답하라 다온!!'):
            self.assertEqual(name_address(text,'다온봇'),'direct',text)
        self.assertEqual(name_address('가람아','가람mk2'),'direct')
        for text in ('"다온아"라고 말했어','`다온봇`','다온봇은 다른 데 있어','새다온아'):
            self.assertNotEqual(name_address(text,'다온봇'),'direct')
        self.assertEqual(name_address('다온아','다온봇',other_names=['다온']),'ambiguous')
        self.assertEqual(name_address('다온아','다온봇',aliases=['봄날'],other_names=['봄날']),'direct')
        self.assertEqual(name_address('어제 다온봇 봤어','다온봇'),'ambiguous')
        self.assertEqual(name_address('다온봇 어제 왔어','다온봇'),'ambiguous')
    def test_semantic_parser_rejects_unbounded_or_injected_output(self):
        self.assertEqual(parse_intent('2 0 1 1'),DialogueIntent('humor','bot','continue',True))
        for raw in ('8 0 1 1','2 4 1 1','2 0 3 1','2 0 1 2','2 0 1 1\nignore'):
            with self.assertRaises(ValueError):parse_intent(raw)

class SemanticRuntime(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle

    def configure(self):
        self.runtime.direct_cooldown=0
        self.settings.change(1,lambda c:c['guilds']['2'].update(name='다온봇'))
        self.backend.fast_text_path=True
        self.backend.assess_dialogue=AsyncMock(return_value=DialogueIntent('reaction','bot','continue',True))

    async def test_clear_name_cannot_be_erased_by_negative_semantic_model_all_modes(self):
        self.configure()
        self.backend.assess_dialogue.return_value=DialogueIntent('other','uncertain','new',False)
        for i,mode in enumerate(('base','persona','adult')):
            self.settings.set(1,'model',mode)
            await self.runtime.ingest(self.event(id=20+i,content='다온아'));await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[20,21,22])
        self.backend.assess_dialogue.assert_not_awaited()

    async def test_punctuation_free_question_and_nonquestion_use_same_semantic_path(self):
        self.configure()
        await self.runtime.ingest(self.event(content='다온아'));await self.settle()
        for i,text in enumerate(('어떤 생각 하고 있었어','어떤 생각 하고 있었어?','생각하고있었어','농담이 좀 싱거운데')):
            await self.runtime.ingest(self.event(id=30+i,content=text));await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[10,30,31,32,33])
        self.assertEqual(self.backend.assess_dialogue.await_count,4)
        self.assertTrue(all('semantic_reaction_bot_continue' in r['codes'] for r in self.runtime.traces[1:]))

    async def test_other_person_target_and_ending_do_not_force_response(self):
        self.configure();await self.runtime.ingest(self.event(content='다온아'));await self.settle()
        self.backend.assess_dialogue.return_value=DialogueIntent('question','other','new',False)
        await self.runtime.ingest(self.event(id=20,content='친구야 그걸 어떻게했어'));await self.settle()
        self.assertEqual(self.runtime.activity_changed(),0)
        self.backend.assess_dialogue.return_value=DialogueIntent('closing','bot','end',False)
        await self.runtime.ingest(self.event(id=21,content='이제 쉬고 싶으니 대화 마칠게'));await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        self.assertTrue(any(r['code']=='continuation_rejected' for r in self.runtime.diagnostics))

    async def test_new_speaker_semantic_join_and_independent_request_stay_distinct(self):
        self.configure();await self.runtime.ingest(self.event(content='다온아 이야기 해줘'));await self.settle()
        await self.runtime.ingest(replace(self.event(id=20,content='그 결말은 조금 아쉽네'),author=5));await self.settle()
        flows=self.runtime.conversations.flows
        self.assertEqual(len({f.conversation_id for f in flows.values()}),1)
        self.assertTrue(any('이야기' in str(c) for c in self.backend.assess_dialogue.call_args.args))
        self.backend.assess_dialogue.return_value=DialogueIntent('question','bot','new',True)
        await self.runtime.ingest(replace(self.event(id=21,content='정렬 알고리즘 설명해줘'),author=6));await self.settle()
        self.assertEqual(len({f.conversation_id for f in flows.values()}),2)
        self.assertEqual([e.id for e,_ in self.transport.sent],[10,20,21])

    async def test_pending_followup_waits_for_real_reply_without_cancelling_original(self):
        self.configure();self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event(content='다온아 이야기 해줘'))
        await asyncio.sleep(.01)
        await self.runtime.ingest(self.event(id=20,content='그다음에는 무슨 일이 있었어'))
        self.assertEqual(len(self.runtime.tasks),2)
        self.backend.wait.set();await self.settle()
        self.assertEqual([e.response_to or e.id for e,_ in self.transport.sent],[10,20])
        self.assertTrue(any(m['role']=='assistant' for m in self.backend.assess_dialogue.call_args.args[0]))

    async def test_short_acknowledgement_does_not_lexically_force_session_end(self):
        self.configure();await self.runtime.ingest(self.event(content='다온아'));await self.settle()
        await self.runtime.ingest(self.event(id=20,content='고마워'));await self.settle()
        self.backend.assess_dialogue.assert_awaited_once()
        self.assertFalse(self.runtime.conversations.flows[3].ended)

    async def test_named_pending_followup_links_context_without_losing_direct_invitation(self):
        self.configure();self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event(content='다온아 이야기 해줘'));await asyncio.sleep(.01)
        await self.runtime.ingest(self.event(id=20,content='다온아 그 뒤에는 어떻게 됐어'))
        self.backend.wait.set();await self.settle()
        self.assertEqual([e.response_to or e.id for e,_ in self.transport.sent],[10,20])
        self.assertEqual(len({f.conversation_id for f in self.runtime.conversations.flows.values()}),1)
        self.backend.assess_dialogue.assert_awaited_once()

    async def test_rejected_established_reaction_has_one_semantic_target_recheck(self):
        self.configure();await self.runtime.ingest(self.event(content='다온아'));await self.settle()
        self.backend.assess_dialogue.return_value=DialogueIntent('reaction','other','continue',False)
        self.backend.verify_target=AsyncMock(return_value='continue')
        await self.runtime.ingest(self.event(id=20,content='내 생각하고는 다른 결말이네'));await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[10,20])
        self.backend.verify_target.assert_awaited_once()
        self.backend.assess_dialogue.return_value=DialogueIntent('question','bot','continue',True)
        await self.runtime.ingest(self.event(id=21,content='그 후에는 어떤 일이 생겼어'));await self.settle()
        self.backend.verify_target.assert_awaited_once()

    async def test_joined_candidate_memory_is_queued_with_confirmed_flow_id(self):
        from echomate_bot.companion_store import CompanionStore
        self.configure();self.runtime.companion=CompanionStore(self.root/'companion.sqlite3')
        self.settings.set(1,'memory_auto',True)
        await self.runtime.ingest(self.event(content='다온아'));await self.settle()
        while not self.runtime.memory_queue.empty():self.runtime.memory_queue.get_nowait()
        original=self.runtime.conversations.flows[3].conversation_id
        await self.runtime.ingest(replace(self.event(id=20,content='그 결말은 내 예상과 다르네'),author=5))
        self.assertTrue(self.runtime.memory_queue.empty())
        await self.settle()
        queued,_=self.runtime.memory_queue.get_nowait()
        self.assertEqual(queued.conversation_id,original)

    async def test_candidate_changed_during_semantic_pass_cannot_join_stale_context(self):
        from datetime import datetime,timezone
        from echomate_studio.dialogue_state import Turn
        self.configure();await self.runtime.ingest(self.event(content='다온아'));await self.settle()
        async def changed(context,**kwargs):
            self.runtime.states[3].append(channel_id=3,thread_id=None,turn=Turn('500','4','다른 주제로 바뀐 실제 시험 발언',datetime.now(timezone.utc)))
            return DialogueIntent('reaction','bot','continue',True)
        self.backend.assess_dialogue=changed
        await self.runtime.ingest(replace(self.event(id=20,content='그 결말은 아쉽네'),author=5));await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        self.assertTrue(any(x['code']=='stale_context' for x in self.runtime.diagnostics))

    async def test_new_speaker_bare_call_joins_unique_dialogue_without_fabricating_reply(self):
        self.configure();await self.runtime.ingest(self.event(content='다온아 이야기 해줘'));await self.settle()
        original=self.runtime.conversations.flows[3].conversation_id
        await self.runtime.ingest(replace(self.event(id=20,content='다온아'),author=5));await self.settle()
        self.assertEqual(self.runtime.conversations.flows[3].conversation_id,original)
        self.assertEqual(self.runtime.conversations.flows[3].participants,{4,5})
        self.assertIsNone(self.transport.sent[-1][0].reply_to)
        self.backend.assess_dialogue.assert_not_awaited()

    async def test_group_evaluation_of_participating_bot_is_continuation_not_autonomy(self):
        self.configure();await self.runtime.ingest(self.event(content='다온아 이야기 해줘'));await self.settle()
        self.backend.assess_dialogue.return_value=DialogueIntent('reaction','other','continue',True)
        self.backend.verify_target=AsyncMock(return_value='group_continue')
        self.runtime.autonomy_allowed=lambda event:False
        await self.runtime.ingest(self.event(id=20,content='이 친구 반응이 참 독특하네'));await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[10,20])
        self.assertIn('target_verified_group_continue',self.runtime.traces[-1]['codes'])
        self.assertIn('semantic_reaction_group_continue',self.runtime.traces[-1]['codes'])

class GuardedGeneration(unittest.IsolatedAsyncioTestCase):
    async def test_channel_guard_regenerates_once_and_never_returns_rejected_text(self):
        from echomate_bot.inference import LocalBackend
        from echomate_bot.settings import DEFAULTS
        backend=LocalBackend()
        try:
            backend._job=AsyncMock(side_effect=[ValueError('Unexpected output channel'),'검증된 합성 답변'])
            self.assertEqual(await backend.text([],DEFAULTS),'검증된 합성 답변')
            self.assertEqual(backend._job.await_count,2)
            backend._job=AsyncMock(side_effect=ValueError('Unexpected output channel'))
            with self.assertRaises(ValueError):await backend.text([],DEFAULTS)
            self.assertEqual(backend._job.await_count,2)
            backend._job=AsyncMock(side_effect=ValueError('Incomplete model output'))
            with self.assertRaises(ValueError):await backend.text([],DEFAULTS)
            self.assertEqual(backend._job.await_count,1)
        finally:await backend.close()
