import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
SPEC=importlib.util.spec_from_file_location("preview_persona_candidates",ROOT/"tools"/"preview_persona_candidates.py")
MOD=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

class CandidatePreviewTests(unittest.TestCase):
    def test_global_holdout_and_short_opt_in_no_text_exposure(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            a=root/"early.json"
            b=root/"late.json"
            early=[{"Timestamp":f"2020-01-{i+1:02d}T00:00:00Z",
                    "Contents":f"early invented sentence {i}"} for i in range(10)]
            late=[{"Timestamp":f"2025-01-{i+1:02d}T00:00:00Z",
                   "Contents":f"late invented sentence {i}"} for i in range(9)]
            late.append({"Timestamp":"2025-01-10T00:00:00Z","Contents":"ㅋㅋ"})
            a.write_text(json.dumps(early),encoding="utf-8")
            b.write_text(json.dumps(late),encoding="utf-8")
            base=MOD.preview([a,b])
            short=MOD.preview([a,b],preserve_two_char=True)
            self.assertEqual(base["counts"]["training_candidates"],18)
            self.assertEqual(base["counts"]["validation_candidates"],1)
            self.assertEqual(short["counts"]["validation_candidates"],2)
            self.assertEqual(short["counts"]["training_candidates"],18)
            self.assertNotIn("early invented",str(short))
            self.assertNotIn("late invented",str(short))
            self.assertTrue(short["global_chronological_cutoff"])
            self.assertEqual(short["status"],"aggregate_preview_only_no_training")

    def test_preview_no_approval_or_output_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            src=root/"messages.json"
            src.write_text(json.dumps([{"Timestamp":"2026-01-01T00:00:00Z",
                 "Contents":"synthetic text only"}]),encoding="utf-8")
            self.assertIsInstance(MOD.preview([src])["counts"],dict)
            self.assertEqual(sorted(p.name for p in root.iterdir()),["messages.json"])
            with self.assertRaises(ValueError):
                MOD.preview([src,src])
