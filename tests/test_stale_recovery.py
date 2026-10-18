import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.dialogue_state import DialogueState, Turn
from echomate_studio.turn_pipeline import TurnResult
from echomate_studio.stale_recovery import recover_latest


class StaleRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.state = DialogueState()
        self.now = datetime.now(timezone.utc)
        self.add("1", "hello", 0)

    def add(self, mid, text, seconds):
        self.state.append(channel_id=1, thread_id=None,
                          turn=Turn(mid, "user", text, self.now + timedelta(seconds=seconds)))

    def call(self, evaluate, **extra):
        return recover_latest(state=self.state, channel_id=1, thread_id=None,
                              evaluate=evaluate, **extra)

    def test_stable_answer(self):
        result = self.call(lambda: TurnResult("좋아", "ready", 1))
        self.assertEqual(result.reply, "좋아")
        self.assertEqual(result.attempts, 1)

    def test_message_arrives_and_restarts(self):
        count = [0]
        def evaluate():
            count[0] += 1
            if count[0] == 1:
                self.add("2", "아니, 내일", 1)
                return TurnResult(None, "stale_after_generation", 1)
            return TurnResult("내일 가자", "ready", 2)
        result = self.call(evaluate)
        self.assertEqual(result.reply, "내일 가자")
        self.assertEqual(result.attempts, 2)

    def test_continuous_changes_silence(self):
        counter = [1]
        def evaluate():
            counter[0] += 1
            self.add(str(counter[0]), "또 바뀜", counter[0])
            return TurnResult(None, "stale_after_generation", counter[0]-1)
        result = self.call(evaluate)
        self.assertIsNone(result.reply)
        self.assertEqual(result.reason, "stale_retry_exhausted")

    def test_nonmaterial_must_be_explicit(self):
        def evaluate():
            self.add("2", "ㅋㅋ", 1)
            return TurnResult("응", "ready", 1)
        self.assertIsNone(self.call(evaluate, max_attempts=1).reply)

    def test_invalid_retry_count(self):
        with self.assertRaises(ValueError):
            self.call(lambda: TurnResult(None, "disabled", 0), max_attempts=0)
