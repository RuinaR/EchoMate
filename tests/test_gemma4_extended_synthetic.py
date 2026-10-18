import importlib.util
import pathlib
import unittest
from unittest.mock import patch

PATH = pathlib.Path(__file__).resolve().parents[1] / "tools" / "smoke_gemma4_12b_lora.py"
SPEC = importlib.util.spec_from_file_location("gemma4_synthetic_extended", PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

class ExtendedSyntheticTests(unittest.TestCase):
    def test_steps_and_sequence_limits(self):
        for steps in (0, 4):
            with self.assertRaises(ValueError):
                mod.check(steps=steps)
        for length in (15, 65):
            with self.assertRaises(ValueError):
                mod.check(seq_len=length)
        self.assertEqual(mod.check(32, True, 3)["steps"], 3)

    def test_no_model_or_personal_data_without_optin(self):
        with patch.object(mod, "run", side_effect=AssertionError("ran")):
            report = mod.check(tokenizer_smoke=True)
        self.assertEqual(report["status"], "not_run")
        self.assertTrue(report["synthetic_only"])

    def test_fixed_synthetic_phrase_only(self):
        source = PATH.read_text(encoding="utf-8")
        self.assertIn("안녕! 오늘 게임 재밌다", source)
        self.assertNotIn("persona-train.jsonl", source)

if __name__ == "__main__":
    unittest.main()
