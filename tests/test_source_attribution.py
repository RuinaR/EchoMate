"""Synthetic source attribution and persistent-state boundaries; no model judge."""
import json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from echomate_bot.companion_store import CompanionStore
from echomate_bot.summarization import validated_digest,render_digest,Summarizer
from echomate_studio.dialogue_state import Turn

class SourceMemory(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='local_data');self.store=CompanionStore(Path(self.tmp.name)/'synthetic.sqlite3',clock=lambda:2000000000);self.store.set_consent(2,4,'memory',True)
 def tearDown(self):self.tmp.cleanup()
 def extract(self,text,id=1):
  e=SimpleNamespace(id=id,guild=2,channel=3,author=4,content=text,timestamp=datetime.fromtimestamp(2000000001,timezone.utc))
  return self.store.extract(e,'Asia/Seoul')
 def test_hypothetical_role_is_not_a_persistent_preference(self):
  for text in ('나는 매운 요리를 좋아해. 만약 가상의 역할을 맡는다면 그렇게 말할 거야.','나는 매운 요리를 좋아해라고 한다면 그건 가정이야.','나는 반어로 좋아해라고 말한 거야.'):
   self.assertIsNone(self.extract(text))
  self.assertEqual(self.store.memories(2,4,3),[])
 def test_tail_negation_is_never_lost_to_memory_truncation(self):
  text='나는 보드게임을 좋아해. '+('상황 설명 '*53)+'실제 취향이 아니라 역할극이야.'
  self.assertGreater(len(text),300);self.assertIsNone(self.extract(text));self.assertEqual(self.store.memories(2,4,3),[])
 def test_direct_known_preference_is_kept_whole_and_isolated(self):
  for i,text in enumerate(('나는 담백한 두부 요리를 좋아해.','나는 매운 라면과 가정식 요리를 좋아해.')):
   self.assertTrue(self.extract(text,id=i+1));rows=self.store.memories(2,4,3)
   self.assertIn(text,[row['summary'] for row in rows]);self.assertEqual(self.store.memories(2,5,3),[])
 def test_nested_and_unquoted_third_party_reports_remain_ineligible(self):
  for text in ("친구가 '난 공포게임 싫어'라고 했어.",'수빈이가 난 공포게임 싫다고 전했어.','나는 동생이 우동을 좋아한다고 들었어.',"수빈이가 '난 퍼즐을 좋아해'라 했어.",'수빈이가 난 퍼즐을 좋아해라 했어.'):
   self.assertIsNone(self.extract(text))
  self.assertEqual(self.store.memories(2,4,3),[])
 def test_no_consent_means_no_memory_even_for_a_direct_preference(self):
  self.store.set_consent(2,4,'memory',False);self.assertIsNone(self.extract('나는 산책을 좋아해.'))

class SummaryAttribution(unittest.TestCase):
 def turn(self,text,*,bot=False,id='t1',user='4'):
  return Turn(id,user,text,datetime(2026,10,27,tzinfo=timezone.utc),is_bot=bot,reply_to='original')
 def digest(self,turn,text,evidence=None):
  return json.dumps(dict(items=[dict(kind='topic',text=text,source=turn.message_id,evidence=evidence or turn.content)],ended=False),ensure_ascii=False)
 def test_reported_preference_cannot_become_an_unqualified_fact(self):
  for source in ('친구가 난 공포게임 싫다고 전했어.',"수빈이가 '난 퍼즐을 좋아해'라 했어.",'수빈이가 난 퍼즐을 좋아해라 했어.'):
   t=self.turn(source)
   with self.assertRaisesRegex(ValueError,'attribution'):validated_digest(self.digest(t,'공포게임을 싫어한다'),[t])
 def test_reporter_and_source_time_come_from_event_not_model(self):
  t=self.turn('친구가 난 공포게임 싫다고 전했어.');body=validated_digest(self.digest(t,'친구가 공포게임을 싫어한다고 전했다'),[t]);item=body['items'][0]
  self.assertEqual(item['reporter'],'4');self.assertEqual(item['observed_at'],t.timestamp.isoformat());self.assertEqual(item['reply_to'],'original');self.assertFalse(item['execution_verified']);self.assertIn('전달자 4',render_digest(body));self.assertNotIn('quoted_speaker',item)
 def test_generated_preference_stays_generated_with_actual_bot_reporter(self):
  t=self.turn('너는 원래 도예를 좋아했잖아.',bot=True,user='99');item=validated_digest(self.digest(t,'도예를 좋아하는 것으로 답했다'),[t])['items'][0]
  self.assertEqual(item['source_role'],'PRIOR_MODEL_RESPONSE');self.assertEqual(item['reporter'],'99');self.assertFalse(item['execution_verified'])
 def test_legacy_summary_never_invents_a_reporter(self):
  text=render_digest(dict(items=[dict(kind='topic',text='이전 주제',source='old')]))
  self.assertIn('LEGACY_UNKNOWN',text);self.assertIn('LEGACY_UNVERIFIED_SOURCE',text)
 def test_direct_preference_still_supports_a_grounded_digest(self):
  t=self.turn('나는 산책과 담백한 두부 요리를 좋아해.')
  self.assertEqual(validated_digest(self.digest(t,'산책과 두부 요리를 좋아한다'),[t])['items'][0]['reporter'],'4')

class SummaryFallback(unittest.IsolatedAsyncioTestCase):
 async def test_real_guard_rejects_report_loss_and_selects_original_source(self):
  with tempfile.TemporaryDirectory(dir='local_data') as folder:
   store=CompanionStore(Path(folder)/'synthetic.sqlite3');store.set_consent(2,4,'summaries',True)
   turns=[Turn('31','4','친구가 난 공포게임 싫다고 전했어.',datetime.now(timezone.utc)),Turn('32','99','그건 친구가 전한 말이지 네 취향은 아니구나.',datetime.now(timezone.utc),is_bot=True)]
   raw=json.dumps(dict(items=[dict(kind='topic',text='공포게임을 싫어한다',source='31',evidence='공포게임 싫다고 전했어')],ended=False),ensure_ascii=False)
   backend=SimpleNamespace(summarize_dialogue=AsyncMock(return_value=raw));summarizer=Summarizer(store,backend)
   event=SimpleNamespace(id=33,guild=2,channel=3,author=4,content='내 대화 요약을 보여 줘',member_mentions=(),conversation_id=None)
   answer=await summarizer.answer(event,turns,bot_id=99)
   self.assertIn('원문',answer);self.assertIn(turns[0].content,answer);self.assertEqual(store.digests(2,4,3),[])
