import json
from pathlib import Path
import sys
import subprocess
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

    def test_cli_accepts_three_independent_channel_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = []
            for index in range(3):
                path = root / f"channel_{index}.json"
                record = {"ID": str(index + 1), "Timestamp": "2026-10-01 01:00:00",
                          "Contents": f"채널 {index} 테스트", "Attachments": ""}
                path.write_text(json.dumps([record], ensure_ascii=False), encoding="utf-8")
                paths.append(str(path))
            command = [sys.executable, "-m", "echomate_studio.analyze", *paths]
            process = subprocess.run(command, capture_output=True, text=True,
                                     check=True, env={**__import__("os").environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")})
            channels = json.loads(process.stdout)["channels"]
            self.assertEqual(len(channels), 3)
            self.assertEqual([item["total_records"] for item in channels], [1, 1, 1])
            self.assertEqual(len({item["source_label"] for item in channels}), 3)

    def test_invalid_parameter(self):
        folder, path = self.write([])
        try:
            with self.assertRaises(ValueError):
                analyze_file(path, half_life_days=0)
        finally:
            folder.cleanup()


if __name__ == "__main__":
    unittest.main()
