import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.dialogue_state import Turn
from echomate_studio.engagement_evidence import derive_engagement

NOW=datetime(2026,10,18,tzinfo=timezone.utc)
def t(mid, bot=False, reply=None):
    return Turn(mid,"bot" if bot else "human","내용",NOW,is_bot=bot,reply_to=reply)

class EngagementEvidenceTests(unittest.TestCase):
    def test_reply_to_bot_with_verified_topic(self):
        result=derive_engagement([t("a",True),t("b",reply="a")],topic_continues=True)
        self.assertTrue(result.ongoing_engagement)
        self.assertTrue(result.addressed_to_bot)
        self.assertTrue(result.topic_continues)
    def test_time_or_adjacent_message_does_not_prove_reply(self):
        result=derive_engagement([t("a",True),t("b")],topic_continues=True)
        self.assertFalse(result.addressed_to_bot)
    def test_reply_to_other_human_not_engagement(self):
        result=derive_engagement([t("a"),t("b",True),t("c",reply="a")],topic_continues=True)
        self.assertFalse(result.ongoing_engagement)
    def test_verified_reply_needs_topic_signal(self):
        result=derive_engagement([t("a",True),t("b",reply="a")])
        self.assertTrue(result.addressed_to_bot)
        self.assertFalse(result.topic_continues)
    def test_unknown_reference_or_bot_latest(self):
        self.assertFalse(derive_engagement([t("a",reply="missing")],topic_continues=True).addressed_to_bot)
        self.assertFalse(derive_engagement([t("a",True)],topic_continues=True).ongoing_engagement)
