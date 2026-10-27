"""Structural provenance and quotation regressions, not a Korean accuracy judge."""
import json,unittest
from copy import deepcopy
from echomate_bot.structured import source_span,source_spans
from echomate_bot.correction_context import correction_view,correction_requested
from korean_claim_extraction import parse,parse_reading

class ExactSources(unittest.TestCase):
 def test_overlapping_occurrences_are_ambiguous_without_offsets(self):
  self.assertEqual(source_spans('가가가','가가'),((0,2),(1,3)))
  with self.assertRaises(ValueError):source_span('가가가','가가')
 def test_explicit_position_disambiguates_but_cannot_forge_a_quote(self):
  self.assertEqual(source_span('가가가','가가',[1,3]),(1,3))
  for span in ([True,2],[-1,1],[0,10],[0,1]):
   with self.assertRaises(ValueError):source_span('가가가','가가',span)
 def test_offsets_are_original_unicode_code_points_without_normalization(self):
  text='A🙂e\u0301Z';self.assertEqual(source_span(text,'e\u0301',[2,4]),(2,4));self.assertEqual(text,'A🙂e\u0301Z')
  with self.assertRaises(ValueError):source_span(text,'é',[2,3])
 def test_legacy_claim_extraction_rejects_overlapping_ambiguous_evidence(self):
  atom=dict(quote='가가',actor='bot',act='assertion',feature='memory',property='enabled',value=True,time='now')
  with self.assertRaises(ValueError):parse(json.dumps(dict(version=1,atoms=[atom])),'가가가')

class ReadingProposals(unittest.TestCase):
 def setUp(self):
  self.text='other says preference; later source correction is global'
  self.sources={'source1':dict(text=self.text,reporter='reporter4',version=2,at='synthetic-time')}
  self.item=dict(source='source1',span=[11,21],quote='preference',subject='other',quoted_speaker='unverified label',predicate='likes',polarity='positive',mode='reported',time='unknown',uncertainty=['subject unresolved'])
 def raw(self,item=None):return json.dumps(dict(version=1,items=[item or self.item]))
 def test_anchored_proposal_never_grants_storage_or_world_truth(self):
  result=parse_reading(self.raw(),self.sources);r=result['items'][0]
  self.assertFalse(result['runtime_enabled']);self.assertFalse(r['storage_eligible']);self.assertIn('unvalidated',r['deferred_reason']);self.assertEqual(r['reporter'],'reporter4');self.assertEqual(r['source_version'],2)
  # A well-anchored but wrong interpretation is still only a proposal.
  wrong=dict(self.item,subject='reporter',mode='asserted',uncertainty=[])
  self.assertFalse(parse_reading(self.raw(wrong),self.sources)['items'][0]['storage_eligible'])
 def test_full_context_keeps_late_correction_outside_local_candidate(self):
  r=parse_reading(self.raw(),self.sources)['items'][0];self.assertEqual(r['full_source'],self.text);self.assertIn('correction',r['full_source'])
 def test_model_cannot_supply_reporter_version_or_authorization(self):
  for name,value in [('reporter','invented'),('source_version',99),('storage_eligible',True),('confidence',1.)]:
   item=dict(self.item,**{name:value})
   with self.assertRaises(ValueError):parse_reading(self.raw(item),self.sources)
 def test_missing_unknown_or_modified_source_is_not_accepted(self):
  with self.assertRaises(ValueError):parse_reading(self.raw(),{})
  altered=deepcopy(self.sources);altered['source1']['text']='different source'
  with self.assertRaises(ValueError):parse_reading(self.raw(),altered)
 def test_no_evidence_is_not_a_successful_semantic_verdict(self):
  result=parse_reading('{"version":1,"items":[]}',self.sources)
  self.assertEqual(result['status'],'NO_EVIDENCE');self.assertFalse(result['runtime_enabled'])
 def test_duplicate_keys_or_duplicate_source_interpretations_are_rejected(self):
  with self.assertRaises(ValueError):parse_reading('{"version":1,"version":1,"items":[]}',self.sources)
  with self.assertRaises(ValueError):parse_reading(json.dumps(dict(version=1,items=[self.item,self.item])),self.sources)

class SharedQuotationView(unittest.TestCase):
 def test_quoted_correction_does_not_erase_previous_model_context(self):
  history=[dict(role='user',content='이전 발언'),dict(role='assistant',content='기존 응답'),dict(role='user',content="문자열 '정정할게.'를 읽었어.")];original=deepcopy(history)
  out,count=correction_view(history,history[-1]['content'],local_history=True)
  self.assertFalse(correction_requested(history[-1]['content']));self.assertEqual(count,0);self.assertEqual(out,original);self.assertEqual(history,original)
 def test_direct_correction_keeps_user_sources_and_marks_generated_claims(self):
  history=[dict(role='user',content='기존 원문'),dict(role='assistant',content='추측'),dict(role='user',content='정정할게. 그건 틀렸어.')];original=deepcopy(history)
  out,count=correction_view(history,history[-1]['content'],local_history=True)
  self.assertEqual(count,1);self.assertEqual(out[0],original[0]);self.assertEqual(out[-1],original[-1]);self.assertEqual(history,original)
