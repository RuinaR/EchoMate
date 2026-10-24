import hashlib,json
from pathlib import Path
import tempfile
import unittest
from audit_portable import audit


class FullAudit(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='local_data');self.root=Path(self.tmp.name)
        (self.root/'runtime').mkdir();(self.root/'runtime/python.exe').write_bytes(b'synthetic interpreter')
        self.files={'runtime/python.exe':dict(bytes=21,sha256=hashlib.sha256(b'synthetic interpreter').hexdigest())}
        self.save()
    def tearDown(self):self.tmp.cleanup()
    def save(self):
        (self.root/'manifest.json').write_text(json.dumps(dict(schema=1,python='synthetic',files=self.files)),encoding='utf-8')
    def test_full_hash_detects_same_size_tampering_without_repair(self):
        self.assertTrue(audit(self.root)['passed'])
        (self.root/'runtime/python.exe').write_bytes(b'Synthetic interpreter')
        self.assertEqual(audit(self.root)['mismatches'][0]['reason'],'sha256')
        self.assertEqual((self.root/'runtime/python.exe').read_bytes(),b'Synthetic interpreter')
    def test_manifest_cannot_escape_or_hide_extra_private_file(self):
        for name in ('../outside','C:/outside','runtime/../outside','runtime\\python.exe'):
            self.files={name:dict(bytes=0,sha256='0'*64)};self.save()
            with self.assertRaises(ValueError):audit(self.root)
        self.files={};self.save();(self.root/'settings.json').write_text('synthetic')
        self.assertFalse(audit(self.root)['passed']);self.assertIn('settings.json',audit(self.root)['extra'])
    def test_case_alias_and_boolean_size_are_rejected(self):
        self.files['RUNTIME/python.exe']=self.files['runtime/python.exe'];self.save()
        with self.assertRaises(ValueError):audit(self.root)
        self.files.pop('RUNTIME/python.exe');self.files['runtime/python.exe']['bytes']=True;self.save()
        with self.assertRaises(ValueError):audit(self.root)
    def test_case_insensitive_private_file_is_rejected_even_with_valid_hash(self):
        name='Settings.JSON';content=b'synthetic';(self.root/name).write_bytes(content)
        self.files[name]=dict(bytes=len(content),sha256=hashlib.sha256(content).hexdigest());self.save()
        self.assertEqual(audit(self.root)['forbidden'],[name])
