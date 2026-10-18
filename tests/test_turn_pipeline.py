import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.dialogue_state import DialogueState, Turn
from echomate_studio.participation import ParticipationPolicy, ContextAssessment
from echomate_studio.turn_pipeline import evaluate_turn
from echomate_studio.mention_reply import MentionPolicy


class TurnPipelineTests(unittest.TestCase):
    def setUp(self):
        self.state = DialogueState()
        self.now = datetime(2026, 10, 18, tzinfo=timezone.utc)
        self.state.append(channel_id=1, thread_id=None, turn=Turn(
            "1", "human", "메이플 할래?", self.now))
        self.policy = ParticipationPolicy(enabled=True,
            allowed_channel_ids=frozenset({1}), opportunity_probability=1.0,
            cooldown_seconds=0)

    def run_turn(self, assessor=None, generator=None, **overrides):
        kwargs = dict(state=self.state, policy=self.policy, channel_id=1, thread_id=None,
            now=self.now, seconds_since_last_speech=300, seconds_since_last_human_message=0,
            assessor=assessor or (lambda _: ContextAssessment(False, True, True)),
            generator=generator or (lambda _: "응 좋아 😂"))
        kwargs.update(overrides)
        return evaluate_turn(**kwargs)

    def test_direct_mention_bypasses_autonomous_frequency(self):
        mention = MentionPolicy(allowed_channel_ids=frozenset({1}), cooldown_seconds=0)
        result = self.run_turn(
            policy=ParticipationPolicy(),
            mention_policy=mention, bot_user_id=123,
            latest_message_content="안녕 <@123>",
            assessor=lambda _: ContextAssessment(False, False, False))
        self.assertEqual(result.reason, "direct_mention_ready")
        self.assertIsNotNone(result.reply)

    def test_direct_mention_still_blocked_by_sensitivity(self):
        mention = MentionPolicy(allowed_channel_ids=frozenset({1}), cooldown_seconds=0)
        result = self.run_turn(
            policy=ParticipationPolicy(),
            mention_policy=mention, bot_user_id=123,
            latest_message_content="<@123> 지금?",
            assessor=lambda _: ContextAssessment(True, True, True))
        self.assertEqual(result.reason, "context_veto")

    def test_direct_mention_scope_and_optout(self):
        mention = MentionPolicy(allowed_channel_ids=frozenset({5}), cooldown_seconds=0)
        result = self.run_turn(policy=ParticipationPolicy(),
            mention_policy=mention, bot_user_id=123, latest_message_content="<@123>")
        self.assertEqual(result.reason, "outside_scope")
        allowed = MentionPolicy(allowed_channel_ids=frozenset({1}), cooldown_seconds=0)
        result = self.run_turn(policy=ParticipationPolicy(),
            mention_policy=allowed, bot_user_id=123,
            latest_message_content="<@123>", opted_out=True)
        self.assertEqual(result.reason, "opt_out")

    def test_ready(self):
        result = self.run_turn()
        self.assertEqual(result.reply, "응 좋아 😂")
        self.assertEqual(result.reason, "ready")

    def test_sensitive_context_blocks_generation(self):
        called = []
        result = self.run_turn(
            assessor=lambda _: ContextAssessment(True, True, True),
            generator=lambda _: called.append(1))
        self.assertIsNone(result.reply)
        self.assertFalse(called)

    def test_disabled_does_not_call_models(self):
        called = []
        result = self.run_turn(policy=ParticipationPolicy(),
            assessor=lambda _: called.append(1),
            generator=lambda _: called.append(2))
        self.assertIsNone(result.reply)
        self.assertFalse(called)

    def test_new_message_invalidates_generated_response(self):
        def generate(_):
            self.state.append(channel_id=1, thread_id=None, turn=Turn(
                "2", "human", "아니 취소", self.now))
            return "좋아"
        result = self.run_turn(generator=generate)
        self.assertEqual(result.reason, "stale_after_generation")
        self.assertIsNone(result.reply)

    def test_model_failure_is_silence(self):
        def broken(_):
            raise RuntimeError("offline")
        self.assertEqual(self.run_turn(assessor=broken).reason, "assessor_error")
        self.assertEqual(self.run_turn(generator=broken).reason, "generation_error")

    def test_no_human_context(self):
        state = DialogueState()
        self.assertEqual(self.run_turn(state=state).reason, "no_recent_human_context")
