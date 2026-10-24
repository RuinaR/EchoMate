import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from run_persona_pilot import development_regression
from persona_dataset import audit,compiler_hashes


class DevelopmentOnly(unittest.TestCase):
    def setUp(self):
        self.source=Path('tests/fixtures/persona_evidence_pilot.json');raw=self.source.read_bytes()
        self.records,_=audit(json.loads(raw));r=next(r for r in self.records if r['split']=='development')
        self.row=dict(id=r['id'],group=r['group'],character=r['character'],split='development',prompt=[1],input_ids=[1,2],labels=[-100,2])
        self.summary=dict(source_sha256=hashlib.sha256(raw).hexdigest(),compiler_hashes=compiler_hashes(),tokenizer_hashes={'synthetic':'sealed'})

    def invoke(self,row=None,identities=None,change=None):
        with tempfile.TemporaryDirectory(dir='local_data') as d:
            p=Path(d);raw=(json.dumps(row or self.row)+'\n').encode();(p/'development.jsonl').write_bytes(raw)
            summary={**self.summary,'development_sha256':hashlib.sha256(raw).hexdigest()}
            if change:summary.update(change)
            (p/'summary.json').write_text(json.dumps(summary),encoding='utf-8')
            return development_regression(self.source,p,identities or [self.row['id']],self.summary,16)

    def test_consumed_development_is_explicitly_not_independent_or_training(self):
        rows,manifest=self.invoke();self.assertEqual(rows,[self.row])
        self.assertIn('NOT independent',manifest['scope']);self.assertIn('NOT training',manifest['scope'])

    def test_train_or_independent_cannot_be_disguised_as_development(self):
        for split in ('train','independent'):
            r=next(r for r in self.records if r['split']==split);row={**self.row,'id':r['id'],'group':r['group'],'character':r['character']}
            with self.assertRaises(ValueError):self.invoke(row,[r['id']])

    def test_bad_mask_template_or_missing_ids_rejected(self):
        with self.assertRaises(ValueError):self.invoke({**self.row,'labels':[1,2]})
        with self.assertRaises(ValueError):self.invoke(change={'tokenizer_hashes':{'wrong':'template'}})
        with self.assertRaises(ValueError):self.invoke(identities=['not-a-development-id'])
