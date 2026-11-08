"""Isolated identity research baseline. No production Discord writer."""

from contextlib import closing, contextmanager
from dataclasses import dataclass
from enum import Enum
import sqlite3

SCHEMA_ID = 1162037577
DELETED_REVISION = 2**63 - 1


class Topic(str, Enum):
    EVERYDAY = "everyday"
    PROJECT = "project"
    LEARNING = "learning"


class Feedback(str, Enum):
    BRIEFER = "briefer"
    MORE_DETAIL = "more_detail"


@dataclass(frozen=True)
class Scope:
    character: str
    guild: int
    channel: int  # A thread uses its own channel ID.
    subject: int

    def __post_init__(self):
        if not isinstance(self.character, str) or not 0 < len(self.character) <= 80:
            raise ValueError("invalid character identity")
        for value in (self.guild, self.channel, self.subject):
            positive_integer(value)

    def key(self):
        return self.character, str(self.guild), str(self.channel), str(self.subject)


def positive_integer(value):
    if type(value) is not int or not 0 < value < 2**63:
        raise ValueError("expected a positive SQLite integer")


@dataclass(frozen=True)
class State:
    """Topic-local expression policy in integer units; no user/world facts."""

    count: int = 0
    detail: int = 0
    step: int = 1
    last_direction: int = 0
    last_source: int | None = None
    last_revision: int | None = None

    def advance(self, source, revision, feedback):
        direction = 1 if Feedback(feedback) is Feedback.MORE_DETAIL else -1
        repeated = direction == self.last_direction
        effective_step = self.step if repeated else 1
        detail = max(-6, min(6, self.detail + direction * effective_step))
        # G: repeated explicit feedback increases plasticity; reversals reset it.
        step = min(2, self.step + 1) if repeated else 1
        return State(self.count + 1, detail, step, direction, source, revision)

    def guidance(self):
        if self.detail >= 2:
            return "필요한 설명을 조금 더 자세히 한다."
        if self.detail <= -2:
            return "핵심을 짧게 먼저 말한다."
        return None


class ExperienceJournal:
    """Dedicated SQLite journal for explicitly reviewed, subject-only feedback.

    authorize(scope, epoch) must consult a trusted, current permission source.
    The prototype does not provide atomicity with an external consent store.
    Source IDs and revisions are supplied by a trusted caller, never a model.
    """

    def __init__(self, path, *, authorize):
        self.path = path
        self.authorize = authorize
        with self._transaction() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            application = db.execute("PRAGMA application_id").fetchone()[0]
            if (application, version) == (0, 0):
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table'").fetchone():
                    raise ValueError("identity journal requires a dedicated database")
                db.execute("""
                    CREATE TABLE experience(
                        character TEXT NOT NULL, guild TEXT NOT NULL, channel TEXT NOT NULL,
                        subject TEXT NOT NULL, source INTEGER NOT NULL, revision INTEGER NOT NULL,
                        epoch INTEGER NOT NULL, topic TEXT, feedback TEXT, expires INTEGER,
                        PRIMARY KEY(character,guild,channel,subject,source)
                    )
                """)
                db.execute("""
                    CREATE TABLE revoked(
                        guild TEXT NOT NULL, subject TEXT NOT NULL, epoch INTEGER NOT NULL,
                        PRIMARY KEY(guild,subject)
                    )
                """)
                db.execute(f"PRAGMA application_id={SCHEMA_ID}")
                db.execute("PRAGMA user_version=1")
            elif (application, version) != (SCHEMA_ID, 1):
                raise ValueError("unsupported identity journal version")

    @contextmanager
    def _transaction(self, *, write=True):
        with closing(sqlite3.connect(self.path)) as db:
            if write:
                db.execute("PRAGMA secure_delete=ON")
            else:
                db.execute("PRAGMA query_only=ON")
            with db:
                db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                yield db

    def _allowed(self, db, scope, epoch):
        row = db.execute(
            "SELECT epoch FROM revoked WHERE guild=? AND subject=?",
            (str(scope.guild), str(scope.subject)),
        ).fetchone()
        return (row is None or epoch > row[0]) and self.authorize(scope, epoch) is True

    def record_feedback(self, scope, *, source, revision, epoch, topic, feedback, now, expires):
        for value in (source, revision, epoch, now, expires):
            positive_integer(value)
        if (revision == DELETED_REVISION or not isinstance(topic, Topic)
                or not isinstance(feedback, Feedback) or expires <= now):
            raise ValueError("expected reviewed feedback and a future expiry")
        with self._transaction() as db:
            if not self._allowed(db, scope, epoch):
                return False
            return bool(db.execute("""
                INSERT INTO experience VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(character,guild,channel,subject,source) DO UPDATE SET
                    revision=excluded.revision, epoch=excluded.epoch, topic=excluded.topic,
                    feedback=excluded.feedback, expires=excluded.expires
                WHERE excluded.revision > experience.revision
            """, (*scope.key(), source, revision, epoch, topic.value, feedback.value, expires)).rowcount)

    def invalidate_source(self, scope, *, source, revision, epoch, deleted=False):
        """Remove the contribution and reject retries of this or older revisions."""
        for value in (source, revision, epoch):
            positive_integer(value)
        if deleted:
            revision = DELETED_REVISION
        with self._transaction() as db:
            if not self._allowed(db, scope, epoch):
                return
            db.execute("""
                INSERT INTO experience VALUES(?,?,?,?,?,?,?,NULL,NULL,NULL)
                ON CONFLICT(character,guild,channel,subject,source) DO UPDATE SET
                    revision=excluded.revision, epoch=excluded.epoch,
                    topic=NULL, feedback=NULL, expires=NULL
                WHERE excluded.epoch >= experience.epoch AND excluded.revision >= experience.revision
            """, (*scope.key(), source, revision, epoch))

    def revoke(self, *, guild, subject, epoch):
        """Reject this and earlier epochs across all character and channel scopes."""
        for value in (guild, subject, epoch):
            positive_integer(value)
        key = str(guild), str(subject)
        with self._transaction() as db:
            db.execute("""
                INSERT INTO revoked VALUES(?,?,?)
                ON CONFLICT(guild,subject) DO UPDATE SET epoch=max(epoch,excluded.epoch)
            """, (*key, epoch))
            db.execute("DELETE FROM experience WHERE guild=? AND subject=? AND epoch<=?", (*key, epoch))

    def state(self, scope, *, epoch, topic, now):
        positive_integer(epoch)
        positive_integer(now)
        if not isinstance(topic, Topic):
            raise ValueError("expected a trusted topic")
        state = State()
        with self._transaction(write=False) as db:
            if not self._allowed(db, scope, epoch):
                return state
            rows = db.execute("""
                SELECT source,revision,feedback FROM experience
                WHERE character=? AND guild=? AND channel=? AND subject=?
                    AND epoch=? AND topic=? AND expires>?
                ORDER BY source
            """, (*scope.key(), epoch, topic.value, now))
            for source, revision, feedback in rows:
                state = state.advance(source, revision, feedback)
        return state
