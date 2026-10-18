"""Synthetic tests of supervision boundaries, split selection and privacy paths."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))
import persona_experiments as exp
from persona_report import summarize
from evaluate_persona_candidate import fresh_cases, retired_cases
import json
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


class Tokenizer:
    all_special_tokens = ["<bos>", "<turn|>"]
    unk_token_id = -1
    def apply_chat_template(self, messages, **kwargs):
        assert kwargs["enable_thinking"] is False
        assert kwargs["add_generation_prompt"] is True
        return {"input_ids": [1, 10, 11, 12]}
    def __call__(self, text, **kwargs):
        assert kwargs["add_special_tokens"] is False
        return {"input_ids": [20+i for i in range(len(text))]}
    def convert_tokens_to_ids(self, token):
        return 99


class PersonaExperimentTests(unittest.TestCase):
    def test_response_mask_keeps_first_response_and_end_turn(self):
        item = exp.style_example(Tokenizer(), "ㅋㅋ", 7)
        self.assertEqual(item["input_ids"], [1, 10, 11, 12, 20, 21, 99])
        self.assertEqual(item["labels"], [-100]*4 + [20, 21, 99])
        self.assertIsNone(exp.style_example(Tokenizer(), "ㅋㅋ", 6))
        self.assertIsNone(exp.style_example(Tokenizer(), "<turn|>", 100))

    def test_stratified_selection_is_unique_reproducible_and_short_aware(self):
        texts = ["a"*3]*50 + ["b"*12]*50 + ["c"*30]*50
        selected = exp.sampled_indices(texts, 20, 42)
        self.assertEqual(selected, exp.sampled_indices(texts, 20, 42))
        self.assertEqual(len(set(selected)), 20)
        self.assertEqual(sum(i < 50 for i in selected), 7)
        self.assertNotEqual(selected, exp.sampled_indices(texts, 20, 43))

    def test_private_path_rejects_sibling_local_data_and_traversal(self):
        with self.assertRaises(ValueError):
            exp.private_path(ROOT.parent/"other/local_data/result.json")
        with self.assertRaises(ValueError):
            exp.private_path(ROOT/"local_data/../public.json")
        self.assertEqual(exp.private_path(ROOT/"local_data/a.json").name, "a.json")

    def test_metrics_distinguish_truncation_and_memorization(self):
        text = "synthetic long private training sentence"
        m = exp.reply_metrics(text, 96, False, {text})
        self.assertTrue(m["exact_train_match"])
        self.assertTrue(m["long_train_substring"])
        self.assertFalse(m["ended"])

    def test_dashboard_counts_termination_without_treating_it_as_quality(self):
        rows = [dict(variant="base", chars=10, seconds=1., ended=True,
                     formal_marker=False, exact_train_match=True, long_train_substring=False),
                dict(variant="base", chars=30, seconds=3., ended=False,
                     formal_marker=True, exact_train_match=False, long_train_substring=True)]
        result = summarize({"results": rows})["base"]
        self.assertEqual(result["mean_chars"], 20.)
        self.assertEqual(result["ended"], 1)
        self.assertEqual(result["long_train_substrings"], 1)
        self.assertNotIn("quality_score", result)

    def test_pilot_bounds_reject_unbounded_steps_and_modality_targets(self):
        cfg = dict(steps=60, rank=4, seq_len=256, accumulation=2,
                   validation_samples=32, eval_every=20, patience=2,
                   lr=2e-5, dropout=.05, targets=["q_proj"])
        exp.validate_config(cfg)
        for changes in ({"steps": 5000}, {"targets": ["all-linear"]}, {"lr": .1}):
            with self.assertRaises(ValueError):
                exp.validate_config({**cfg, **changes})

    def test_replacement_holdout_is_distinct_and_has_real_chat_role_sequence(self):
        old = {json.dumps(case, ensure_ascii=False, sort_keys=True) for case in retired_cases()}
        fresh = fresh_cases()
        self.assertFalse(old & {json.dumps(case, ensure_ascii=False, sort_keys=True) for case in fresh})
        memory = next(text for category, text in fresh if category == "memory")
        self.assertEqual([m["role"] for m in memory], ["user", "assistant", "user"])

    def test_queue_propagates_child_failure_and_keeps_durable_status(self):
        private_test_root = ROOT/"local_data"
        private_test_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_test_root, prefix="synthetic-test-") as tmp:
            root = Path(tmp)
            plan = root/"plan.json"
            plan.write_text(json.dumps([{"id": "synthetic", "config": {}}]))
            args = SimpleNamespace(config=plan, output=root/"runs")
            with patch.object(exp, "PRIVATE", root), patch.object(exp.subprocess, "run",
                    return_value=SimpleNamespace(returncode=2)):
                with self.assertRaises(RuntimeError):
                    exp.queue(args)
            state = json.loads((root/"runs/queue-state.json").read_text())
            self.assertEqual(state["runs"]["synthetic"]["status"], "failed")
            self.assertEqual(state["runs"]["synthetic"]["exit_code"], 2)


if __name__ == "__main__":
    unittest.main()
