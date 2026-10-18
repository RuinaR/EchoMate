import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.reminders import (
    ReminderStore,parse_reminder_request,plan_reminder,reminder_text
)

NOW=datetime(2026,10,18,12,0,tzinfo=timezone.utc)

class ReminderTests(unittest.TestCase):
    def test_natural_requests(self):
        self.assertEqual(parse_reminder_request("오늘 2시간 후에 나 멘션해줘"),timedelta(hours=2))
        self.assertEqual(parse_reminder_request("30분 후에 알림 해줘"),timedelta(minutes=30))
        self.assertEqual(parse_reminder_request("1시간 20분 후에 나 멘션해줘"),timedelta(hours=1,minutes=20))
        self.assertIsNone(parse_reminder_request("나중에 멘션해줘"))
        self.assertIsNone(parse_reminder_request("100시간 후에 멘션해줘"))
        self.assertIsNone(parse_reminder_request("2시간 후에 다른사람 멘션해줘"))

    def test_durable_reopen_and_exactly_one_claim(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"reminders.sqlite3"
            store=ReminderStore(path)
            self.assertTrue(store.schedule(source_message_id="m1",guild_id=1,channel_id=2,requester_id=3,
                                           due_at=NOW+timedelta(hours=2)))
            self.assertFalse(store.schedule(source_message_id="m1",guild_id=1,channel_id=2,requester_id=3,
                                            due_at=NOW+timedelta(hours=2)))
            reopened=ReminderStore(path)
            self.assertEqual(reopened.claim_due(NOW+timedelta(hours=1)),[])
            due=reopened.claim_due(NOW+timedelta(hours=2))
            self.assertEqual(len(due),1)
            self.assertEqual(due[0]["requester_id"],3)
            self.assertEqual(reopened.claim_due(NOW+timedelta(hours=3)),[])
            self.assertTrue(reopened.finish(due[0]["id"],sent=True))
            self.assertFalse(reopened.finish(due[0]["id"],sent=True))

    def test_scope_and_mention_identity(self):
        with tempfile.TemporaryDirectory() as d:
            store=ReminderStore(Path(d)/"r.db")
            opts=dict(content="오늘 2시간 후에 나 멘션해줘",source_message_id="1",
                guild_id=1,channel_id=2,requester_id=456,now=NOW)
            self.assertEqual(plan_reminder(store,**opts,allowed_channels=frozenset()),"outside_scope")
            self.assertEqual(plan_reminder(store,**opts,allowed_channels=frozenset({2})),"scheduled")
            self.assertEqual(plan_reminder(store,**opts,allowed_channels=frozenset({2})),"duplicate")
            self.assertEqual(reminder_text(456),"<@456> 부탁한 시간이 됐어!")

    def test_failed_send_no_auto_retry(self):
        with tempfile.TemporaryDirectory() as d:
            store=ReminderStore(Path(d)/"r.db")
            store.schedule(source_message_id="m",guild_id=1,channel_id=2,requester_id=3,due_at=NOW)
            due=store.claim_due(NOW)
            self.assertTrue(store.finish(due[0]["id"],sent=False))
            self.assertEqual(store.claim_due(NOW+timedelta(days=1)),[])
