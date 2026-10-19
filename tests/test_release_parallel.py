"""SDK, SQLite migration/crash boundaries, and privacy regression evidence."""
import asyncio
from dataclasses import replace
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import sqlite3
import tempfile
import unittest
import test_bot_integration as base
from echomate_bot.companion_store import CompanionStore
from echomate_bot.discord_app import DiscordTransport
from echomate_bot.actions import Action,Kind

class SourceGuards(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown
    event=base.BotIntegration.event
    async def test_source_edit_without_gateway_notification_vetoes_send(self):
        current=SimpleNamespace(content='수정한 메시지',reply=AsyncMock())
        transport=DiscordTransport(SimpleNamespace(user=SimpleNamespace(id=999)))
        transport.channel=lambda event:SimpleNamespace(fetch_message=AsyncMock(return_value=current))
        event=replace(self.event(),target_content_hash=hashlib.sha256('원본'.encode()).hexdigest())
        with self.assertRaises(ValueError):await transport.execute(event,Action(Kind.TEXT,'답변'),None,AsyncMock(return_value=True))
        current.reply.assert_not_awaited()

    async def test_supplement_deleted_or_changed_cannot_reply_to_unrelated_latest_message(self):
        root=SimpleNamespace(content='원본',reply=AsyncMock())
        changed=SimpleNamespace(content='다른 내용')
        channel=SimpleNamespace(fetch_message=AsyncMock(side_effect=[root,changed]))
        transport=DiscordTransport(SimpleNamespace(user=SimpleNamespace(id=999)));transport.channel=lambda event:channel
        event=replace(self.event(id=11),response_to=10,target_content_hash=hashlib.sha256('원본'.encode()).hexdigest(),source_content_hash=hashlib.sha256('보충'.encode()).hexdigest())
        with self.assertRaises(ValueError):await transport.execute(event,Action(Kind.TEXT,'답변'),None,AsyncMock(return_value=True))
        root.reply.assert_not_awaited();self.assertEqual([c.args[0] for c in channel.fetch_message.call_args_list],[10,11])

class StoreAudit(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory(dir='local_data');self.path=Path(self.temp.name)/'store.sqlite3';self.store=CompanionStore(self.path)
    def tearDown(self):self.temp.cleanup()
    def test_v1_migration_preserves_records_and_foreign_key_deletion(self):
        key=self.store.add_memory(2,4,3,'나는 퍼즐을 좋아해')
        with self.store.db() as db:db.execute('DROP TABLE memory_flows');db.execute('DROP TABLE subject_consents');db.execute('PRAGMA user_version=1')
        migrated=CompanionStore(self.path)
        self.assertIsNone(migrated.error);self.assertEqual(migrated.memories(2,4)[0]['memory_id'],key)
        with migrated.db() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],3)
        plan=migrated.add_memory(2,4,3,'나는 내일 오후 3시에 모임 약속이 있어','plan',conversation_id='one')
        migrated.delete_memory(2,plan)
        with migrated.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM memory_flows').fetchone()[0],0)
    def test_task_memory_is_flow_bound_but_explicit_own_archive_query_can_retrieve(self):
        self.store.add_memory(2,4,3,'나는 내일 오후 3시에 모임 약속이 있어','plan',conversation_id='one')
        self.assertFalse(self.store.memories(2,4,3,conversation_id='two'))
        self.assertTrue(self.store.memories(2,4,3,conversation_id='one'))
        self.assertTrue(self.store.memories(2,4,3,conversation_id='two',allow_user_archive=True))
        self.assertFalse(self.store.memories(2,5,3,conversation_id='one',allow_user_archive=True))
    def test_lock_and_newer_schema_do_not_initialize_over_existing_data(self):
        key=self.store.add_memory(2,4,3,'나는 퍼즐을 좋아해')
        other=sqlite3.connect(self.path);other.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaises(sqlite3.OperationalError):self.store.set_affinity(2,4,55)
        finally:other.rollback();other.close()
        self.assertEqual(self.store.memories(2,4)[0]['memory_id'],key)
        with self.store.db() as db:db.execute('PRAGMA user_version=99')
        self.assertEqual(CompanionStore(self.path).error,'ValueError')
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM memories').fetchone()[0],1)
    def test_rollback_and_explicit_sqlite_backup_restore_preserve_committed_records(self):
        self.store.add_memory(2,4,3,'나는 퍼즐을 좋아해')
        with self.assertRaises(OSError):
            with self.store.db() as db:
                db.execute('DELETE FROM memories');raise OSError('Injected disk write failure')
        backup=self.path.with_name('qa-only-backup.sqlite3')
        with sqlite3.connect(self.path) as source,sqlite3.connect(backup) as target:source.backup(target)
        self.assertEqual(len(CompanionStore(backup).memories(2,4)),1)
    def test_automatic_subject_consent_is_not_inferred_from_owner_enable_and_is_revocable(self):
        self.assertFalse(self.store.automatic_allowed(2,4))
        self.store.resume_subject(2,4);self.assertTrue(self.store.automatic_allowed(2,4))
        self.assertFalse(self.store.automatic_allowed(5,4));self.assertFalse(self.store.automatic_allowed(2,5))
        self.store.forget(2,4);self.assertFalse(self.store.automatic_allowed(2,4))
        self.store.resume_subject(2,7);self.store.forget(2)
        self.assertFalse(self.store.automatic_allowed(2,7))
