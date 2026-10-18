import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.reply_quality import inspect_reply


class ReplyQualityTests(unittest.TestCase):
    def test_known_false_facts_and_role_confusion(self):
        self.assertIn("unverified_service_status_claim",
                      inspect_reply("메이플 할래?", "메이플은 서비스가 종료됐어"))
        self.assertIn("possible_physical_gameplay_claim",
                      inspect_reply("메이플 할래?", "응 지금 들어올게"))

    def test_topic_drift(self):
        self.assertIn("possible_topic_drift",
                      inspect_reply("아이고 힘들다", "누구랑 게임하자?"))

    def test_ordinary_reply_not_flagged(self):
        self.assertEqual(inspect_reply("아이고 힘들다", "무슨 일 있었어?"), [])

    def test_empty_and_emoji(self):
        self.assertEqual(inspect_reply("안녕", ""), ["empty_reply"])
        self.assertIn("unicode_emoji_present", inspect_reply("ㅋㅋ", "ㅋㅋ 😂"))
