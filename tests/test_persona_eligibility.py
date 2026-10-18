import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.persona_eligibility import audit_eligibility

class PersonaEligibilityTests(unittest.TestCase):
    def test_aggregate_and_no_content_leak(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"channel.json"
            contents=["안녕 반가워","안녕 반가워","ㅋㅋㅋㅋㅋㅋ","가",
                      "help@example.org","010-1234-5678","1234567890",
                      "유효한 고유 표현"]
            p.write_text(json.dumps([{"Contents":x} for x in contents],ensure_ascii=False),encoding="utf-8")
            out=audit_eligibility([p])
            counts=out["channels"][0]["counts"]
            self.assertEqual(counts["needs_human_review"],2)
            self.assertEqual(counts["exact_duplicate_in_channel"],1)
            self.assertEqual(counts["repetition_only"],1)
            self.assertEqual(counts["too_short_to_evaluate"],1)
            self.assertEqual(counts["potential_private_identifiers"],3)
            for secret in contents:
                self.assertNotIn(secret,str(out))
    def test_reject_duplicate_path(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"file.json"
            p.write_text("[]",encoding="utf-8")
            with self.assertRaises(ValueError):
                audit_eligibility([p,p])
    def test_channel_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.json"
            q=Path(d)/"b.json"
            for file in (p,q):
                file.write_text('[{"Contents":"같은 문자열"}]',encoding="utf-8")
            out=audit_eligibility([p,q])
            self.assertEqual([c["counts"]["needs_human_review"] for c in out["channels"]],[1,1])
