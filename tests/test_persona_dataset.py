import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.persona_dataset import build

class PersonaDatasetTests(unittest.TestCase):
    def test_rights_and_review_both_required(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(PermissionError):
                build([],root/"local_data",rights_confirmed=True)
            self.assertFalse((root/"local_data").exists())
    def test_chronology_no_cross_split_text_leak(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            src=root/"messages.json"
            rows=[{"Timestamp":f"2020-01-{i+1:02d}T00:00:00Z",
                   "Contents":("shared phrase" if i==0 else f"private style phrase {i}")}
                  for i in range(9)]
            rows.append({"Timestamp":"2026-01-01T00:00:00Z","Contents":"shared phrase"})
            src.write_text(json.dumps(rows),encoding="utf-8")
            out=root/"local_data"/"persona-dataset"
            report=build([src],out,rights_confirmed=True,privacy_reviewed=True)
            training=(out/"persona-train.jsonl").read_text(encoding="utf-8")
            validation=(out/"persona-validation.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("shared phrase",training)
            self.assertIn("shared phrase",validation)
            self.assertEqual(report["counts"]["cross_split_excluded"],1)
            self.assertNotIn("shared phrase",str(report))
            self.assertTrue(all("text" in json.loads(x) for x in training.splitlines()))
    def test_unsafe_output_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(ValueError):
                build([root/"unused.json"],root/"public",rights_confirmed=True,privacy_reviewed=True)
