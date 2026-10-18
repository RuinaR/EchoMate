import importlib.util
import unittest
from pathlib import Path

p=Path(__file__).resolve().parents[1]/"tools"/"smoke_gemma4b_lora.py"
spec=importlib.util.spec_from_file_location("smoke_gemma4b_lora",p)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SyntheticLoRASmokeTests(unittest.TestCase):
    def test_no_training_default(self):
        result=module.preflight()
        self.assertEqual(result["status"],"not_run")
        self.assertTrue(result["synthetic_only"])
    def test_explicit_opt_in(self):
        result=module.preflight(allow_training=True,seq_len=32)
        self.assertEqual(result["status"],"ready")
    def test_reject_unbounded_lengths(self):
        for length in (-1,0,7,65,10000):
            with self.assertRaises(ValueError):
                module.preflight(allow_training=True,seq_len=length)
