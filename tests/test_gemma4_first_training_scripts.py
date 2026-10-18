from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class Gemma4FirstTrainingScriptsTests(unittest.TestCase):
    def test_synthetic_gpu_script_ascii_and_private(self):
        text=(ROOT/"tools"/"run_gemma4_short_synthetic_e2e.ps1").read_bytes()
        self.assertTrue(text.isascii())
        decoded=text.decode("ascii")
        self.assertIn("--include-short-samples",decoded)
        self.assertIn("local_data",decoded)
        self.assertNotIn("messages1.json",decoded)
        self.assertNotIn("messages2.json",decoded)
    def test_first_training_script_has_three_approvals_and_preflight_gate(self):
        text=(ROOT/"tools"/"run_first_persona_training.ps1").read_bytes()
        self.assertTrue(text.isascii())
        code=text.decode("ascii")
        for flag in ("ConfirmRights","ConfirmPrivacyReview","ApprovePrivateTraining"):
            self.assertIn(flag,code)
        self.assertIn("gemma4_corpus_preflight.py",code)
        self.assertIn("if ($LASTEXITCODE -ne 0)",code)
        self.assertIn("train_persona_gemma4.py",code)
        self.assertNotIn("git push",code)
