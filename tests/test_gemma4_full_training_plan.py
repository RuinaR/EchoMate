import ast
import importlib.util
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class Gemma4FullTrainingPlanTests(unittest.TestCase):
    def test_full_trainer_python_syntax_and_distinct_entrypoint(self):
        path=ROOT/"tools"/"train_persona_gemma4_full.py"
        tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
        self.assertTrue(any(isinstance(x,ast.FunctionDef) and x.name=="train" for x in tree.body))
        self.assertTrue(any(isinstance(x,ast.FunctionDef) and x.name=="main" for x in tree.body))
    def test_fail_closed_launch_and_not_approved_sources(self):
        script=(ROOT/"tools"/"run_full_persona_training.ps1").read_bytes()
        self.assertTrue(script.isascii())
        s=script.decode("ascii")
        for token in ("ConfirmRights","ConfirmPrivacyReview",
                      "ApprovePrivateTraining","gemma4_corpus_preflight.py",
                      "train_persona_gemma4_full.py","if ($LASTEXITCODE -ne 0)"):
            self.assertIn(token,s)
        self.assertNotIn("NOT-APPROVED.zip",s)
    def test_full_protocol_has_validation_and_rollback_checkpoint(self):
        s=(ROOT/"tools"/"train_persona_gemma4_full.py").read_text(encoding="utf-8")
        for token in ("validation_baseline","best_validation_loss","best_step",
                      "patience","save_pretrained","optimizer_resume_supported"):
            self.assertIn(token,s)

if __name__=="__main__":
    unittest.main()
