"""Tiny official serialization fixtures; never opens actual model weights."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class ShardedPreparation(unittest.TestCase):
    def test_tensor_roundtrip_preserves_source_and_refuses_overwrite(self):
        import sys
        sys.path.insert(0,str(Path('tools').resolve()))
        import torch
        from safetensors.torch import save_file
        from prepare_sharded_model import stage
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            root=Path(folder);source=root/'model.safetensors'
            save_file({'a':torch.arange(512,dtype=torch.float32),'b':torch.arange(512,dtype=torch.int32)},source)
            before=hashlib.sha256(source.read_bytes()).hexdigest()
            with patch('prepare_sharded_model.model_memory_budget'):
                with self.assertRaises(ValueError):stage(source,root/'oversized',1024)
                self.assertFalse((root/'oversized').exists())
                result=stage(source,root/'shards',2048)
                self.assertEqual(result['tensor_count'],2);self.assertEqual(result['shards'],2)
                self.assertTrue((root/'shards/model.safetensors.index.json').exists())
                with self.assertRaises(ValueError):stage(source,root/'shards',1024)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
            self.assertFalse(result['selected_in_app'])

    def test_insufficient_space_is_rejected_before_copy_or_tensor_import(self):
        import sys
        sys.path.insert(0,str(Path('tools').resolve()))
        from prepare_sharded_model import stage
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            root=Path(folder);source=root/'model.safetensors';source.write_bytes(b'not-weights')
            with patch('prepare_sharded_model.shutil.disk_usage',return_value=SimpleNamespace(free=0)):
                with self.assertRaises(OSError):stage(source,root/'out')
            self.assertFalse((root/'out').exists())
