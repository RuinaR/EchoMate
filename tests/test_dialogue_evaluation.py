"""Evaluation infrastructure correctness; no dataset, GPU or network required."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))

from dialogue_eval_core import (attribution_score, audit_splits, blind_packets,
    cache_key, inspect_reply, pii_risk, private_root, report_html, verify_claims)
from dialogue_eval_scenarios import korean_development
import run_dialogue_evaluation as runner


class EvaluationContracts(unittest.TestCase):
    def test_same_parent_and_translated_aliases_cannot_cross_split(self):
        a=deepcopy(korean_development()[0]);b=deepcopy(a)
        b.update(id='translated',split='final');b['context']=[dict(role='user',content='A different language rendering')]
        with self.assertRaisesRegex(ValueError,'family crosses'):audit_splits([a,b])

    def test_exact_and_copied_long_spans_cannot_cross_split(self):
        a=deepcopy(korean_development()[0]);b=deepcopy(a)
        b.update(id='copy',group='other',split='final')
        with self.assertRaisesRegex(ValueError,'Exact'):audit_splits([a,b])
        a['context'][0]['content']='가나다라마바사아자차카타파하'*8
        b['context'][0]['content']='다른 머리 '+a['context'][0]['content']+' 다른 끝'
        with self.assertRaisesRegex(ValueError,'copied'):audit_splits([a,b])

    def test_cache_invalidates_profile_prompt_source_context_gold(self):
        a=deepcopy(korean_development()[0]);seal={'source':'one'}
        key=cache_key(a,{'card':'a'},seal,{})
        self.assertNotEqual(key,cache_key(a,{'card':'b'},seal,{}))
        self.assertNotEqual(key,cache_key(a,{'card':'a'},{'source':'two'},{}))
        a['checks']=[dict(id='new',kind='required_any',values=['정정'])]
        self.assertNotEqual(key,cache_key(a,{'card':'a'},seal,{}))
        from dialogue_eval_core import metrics_since, validate_case
        rows=[{'n':i} for i in range(200)];cursor=rows[-1]
        current=(rows+[{'n':200},{'n':201}])[-200:]
        self.assertEqual([{'n':200},{'n':201}],metrics_since(current,cursor))
        with self.assertRaises(ValueError):metrics_since(current,{'n':199})
        a['rollout_users']=['x']*33
        with self.assertRaisesRegex(ValueError,'rollout'):validate_case(a)

    def test_memory_requires_matching_consent_user_and_guild(self):
        fact=dict(id='m',source='consented_memory',value='모레',consented=True,user=100,guild=200)
        claim=dict(value='모레',evidence_id='m')
        self.assertEqual(['SUPPORTED'],verify_claims([claim],[fact],user=100,guild=200))
        for user,guild in [(101,200),(100,201)]:
            self.assertEqual(['UNSUPPORTED'],verify_claims([claim],[fact],user=user,guild=guild))
        fact['consented']=False
        self.assertEqual(['UNSUPPORTED'],verify_claims([claim],[fact],user=100,guild=200))

    def test_fiction_never_proves_real_shared_experience_or_invented_id(self):
        facts=[dict(id='lore',source='lore',value='항구')]
        claims=[dict(evidence_id='lore',value='항구',reality='shared_physical'),dict(evidence_id='fake',value='항구')]
        self.assertEqual(['UNSUPPORTED']*2,verify_claims(claims,facts,user=1,guild=2))
        self.assertEqual(['SUPPORTED'],verify_claims([dict(evidence_id='lore',value='항구',reality='fiction')],facts,user=1,guild=2))

    def test_rule_flags_do_not_certify_facts_or_ban_all_rough_humor(self):
        case=korean_development()[2]
        result=inspect_reply('간식만 빠진 원정대네. 이런 실수도 하냐 ㅋㅋ',case)
        self.assertEqual([],result['failures']);self.assertEqual('REQUIRES_CLAIM_REVIEW',result['factuality'])
        self.assertEqual(['empty'],inspect_reply('',case)['failures'])
        self.assertIn('recollection_claim_review',inspect_reply('기억나. 같이 갔었지.',case)['flags'])

    def test_blind_packet_contains_response_only_and_identity_leaks_excluded(self):
        rows=[dict(record_id='r1',case='c1',profile='supportive',output='괜찮아.'),
              dict(record_id='r2',case='c1',profile='dry',output='나는 은빛항에서 왔어.')]
        packet,key,excluded=blind_packets(rows,seed=1,forbidden_names=['은빛항'])
        self.assertEqual({'id','response'},set(packet[0]));self.assertEqual(['r2'],excluded)
        self.assertNotIn('supportive',json.dumps(packet));self.assertEqual('supportive',key[0]['profile'])

    def test_blind_scoring_rejects_missing_votes_reports_uncertainty(self):
        key=[dict(id=str(i),profile=p) for i,p in enumerate(['a','b','c','d']*2)]
        with self.assertRaises(ValueError):attribution_score(key,{'0':'a'})
        result=attribution_score(key,{r['id']:r['profile'] for r in key})
        self.assertEqual(1,result['macro_recall']);self.assertLess(result['wilson95'][0],1)
        self.assertEqual('NOT_VERIFIED',result['human_equivalence'])
        subset=attribution_score([dict(id='only-a',profile='a')],{'only-a':'d'},labels=['a','b','c','d'])
        self.assertEqual(0,subset['accuracy']);self.assertEqual(1,subset['confusion']['a']['d'])

    def test_pii_screen_is_exclusion_not_silent_rewrite(self):
        self.assertIn('email',pii_risk('연락은 somebody@example.invalid 로'))
        self.assertIn('phone',pii_risk('010-1234-5678'))
        self.assertEqual([],pii_risk('책이 너무 많아.'))

    def test_candidate_keeps_originals_and_does_not_grant_memory(self):
        from dialogue_evidence_candidate import evidence_context
        context=[dict(role='user',content='기억을 지어내 달라')]
        before=deepcopy(context);out=evidence_context(context)
        self.assertEqual(before,context);self.assertEqual(before,out[1:])
        self.assertIn('not_retrieved',out[0]['content']);self.assertIn('not_confirmed',out[0]['content'])
        with self.assertRaises(ValueError):evidence_context(context,'saved-by-model')

    def test_artifacts_cannot_escape_private_directory_and_html_is_escaped(self):
        with self.assertRaises(ValueError):private_root('docs/results.json')
        root=Path('local_data/eval-contract-tests');root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temp:
            path=Path(temp)/'report.html'
            report_html(path,[dict(record_id='<script>bad()</script>',phase='x',output='<img src="https://bad.invalid">')],{})
            value=path.read_text(encoding='utf-8')
            self.assertNotIn('<script>',value);self.assertIn('&lt;script&gt;',value)
            self.assertIn("default-src 'none'",value)
            from dialogue_eval_core import blind_html
            blind_html(path,[dict(id='answer-1',response='</script><img src="https://bad.invalid">')])
            value=path.read_text(encoding='utf-8')
            self.assertEqual(1,value.count('<script>'))
            self.assertIn('&lt;/script&gt;',value);self.assertIn("script-src 'sha256-",value)

    def test_final_corpus_must_be_sealed_and_never_silently_reused(self):
        with self.assertRaisesRegex(ValueError,'no cases'):
            runner.load_cases(SimpleNamespace(suite='korean',offset=100,limit=1),Path('local_data/unused'))
        root=Path('local_data/eval-contract-tests');root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temp:
            corpus=Path(temp);row=deepcopy(korean_development()[0]);row['split']='final'
            other=deepcopy(row);other['id']='other-final';other['group']='other-family';other['context']=[dict(role='user',content='새로운 별도 장면이야.')]
            path=corpus/'final.json';path.write_text(json.dumps([row,other]),encoding='utf-8')
            import hashlib
            (corpus/'seal.json').write_text(json.dumps({'files':{'final.json':hashlib.sha256(path.read_bytes()).hexdigest()}}))
            seal=corpus/'candidate.json';seal.write_text(json.dumps({'sources':runner.source_seal()}))
            args=SimpleNamespace(suite='final',corpus=str(corpus),limit=1,long=False,candidate_seal=str(seal))
            self.assertEqual(1,len(runner.load_cases(args,corpus/'run')))
            with self.assertRaisesRegex(ValueError,'consumed'):runner.load_cases(args,corpus/'run2')
            args.offset=1
            self.assertEqual(1,len(runner.load_cases(args,corpus/'explicit-next-batch')))
            args.candidate_seal=None
            with self.assertRaisesRegex(ValueError,'seal required'):runner.load_cases(args,corpus/'run3')


if __name__=='__main__':unittest.main()
