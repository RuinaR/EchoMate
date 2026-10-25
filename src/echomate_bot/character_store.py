"""Explicit opt-in character namespaces, reusing CompanionStore's v7 contracts.

One SQLite file/transaction keeps consent global and records character-local.
Old tables remain a legacy area. Opening an ordinary operating DB is rejected;
create a new file or explicitly import a read-only legacy snapshot first.
"""
from __future__ import annotations

from contextlib import contextmanager, closing
import hashlib
import os
import re
import secrets
import sqlite3
import threading
import time

from .companion_store import CompanionStore
from .settings import private_path

SCOPED = frozenset(('relationships', 'relationship_events', 'memories', 'memory_flows',
    'memory_cutoffs', 'source_parts', 'tombstones', 'member_aliases', 'alias_evidence',
    'conversation_summaries', 'dialogue_summaries', 'summary_participants',
    'summary_sources', 'summary_tombstones', 'relationship_history', 'memories_lookup',
    'source_part_lookup', 'digest_subject', 'digest_source'))
SHARED_METHODS = frozenset(('reserve_reminder', 'reminders', 'change_reminder', 'due',
    'defer_preflight', 'claim', 'processing', 'finish', 'recover'))
GLOBAL_MUTATIONS = frozenset(('delete_personal', 'forget', 'forget_memories', 'delete_source'))
# SQL is existing application source, never interpolated user input. Preserve
# literals/comments; only allowlisted identifiers are namespaced. Real tables
# preserve UPSERT, foreign keys, rowcount and lastrowid (unlike writable views).
TOKENS = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\n]*|/\*[\s\S]*?\*/|[A-Za-z_][A-Za-z_0-9]*")


def prefix_for(character_id):
    if not isinstance(character_id, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,47}', character_id):
        raise ValueError('Invalid stable character ID')
    return 'ch_'+hashlib.sha256(character_id.encode()).hexdigest()[:24]+'_'


def namespace_sql(sql, prefix):
    if not prefix:
        return sql
    def replace(match):
        token = match.group()
        if token.startswith('"') and token.endswith('"'):
            name = token[1:-1].casefold()
            return '"'+prefix+name+'"' if name in SCOPED else token
        name=token.casefold()
        return prefix+name if name in SCOPED else token
    return TOKENS.sub(replace, sql)


class ScopedConnection:
    def __init__(self, connection, prefix, nested=False, character_id=None):
        self.connection = connection
        self.prefix = prefix
        self.nested = nested
        self.character_id = character_id

    def execute(self, sql, parameters=()):
        if self.nested and sql.strip().upper() in ('BEGIN', 'BEGIN IMMEDIATE'):
            return self.connection.execute('SELECT 1')
        return self.connection.execute(namespace_sql(sql, self.prefix), parameters)

    def executemany(self, sql, parameters):
        return self.connection.executemany(namespace_sql(sql, self.prefix), parameters)

    def executescript(self, sql):
        if self.nested:
            raise RuntimeError('Schema changes prohibited inside privacy transaction')
        return self.connection.executescript(namespace_sql(sql, self.prefix))


