import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.corpus_audit import audit

class CorpusAuditTests(unittest.TestCase):
    def test_two_channels_not_joined_and_no_text_export(self):
        with tempfile.TemporaryDirectory() as d:
            paths=[]
            for i in (1,2):
                p=Path(d)/f"channel{i}.json"
                records=[{"ID":"1","Timestamp":"2026-10-18T00:00:02Z","Contents":"비밀원문ㅋㅋㅋㅋㅋㅋ","Attachments":[]},
                         {"ID":"2","Timestamp":"2026-10-18T00:00:01Z","Contents":"비밀원문ㅋㅋㅋㅋㅋㅋ","Attachments":[]}]
                p.write_text(json.dumps(records,ensure_ascii=False),encoding="utf-8")
                paths.append(p)
            r=audit(paths)
            self.assertEqual(r["channel_count"],2)
            self.assertEqual(r["channels"][0]["repeated_normalized_message_occurrences"],2)
            self.assertEqual(r["channels"][0]["adjacent_within_10_sec"],1)
            self.assertNotIn("비밀원문",str(r))
            self.assertTrue(r["channels"][1]["reverse_chronological"])
    def test_sensitivity_hints(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"channel.json"
            p.write_text(json.dumps([
                {"ID":"1","Timestamp":"2026-10-18T00:00:00Z","Contents":"ㅋㅋㅋㅋㅋㅋ","Attachments":[]},
                {"ID":"2","Timestamp":"2026-10-18T00:00:01Z","Contents":"hello@example.org 1234567890 https://x.test <@1234567>","Attachments":[]}
            ],ensure_ascii=False),encoding="utf-8")
            r=audit([p])["channels"][0]
            self.assertEqual(r["repeated_character_only"],1)
            self.assertEqual(r["potentially_sensitive_counts"]["urls"],1)
            self.assertEqual(r["potentially_sensitive_counts"]["email_shapes"],1)
            self.assertEqual(r["potentially_sensitive_counts"]["long_numbers"],1)
            self.assertEqual(r["potentially_sensitive_counts"]["mentions"],1)
            self.assertFalse(r["reverse_chronological"])
    def test_duplicate_paths_and_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.json";p.write_text("[]",encoding="utf-8")
            self.assertEqual(audit([p])["channels"][0]["record_count"],0)
            with self.assertRaises(ValueError): audit([p,p])
