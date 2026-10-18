import random
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.participation import (
    ParticipationPolicy, ContextAssessment, SilenceReason, decide
)


class ParticipationTests(unittest.TestCase):
    def setUp(self):
        self.policy = ParticipationPolicy(
            enabled=True, allowed_channel_ids=frozenset({123}),
            opportunity_probability=1.0, cooldown_seconds=30, max_idle_seconds=600)
        self.good = ContextAssessment(False, True, True)

    def decision(self, assessment=None, policy=None, **kwargs):
        args = dict(channel_id=123, thread_id=None, is_bot_message=False,
                    opted_out=False, seconds_since_last_speech=100,
                    seconds_since_last_human_message=5, rng=random.Random(1))
        args.update(kwargs)
        return decide(policy or self.policy, assessment or self.good, **args)

    def test_high_frequency_still_silent_for_sensitive_context(self):
        result = self.decision(ContextAssessment(True, True, True))
        self.assertFalse(result.speak)
        self.assertEqual(result.reason, SilenceReason.SENSITIVE)

    def test_high_frequency_still_silent_when_nothing_to_add(self):
        self.assertEqual(self.decision(ContextAssessment(False, False, True)).reason,
                         SilenceReason.NO_CONTRIBUTION)

    def test_high_frequency_does_not_interrupt(self):
        self.assertEqual(self.decision(ContextAssessment(False, True, False)).reason,
                         SilenceReason.INTERRUPTION)

    def test_very_quiet_channel_stays_silent(self):
        self.assertEqual(self.decision(seconds_since_last_human_message=601).reason,
                         SilenceReason.INACTIVE)

    def test_allowed_context_can_speak(self):
        self.assertTrue(self.decision().speak)

    def test_guardrails(self):
        self.assertEqual(self.decision(channel_id=999).reason, SilenceReason.OUTSIDE_SCOPE)
        self.assertEqual(self.decision(is_bot_message=True).reason, SilenceReason.BOT_MESSAGE)
        self.assertEqual(self.decision(opted_out=True).reason, SilenceReason.OPT_OUT)
        self.assertEqual(self.decision(seconds_since_last_speech=2).reason, SilenceReason.COOLDOWN)

    def test_zero_frequency_and_invalid_config(self):
        p = ParticipationPolicy(enabled=True, allowed_channel_ids=frozenset({123}),
                                opportunity_probability=0, cooldown_seconds=0)
        self.assertEqual(self.decision(policy=p).reason, SilenceReason.RANDOM_GATE)
        with self.assertRaises(ValueError):
            ParticipationPolicy(opportunity_probability=1.1)
