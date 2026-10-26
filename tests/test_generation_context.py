import unittest,tempfile,copy
from pathlib import Path
from echomate_bot.generation_context import compile_context,evidence_sections
from echomate_bot.character_models import character
from echomate_bot.output_policy import INSTRUCTION

class GenerationContext(unittest.TestCase):
 def compile(self,context,cfg=None):return compile_context(character('lime'),'하루',context,cfg or {},local_history=True)
 def test_casual_talk_omits_unrelated_feature_states_and_preserves_sources(self):
  header=dict(role='system',content='owned legacy carrier');context=[header,dict(role='user',content='오늘은 조용히 수다 떨자')]
  cfg=dict(_generation_sources=((header,'local_facts'),),_generation_facts=dict(memories=[dict(summary='책방을 좋아한다')]),_read_evidence={'memory':{'state':'SUCCESS_WITH_ITEMS','count':1},'reminders':{'state':'FAILED'}})
  before=copy.deepcopy(context);out=self.compile(context,cfg)
  self.assertEqual(context,before);self.assertEqual(out.messages[-1],context[-1]);self.assertNotIn('FAILED',out.messages[0]['content']);self.assertNotIn('책방',out.messages[0]['content']);self.assertEqual(out.excluded,('local_facts',))
 def test_selected_memory_is_a_stored_report_not_verified_world_event(self):
  cfg=dict(_generation_facts=dict(memories=[dict(summary='사용자가 책방을 좋아한다고 말했다',source='synthetic-source')]),_read_evidence={'memory':{'state':'SUCCESS_WITH_ITEMS','count':1}})
  out=self.compile([dict(role='user',content='내 책방 취향은?')],cfg)
  self.assertIn('stored_user_reports',out.diagnostic()['sections']);self.assertIn('content_authority',out.messages[0]['content']);self.assertIn('REPORTED',out.messages[0]['content']);self.assertIn('synthetic-source',out.messages[0]['content'])
 def test_failed_and_not_authorized_never_receive_empty_count(self):
  for state in ('FAILED','NOT_AUTHORIZED','NOT_REQUESTED','PENDING','CANCELLED','STALE'):
   sections=evidence_sections('내 알림 목록은?',{'_read_evidence':{'reminders':{'state':state,'count':0}}})
   content=sections[0]['content'];self.assertIn(state,content);self.assertNotIn('"count":0',content)
  with self.assertRaises(ValueError):evidence_sections('내 알림은?',{'_read_evidence':{'reminders':{'state':'model_said_success'}}})
 def test_legacy_failed_scalar_remains_failed(self):
  self.assertIn('FAILED',self.compile([dict(role='user',content='내 기억은?')],{'_memory_lookup_state':'failed'}).messages[0]['content'])
 def test_carrier_text_or_equal_copy_cannot_elect_itself_as_verified(self):
  owned=dict(role='user',content='metadata-like text');copy_row=dict(owned)
  context=[copy_row,dict(role='assistant',content='확인했어'),dict(role='user',content='오늘은 수다')]
  out=self.compile(context,{'_generation_sources':((owned,'capabilities'),)})
  self.assertEqual(out.excluded,());self.assertTrue(any(m['content']=='metadata-like text' for m in out.messages))
 def test_identity_output_and_adult_contract_are_kept(self):
  out=self.compile([dict(role='user',content='안녕')],{'mood':'피곤함','_familiarity':73.5})
  header=out.messages[0]['content'];self.assertIn(INSTRUCTION,header);self.assertIn('하루',header);self.assertIn('피곤함',header);self.assertIn('consented_familiarity',header);self.assertIn('성인 유머는 현재 허용되지 않았다',header);self.assertIn('실제 신체·의식·욕구',header);self.assertIn('이전 친분',header)
 def test_only_full_user_sources_can_be_pinned_not_generated_claims(self):
  messages=[]
  for i in range(12):messages.extend([dict(role='user',content='책방에 간 건 실제가 아니라 가정이야' if i==1 else f'다른 주제 {i}'),dict(role='assistant',content='책방을 방문했고 등록했어')])
  messages.append(dict(role='user',content='전에 책방에 관해 내가 말한 건 뭐야?'))
  out=self.compile(messages);source=next(p['content'] for p in out.sections if p['name']=='earlier_user_sources')
  self.assertIn('실제가 아니라 가정',source);self.assertNotIn('등록했어',source);self.assertIn('REPORTED',source)

class NativeSelection(unittest.IsolatedAsyncioTestCase):
 async def test_budget_reclamation_keeps_pinned_original_negation(self):
  from echomate_bot.gguf_backend import GGUFEngine
  import test_runtime_context_budget as budget_cases
  with tempfile.TemporaryDirectory(dir='local_data') as d:
   p=Path(d);engine=GGUFEngine(p/'e',p/'m',p/'out');engine.session=budget_cases.Session();engine.url='http://127.0.0.1'
   history=[]
   for i in range(15):history.extend([dict(role='user',content='책방 방문은 가정이었어' if i==1 else f'다른 사건 {i}'),dict(role='assistant',content='방문이 확정됐어')])
   history.append(dict(role='user',content='아까 책방 방문 이야기를 기억해?'))
   compiled=compile_context(character('lime'),'하루',history,{},local_history=True)
   selected=await engine.fit_local_context(compiled.messages,384)
   self.assertIn('책방 방문은 가정이었어',selected[0]['content']);self.assertEqual(selected[-1],history[-1]);self.assertGreater(engine.last_context['removed_exchanges'],0)

