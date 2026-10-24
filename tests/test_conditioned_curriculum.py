from copy import deepcopy
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from conditioned_curriculum import validate,export


class Curriculum(unittest.TestCase):
    def setUp(self):self.data=json.loads((Path(__file__).parent/'fixtures/conditioned_curriculum.json').read_text('utf-8'))
    def test_source_groups_and_character_targets(self):
        result=validate(self.data)
        self.assertEqual(result['counts'],dict(train=24,validation=8));self.assertEqual(result['groups'],8)
    def test_export_hashes_match_file_bytes_on_windows_too(self):
        source=Path(__file__).parent/'fixtures/conditioned_curriculum.json'
        with tempfile.TemporaryDirectory(dir=source.parents[2]/'local_data') as folder,patch('builtins.print'):
            root=Path(folder)/'export';export(source,root);m=json.loads((root/'manifest.json').read_text('utf-8'))
            for split in ('train','validation'):
                raw=(root/(split+'.jsonl')).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),m[split+'_sha256']);self.assertNotIn(b'\r\n',raw)
    def test_relabelled_same_source_is_not_independent_validation(self):
        row=deepcopy(self.data['scenarios'][0]);row.update(id='changed-id',split='validation');self.data['scenarios'].append(row)
        with self.assertRaisesRegex(ValueError,'Source group leakage'):validate(self.data)
    def test_completion_target_requires_own_consent_and_receipt(self):
        row=next(r for r in self.data['scenarios'] if r['evidence']['kind']=='completion')
        row['evidence']['receipts'][0]['owner']='other_user'
        with self.assertRaisesRegex(ValueError,'Foreign receipt'):validate(self.data)
        row['evidence']['receipts'][0]['owner']='speaker';row['evidence']['consent']=False
        with self.assertRaisesRegex(ValueError,'receipt/consent'):validate(self.data)
