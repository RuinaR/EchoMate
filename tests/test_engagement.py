import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.engagement import EngagementPolicy, continue_engagement

class EngagementTests(unittest.TestCase):
    def test_continue_only_when_addressed_and_topic_continues(self):
        p=EngagementPolicy(max_gap_seconds=120)
        args=dict(ongoing=True,seconds_since_last_bot_reply=10,addressed_to_bot=True,topic_continues=True)
        self.assertTrue(continue_engagement(p,**args))
        self.assertFalse(continue_engagement(p,**{**args,"addressed_to_bot":False}))
        self.assertFalse(continue_engagement(p,**{**args,"topic_continues":False}))
        self.assertFalse(continue_engagement(p,**{**args,"seconds_since_last_bot_reply":121}))
    def test_invalid(self):
        with self.assertRaises(ValueError): EngagementPolicy(max_gap_seconds=0)
        self.assertFalse(continue_engagement(EngagementPolicy(enabled=False),
            ongoing=True,seconds_since_last_bot_reply=0,addressed_to_bot=True,topic_continues=True))
