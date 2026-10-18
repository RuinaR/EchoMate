import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.reaction_reply import choose_conversation_response
from echomate_studio.reactions import ReactionPolicy

class ReactionReplyTests(unittest.TestCase):
    def setUp(self):
        self.policy=ReactionPolicy(enabled=True,allowed_channel_ids=frozenset({10}),emojis=("❓","❤️","👍"))
    def choose(self,**kwargs):
        data=dict(text_reply="웅",suggested_emoji="❓",
                  ongoing_engagement=True,addressed_to_bot=True,topic_continues=True,
                  policy=self.policy,channel_id=10,thread_id=None)
        data.update(kwargs)
        return choose_conversation_response(**data)
    def test_semantic_reaction_replaces_text(self):
        self.assertEqual(self.choose().kind,"reaction")
        self.assertEqual(self.choose().emoji,"❓")
    def test_unverified_or_unrelated_uses_text(self):
        for change in ({"ongoing_engagement":False},{"addressed_to_bot":False},
                       {"topic_continues":False},{"channel_id":11},
                       {"opted_out":True},{"author_is_bot":True}):
            self.assertEqual(self.choose(**change).kind,"text")
    def test_unsupported_or_disabled(self):
        self.assertEqual(self.choose(suggested_emoji="❌").kind,"text")
        self.assertEqual(self.choose(policy=ReactionPolicy()).kind,"text")
    def test_empty_output_is_silent(self):
        self.assertEqual(self.choose(text_reply=None,suggested_emoji=None).kind,"silent")
    def test_thread_allowlist(self):
        p=ReactionPolicy(enabled=True,allowed_thread_ids=frozenset({99}),emojis=("❓",))
        self.assertEqual(self.choose(policy=p,channel_id=11,thread_id=99).kind,"reaction")
