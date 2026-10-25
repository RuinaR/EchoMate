"""Real synthetic SQLite namespaces and global privacy, never operating DBs."""
from datetime import datetime,timezone
import hashlib
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from echomate_bot.character_store import CharacterStores,namespace_sql,prefix_for
from echomate_bot.companion_store import CompanionStore
from echomate_bot.operation_receipts import read_receipt,MemorySelection


class CharacterStorage(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='local_data')
        self.path=Path(self.temp.name)/'characters.sqlite3'
        self.now=2000000000.
        self.hub=CharacterStores.create(self.path,clock=lambda:self.now)
        self.a=self.hub.for_character('lime');self.b=self.hub.for_character('yaho')
        for category in ('relationships','memory','summaries'):
            self.hub.legacy.set_consent(2,4,category,True)
        self.now+=1

    def tearDown(self):self.temp.cleanup()

    def add(self,store,text='나는 퍼즐을 좋아한다',source=10,receipts=None):
        return store.add_memory(2,4,3,text,source=source,require_consent=True,receipts=receipts)

    def event(self):
        return SimpleNamespace(id=77,guild=2,author=4,channel=3,parent=None,timestamp=datetime.fromtimestamp(self.now,timezone.utc),raw_parts=())

    def test_character_database_version_refuses_legacy_downgrade_and_recovers_readonly(self):
        self.add(self.a)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],8)
        old=CompanionStore(self.path)
        self.assertEqual(old.error,'ValueError')
        self.a.error='OperationalError'
        self.assertTrue(self.a.recover_readonly())
        self.assertEqual(self.a.schema_version,8)
        self.assertTrue(self.a.memories(2,4))
        # A copied v7 file upgrades only in the explicitly separate destination.
        source=self.path.parent/'legacy.sqlite3';legacy=CompanionStore(source)
        self.assertEqual(legacy.schema_version,7)
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        imported=CharacterStores.import_legacy_copy(source,self.path.parent/'imported.sqlite3')
        self.assertEqual(imported.legacy.schema_version,8)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)

    def test_same_source_and_user_have_distinct_memories_and_affinity(self):
        self.add(self.a);self.add(self.b,'나는 독서를 좋아한다')
        self.add(self.hub.legacy,'나는 산책을 좋아한다')
        self.a.set_affinity(2,4,85,require_consent=True)
        self.assertEqual(self.a.familiarity(2,4),85)
        self.assertEqual(self.b.familiarity(2,4),50)
        self.assertEqual([r['summary'] for r in self.a.memories(2,4)],['나는 퍼즐을 좋아한다'])
        self.assertEqual([r['summary'] for r in self.b.memories(2,4)],['나는 독서를 좋아한다'])
        self.assertEqual([r['summary'] for r in self.hub.legacy.memories(2,4)],['나는 산책을 좋아한다'])
        self.assertEqual(self.b.consent(2,4),self.a.consent(2,4))

    def test_current_memory_receipt_is_bound_to_character(self):
        receipts=[];self.add(self.a,receipts=receipts)
        self.assertTrue(receipts[0].current(self.a))
        self.assertFalse(receipts[0].current(self.b))
        self.assertFalse(receipts[0].current(self.hub.legacy))

    def test_empty_read_and_selection_cannot_cross_character(self):
        consent=self.a.subject_snapshot(2,4)
        proof=read_receipt('memory',self.event(),[],consent,character_id='lime')
        self.assertTrue(proof.current(self.a));self.assertFalse(proof.current(self.b))
        version=self.a.consent_version(2,4,'memory')
        selection=MemorySelection(2,4,3,'기억','test',False,(),version,'lime')
        self.assertTrue(selection.current(self.a));self.assertFalse(selection.current(self.b))

    def test_withdrawal_is_shared_and_invalidates_pending_proofs(self):
        receipts=[];self.add(self.a,receipts=receipts)
        self.b.set_consent(2,4,'memory',False)
        self.assertFalse(receipts[0].current(self.a))
        self.assertFalse(self.a.automatic_allowed(2,4,'memory'))
        self.assertIsNone(self.add(self.a,source=11))

    def test_global_delete_removes_all_namespaces_atomically(self):
        for store in (self.a,self.b,self.hub.legacy):self.add(store)
        self.a.delete_personal(2,4,'memory')
        for store in (self.a,self.b,self.hub.legacy):
            self.assertFalse(store.memories(2,4));self.assertFalse(store.consent(2,4)['memory'])

    def test_delete_failure_rolls_back_other_characters_and_consent(self):
        for store in (self.a,self.b,self.hub.legacy):self.add(store)
        before=self.a.subject_snapshot(2,4)
        original=CompanionStore.delete_personal
        def fail(store,*args,**kwargs):
            if store.character_id=='yaho':raise sqlite3.OperationalError('synthetic lock')
            return original(store,*args,**kwargs)
        with patch.object(CompanionStore,'delete_personal',fail):
            with self.assertRaises(sqlite3.OperationalError):self.a.delete_personal(2,4,'memory')
        self.assertEqual(self.a.subject_snapshot(2,4),before)
        self.assertTrue(all(store.memories(2,4) for store in (self.a,self.b,self.hub.legacy)))

    def test_global_delete_includes_namespace_registered_by_another_hub(self):
        other=CharacterStores(self.path,clock=lambda:self.now)
        added=other.for_character('third-character')
        self.add(added)
        self.assertNotIn('third-character',self.hub.stores)
        self.a.delete_personal(2,4,'memory')
        self.assertFalse(added.memories(2,4))
        self.assertFalse(added.consent(2,4)['memory'])

    def test_global_forget_ack_uses_final_epoch_and_caller_namespace(self):
        self.add(self.a);self.add(self.b)
        receipts=[];self.a.forget_memories(2,4,receipts=receipts)
        self.assertEqual(len(receipts),1)
        self.assertTrue(receipts[0].current(self.a))
        self.assertFalse(receipts[0].current(self.b))
        self.assertFalse(self.b.memories(2,4))

    def test_reminders_survive_character_changes_and_share_one_claim(self):
        row=self.a.reserve_reminder(self.event(),self.now+1,'UTC','합성 알림')
        self.assertEqual(self.b.reminders(2,4)[0]['reminder_id'],row['reminder_id'])
        self.now+=2
        self.assertEqual(len(self.hub.legacy.due(60)),1)
        self.assertIsNotNone(self.b.claim(row['reminder_id']))
        self.assertIsNone(self.a.claim(row['reminder_id']))
        self.b.finish(row['reminder_id'],'delivered')
        self.assertEqual(self.a.reminders(2,4)[0]['status'],'delivered')

    def test_reopen_preserves_scopes_and_rejects_plain_legacy_file(self):
        self.add(self.a)
        reopened=CharacterStores(self.path,clock=lambda:self.now)
        self.assertTrue(reopened.for_character('lime').memories(2,4))
        self.assertFalse(reopened.for_character('yaho').memories(2,4))
        old=Path(self.temp.name)/'old.sqlite3';CompanionStore(old)
        with self.assertRaises(sqlite3.OperationalError):CharacterStores(old)

    def test_new_legacy_api_cannot_silently_open_scoped_database(self):
        self.add(self.a)
        wrong=CompanionStore(self.path,clock=lambda:self.now)
        self.assertEqual(wrong.error,'ValueError')
        with self.assertRaises(RuntimeError):wrong.memories(2,4)
        self.assertTrue(self.a.memories(2,4))

    def test_explicit_legacy_copy_preserves_original_and_quarantines_records(self):
        source=Path(self.temp.name)/'old.sqlite3';store=CompanionStore(source,clock=lambda:self.now)
        store.add_memory(2,4,3,'나는 독서를 좋아한다')
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        imported=CharacterStores.import_legacy_copy(source,Path(self.temp.name)/'copy.sqlite3',clock=lambda:self.now)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
        self.assertTrue(imported.legacy.memories(2,4))
        self.assertFalse(imported.for_character('lime').memories(2,4))
        with self.assertRaises(FileExistsError):CharacterStores.import_legacy_copy(source,source)

    def test_sql_routing_preserves_literals_parameters_and_real_foreign_keys(self):
        prefix=prefix_for('lime')
        sql="SELECT memories.source FROM memories WHERE summary='memories' -- memories\n"
        mapped=namespace_sql(sql,prefix)
        self.assertIn("summary='memories' -- memories",mapped)
        self.assertIn(prefix+'memories.source',mapped)
        key=self.add(self.a)
        with self.a.db() as db:
            self.assertEqual(db.execute('SELECT summary FROM memories WHERE memory_id=?',(key,)).fetchone()[0],'나는 퍼즐을 좋아한다')
            self.assertEqual(db.execute('SELECT SUMMARY FROM MEMORIES WHERE memory_id=?',(key,)).fetchone()[0],'나는 퍼즐을 좋아한다')
            self.assertEqual(db.execute('SELECT summary FROM "MEMORIES" WHERE memory_id=?',(key,)).fetchone()[0],'나는 퍼즐을 좋아한다')
            self.assertTrue(db.execute('PRAGMA foreign_keys').fetchone()[0])
        with self.assertRaises(ValueError):self.hub.for_character('lime; DROP TABLE memories')

    def test_failed_legacy_copy_does_not_publish_destination_or_edit_source(self):
        source=Path(self.temp.name)/'old.sqlite3';CompanionStore(source)
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        destination=Path(self.temp.name)/'failed.sqlite3'
        with patch('echomate_bot.character_store.os.rename',side_effect=OSError('synthetic disk failure')):
            with self.assertRaises(OSError):CharacterStores.import_legacy_copy(source,destination)
        self.assertFalse(destination.exists())
        self.assertFalse(list(destination.parent.glob('.character-copy-*')))
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
