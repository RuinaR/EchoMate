import unittest
from dataclasses import replace
from datetime import datetime,timezone
from copy import deepcopy
from unittest.mock import patch
import test_local_chat as local_cases
from echomate_bot.read_evidence import ReadEvidence,ReadState,execute_read,read_question,read_answer
from echomate_bot.correction_context import correction_view,correction_requested
from echomate_bot.companion import handle_request,outcome_state,request_kind
from echomate_bot.runtime import Event
from echomate_bot.settings import DEFAULTS

class SourceViews(unittest.TestCase):
 def test_digest_cannot_promote_a_model_claim_into_execution_proof(self):
  import json
  from types import SimpleNamespace
  from echomate_bot.summarization import validated_digest,render_digest
  turn=SimpleNamespace(message_id='2',is_bot=True,content='알림 예약을 완료했어.')
  item=dict(kind='decision',text='알림 예약을 완료했다',source='2',evidence='알림 예약을 완료했어')
  body=validated_digest(json.dumps(dict(items=[item],ended=False)),[turn])
  self.assertEqual(body['items'][0]['source_role'],'PRIOR_MODEL_RESPONSE');self.assertFalse(body['items'][0]['execution_verified'])
  self.assertIn('실행 근거 아님',render_digest(body))
  item['source_role']='VERIFIED_READ_RESULT'
  with self.assertRaises(ValueError):validated_digest(json.dumps(dict(items=[item],ended=False)),[turn])
 def test_correction_changes_only_the_generation_view(self):
  history=[dict(role='user',content='물이 고였어'),dict(role='assistant',content='작은 접시 때문이야'),dict(role='user',content='정정할게. 접시 크기는 말하지 않았어.')]
  before=deepcopy(history);view,count=correction_view(history,history[-1]['content'],local_history=True)
  self.assertEqual(count,1);self.assertEqual(history,before);self.assertEqual(view[0],history[0]);self.assertEqual(view[-1],history[-1]);self.assertNotIn('작은 접시',view[1]['content'])
 def test_quoted_conditional_and_runtime_metadata_are_not_current_corrections(self):
  for text in ('친구가 "정정할게. 사실 오늘이야"라고 했어','만약 정정할게라고 말한다면?','오늘은 그냥 수다 떨자'):
   self.assertFalse(correction_requested(text))
  values=[dict(role='user',content='[요약] 정정할게'),dict(role='assistant',content='정상 설명')]
  self.assertEqual(correction_view(values,'새 이야기',local_history=False),(values,0))
  self.assertTrue(correction_requested('시간은 말하지 않았어. 네가 임의로 정한 거야.'))
 def test_read_intents_do_not_capture_reports_or_future_chat(self):
  for text in ('친구가 네가 내 알림을 확인했다고 하던데','다음에 같이 생각해 보자','알림이라는 단어가 생각났어','만약 내 알림 목록 확인했어라고 묻는다면'):
   self.assertIsNone(read_question(text))
  self.assertEqual(read_question('내가 등록한 알림이 뭐야?'),('reminders','read'))
  self.assertEqual(read_question('내 기억을 아직 조회하지 않았지?'),('memory','status'))
  self.assertEqual(read_question('내 알림 목록 확인했어?'),('reminders','status'))
  self.assertEqual(read_question('알림이 없다는 거야, 조회가 안 된 거야?'),('reminders','read'))
 def test_all_read_states_are_explicit_not_a_model_vote(self):
  self.assertEqual(len(ReadState),9)
  for state in ReadState:self.assertIn(state.value,ReadEvidence('reminders',state).public().values())
 def test_past_cancellation_report_is_not_a_new_cancellation(self):
  from echomate_bot.intent_router import plan_intent,IntentMode
  self.assertEqual(plan_intent('알림을 취소한 거야. 전부 실패했다거나 아직 예약돼 있다고 하지 말아 줘.','reminder').mode,IntentMode.MENTION)
  for text in ('알림 취소 1234abcd','내 알림 10분 더 늦춰','알림 취소해 줘'):
   self.assertEqual(plan_intent(text,'reminder').mode,IntentMode.REQUEST)

