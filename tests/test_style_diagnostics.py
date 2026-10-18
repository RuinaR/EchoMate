import json
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.style_diagnostics import diagnostics, ENDING

class StyleDiagnosticsTests(unittest.TestCase):
    def test_ending_patterns(self):
        examples = {"question": "뭐해?", "exclamation": "헐!", "period": "맞아.",
                    "laughter": "ㅋㅋㅋㅋ", "crying": "ㅠㅠ", "ellipsis": "음..."}
        for name, message in examples.items():
            with self.subTest(name=name):
                self.assertIsNotNone(ENDING[name].search(message))
                self.assertIsNotNone(ENDING[name].search(message + " "))
    def test_aggregates_without_leaking_text(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"messages.json"
            messages = [{"ID":str(i),"Timestamp":"2026-10-18T00:00:00","Contents":v,"Attachments":[]}
                        for i,v in enumerate(["비밀이야?", "ㅋㅋㅋ", "ㅠㅠ", "좋아.", "음..."])]
            p.write_text(json.dumps(messages,ensure_ascii=False),encoding="utf-8")
            report=diagnostics([p])
            self.assertEqual(report["text_count"],5)
            self.assertGreater(report["ending_rates"]["question"],0)
            self.assertGreater(report["ending_rates"]["laughter"],0)
            self.assertNotIn("비밀이야",str(report))
    def test_empty_and_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.json"
            p.write_text("[]",encoding="utf-8")
            self.assertEqual(diagnostics([p])["text_count"],0)
            with self.assertRaises(ValueError):
                diagnostics([p,p])
