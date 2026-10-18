import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.mention_reply import MentionPolicy, mentions_bot, permit_mention_reply

class MentionReplyTests(unittest.TestCase):
    def setUp(self):
        self.policy=MentionPolicy(allowed_channel_ids=frozenset({100}),cooldown_seconds=2)
        self.kw=dict(content="안녕 <@12345>", bot_user_id=12345, channel_id=100,
                     thread_id=None,author_is_bot=False,opted_out=False,seconds_since_last_reply=20)
    def test_exact_bot_id(self):
        self.assertTrue(mentions_bot("<@12345>",12345))
        self.assertTrue(mentions_bot("<@!12345>",12345))
        self.assertFalse(mentions_bot("<@123456>",12345))
        self.assertFalse(mentions_bot("이름만 언급 12345",12345))
    def test_direct_mention_pass(self):
        self.assertEqual(permit_mention_reply(self.policy,**self.kw),(True,"direct_mention"))
    def test_scope_bot_optout_and_cooldown(self):
        for change,reason in [({"channel_id":9},"outside_scope"),
                              ({"author_is_bot":True},"bot_message"),
                              ({"opted_out":True},"opt_out"),
                              ({"seconds_since_last_reply":0},"mention_cooldown")]:
            with self.subTest(reason=reason):
                kwargs={**self.kw,**change}
                self.assertEqual(permit_mention_reply(self.policy,**kwargs)[1],reason)
    def test_disabled_and_thread_allowlist(self):
        self.assertEqual(permit_mention_reply(MentionPolicy(enabled=False),**self.kw)[1],"mention_replies_disabled")
        policy=MentionPolicy(allowed_thread_ids=frozenset({777}),cooldown_seconds=0)
        self.assertTrue(permit_mention_reply(policy,**{**self.kw,"channel_id":9,"thread_id":777})[0])
    def test_not_mentioned(self):
        self.assertEqual(permit_mention_reply(self.policy,**{**self.kw,"content":"<@999> hi"})[1],"not_mentioned")
    def test_bad_config(self):
        with self.assertRaises(ValueError):
            MentionPolicy(cooldown_seconds=-1)
