"""Explicit synthetic Runtime integration for one channel and a v8 store."""
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import asyncio
import hashlib
import threading

from .character_store import CharacterCompanionStore
from .identity_continuity import ExperienceJournal, Scope, Topic, positive_integer


class SourceStatus(Enum):
    FOUND = "found"
    DELETED = "deleted"
    UNAVAILABLE = "unavailable"
    CHANGED = "changed"
    FORBIDDEN = "forbidden"
    NETWORK = "network_failure"
    RATE_LIMITED = "rate_limited"
    STALE = "stale"
    STORAGE = "storage_failure"


@dataclass(frozen=True)
class SourceObservation:
    status: SourceStatus
    scope: Scope
    source: int
    revision: int | None = None
    digest: str | None = None


def content_digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ChannelExperience(ExperienceJournal):
    """Use the companion transaction as the authority, with no second DB sync.

    Only a trusted reviewer may call record_feedback with an authenticated
    message source. Neither ingestion nor model generation calls the writer.
    """

    def __init__(self, companion, *, guild, channel, topic):
        if not isinstance(companion, CharacterCompanionStore) or not companion.character_id:
            raise ValueError("a character v8 store is required")
        positive_integer(guild)
        positive_integer(channel)
        if not isinstance(topic, Topic):
            raise ValueError("a reviewed topic is required")
        self.companion = companion
        self.place = guild, channel
        self.topic = topic
        self._verification_lock = threading.RLock()
        self._reconcile_lock = asyncio.Lock()
        self._generation = 0
        self._verified = set()
        self._last_result = None
        with self._transaction() as db:
            self.create_tables(db)
            db.execute("""
                CREATE TABLE IF NOT EXISTS experience_evidence(
                    character TEXT, guild TEXT, channel TEXT, subject TEXT, source INTEGER,
                    revision INTEGER NOT NULL, digest TEXT NOT NULL,
                    PRIMARY KEY(character,guild,channel,subject,source),
                    FOREIGN KEY(character,guild,channel,subject,source)
                        REFERENCES experience(character,guild,channel,subject,source) ON DELETE CASCADE
                )
            """)
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS experience_evidence_invalidated
                AFTER UPDATE OF feedback ON experience WHEN NEW.feedback IS NULL
                BEGIN
                    DELETE FROM experience_evidence WHERE character=NEW.character AND guild=NEW.guild
                        AND channel=NEW.channel AND subject=NEW.subject AND source=NEW.source;
                END
            """)
            db.execute("DROP TRIGGER IF EXISTS experience_consent_changed")
            db.execute("DROP TRIGGER IF EXISTS experience_consent_deleted")
            db.execute("CREATE INDEX IF NOT EXISTS experience_subject ON experience(guild,subject)")
            db.execute("CREATE INDEX IF NOT EXISTS experience_source ON experience(guild,source)")
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS experience_adaptation_changed
                AFTER UPDATE OF enabled,version ON consent_choices
                WHEN NEW.category='adaptation' AND
                    (NEW.enabled != 1 OR NEW.version != OLD.version)
                BEGIN
                    DELETE FROM experience WHERE guild=NEW.guild AND subject=NEW.user;
                END
            """)
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS experience_adaptation_deleted
                AFTER DELETE ON consent_choices WHEN OLD.category='adaptation'
                BEGIN
                    DELETE FROM experience WHERE guild=OLD.guild AND subject=OLD.user;
                END
            """)
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS experience_adaptation_disabled
                AFTER INSERT ON consent_choices WHEN NEW.category='adaptation' AND NEW.enabled=0
                BEGIN
                    DELETE FROM experience WHERE guild=NEW.guild AND subject=NEW.user;
                END
            """)
            # v8's namespace rewriter scopes tombstones, while Discord source
            # IDs are globally unique. Delete every contribution of that source.
            trigger = companion.prefix + "experience_source_deleted"
            db.execute(f"""
                CREATE TRIGGER IF NOT EXISTS {trigger} AFTER INSERT ON tombstones
                BEGIN
                    DELETE FROM experience WHERE guild=NEW.guild AND source=CAST(NEW.source AS INTEGER);
                END
            """)

    @contextmanager
    def _transaction(self, *, write=True):
        with self.companion.db() as db:
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield db

    def accepts(self, guild, channel, parent=None):
        return parent is None and (guild, channel) == self.place

    def quarantine(self, reason=None):
        """Verification is intentionally never restored from SQLite or backup."""
        with self._verification_lock:
            self._generation += 1
            self._verified.clear()
            self._last_result = reason

    def verification_status(self):
        with self._verification_lock:
            return {"session_marks": len(self._verified), "last_result": self._last_result}

    def record_feedback(self, scope, *, source, revision, epoch, topic, feedback, now, expires, digest):
        # Only the trusted reviewer of a current source may invoke this method.
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError("expected a source content digest")
        with self._verification_lock:
            generation = self._generation
        self._validate_feedback(source,revision,epoch,topic,feedback,now,expires)
        if topic is not self.topic:
            raise ValueError("feedback topic does not match this journal")
        with self._transaction() as db:
            if not self._allowed(db,scope,epoch) or not self._source_allowed(db,scope,source):
                return False
            saved=self._store_feedback(db,scope,source,revision,epoch,topic,feedback,expires)
            if saved:
                db.execute("""
                    INSERT INTO experience_evidence VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(character,guild,channel,subject,source) DO UPDATE
                    SET revision=excluded.revision,digest=excluded.digest
                """, (*scope.key(),source,revision,digest))
        if saved:
            self._confirm(generation, scope, epoch, source, revision)
        return saved

    def _digest(self, scope, source, revision):
        with self._transaction(write=False) as db:
            row=db.execute("""
                SELECT digest FROM experience_evidence WHERE character=? AND guild=? AND
                    channel=? AND subject=? AND source=? AND revision=?
            """, (*scope.key(),source,revision)).fetchone()
            return row[0] if row else None

    def _confirm(self, generation, scope, epoch, source, revision):
        with self._verification_lock:
            if generation == self._generation:
                self._verified.add((scope, epoch, source, revision))

    async def reconcile(self, scope, *, epoch, fetch_source, limit=20, current=lambda: True):
        """Explicit, bounded verification using a caller-owned async adapter.

        The adapter must distinguish a verified deletion from permission,
        rate-limit and transport failures. Revision must use the same trusted
        encoding as the reviewer; text or an assumed default is insufficient.
        """
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("source verification limit out of range")
        # A simultaneous request does not trigger a second SDK batch.
        if self._reconcile_lock.locked():
            return 0
        async with self._reconcile_lock:
            return await self._reconcile(scope, epoch, fetch_source, limit, current)

    async def _reconcile(self, scope, epoch, fetch_source, limit, current):
        with self._verification_lock:
            generation = self._generation
            verified = set(self._verified)
        _, rows = await asyncio.to_thread(self.snapshot, scope, epoch=epoch, topic=self.topic,
                                         now=int(self.companion.clock()))
        checked = 0
        for source, revision, _ in rows:
            if (scope, epoch, source, revision) in verified:
                continue
            with self._verification_lock:
                if generation != self._generation:
                    break
            if not current():break
            digest = await asyncio.to_thread(self._digest, scope, source, revision)
            if not digest:
                with self._verification_lock:self._last_result=SourceStatus.UNAVAILABLE.value
                break
            if not current():break
            observation = await fetch_source(scope, source)
            checked += 1
            still_current = await asyncio.to_thread(
                self.companion.consent_version, scope.guild, scope.subject, "adaptation")
            if (type(observation) is not SourceObservation or observation.scope != scope
                    or type(observation.source) is not int or observation.source != source
                    or not isinstance(observation.status,SourceStatus)):
                with self._verification_lock:self._last_result=SourceStatus.UNAVAILABLE.value
                break
            with self._verification_lock:
                if generation != self._generation or not current() or still_current != epoch:
                    self._last_result=SourceStatus.STALE.value
                    break
                self._last_result=observation.status.value
            if observation.status is SourceStatus.DELETED:
                await asyncio.to_thread(self.companion.delete_source, scope.guild, source)
            elif observation.status is SourceStatus.FOUND and type(observation.revision) is int:
                if observation.revision == revision and observation.digest == digest:
                    self._confirm(generation, scope, epoch, source, revision)
                elif observation.digest and observation.revision > revision:
                    with self._verification_lock:self._last_result=SourceStatus.CHANGED.value
                    await asyncio.to_thread(self.invalidate_source, scope, source=source,
                                            revision=revision, epoch=epoch)
                else:
                    with self._verification_lock:self._last_result=SourceStatus.UNAVAILABLE.value
                    break
            else:
                break
            if checked >= limit:
                break
        return checked

    def _allowed(self, db, scope, epoch):
        if scope.character != self.companion.character_id or not self.accepts(scope.guild, scope.channel):
            return False
        row = db.execute("""
            SELECT version FROM consent_choices
            WHERE guild=? AND user=? AND category='adaptation' AND enabled=1
        """, (str(scope.guild), str(scope.subject))).fetchone()
        return row is not None and row[0] == epoch and super()._allowed(db, scope, epoch)

    def authorize(self, scope, epoch):
        return True  # The transaction's _allowed query supplies the authority.

    def _source_allowed(self, db, scope, source):
        guild, subject = str(scope.guild), str(scope.subject)
        # Discord snowflake creation time, independent of untrusted message text.
        created = ((source >> 22) + 1420070400000) / 1000
        row = db.execute("""
            SELECT at FROM consent_choices WHERE guild=? AND user=? AND category='adaptation'
        """, (guild, subject)).fetchone()
        return (row is not None and row[0] <= created <= self.companion.clock()
                and not db.execute("SELECT 1 FROM tombstones WHERE guild=? AND source=?",
                                   (guild, str(source))).fetchone())

    def projection(self, event, character_id):
        if character_id != self.companion.character_id or not self.accepts(event.guild, event.channel, event.parent):
            return None
        epoch = self.companion.consent_version(event.guild, event.author, "adaptation")
        if epoch is None:
            return None
        scope = Scope(character_id, event.guild, event.channel, event.author)
        with self._verification_lock:
            generation = self._generation
            include = {(source, revision) for key, version, source, revision in self._verified
                       if key == scope and version == epoch}
        state, dependencies = self.snapshot(scope, epoch=epoch, topic=self.topic,
                                            now=int(self.companion.clock()), include=include)
        with self._verification_lock:
            if generation != self._generation:
                return None
        return (epoch, state, dependencies, generation) if state.guidance() else None
