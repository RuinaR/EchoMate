"""Exact memory provenance survives generation only while consent/facts do."""
import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from echomate_bot.companion_store import CompanionStore
import test_bot_integration as base


class EvidenceSnapshot(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='local_data');self.now=1000
        self.store=CompanionStore(Path(self.temp.name)/'memory.sqlite3',clock=lambda:self.now)
        self.store.set_consent(2,4,'memory',True)
        self.key=self.store.add_memory(2,4,3,'나는 청록색을 좋아해',expires=1100)
        self.rows=self.store.memories(2,4,3);self.version=self.store.consent_version(2,4,'memory')
    def tearDown(self):self.temp.cleanup()
    def valid(self,**kw):return self.store.memory_evidence_current(kw.get('guild',2),kw.get('user',4),kw.get('channel',3),self.rows,self.version)
    def test_exact_scoped_evidence_and_reopen(self):
        self.assertTrue(self.valid())
        self.assertFalse(self.valid(guild=7));self.assertFalse(self.valid(user=5));self.assertFalse(self.valid(channel=8))
        other=CompanionStore(self.store.path,clock=lambda:self.now)
        self.assertTrue(other.memory_evidence_current(2,4,3,self.rows,self.version))
        self.assertFalse(other.memory_evidence_current(2,4,3,self.rows,None))
    def test_reconsent_does_not_resurrect_old_generation(self):
        self.store.set_consent(2,4,'memory',False);self.assertFalse(self.valid())
        self.store.set_consent(2,4,'memory',True);self.assertFalse(self.valid())
    def test_correction_expiry_and_source_deletion(self):
        self.now=1101;self.assertFalse(self.valid());self.now=1000
        with self.store.db() as db:db.execute('UPDATE memories SET summary=? WHERE memory_id=?',('나는 빨강을 좋아해',self.key))
        self.assertFalse(self.valid())
        self.rows=self.store.memories(2,4,3);self.assertTrue(self.valid())
        self.store.delete_source(2,self.rows[0]['source']);self.assertFalse(self.valid())


class RuntimeEvidence(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle
    async def race(self,change):
        store=CompanionStore(self.root/'memory.sqlite3');self.runtime.companion=store
        store.set_consent(2,4,'memory',True)
        key=store.add_memory(2,4,3,'나는 청록색을 좋아해')
        started=asyncio.Event();release=asyncio.Event()
        async def text(context,cfg):
            self.assertIn(key,str(context));self.assertIn('청록색',str(context))
            started.set();await release.wait();return '네가 좋아하는 색은 청록색이야.'
        self.backend.text=text
        await self.runtime.ingest(self.event(content='<@999> 좋아하는 색에 대해 말해 줘'))
        await asyncio.wait_for(started.wait(),5)
        change(store,key);release.set();await self.settle()
        return store
    async def test_unchanged_memory_and_other_subject_change_preserve_answer(self):
        await self.race(lambda s,k:s.set_consent(2,5,'memory',False))
        self.assertEqual(len(self.transport.sent),1)
    async def test_revoke_during_generation_prevents_send(self):
        await self.race(lambda s,k:s.set_consent(2,4,'memory',False))
        self.assertFalse(self.transport.sent)
        self.assertIn('memory_evidence_changed',[d['code'] for d in self.runtime.diagnostics])
    async def test_delete_during_generation_prevents_send(self):
        await self.race(lambda s,k:s.delete_personal(2,4,'memory'))
        self.assertFalse(self.transport.sent)
    async def test_correction_during_generation_prevents_stale_fact_send(self):
        def change(store,key):
            with store.db() as db:db.execute('UPDATE memories SET summary=? WHERE memory_id=?',('나는 노랑을 좋아해',key))
        await self.race(change);self.assertFalse(self.transport.sent)
    async def test_storage_failure_at_delivery_fails_closed(self):
        await self.race(lambda s,k:setattr(s,'error','Synthetic storage failure'))
        self.assertFalse(self.transport.sent)
        self.assertIn('send_failed',[d['code'] for d in self.runtime.diagnostics])


if __name__=='__main__':unittest.main()
