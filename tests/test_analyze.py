import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.analyze import analyze_file, normalize_text


class AnalysisTests(unittest.TestCase):
    def write(self, records):
        folder = tempfile.TemporaryDirectory()
        path = Path(folder.name) / "one_channel.json"
        path.write_text(json.dumps(records), encoding="utf-8")
        return folder, path

    def test_metadata_and_group_boundary(self):
        folder, path = self.write([
            {"ID": "1", "Timestamp": "2026-10-15 12:00:00", "Contents": "아니", "Attachments": ""},
            {"ID": "2", "Timestamp": "2026-10-15 12:00:03", "Contents": "ㅋㅋㅋ", "Attachments": ""},
            {"ID": "3", "Timestamp": "2026-10-15 12:01:00", "Contents": "<:a:12345>", "Attachments": ""},
            {"ID": "4", "Timestamp": "2026-10-15 12:02:00", "Contents": "", "Attachments": "https://cdn.discordapp.com/a.png"},
        ])
        try:
            r = analyze_file(path)
            self.assertEqual(r["total_records"], 4)
            self.assertEqual(r["text_records_after_filter"], 2)
            self.assertEqual(r["candidate_consecutive_groups"], 1)
            self.assertEqual(r["messages_with_custom_emoji"], 1)
            self.assertEqual(r["messages_with_attachments_or_media_links"], 1)
            self.assertNotIn("아니", str(r))
        finally:
            folder.cleanup()

    def test_duplicate_and_missing_fields(self):
        record = {"ID": 1, "Timestamp": "2026-10-01 01:00:00", "Contents": "응", "Attachments": ""}
        folder, path = self.write([record, record])
        try:
            self.assertEqual(analyze_file(path)["duplicate_ids_within_file"], 1)
        finally:
            folder.cleanup()
        folder, path = self.write([{"ID": 1}])
        try:
            with self.assertRaises(ValueError):
                analyze_file(path)
        finally:
            folder.cleanup()

    def test_emoji_filter_preserves_unicode(self):
        self.assertEqual(normalize_text("헉 😂 <:abc:123> <@123>"), "헉 😂")

    def test_empty_file(self):
        folder, path = self.write([])
        try:
            self.assertEqual(analyze_file(path)["total_records"], 0)
        finally:
            folder.cleanup()

    def test_invalid_parameter(self):
        folder, path = self.write([])
        try:
            with self.assertRaises(ValueError):
                analyze_file(path, half_life_days=0)
        finally:
            folder.cleanup()


if __name__ == "__main__":
    unittest.main()
