"""Public bundle refresh cannot retain stale source bytecode or alter runtime."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest


class PortableManifest(unittest.TestCase):
    def test_refresh_removes_only_owned_source_cache_and_hashes_current_source(self):
        import sys
        sys.path.insert(0,str(Path('tools').resolve()))
        from build_portable import refresh
        Path('dist').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir='dist') as folder:
            root=Path(folder);(root/'manifest.json').write_text('{}',encoding='utf-8')
            (root/'EchoMate.vbs').write_text('Arguments.Named.Exists',encoding='ascii')
            cache=root/'src/echomate_bot/__pycache__';cache.mkdir(parents=True);(cache/'stale.pyc').write_bytes(b'old')
            runtime_cache=root/'runtime/Lib/__pycache__';runtime_cache.mkdir(parents=True);(runtime_cache/'keep.pyc').write_bytes(b'runtime')
            refresh(root)
            self.assertFalse(cache.exists());self.assertEqual((runtime_cache/'keep.pyc').read_bytes(),b'runtime')
            manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))['files']
            name='src/echomate_bot/inference.py'
            self.assertEqual(manifest[name]['sha256'],hashlib.sha256(Path(name).read_bytes()).hexdigest())
            self.assertFalse(any(k.startswith('src/') and k.endswith('.pyc') for k in manifest))

    def test_streaming_digest_matches_reference_across_multiple_blocks(self):
        import sys
        sys.path.insert(0,str(Path('tools').resolve()))
        from build_portable import file_sha256
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            p=Path(folder)/'public-fixture';data=b'abc123'*(600*1024);p.write_bytes(data)
            self.assertEqual(file_sha256(p),hashlib.sha256(data).hexdigest())
