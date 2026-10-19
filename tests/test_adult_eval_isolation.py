"""The benchmark must release a whole CUDA process between inference engines."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
try:
    import evaluate_adult_models as evaluation
finally:
    sys.path.pop(0)


class EngineIsolation(unittest.IsolatedAsyncioTestCase):
    async def test_both_runs_separate_children_in_order_without_parent_gpu_lease(self):
        with tempfile.TemporaryDirectory(dir='local_data') as directory:
            root=Path(directory)/'run';engines=[]
            def child(command,**kwargs):
                engine=command[command.index('--engines')+1];engines.append(engine)
                output=Path(command[command.index('--output')+1]);output.mkdir()
                (output/'responses.jsonl').write_text(json.dumps(dict(condition=engine))+'\n')
                return subprocess.CompletedProcess(command,0)
            with patch.object(evaluation.subprocess,'run',side_effect=child), \
                 patch.object(evaluation,'InstanceLease',side_effect=AssertionError('Parent must not hold child lease')), \
                 patch.object(evaluation,'LocalBackend',side_effect=AssertionError('Parent must not load GPU')), \
                 patch.object(evaluation,'report') as report:
                await evaluation.run(root,Path(directory),'holdout',engines='both')
            self.assertEqual(engines,['torch','gguf'])
            self.assertEqual(len(report.call_args.args[1]),2)
            self.assertEqual(len((root/'responses.jsonl').read_text().splitlines()),2)

    async def test_failed_child_prevents_next_model_and_preserves_failure(self):
        with tempfile.TemporaryDirectory(dir='local_data') as directory:
            root=Path(directory)/'run'
            child=Mock(return_value=subprocess.CompletedProcess([],1))
            with patch.object(evaluation.subprocess,'run',child):
                with self.assertRaises(RuntimeError):
                    await evaluation.run(root,Path(directory),'holdout',engines='both')
            self.assertEqual(child.call_count,1)
            self.assertEqual(json.loads((root/'failure.json').read_text())['engine'],'torch')
