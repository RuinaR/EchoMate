import copy
import json
from pathlib import Path
import unittest
from persona_dataset import audit,messages_for


class DatasetContract(unittest.TestCase):
    def setUp(self):self.data=json.loads((Path(__file__).parent/'fixtures/persona_evidence_pilot.json').read_text('utf-8'))
    def test_balanced_source_split_and_unseen_families(self):
        records,s=audit(self.data)
        self.assertEqual(s['splits'],dict(train=64,development=16,independent=24));self.assertFalse(s['near_duplicates'])
        self.assertFalse({r['group'] for r in records if r['split']=='train'}&{r['group'] for r in records if r['split']!='train'})
        self.assertFalse(any(r['character'] in ('shy','curious') for r in records if r['split']=='train'))
    def test_source_variants_cannot_cross_split(self):
        self.data['cases'][-1]['source_group']=self.data['cases'][0]['source_group']
        with self.assertRaises(ValueError):audit(self.data)
    def test_target_span_and_evidence_cannot_be_promoted(self):
        case=next(c for c in self.data['cases'] if c['evidence']);atom=case['responses']['gentle']['claims'][0]
        for field,value in [('text','다른 내용'),('state','confirmed'),('scope','execution_receipt'),('act','completion')]:
            with self.subTest(field=field):
                x=copy.deepcopy(self.data);c=next(c for c in x['cases'] if c['evidence']);c['responses']['gentle']['claims'][0][field]=value
                with self.assertRaises(ValueError):audit(x)
    def test_missing_claim_review_rejected(self):
        c=next(c for c in self.data['cases'] if c['evidence']);c['responses']['gentle']['claims']=[]
        with self.assertRaises(ValueError):audit(self.data)
    def test_completion_requires_real_fixture_receipt(self):
        c=next(c for c in self.data['cases'] if c['evidence'] and c['evidence'][0].get('receipt'));del c['evidence'][0]['receipt']
        with self.assertRaises(ValueError):audit(self.data)
    def test_no_target_or_rubric_in_prompt(self):
        records,_=audit(self.data)
        for r in records:
            serialized=json.dumps(messages_for(r,self.data),ensure_ascii=False)
            self.assertNotIn(r['response']['text'],serialized);self.assertNotIn(r['response']['strategy'],serialized)
            self.assertEqual(messages_for(r,self.data)[-1]['content'],r['case']['user'])
    def test_private_identifier_and_exact_target_duplicate(self):
        for kind in ('id','duplicate'):
            x=copy.deepcopy(self.data)
            if kind=='id':x['cases'][0]['user']='사용자 123456789012345678'
            else:x['cases'][0]['responses']['playful']['text']=x['cases'][0]['responses']['gentle']['text']
            with self.assertRaises(ValueError):audit(x)
    def test_noncommercial_source_cannot_be_relabeled(self):
        self.data['provenance']['license']='CC-BY-NC-4.0'
        with self.assertRaises(ValueError):audit(self.data)
