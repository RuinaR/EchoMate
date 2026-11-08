"""Explicit synthetic Runtime integration for one channel and a v8 store."""
from contextlib import contextmanager

from .character_store import CharacterCompanionStore
from .identity_continuity import ExperienceJournal, Scope, Topic, positive_integer


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
        state, dependencies = self.snapshot(scope, epoch=epoch, topic=self.topic,
                                            now=int(self.companion.clock()))
        return (epoch, state, dependencies) if state.guidance() else None
