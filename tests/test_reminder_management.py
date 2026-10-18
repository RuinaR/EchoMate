import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.reminders import ReminderStore
from echomate_studio.reminder_commands import handle_reminder_management

NOW=datetime(2026,10,18,12,0,tzinfo=timezone.utc)

class ReminderManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"r.sqlite3"
        self.store=ReminderStore(self.path)
        self.store.schedule(source_message_id="m1",guild_id=1,channel_id=20,requester_id=100,due_at=NOW)
        self.store.schedule(source_message_id="m2",guild_id=1,channel_id=20,requester_id=200,due_at=NOW)
        self.store.schedule(source_message_id="m3",guild_id=2,channel_id=30,requester_id=100,due_at=NOW)
    def command(self,text,**kw):
        args=dict(content=text,guild_id=1,channel_id=20,requester_id=100,
                  allowed_channels=frozenset({20}))
        args.update(kw)
        return handle_reminder_management(self.store,**args)
    def test_list_only_own_guild_and_owner(self):
        res=self.command("내 예약 확인")
        self.assertEqual(res["status"],"listed")
        self.assertEqual(len(res["reminders"]),1)
        self.assertEqual(res["reminders"][0]["channel_id"],20)
        self.assertNotIn("requester_id",res["reminders"][0])
    def test_cancel_one_and_no_cross_user(self):
        self.assertEqual(self.command("예약 2 취소")["status"],"not_found")
        self.assertEqual(self.command("예약 3 취소")["status"],"not_found")
        self.assertEqual(self.command("예약 1 취소")["status"],"cancelled")
        self.assertEqual(self.command("예약 1 취소")["status"],"not_found")
        self.assertEqual(len(self.store.list_pending(guild_id=1,requester_id=200)),1)
        self.assertEqual(self.store.claim_due(NOW)[0]["requester_id"],200)
    def test_cancel_all_and_scope(self):
        self.assertEqual(self.command("내 예약 전부 취소",channel_id=999)["status"],"outside_scope")
        self.assertEqual(self.command("내 예약 전부 취소")["count"],1)
        self.assertEqual(self.command("예약 목록")["reminders"],[])
        self.assertEqual(len(self.store.list_pending(guild_id=2,requester_id=100)),1)
    def test_claimed_not_cancellable(self):
        self.store.claim_due(NOW,limit=1)
        self.assertFalse(self.store.cancel(guild_id=1,requester_id=100,reminder_id=1))
    def test_legacy_schema_migrates_without_losing_data(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"old.db"
            with sqlite3.connect(p) as db:
                db.execute("""CREATE TABLE reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_message_id TEXT NOT NULL UNIQUE,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    requester_id INTEGER NOT NULL,
                    due_at TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'pending'
                    CHECK(state IN ('pending','claimed','sent','failed')))""")
                db.execute("INSERT INTO reminders(source_message_id,guild_id,channel_id,requester_id,due_at) VALUES(?,?,?,?,?)",
                    ("legacy",1,20,100,NOW.isoformat()))
            store=ReminderStore(p)
            self.assertEqual(len(store.list_pending(guild_id=1,requester_id=100)),1)
            self.assertTrue(store.cancel(guild_id=1,requester_id=100,reminder_id=1))
            self.assertEqual(store.claim_due(NOW),[])
