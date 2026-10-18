import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.persona_split_audit import audit, classify

def rec(text,year):
    return {"Contents":text,"Timestamp":f"{year}-01-01T00:00:00+00:00"}

class PersonaSplitAuditTests(unittest.TestCase):
    def test_chronology_and_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.json"
            rows=[rec(f"training text {i}",2020) for i in range(8)]
            rows += [rec("shared words",2020),rec("shared words",2026)]
            p.write_text(json.dumps(rows),encoding="utf-8")
            out=audit([p])
            self.assertEqual(out["counts"]["training_unique_candidates"],9)
            self.assertEqual(out["counts"]["validation_unique_candidates"],1)
            self.assertEqual(out["cross_split_duplicate_unique_texts"],1)
            self.assertEqual(out["validation_unique_after_overlap_removal"],0)
            self.assertNotIn("shared words",str(out))
    def test_direct_identifier_safety_hints(self):
        for message in ("https://example.invalid/a", "www.example.invalid",
                        "<@123456789012345678>", "token=abcdefghijklmnop",
                        "test@example.com"):
            self.assertEqual(classify({"Contents":message})[0], "identifier_hint")
        self.assertEqual(classify({"Contents":"invented ordinary phrase"})[0],"candidate")

    def test_reject_bad_fraction(self):
        with self.assertRaises(ValueError):
            audit([],validation_fraction=0.9)
    def test_invalid_timestamp_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.json"
            p.write_text(json.dumps([rec("normal text",2020),
                {"Contents":"private content","Timestamp":"bad"}]),encoding="utf-8")
            out=audit([p])
            self.assertEqual(out["counts"]["invalid_timestamp"],1)
