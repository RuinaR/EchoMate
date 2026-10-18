import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.model_compare import run_comparison


class ModelCompareTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"schema_version": 1, "weighted_mean_chars": 7.25,
                        "patterns": {"laugh": 0.04, "cry": 0.005, "unicode_emoji": 0.004}}

    def test_two_model_pairing(self):
        calls = []
        def fake(context, *, model, style):
            calls.append((model, context[0]["content"]))
            return "응"
        results = run_comparison(["qwen", "gemma"], self.profile, 2, fake)
        self.assertEqual(len(results), 20)
        self.assertEqual({r["model"] for r in results}, {"qwen", "gemma"})
        self.assertEqual(len(calls), 20)
        self.assertEqual(results[0]["model"], "qwen")
        self.assertEqual(results[2]["model"], "gemma")

    def test_failure_is_recorded(self):
        def fail(context, *, model, style):
            raise RuntimeError("failed")
        results = run_comparison(["qwen", "gemma"], self.profile, 1, fail)
        self.assertEqual(len(results), 10)
        self.assertEqual(results[0]["error"], "RuntimeError")

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            run_comparison(["same", "same"], self.profile)
        with self.assertRaises(ValueError):
            run_comparison(["a", "b"], self.profile, 0)
