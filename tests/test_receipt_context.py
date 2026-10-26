import unittest,json
from datetime import datetime,timezone
from echomate_bot.runtime import Event
from echomate_bot.local_chat import LocalChat
import test_local_chat as local_cases

class ReceiptContext(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=local_cases.LocalRuntime.asyncSetUp
 asyncTearDown=local_cases.LocalRuntime.asyncTearDown
 def reserve(self,text):
  proof=[];row=self.chat.store.reserve_reminder(Event(401,2,3,4,text,datetime.now(timezone.utc)),self.chat.store.clock()+1800,'Asia/Seoul',text,receipts=proof)
  self.chat.operations=[dict(scope=(2,3,4),receipts=proof)]
  return row,proof[0]
 async def test_verified_payload_is_bounded_without_private_identifiers(self):
  row,proof=self.reserve('합성 활동 자료 확인'*30)
  fact=LocalChat.receipt_fact(proof)
  self.assertEqual(fact['request_text'],row['text'][:120]);self.assertTrue(fact['request_text_truncated'])
  self.assertEqual(fact['due_at'],row['due_at']);self.assertEqual(fact['timezone'],'Asia/Seoul')
  self.assertFalse(set(fact)&{'source','requester','target','guild','channel','reminder_id'})
  self.chat.store.change_reminder(2,4,row['reminder_id'],cancel=True)
 async def test_cancellation_honors_store_payload_purge(self):
  row,proof=self.reserve('합성 자료 확인');cancel=[]
  self.chat.store.change_reminder(2,4,row['reminder_id'],cancel=True,receipts=cancel)
  fact=LocalChat.receipt_fact(cancel[0]);self.assertEqual(fact['status'],'cancelled');self.assertIn('취소',fact['meaning']);self.assertEqual(fact['request_text'],dict(cancel[0].values)['text']);self.assertEqual(fact['request_text'],'')
 async def test_stale_or_other_subject_receipt_cannot_enter_generation(self):
  row,proof=self.reserve('합성 소유자 전용 내용')
  await self.chat.send('오늘은 차분하게 이야기하자',self.backend,scope=(2,3,5))
  self.assertNotIn(row['text'],json.dumps(self.backend.text.call_args.args[0],ensure_ascii=False))
  self.chat.store.change_reminder(2,4,row['reminder_id'],cancel=True)
  self.backend.text.reset_mock()
  await self.chat.send('오늘은 어떤 이야기를 해볼까',self.backend)
  self.assertNotIn(row['text'],json.dumps(self.backend.text.call_args.args[0],ensure_ascii=False))
 async def test_changed_receipt_during_generation_still_discards_response(self):
  row,proof=self.reserve('합성 변경 대상')
  async def changed(*args,**kwargs):
   self.chat.store.change_reminder(2,4,row['reminder_id'],cancel=True)
   return '이전 결과'
  self.backend.text.side_effect=changed
  with self.assertRaises(RuntimeError):await self.chat.send('차분하게 다시 말해 줄래',self.backend)
  self.assertEqual(self.chat.status,'failed')
