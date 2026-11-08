"""Explicit synthetic Runtime integration for one channel and a v8 store."""
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import threading

from .character_store import CharacterCompanionStore
from .identity_continuity import ExperienceJournal, Scope, Topic, positive_integer


class SourceStatus(Enum):
    FOUND = "found"
    DELETED = "deleted"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SourceObservation:
    status: SourceStatus
    scope: Scope
    source: int
    revision: int | None = None


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
        self._generation = 0
        self._verified = set()
        with self._transaction() as db:
            self.create_tables(db)
            db.execute("CREATE INDEX IF NOT EXISTS experience_subject ON experience(guild,subject)")
            db.execute("CREATE INDEX IF NOT EXISTS experience_source ON experience(guild,source)")
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS experience_consent_changed
                AFTER UPDATE OF enabled,version ON consent_choices
                WHEN NEW.category='memory' AND
                    (NEW.enabled != 1 OR NEW.version != OLD.version)
                BEGIN
                    DELETE FROM experience WHERE guild=NEW.guild AND subject=NEW.user;
                END
            """)
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS experience_consent_deleted
                AFTER DELETE ON consent_choices WHEN OLD.category='memory'
                BEGIN
                    DELETE FROM experience WHERE guild=OLD.guild AND subject=OLD.user;
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

    def quarantine(self):
        """Verification is intentionally never restored from SQLite or backup."""
        with self._verification_lock:
            self._generation += 1
            self._verified.clear()

    def verification_status(self):
        with self._verification_lock:
            return {"session_marks": len(self._verified)}

    def record_feedback(self, scope, *, source, revision, epoch, topic, feedback, now, expires):
        # Only the trusted reviewer of a current source may invoke this method.
        with self._verification_lock:
            generation = self._generation
        saved = super().record_feedback(scope, source=source, revision=revision, epoch=epoch,
                                        topic=topic, feedback=feedback, now=now, expires=expires)
        if saved:
            self._confirm(generation, scope, epoch, source, revision)
        return saved

    def _confirm(self, generation, scope, epoch, source, revision):
        with self._verification_lock:
            if generation == self._generation:
                self._verified.add((scope, epoch, source, revision))

    async def reconcile(self, scope, *, epoch, fetch_source, limit=20):
        """Explicit, bounded verification using a caller-owned async adapter.

        The adapter must distinguish a verified deletion from permission,
        rate-limit and transport failures. Revision must use the same trusted
        encoding as the reviewer; text or an assumed default is insufficient.
        """
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("source verification limit out of range")
        import asyncio
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
            observation = await fetch_source(scope, source)
            checked += 1
            if (type(observation) is not SourceObservation or observation.scope != scope
                    or type(observation.source) is not int or observation.source != source
                    or observation.status is SourceStatus.UNAVAILABLE):
                # Stop the batch on uncertainty, especially a permission or rate limit error.
                break
            with self._verification_lock:
                if generation != self._generation:
                    break
            if observation.status is SourceStatus.DELETED:
                await asyncio.to_thread(self.companion.delete_source, scope.guild, source)
            elif observation.status is SourceStatus.FOUND and type(observation.revision) is int:
                if observation.revision == revision:
                    self._confirm(generation, scope, epoch, source, revision)
                elif observation.revision > revision:
                    await asyncio.to_thread(self.invalidate_source, scope, source=source,
                                            revision=revision, epoch=epoch)
                else:
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
            WHERE guild=? AND user=? AND category='memory' AND enabled=1
        """, (str(scope.guild), str(scope.subject))).fetchone()
        return row is not None and row[0] == epoch and super()._allowed(db, scope, epoch)

    def authorize(self, scope, epoch):
        return True  # The transaction's _allowed query supplies the authority.

    def _source_allowed(self, db, scope, source):
        guild, subject = str(scope.guild), str(scope.subject)
        # Discord snowflake creation time, independent of untrusted message text.
        created = ((source >> 22) + 1420070400000) / 1000
        row = db.execute("""
            SELECT at, (SELECT MAX(at) FROM memory_cutoffs
                        WHERE guild=? AND user IN (?, '*')) AS cutoff
            FROM consent_choices WHERE guild=? AND user=? AND category='memory'
        """, (guild, subject, guild, subject)).fetchone()
        return (row is not None and row[0] <= created <= self.companion.clock()
                and (row[1] is None or created > row[1])
                and not db.execute("SELECT 1 FROM tombstones WHERE guild=? AND source=?",
                                   (guild, str(source))).fetchone())

    def projection(self, event, character_id):
        if character_id != self.companion.character_id or not self.accepts(event.guild, event.channel, event.parent):
            return None
        epoch = self.companion.consent_version(event.guild, event.author, "memory")
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
