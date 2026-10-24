"""Fault injection only; existing private target must survive partial writes."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from echomate_bot.settings import atomic_private_json


class AtomicPrivateWrite(unittest.TestCase):
    def test_partial_temporary_write_is_cleaned_without_replacing_old_target(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'local_data') as folder:
            root=Path(folder);target=root/'state.json';old=b'{"synthetic":"old"}';target.write_bytes(old)
            write=Path.write_text
            def partial(path,*args,**kwargs):
                if path.suffix=='.tmp':
                    write(path,'synthetic partial');raise OSError('synthetic interrupted write')
                return write(path,*args,**kwargs)
            with patch.object(Path,'write_text',partial),self.assertRaisesRegex(OSError,'interrupted write'):
                atomic_private_json(target,dict(synthetic='new'))
            self.assertEqual(target.read_bytes(),old)
            self.assertEqual(list(root.iterdir()),[target])

    def test_replace_failure_keeps_retry_bound_and_cleans_temp(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'local_data') as folder:
            root=Path(folder);target=root/'state.json';target.write_bytes(b'old')
            with patch.object(Path,'replace',side_effect=PermissionError('synthetic locked')) as replace,patch('echomate_bot.settings.time.sleep'),self.assertRaises(PermissionError):
                atomic_private_json(target,dict(synthetic='new'))
            self.assertEqual(replace.call_count,5);self.assertEqual(target.read_bytes(),b'old')
            self.assertEqual(list(root.iterdir()),[target])
