import json
import unittest
from korean_claim_extraction import parse,messages,compare,calibration,aggregate


class ExtractionContract(unittest.TestCase):
    def test_source_anchor_and_semantic_fields_are_independent(self):
        c=next(c for c in calibration() if c['group']=='reminder-complete');atom=dict(c['atoms'][0]);atom.pop('span');atom['quote']=c['text']
        raw=json.dumps(dict(version=1,atoms=[atom]),ensure_ascii=False)
        self.assertTrue(compare(c,parse(raw,c['text']))['exact'])
        atom['feature']='memory'
        self.assertFalse(compare(c,parse(json.dumps(dict(version=1,atoms=[atom]),ensure_ascii=False),c['text']))['exact'])

    def test_made_up_ambiguous_or_duplicate_sources_fail_closed(self):
        c=calibration()[0];atom=dict(c['atoms'][0]);atom.pop('span');atom['quote']='없는 구간'
        with self.assertRaises(ValueError):parse(json.dumps(dict(version=1,atoms=[atom])),c['text'])
        with self.assertRaises(ValueError):parse('{"version":1,"version":1,"atoms":[]}',c['text'])
        atom['quote']=c['text']
        with self.assertRaises(ValueError):parse(json.dumps(dict(version=1,atoms=[atom,atom])),c['text'])

    def test_gold_and_evidence_are_not_in_extractor_input(self):
        c=calibration()[0];payload=messages(c['text'])[-1]['content']
        self.assertNotIn('gold',payload);self.assertNotIn('evidence',payload)
        self.assertEqual(len({c['text'] for c in calibration()}),len(calibration()))
        report=aggregate([dict(case=c,score=None)])
        self.assertFalse(report['eligible']);self.assertEqual(report['valid'],0)
        self.assertFalse(aggregate([])['eligible'])

    def test_single_json_fence_does_not_relax_atoms_or_accept_prose(self):
        c=calibration()[0];atom=dict(c['atoms'][0]);atom.pop('span');atom['quote']=c['text']
        body=json.dumps(dict(version=1,atoms=[atom]),ensure_ascii=False)
        self.assertTrue(compare(c,parse('```json\n'+body+'\n```',c['text']))['exact'])
        for raw in ('설명이야\n'+body,'설명이야\n```json\n'+body+'\n```','```python\n'+body+'\n```'):
            with self.assertRaises((ValueError,json.JSONDecodeError)):parse(raw,c['text'])
        atom['actor']='invented-user'
        with self.assertRaises(ValueError):parse('```json\n'+json.dumps(dict(version=1,atoms=[atom]))+'\n```',c['text'])
