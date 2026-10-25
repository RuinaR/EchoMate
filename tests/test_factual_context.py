"""Grounded lookup API and speech-about-actions, without a semantic judge."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from echomate_bot.factual_context import lookup_evidence
from echomate_bot.lookup_inquiries import lookup_state_answer
from echomate_bot.intent_router import plan_intent,IntentMode
from echomate_bot.gguf_backend import GGUFLocalBackend
from echomate_bot.character_models import character
import test_local_chat as local_cases

class Evidence(unittest.TestCase):
 def test_failure_is_unknown_not_empty_or_unauthorized(self):
  self.assertEqual(lookup_evidence('failed')['result'],'unknown')
  self.assertIsNone(lookup_evidence('failed')['authorized'])
  self.assertEqual(lookup_evidence('empty')['result'],'empty')
  self.assertTrue(lookup_evidence('found')['authorized'])
  self.assertFalse(lookup_evidence('not_authorized')['attempted'])
  with self.assertRaises(ValueError):lookup_evidence('successful')
 def test_status_is_scoped_and_all_six_states_are_distinct(self):
  answers=[lookup_state_answer('현재 기억 조회 상태를 알려 줘',s) for s in ('not_requested','not_authorized','failed','empty','found','invalidated')]
  self.assertEqual(len(set(answers)),6);self.assertTrue(all(answers))
  self.assertIn('다른 사용자',answers[4]);self.assertIn('아니야',answers[2])
 def test_mixed_quoted_conditional_and_casual_messages_stay_generation(self):
  for text in ('친구가 기억 조회 상태가 뭐야라고 물었어','기억 조회 상태가 뭐야? 그리고 오늘 점심은?',
               '만약 기억 조회 상태를 알려 줘라고 하면?','소설에서 기억 검색 결과를 확인해 줘',
               '기억 조회는 이해했어. 이제 산책 이야기를 하자','"기억 조회 상태가 뭐야?"'):
   with self.subTest(text=text):self.assertIsNone(lookup_state_answer(text,'empty'))
  self.assertIn('빈 결과',lookup_state_answer('기억 조회 실패가 기록 없다는 뜻이야?','failed'))
 def test_discussing_claims_is_not_an_execution_or_clarification(self):
  for text in ('내일 같이 노래 제목을 고민하자는 건 제안이야. 알림을 예약했다고 말하지 말아 줘.',
               '저장했다고 답하지 말아 줘','기억을 조회했다고 주장하는 건 이상해'):
   self.assertEqual(plan_intent(text,'reminder').mode,IntentMode.MENTION)
  self.assertEqual(plan_intent('저장했다고 말하지 마. 그리고 30분 후 물 마시라고 알려 줘','reminder').mode,IntentMode.REQUEST)
 def test_read_mentions_require_a_request_not_a_past_fact(self):
  for text in ('알림 목록을 조회하지 않았어. 왜 확인했다고 해?',
               '예약 목록 조회 영수증이 없다는 뜻이야.',
               '친구는 알림 목록을 보여 줬다고 하더라.'):
   self.assertNotEqual(plan_intent(text,'reminder').mode,IntentMode.REQUEST)
  for text in ('내 알림 목록','내 알림 뭐 있어?','내 알림 목록 보여줘','내 알림 조회해 줘',
               '조회 안 했어. 그리고 내 알림 목록 알려줘'):
   self.assertEqual(plan_intent(text,'reminder').mode,IntentMode.REQUEST)

class GroundedBackend(unittest.IsolatedAsyncioTestCase):
 async def test_status_does_not_ask_model_and_casual_future_still_does(self):
  b=object.__new__(GGUFLocalBackend);b.name='하루';b.name_version=0;b.entry=character('lime');b._job=AsyncMock(return_value='같이 생각해 보자.')
  for state in ('not_requested','not_authorized','failed','empty','found','invalidated'):
   out=await b.text([dict(role='user',content='기억 검색 결과를 확인해 줘')],{'_memory_lookup_state':state})
   self.assertEqual(out,lookup_state_answer('기억 검색 결과를 확인해 줘',state))
  b._job.assert_not_awaited()
  self.assertEqual(await b.text([dict(role='user',content='다음에 같이 생각해 보자.')],{}),'같이 생각해 보자.')
  b._job.assert_awaited_once()

class LocalContracts(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=local_cases.LocalRuntime.asyncSetUp
 asyncTearDown=local_cases.LocalRuntime.asyncTearDown
 async def test_generated_claim_is_history_not_a_persisted_fact_or_receipt(self):
  c=self.chat;b=self.backend
  await c.send('/동의 기억 켜기',b)
  invented='우리가 함께 갔던 일을 저장했어. 알림도 등록했어.'
  b.text.return_value=invented
  await c.send('오늘 어땠어?',b)
  self.assertEqual(c.store.memories(2,4,3),[])
  self.assertEqual(c.store.reminders(2,4),[])
  self.assertEqual(c.last['receipts'],[])
  self.assertEqual(c.last['operation_state'],'NOT_REQUESTED')
  await c.send('방금 말에 무슨 근거가 있어?',b)
  messages=b.text.await_args.args[0]
  self.assertNotIn(invented,messages[0]['content'])
  self.assertTrue(any(m['role']=='assistant' and m['content']==invented for m in messages))
 async def test_claim_discussion_and_actual_status_have_separate_paths(self):
  c=self.chat;b=self.backend
  await c.send('내일 같이 제목을 고민하자는 건 제안이야. 예약했다고 말하지 말아 줘.',b)
  b.text.assert_awaited_once();self.assertEqual(c.last['response_origin'],'backend')
  self.assertEqual(c.store.reminders(2,4),[])
  b.text.reset_mock()
  await c.send('이번 기억 조회 상태가 뭐야?',b)
  b.text.assert_not_awaited();self.assertEqual(c.last['lookup'],'not_authorized')
  self.assertEqual(c.last['response_origin'],'runtime')
