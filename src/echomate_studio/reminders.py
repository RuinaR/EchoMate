"""Local durable reminder requests; Discord delivery is intentionally an adapter concern.

A claimed reminder is never automatically retried, preventing duplicate pings
at the cost of a possible missed reminder if the process crashes during send.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sqlite3

_REQUEST = re.compile(r"(?:오늘\s+)?(?:(?P<hours>[1-9][0-9]?)시간\s*)?(?:(?P<minutes>[1-9][0-9]?)분\s*)?후에?\s*(?:나\s*)?(?:멘션|알림|불러)\s*(?:해줘|해\s*줘|해줄래|부탁해)[!?.\s]*$")
_MAX_DELAY_SECONDS = 7 * 86400

def parse_reminder_request(message: str) -> timedelta | None:
    if not isinstance(message, str):
        return None
    match = _REQUEST.fullmatch(message.strip())
    if not match or (not match.group("hours") and not match.group("minutes")):
        return None
    seconds = int(match.group("hours") or 0) * 3600 + int(match.group("minutes") or 0) * 60
    if seconds < 60 or seconds > _MAX_DELAY_SECONDS:
        return None
    return timedelta(seconds=seconds)

class ReminderStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_message_id TEXT NOT NULL UNIQUE,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                requester_id INTEGER NOT NULL,
                due_at TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending'
                    CHECK(state IN ('pending','claimed','sent','failed'))
            )""")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.execute("PRAGMA busy_timeout=15000")
        return db

    def schedule(self, *, source_message_id: str, guild_id: int,
                 channel_id: int, requester_id: int, due_at: datetime) -> bool:
        if (not source_message_id or any(type(x) is not int or x <= 0
                for x in (guild_id, channel_id, requester_id)) or
                due_at.tzinfo is None):
            raise ValueError("valid message and Discord IDs, aware datetime required")
        with self._connect() as db:
            cursor = db.execute("""INSERT OR IGNORE INTO reminders
                (source_message_id,guild_id,channel_id,requester_id,due_at)
                VALUES (?,?,?,?,?)""",
                (source_message_id,guild_id,channel_id,requester_id,
                 due_at.astimezone(timezone.utc).isoformat()))
            return cursor.rowcount == 1

    def claim_due(self, now: datetime, *, limit: int = 25) -> list[dict]:
        if now.tzinfo is None or limit < 1 or limit > 100:
            raise ValueError("aware now and limit 1..100 required")
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("""SELECT id,guild_id,channel_id,requester_id
                FROM reminders WHERE state='pending' AND due_at<=?
                ORDER BY due_at,id LIMIT ?""",
                (now.astimezone(timezone.utc).isoformat(),limit)).fetchall()
            for row in rows:
                db.execute("UPDATE reminders SET state='claimed' WHERE id=? AND state='pending'",(row[0],))
            db.commit()
            return [dict(zip(("id","guild_id","channel_id","requester_id"),r)) for r in rows]
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def finish(self, reminder_id: int, *, sent: bool) -> bool:
        with self._connect() as db:
            return db.execute("UPDATE reminders SET state=? WHERE id=? AND state='claimed'",
                              ("sent" if sent else "failed",reminder_id)).rowcount == 1

def reminder_text(requester_id: int) -> str:
    if type(requester_id) is not int or requester_id <= 0:
        raise ValueError("requester ID required")
    return f"<@{requester_id}> 부탁한 시간이 됐어!"

def plan_reminder(store: ReminderStore, *, content: str, source_message_id: str,
                  guild_id: int, channel_id: int, requester_id: int,
                  now: datetime, allowed_channels: frozenset[int]) -> str:
    """Caller must check real bot identity, guild permissions and human authorship."""
    if channel_id not in allowed_channels:
        return "outside_scope"
    if now.tzinfo is None:
        raise ValueError("aware now required")
    delay = parse_reminder_request(content)
    if delay is None:
        return "not_supported"
    return "scheduled" if store.schedule(
        source_message_id=source_message_id, guild_id=guild_id,
        channel_id=channel_id, requester_id=requester_id, due_at=now+delay) else "duplicate"