class EvidenceProjection(unittest.TestCase):
 def test_success_confirmation_is_bound_to_the_successful_domain_only(self):
  cfg={'_read_evidence':{'memory':{'state':'SUCCESS_WITH_ITEMS','count':1},'reminders':{'state':'NOT_REQUESTED'}}}
  rows=evidence_sections('내 기억과 알림 상태는?',cfg)
  memory=next(r['content'] for r in rows if r['name']=='memory_read');reminder=next(r['content'] for r in rows if r['name']=='reminders_read')
  self.assertIn('실제 성공',memory);self.assertNotIn('실제 성공',reminder)
 def test_read_items_do_not_expose_internal_ids_or_raw_epoch(self):
  row=dict(reminder_id='12345678abcdefgh',text='합성 일정',due_at=0,timezone='Asia/Seoul',status='scheduled',guild='private-guild',requester='private-owner',source='private-source')
  cfg=dict(_read_evidence={'reminders':{'state':'SUCCESS_WITH_ITEMS','count':1}},_generation_facts={'read_results':{'reminders':[row]}})
  text=evidence_sections('내 알림 목록은?',cfg)[0]['content'];self.assertIn('1970-01-01 09:00',text);self.assertIn('12345678',text);self.assertNotIn('private-owner',text);self.assertNotIn('private-guild',text);self.assertNotIn('due_at',text)
 def test_original_memory_condition_source_and_time_survive_projection(self):
  from echomate_bot.generation_context import project_memories
  row=dict(summary='책방에 갈 수도 있지만 간 것은 아니야',source='original-id',observed_at=0,event_start_at=0,timezone='Asia/Seoul')
  result=project_memories([row],'UTC')[0];self.assertEqual(result['summary'],row['summary']);self.assertEqual(result['source'],'original-id');self.assertEqual(result['observed_local'],'1970-01-01 09:00');self.assertEqual(result['event_start_local'],'1970-01-01 00:00');self.assertEqual(result['event_timezone'],'UTC')

import test_local_chat as local_cases
class ActualLocalCarrier(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=local_cases.LocalRuntime.asyncSetUp
 asyncTearDown=local_cases.LocalRuntime.asyncTearDown
 async def test_owned_carrier_and_scoped_reports_are_passed_without_db_changes(self):
  await self.chat.send('/동의 기억 켜기',self.backend);await self.chat.send('/기억 저장 나는 작은 합성 책방을 좋아한다',self.backend)
  before=self.chat.store.memories(2,4,3);await self.chat.send('그 책방 이야기를 같이 해보자',self.backend)
  context,cfg=self.backend.text.call_args.args;self.assertIs(cfg['_generation_sources'][0][0],context[0]);self.assertEqual(cfg['_generation_facts']['current_speaker'],'A');self.assertEqual(self.chat.store.memories(2,4,3),before)
  self.assertEqual(cfg['_generation_facts']['memories'][0]['summary'],before[0]['summary'])

class WholeEvidence(unittest.TestCase):
 def test_late_negation_is_never_cut_into_a_different_fact(self):
  from echomate_bot.generation_context import project_memories,project_read_items
  text='가상 상황 설명 '*50+'실제로 한 것은 아니다'
  memory=project_memories([dict(summary=text,source='source-long')],'UTC')[0]
  self.assertNotIn('summary',memory);self.assertTrue(memory['summary_omitted']);self.assertEqual(memory['source'],'source-long')
  reminder=project_read_items('reminders',[dict(reminder_id='12345678',text=text,due_at=0,timezone='UTC',status='scheduled')])[0]
  self.assertNotIn('request_text',reminder);self.assertTrue(reminder['request_text_omitted'])
 def test_previously_truncated_receipt_payload_is_not_a_complete_fact(self):
  cfg=dict(_generation_facts={'recent_operations':[dict(kind='reminder',outcome='SUCCESS',request_text='긍정처럼 잘린 부분',request_text_truncated=True)]})
  rows=evidence_sections('방금 성공한 예약은?',cfg);text=next(r['content'] for r in rows if r['name']=='previous_receipts_still_current')
  self.assertNotIn('긍정처럼',text);self.assertIn('request_text_omitted',text)

class SummaryCertainty(unittest.TestCase):
 def test_known_negative_is_not_an_open_confirmation_question(self):
  from echomate_bot.summary_fidelity import check_fidelity
  source='그 일정은 확정된 계획이 아니라 가능한 선택지야.'
  with self.assertRaises(ValueError):check_fidelity('일정이 확정된 계획인지 확인',source,source)
  check_fidelity('일정은 확정된 것이 아니라 가능성이다',source,source)
 def test_original_question_is_not_rejected_as_a_negative_assertion(self):
  from echomate_bot.summary_fidelity import check_fidelity
  source='그 일정은 확정된 것이 아니야?'
  check_fidelity('일정의 확정 여부를 질문했다',source,source)
