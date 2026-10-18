import unittest
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.qlora_environment import inspect,PACKAGES

class QloraEnvironmentTests(unittest.TestCase):
    def test_no_gpu_check_by_default(self):
        result=inspect()
        self.assertEqual(result["status"],"diagnostic_only_no_training")
        self.assertFalse(result["training_environment_ready"])
        self.assertEqual(result["gpu"]["status"],"not_checked")
        self.assertEqual(set(result["packages"]),set(PACKAGES))
    @patch("echomate_studio.qlora_environment.shutil.which",return_value=None)
    def test_gpu_tool_absent(self,_):
        self.assertEqual(inspect(query_gpu=True)["gpu"]["status"],"nvidia_smi_missing")
    @patch("echomate_studio.qlora_environment.subprocess.run")
    @patch("echomate_studio.qlora_environment.shutil.which",return_value="nvidia-smi")
    def test_gpu_query(self,which,run):
        run.return_value.returncode=0
        run.return_value.stdout="NVIDIA RTX 4070, 12282, 9000, 8.9"
        out=inspect(query_gpu=True)
        self.assertEqual(out["gpu"]["status"],"ok")
        self.assertIn("4070",out["gpu"]["summary"])
        self.assertTrue(any(call.kwargs.get("timeout") == 10 and\n                            "--query-gpu=name,memory.total,memory.free,compute_cap" in call.args[0]\n                            for call in run.call_args_list),\n                        "nvidia-smi query must use a 10-second timeout")
