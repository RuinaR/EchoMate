import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.context_compare import SCENARIOS, quality_hints, compare

class ContextCompareTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"schema_version": 1, "weighted_mean_chars": 7,
                        "patterns": {"laugh": 0.04, "cry": 0, "unicode_emoji": 0.003}}
    def test_unknown_time_hallucination(self):
        self.assertIn("fabricated_time_candidate",
                      quality_hints(SCENARIOS[0], "7시에 만나기로 했어"))
        self.assertNotIn("fabricated_time_candidate",
                         quality_hints(SCENARIOS[0], "시간을 정한 기록이 없어"))
    def test_changed_time(self):
        changed = SCENARIOS[2]
        self.assertIn("missing_known_fact", quality_hints(changed, "9시에 가자"))
        self.assertEqual(quality_hints(changed, "10시에 가자"), [])
    def test_model_receives_entire_context(self):
        contexts = []
        def fake(context, *, model, style):
            contexts.append((model, list(context)))
            return "10시"
        result = compare(["qwen", "gemma"], self.profile, generate_fn=fake)
        self.assertEqual(len(result), len(SCENARIOS) * 2)
        self.assertTrue(any(len(ctx) == 5 for _, ctx in contexts))
        self.assertEqual({name for name, _ in contexts}, {"qwen", "gemma"})
    def test_hanzi_flag(self):
        self.assertIn("hanzi_present", quality_hints(SCENARIOS[3], "哈哈"))
