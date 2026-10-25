"""Layer boundaries, not model-quality certification."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from echomate_bot.intent_router import plan_intent,IntentMode,history_review,execution_text
from echomate_bot.companion import request_kind
from echomate_bot.summarization import validated_digest,Summarizer
import test_followup_release as digest_tests
import test_operation_grounding as operation_tests


class IntentBoundary(unittest.TestCase):
    def test_summary_does_not_steal_current_emotion_and_payload_keeps_quotes(self):
        self.assertFalse(history_review('오늘 도자기 수업에서 그릇을 찌그러뜨렸어. 조언 말고 잠깐 이야기하고 싶어.'))
        self.assertTrue(history_review('아까 우리가 무슨 결정을 했지?'))
        self.assertTrue(history_review('내 대화 요약 보여줘'))
        self.assertEqual(execution_text('너 이름이 뭐야? 그리고 20분 뒤에 스트레칭하라고 알려줘','reminder'),'20분 뒤에 스트레칭하라고 알려줘')
        self.assertEqual(execution_text('30분 뒤에 "예약하지 마"라고 알려줘','reminder'),'30분 뒤에 "예약하지 마"라고 알려줘')

    def test_current_request_is_distinct_from_feature_topic(self):
        cases={
            '20분 뒤에 물 마시라고 알려줘':IntentMode.REQUEST,
            '내 알림 목록 보여줘':IntentMode.REQUEST,
            '친구가 20분 뒤에 물 마시라는 알림을 부탁했다는 이야기를 들었어.':IntentMode.MENTION,
            '만약 40분 뒤 알림을 부탁한다면 어떨지 얘기한 거야.':IntentMode.MENTION,
            '알림 기능에 대한 농담이야.':IntentMode.MENTION,
            '30분 뒤 알림을 예로 든 것뿐이야. 지금 예약하지 마.':IntentMode.PROHIBITED,
            '다음에 같이 찾아보자':IntentMode.CHAT,
            '우리 대화 요약해 줘':IntentMode.REQUEST,
            '내일 알려줘':IntentMode.REQUEST,
            '친구가 40분 후 알림을 부탁했다는 이야기를 들었어. 그리고 20분 후에 물 마시라고 알려줘.':IntentMode.REQUEST,
            '20분 뒤 알림을 부탁해. 그리고 30분 뒤 알림도 부탁해.':IntentMode.CLARIFY,
            '내 기억 삭제해 줘. 그리고 내 알림 목록 보여줘':IntentMode.CLARIFY,
            '일상 이야기. '*9+'내 기억 삭제해 줘. 그리고 내 알림 목록 보여줘':IntentMode.CLARIFY,
        }
        for text,expected in cases.items():
            with self.subTest(text=text):self.assertEqual(plan_intent(text,request_kind(text)).mode,expected)


class ExecutionBoundary(unittest.IsolatedAsyncioTestCase):
    setUp=operation_tests.OperationRaces.setUp
    event=operation_tests.OperationRaces.event
    settle=operation_tests.OperationRaces.settle
    asyncTearDown=operation_tests.OperationRaces.asyncTearDown
    async def test_summary_intent_error_is_not_no_history_or_a_failed_turn(self):
        self.backend.is_history_request=AsyncMock(side_effect=ValueError('native budget'))
        await self.runtime.ingest(self.event(content='<@999> 아까 우리 대화 요약해 줘'))
        await self.settle()
        self.assertIn('비었다는 뜻은 아니야',self.transport.sent[-1][1].text)
        self.assertEqual(self.runtime.failures,0)

    async def test_readonly_name_and_reminder_receipt_do_not_replace_each_other(self):
        from echomate_bot.gguf_backend import GGUFLocalBackend
        from echomate_bot.character_models import character
        from types import MethodType
        self.backend.name='하루';self.backend.entry=character('lime')
        self.backend.grounded_reply=MethodType(GGUFLocalBackend.grounded_reply,self.backend)
        await self.runtime.ingest(self.event(content='<@999> 너 이름이 뭐야? 그리고 20분 뒤에 물 마시라고 알려줘'))
        await self.settle()
        answer=self.transport.sent[-1][1].text
        self.assertIn('하루',answer);self.assertIn('예약',answer)
        self.assertEqual(len(self.store.reminders(2,4,active=True)),1)
        self.assertEqual(self.runtime.failures,0)

    async def test_outer_command_uses_its_time_not_reported_time_with_terminal_period(self):
        import time
        now=time.time()
        await self.runtime.ingest(self.event(content='<@999> 친구가 40분 후 알림을 부탁했다는 이야기를 들었어. 그리고 20분 후에 물 마시라고 알려줘.'))
        await self.settle()
        rows=self.store.reminders(2,4,active=True)
        self.assertEqual(len(rows),1)
        self.assertAlmostEqual(rows[0]['due_at']-now,20*60,delta=5)
        self.assertNotIn('친구',rows[0]['text'])
        self.assertEqual(self.runtime.failures,0)

    async def test_reported_and_conditional_reminders_never_create_state(self):
        for i,text in enumerate(('친구가 20분 후 알림을 부탁했다는 이야기를 들었어.',
                                 '만약 40분 뒤 알림을 부탁한다면 어떨지 얘기한 거야.')):
            await self.runtime.ingest(self.event(id=300+i,content='<@999> '+text));await self.settle()
        self.assertFalse(self.store.reminders(2,4,active=True))
        self.assertEqual(self.runtime.failures,0)


class SummaryBoundary(unittest.IsolatedAsyncioTestCase):
    setUp=digest_tests.DigestStoreQA.setUp
    tearDown=digest_tests.DigestStoreQA.tearDown
    async def test_untrusted_json_types_reject_cleanly_and_fallback_never_persists(self):
        malformed=[[],[{}],None,dict(items=[None],ended=False),
                   dict(items=[dict(kind=[],text='x',source='12',evidence='abcde')],ended=False)]
        for body in malformed:
            with self.subTest(body=body):
                with self.assertRaises(ValueError):validated_digest(json.dumps(body),self.turns)
        backend=SimpleNamespace(summarize_dialogue=AsyncMock(return_value='null'))
        event=SimpleNamespace(author=4,guild=2,channel=3,id=20,content='우리 대화 요약해 줘',member_mentions=(),conversation_id='flow')
        answer=await Summarizer(self.store,backend).answer(event,self.turns,bot_id=999)
        self.assertIn('검증하지 못해',answer)
        self.assertIn('출처 12',answer)
        self.assertIn(self.turns[2].content,answer)
        self.assertFalse(self.store.digests(2,4,3))
        self.assertIsNone(await Summarizer(self.store,backend).answer(event,self.turns,bot_id=999,fresh=lambda:False))


class SemanticBudget(unittest.IsolatedAsyncioTestCase):
    async def test_current_and_both_reply_pairs_survive_native_selection(self):
        from echomate_bot.context_budget import fit_social
        from copy import deepcopy
        rows=[dict(id=str(i),speaker='4',bot=False,text='old '*80) for i in range(8)]
        rows.extend([dict(id='10',speaker='4',bot=False,text='actual question'),
                     dict(id='11',speaker='999',bot=True,reply='10',text='actual answer')])
        data=dict(current=dict(id='12',text='new correction',reply='11'),
                  frames=[dict(index='0',turns=rows,current_peers=['4'])],
                  surrounding=[dict(id='human',text='question to a human')],
                  pending_human_exchange=dict(source='human'))
        original=deepcopy(data)
        async def count(messages):return len(messages[1]['content'])
        result,tokens,removed=await fit_social([dict(role='system',content='policy'),dict(role='user',content=json.dumps(data))],1000,count)
        selected=json.loads(result[1]['content'])
        self.assertEqual(data,original);self.assertEqual(selected['current'],data['current'])
        self.assertEqual(selected['surrounding'],data['surrounding'])
        self.assertEqual(selected['pending_human_exchange'],data['pending_human_exchange'])
        self.assertEqual(selected['frames'][0]['turns'][-2:],rows[-2:])
        self.assertGreater(removed,0);self.assertLessEqual(tokens,1000)
        with self.assertRaises(ValueError):await fit_social(result,10,count)