class CharacterCompanionStore(CompanionStore):
    character_namespaced=True

    def __init__(self, hub, character_id=None):
        self.hub = hub
        self.character_id = character_id
        self.prefix = prefix_for(character_id) if character_id else ''
        super().__init__(hub.path, clock=hub.clock)
        if self.error:
            raise RuntimeError('Character storage initialization failed')

    @classmethod
    def bind_existing(cls,hub,character_id):
        """Bind registered tables without DDL/cleanup before atomic deletion."""
        prefix=prefix_for(character_id)
        with hub.legacy.db() as db:
            names={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            tables=SCOPED-{'relationship_history','memories_lookup','source_part_lookup','digest_subject','digest_source'}
            if any(prefix+table not in names for table in tables):raise ValueError('Incomplete character namespace')
        store=cls.__new__(cls)
        store.hub=hub;store.character_id=character_id;store.prefix=prefix
        store.path=hub.path;store.clock=hub.clock;store.lock=threading.RLock()
        store.error=None;store.last_error=None;store.schema_version=7
        return store

    def __getattribute__(self, name):
        if name in SHARED_METHODS:
            if object.__getattribute__(self, 'character_id') is not None:
                return getattr(object.__getattribute__(self, 'hub').legacy, name)
        if name in GLOBAL_MUTATIONS:
            hub = object.__getattribute__(self, 'hub')
            if not getattr(hub.local, 'mutating', False):
                return lambda *args, **kwargs: hub.mutate_all(self, name, *args, **kwargs)
        return super().__getattribute__(name)

    @contextmanager
    def db(self):
        with self.hub.lock:
            connection = getattr(self.hub.local, 'transaction', None)
            if connection is not None:
                yield ScopedConnection(connection, self.prefix, nested=True, character_id=self.character_id)
            else:
                with super().db() as connection:
                    yield ScopedConnection(connection, self.prefix, character_id=self.character_id)

    def recover_readonly(self):
        # The parent only verifies v7 legacy tables. Verify this namespace too.
        with self.hub.lock:
            with closing(sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro', uri=True)) as db:
                names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                tables = SCOPED - {'relationship_history','memories_lookup','source_part_lookup','digest_subject','digest_source'}
                if any(self.prefix+name not in names for name in tables):
                    return False
            return super().recover_readonly()


class CharacterStores:
    SCHEMA = 1

    def __init__(self, path, *, clock=time.time, _create=False):
        self.path = private_path(path)
        self.clock = clock
        self.lock = threading.RLock()
        self.local = threading.local()
        self.stores = {}
        if _create:
            if self.path.exists():
                raise FileExistsError('New character store must not overwrite a DB')
        else:
            self._check_marker()
        self.legacy = CharacterCompanionStore(self)
        with self.legacy.db() as db:
            if _create:
                db.execute('CREATE TABLE character_store_version(version INTEGER NOT NULL CHECK(version=1))')
                db.execute('INSERT INTO character_store_version VALUES(1)')
                db.execute('CREATE TABLE character_namespaces(character_id TEXT PRIMARY KEY,prefix TEXT UNIQUE NOT NULL)')
            rows = list(db.execute('SELECT character_id,prefix FROM character_namespaces'))
        for row in rows:
            if row['prefix'] != prefix_for(row['character_id']):
                raise ValueError('Corrupt character namespace binding')
            self.for_character(row['character_id'])

    @classmethod
    def create(cls, path, *, clock=time.time):
        return cls(path, clock=clock, _create=True)

    def _check_marker(self):
        if not self.path.is_file():
            raise ValueError('Explicit character-store creation required')
        with closing(sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro', uri=True)) as db:
            rows = list(db.execute('SELECT version FROM character_store_version'))
            if rows != [(self.SCHEMA,)]:
                raise ValueError('Unsupported character-store schema')

    def for_character(self, character_id):
        prefix = prefix_for(character_id)
        with self.lock:
            if character_id not in self.stores:
                if getattr(self.local, 'transaction', None) is not None:
                    raise RuntimeError('Cannot create namespace during privacy transaction')
                store = CharacterCompanionStore(self, character_id)
                with self.legacy.db() as db:
                    db.execute('INSERT OR IGNORE INTO character_namespaces VALUES(?,?)', (character_id, prefix))
                self.stores[character_id] = store
            return self.stores[character_id]

    def mutate_all(self, caller, method, *args, **kwargs):
        if method not in GLOBAL_MUTATIONS:
            raise ValueError('Unapproved global mutation')
        with self.lock:
            if getattr(self.local, 'transaction', None) is not None:
                raise RuntimeError('Nested privacy mutation')
            # Another controller instance may have registered a character since
            # this hub opened. Include it, rather than deleting only cached IDs.
            with self.legacy.db() as db:
                registered=list(db.execute('SELECT character_id,prefix FROM character_namespaces'))
            for row in registered:
                if row['prefix']!=prefix_for(row['character_id']):raise ValueError('Corrupt character namespace binding')
                if row['character_id'] not in self.stores:
                    self.stores[row['character_id']]=CharacterCompanionStore.bind_existing(self,row['character_id'])
            # Exactly one physical transaction: a failure in any character rolls
            # back consent epochs, deletions, tombstones and reminder changes.
            with self.legacy.db() as facade:
                db = facade.connection
                db.execute('BEGIN IMMEDIATE')
                current={r[0] for r in db.execute('SELECT character_id FROM character_namespaces')}
                if current!=set(self.stores):
                    raise RuntimeError('Namespace registry changed; retry privacy mutation')
                self.local.transaction = db
                self.local.mutating = True
                try:
                    result = None
                    # Shared consent is updated by each existing contract. The
                    # epoch may advance multiple times, but never decreases or
                    # re-enables. All changes are committed atomically.
                    stores = [store for store in (self.legacy, *self.stores.values()) if store is not caller]
                    for store in (*stores, caller):
                        options = dict(kwargs)
                        if store is not caller and 'receipts' in options:
                            options['receipts'] = None
                        result = getattr(store, method)(*args, **options)
                    return result
                finally:
                    self.local.transaction = None
                    self.local.mutating = False

    @classmethod
    def import_legacy_copy(cls, source, destination, *, clock=time.time):
        source = private_path(source)
        destination = private_path(destination)
        if destination.exists() or source == destination:
            raise FileExistsError('A separate new destination is required')
        destination.parent.mkdir(parents=True, exist_ok=True)
        # A SQLite backup reads a consistent WAL-aware snapshot, never edits the
        # source and never invents an owner character for legacy records.
        temporary=destination.with_name('.character-copy-'+secrets.token_hex(12))
        try:
            with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro', uri=True)) as old:
                with closing(sqlite3.connect(temporary)) as new:
                    old.backup(new)
                    new.execute('CREATE TABLE character_store_version(version INTEGER NOT NULL CHECK(version=1))')
                    new.execute('INSERT INTO character_store_version VALUES(1)')
                    new.execute('CREATE TABLE character_namespaces(character_id TEXT PRIMARY KEY,prefix TEXT UNIQUE NOT NULL)')
                    new.commit()
            if destination.exists():raise FileExistsError('Destination appeared during copy')
            os.rename(temporary,destination)
        finally:
            for path in (temporary,temporary.with_name(temporary.name+'-wal'),temporary.with_name(temporary.name+'-shm')):
                path.unlink(missing_ok=True)
        return cls(destination, clock=clock)