class ReadAndCompound(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=local_cases.LocalRuntime.asyncSetUp
 asyncTearDown=local_cases.LocalRuntime.asyncTearDown
 def event(self,text):return Event(123,2,3,4,text,datetime.now(timezone.utc))
 def cfg(self):
  cfg=deepcopy(DEFAULTS);cfg['guilds']={'2':dict(timezone='Asia/Seoul')};return cfg
 async def test_success_requires_current_read_receipt_and_is_scoped(self):
  event=self.event('내가 등록한 알림이 뭐야?');record=execute_read(self.chat.store,event,'reminders',self.cfg())
  self.assertEqual(record.state,ReadState.SUCCESS_EMPTY);self.assertTrue(record.receipt.current(self.chat.store))
  self.chat.store.reserve_reminder(event,self.chat.store.clock()+1800,'Asia/Seoul','합성 알림')
  self.assertEqual(record.checked(self.chat.store).state,ReadState.STALE)
  other=execute_read(self.chat.store,replace(event,author=5),'reminders',self.cfg());self.assertEqual(other.state,ReadState.SUCCESS_EMPTY)
 async def test_failed_memory_read_does_not_undo_a_successful_reminder(self):
  receipts=[];outcomes=[];event=self.event('내가 전에 무슨 게임 한다고 했어? 그리고 30분 후 물 마시라고 알려줘')
  with patch.object(self.chat.store,'memories',side_effect=OSError('synthetic read failed')):
   answer=handle_request(self.chat.store,event,self.cfg(),999,receipts=receipts,outcomes=outcomes)
  self.assertEqual(outcome_state(outcomes),'PARTIAL');self.assertEqual(outcomes[0]['state'],'FAILED');self.assertEqual(outcomes[1]['state'],'SUCCESS')
  self.assertIn('실패',answer);self.assertEqual(len(self.chat.store.reminders(2,4)),1);self.assertTrue(all(r.current(self.chat.store) for r in receipts))
 async def test_incomplete_reminder_cannot_invent_time_after_successful_read(self):
  outcomes=[];receipts=[];event=self.event('내가 전에 어떤 취미 말했어? 그리고 내일 저녁에 다시 가라고 알려줘')
  answer=handle_request(self.chat.store,event,self.cfg(),999,receipts=receipts,outcomes=outcomes)
  self.assertEqual(outcomes[0]['state'],'SUCCESS_EMPTY');self.assertEqual(outcomes[1]['state'],'NEEDS_INFORMATION');self.assertEqual(outcome_state(outcomes),'PARTIAL')
  self.assertEqual(self.chat.store.reminders(2,4),[]);self.assertTrue('시각' in answer or '시간' in answer)
 async def test_local_status_never_treats_a_model_claim_as_a_read(self):
  await self.chat.send('내 알림 목록 확인했어?',self.backend)
  self.backend.text.assert_not_awaited();self.assertEqual(self.chat.last['reads']['reminders']['state'],'NOT_REQUESTED')
  await self.chat.send('내가 등록한 알림이 뭐야?',self.backend)
  self.assertEqual(self.chat.last['reads']['reminders']['state'],'SUCCESS_EMPTY');self.assertTrue(self.chat.last['receipts'][0]['current'])
 async def test_correction_alone_cannot_modify_saved_memory(self):
  await self.chat.send('/동의 기억 켜기',self.backend);await self.chat.send('/기억 저장 나는 합성 퍼즐을 좋아한다',self.backend)
  before=self.chat.store.memories(2,4,3)
  await self.chat.send('나는 그걸 좋아한다고 말한 적 없어. 지금 대화에서만 정정할게.',self.backend)
  self.assertEqual(self.chat.store.memories(2,4,3),before)
 async def test_pending_read_cancellation_has_no_success_claim(self):
  import asyncio,threading
  entered=asyncio.Event();release=threading.Event();loop=asyncio.get_running_loop()
  def slow(*args,**kwargs):loop.call_soon_threadsafe(entered.set);release.wait(5);return []
  with patch.object(self.chat.hub.legacy,'reminders',side_effect=slow):
   task=asyncio.create_task(self.chat.send('내가 등록한 알림이 뭐야?',self.backend))
   try:
    await asyncio.wait_for(entered.wait(),2)
    self.assertEqual(self.chat.snapshot()['read_execution']['reminders']['state'],'PENDING')
    task.cancel();release.set()
    with self.assertRaises(asyncio.CancelledError):await task
   finally:release.set()
  self.assertEqual(self.chat.last['reads']['reminders']['state'],'CANCELLED')
  self.assertFalse(any(r['role']=='assistant' for r in self.chat.rows))
