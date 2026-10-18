import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.dialogue_state import DialogueState, Turn


class DialogueStateTests(unittest.TestCase):
    def setUp(self):
        self.state = DialogueState(limit=3, max_age_seconds=30)
        self.t = datetime(2026, 10, 18, tzinfo=timezone.utc)

    def add(self, mid, sec, channel=1, thread=None, author="u1", bot=False, reply=None):
        return self.state.append(channel_id=channel, thread_id=thread, turn=Turn(
            str(mid), author, str(mid), self.t + timedelta(seconds=sec), bot, reply))

    def test_channel_thread_isolation(self):
        self.add(1, 0, channel=1)
        self.add(2, 0, channel=2)
        self.add(3, 1, channel=1, thread=10)
        self.assertEqual([t.message_id for t in self.state.snapshot(channel_id=1, thread_id=None, now=self.t)[1]], ["1"])
        self.assertEqual([t.message_id for t in self.state.snapshot(channel_id=1, thread_id=10, now=self.t+timedelta(seconds=2))[1]], ["3"])

    def test_duplicate_and_out_of_order(self):
        self.assertTrue(self.add(1, 5))
        self.assertFalse(self.add(1, 5))
        self.assertFalse(self.add(2, 2))

    def test_capacity_and_ttl(self):
        for index in range(5):
            self.add(index, index)
        self.assertEqual(len(self.state.snapshot(channel_id=1, thread_id=None, now=self.t+timedelta(seconds=5))[1]), 3)
        self.assertEqual(len(self.state.snapshot(channel_id=1, thread_id=None, now=self.t+timedelta(seconds=100))[1]), 0)

    def test_stale_generation(self):
        self.add(1, 0)
        version, _ = self.state.snapshot(channel_id=1, thread_id=None, now=self.t)
        self.assertTrue(self.state.is_current(channel_id=1, thread_id=None, version=version))
        self.add(2, 1)
        self.assertFalse(self.state.is_current(channel_id=1, thread_id=None, version=version))

    def test_speaker_and_reply_context(self):
        turns = [Turn("m1", "alice", "메이플 할래?", self.t),
                 Turn("m2", "bob", "내일", self.t, reply_to="m1"),
                 Turn("m3", "bot", "몇 시?", self.t, is_bot=True)]
        out = self.state.to_model_context(turns)
        self.assertEqual([m["role"] for m in out], ["user", "user", "assistant"])
        self.assertIn("alice", out[0]["content"])
        self.assertIn("답장 대상 메시지 m1", out[1]["content"])
        self.assertEqual(out[2]["content"], "몇 시?")
