import json
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.style_profile import build_profile, profile_to_style

class StyleProfileTests(unittest.TestCase):
    def test_three_channels_and_no_message_leaks(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for i, contents in enumerate(("ㅋㅋㅋㅋ", "아 진짜?", "ㅇㅇ 😂")):
                path = Path(directory) / ("channel" + str(i) + ".json")
                path.write_text(json.dumps([{"ID":str(i),"Timestamp":"2026-10-18T00:00:00",
                    "Contents":contents,"Attachments":""}], ensure_ascii=False),encoding="utf-8")
                paths.append(path)
            report = build_profile(paths)
            self.assertEqual(report["source_channel_count"], 3)
            self.assertEqual(report["text_message_count"], 3)
            self.assertGreater(report["patterns"]["laugh"], 0)
            self.assertNotIn("아 진짜", str(report))
            self.assertIn("한국어", profile_to_style(report))

    def test_half_life_favors_newer_message(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "channel.json"
            p.write_text(json.dumps([
                {"ID":"1","Timestamp":"2025-01-01T00:00:00","Contents":"ㅋ"*100,"Attachments":""},
                {"ID":"2","Timestamp":"2026-10-18T00:00:00","Contents":"응","Attachments":""}
            ], ensure_ascii=False),encoding="utf-8")
            short = build_profile([p],half_life_days=30)
            long = build_profile([p],half_life_days=2000)
            self.assertLess(short["weighted_mean_chars"], long["weighted_mean_chars"])

    def test_duplicate_input_and_empty(self):
        with self.assertRaises(ValueError):
            build_profile([])
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "c.json"
            p.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_profile([p,p])
            self.assertEqual(build_profile([p])["text_message_count"],0)

if __name__ == "__main__":
    unittest.main()
