import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
class SyntheticTrainerQATests(unittest.TestCase):
    def test_script_is_synthetic_and_local(self):
        text = (ROOT / "tools" / "run_gemma4_synthetic_e2e.ps1").read_text(encoding="utf-8")
        self.assertIn("local_data\\gemma4-synthetic-e2e", text)
        self.assertIn("--max-steps 2 --seq-len 32", text)
        self.assertIn("Test-Path $out", text)
        self.assertNotIn("messages1.json", text)
        self.assertNotIn("messages2.json", text)
    def test_synthetic_dataset_is_distinct(self):
        text = (ROOT / "tools" / "run_gemma4_synthetic_e2e.ps1").read_text(encoding="utf-8")
        self.assertIn("$syntheticTrain", text)
        self.assertIn("$syntheticVal", text)
        self.assertIn("ConvertTo-Json -Compress", text)
