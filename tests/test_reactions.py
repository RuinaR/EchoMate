import random
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.reactions import ReactionPolicy, choose_reaction


class ReactionTests(unittest.TestCase):
    def setUp(self):
        self.policy = ReactionPolicy(enabled=True, allowed_channel_ids=frozenset({10}),
                                     allowed_thread_ids=frozenset({20}),
                                     probability=1, cooldown_seconds=60,
                                     emojis=("👍",))

    def select(self, **extra):
        args = dict(channel_id=10, thread_id=None, is_bot_message=False,
                    is_own_message=False, opted_out=False, seconds_since_reaction=100,
                    rng=random.Random(0))
        args.update(extra)
        return choose_reaction(self.policy, **args)

    def test_enabled_allowed_channel(self):
        self.assertEqual(self.select(), "👍")

    def test_independent_thread_allowlist(self):
        self.assertEqual(self.select(channel_id=999, thread_id=20), "👍")
        self.assertIsNone(self.select(channel_id=999, thread_id=21))

    def test_no_bot_self_or_optout(self):
        self.assertIsNone(self.select(is_bot_message=True))
        self.assertIsNone(self.select(is_own_message=True))
        self.assertIsNone(self.select(opted_out=True))

    def test_cooldown_and_disable(self):
        self.assertIsNone(self.select(seconds_since_reaction=59))
        self.assertIsNone(choose_reaction(ReactionPolicy(), channel_id=10,
                          thread_id=None, is_bot_message=False, is_own_message=False,
                          opted_out=False, seconds_since_reaction=1000))

    def test_invalid_probability_and_custom_emoji(self):
        with self.assertRaises(ValueError):
            ReactionPolicy(probability=2)
        with self.assertRaises(ValueError):
            ReactionPolicy(emojis=("<:foo:123>",))

    def test_zero_probability(self):
        policy = ReactionPolicy(enabled=True, allowed_channel_ids=frozenset({10}),
                                probability=0, cooldown_seconds=0)
        self.assertIsNone(choose_reaction(policy, channel_id=10, thread_id=None,
                          is_bot_message=False, is_own_message=False,
                          opted_out=False, seconds_since_reaction=100))
