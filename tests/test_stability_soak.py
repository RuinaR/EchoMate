"""Elapsed mock operation and optional counter failures; never loads weights."""
import asyncio
from pathlib import Path
import tempfile
import unittest
import json

from echomate_bot.loader_memory import MemoryRecorder,memory_snapshot


class StabilitySoak(unittest.IsolatedAsyncioTestCase):
    async def test_soak_continues_at_real_quota_without_loosening_it(self):
        from verify_stability_soak import run
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            result=await run(Path(folder)/'seeded',seconds=30,period=.001,max_iterations=15,reminder_seed_per_user=30)
            self.assertTrue(result['passed']);self.assertEqual(result['iterations'],15)
            self.assertEqual(result['counts']['seeded_reminder_cancellations'],240)
            self.assertEqual(result['counts']['reminder_limit_veto'],1)
            self.assertEqual(result['counts'].get('reminder_cancel',0),0)

    async def test_unsafe_sample_is_preserved_before_safety_exception(self):
        from unittest.mock import patch
        import verify_retention_soak
        from echomate_bot.processes import ResourceLimitError
        class Probe:
            traces=[]
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            for reason,field,value in (('ram','ram_available',2*1024**3),('commit','commit_available',1024**3),('probe_private','process_private',257*1024**2)):
                root=Path(folder)/reason;root.mkdir()
                async def fake_run(*args,observe,**kwargs):
                    sample=dict(seconds=0,process_private=20*1024**2,ram_available=4*1024**3,commit_available=4*1024**3)
                    sample[field]=value;observe(Probe(),[],sample)
                with patch.object(verify_retention_soak,'run',fake_run):
                    with self.assertRaises(ResourceLimitError) as caught:await verify_retention_soak.verify(root,60)
                self.assertEqual(caught.exception.reason,reason)
                saved=json.loads((root/'safety-stop.json').read_text('utf-8'))
                self.assertEqual(saved['reason'],reason);self.assertEqual(saved['sample'][field],value)

    def test_daily_reminder_quota_is_expected_veto_without_deleting_history(self):
        from collections import Counter
        from datetime import datetime,timezone
        from echomate_bot.runtime import Event
        from echomate_bot.companion_store import CompanionStore
        from verify_stability_soak import reminder_probe
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            store=CompanionStore(Path(folder)/'companion.sqlite3');counts=Counter()
            for i in range(31):reminder_probe(store,Event(1000+i,2,3,4,'합성 예약',datetime.now(timezone.utc)),counts)
            self.assertEqual(counts['reminder_cancel'],30);self.assertEqual(counts['reminder_limit_veto'],1)
            with store.db() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM reminders').fetchone()[0],30)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM reminders WHERE status='cancelled'").fetchone()[0],30)

    async def test_diagnostic_wrappers_reject_failed_workload_after_preserving_report(self):
        from unittest.mock import AsyncMock,patch
        import compare_retention
        import verify_retention_soak
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            for module,call,report_name in ((compare_retention,lambda p:compare_retention.compare(p,False),'retention-private.json'),
                (verify_retention_soak,lambda p:verify_retention_soak.verify(p,60),'retention-summary.json')):
                root=Path(folder)/module.__name__;root.mkdir()
                with patch.object(module,'run',AsyncMock(return_value=dict(passed=False,iterations=0))):
                    with self.assertRaisesRegex(RuntimeError,'complete safely'):await call(root)
                saved=json.loads((root/report_name).read_text('utf-8'))
                self.assertFalse(saved.get('result',saved)['passed'])

    async def test_measurement_history_is_bounded_but_stream_keeps_all_samples(self):
        from verify_stability_soak import run
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            root=Path(folder)/'bounded'
            result=await run(root,seconds=10,period=.001,max_iterations=3,sample_interval=.001,
                sample_history_limit=1,diagnostic_retention=False,restart_every_iterations=2)
            saved=json.loads((root/'summary-private.json').read_text('utf-8'))
            stream=[json.loads(s) for s in (root/'samples.jsonl').read_text('utf-8').splitlines()]
            self.assertTrue(result['passed']);self.assertEqual(result['iterations'],3)
            self.assertEqual(len(saved['samples']),1);self.assertEqual(len(stream),3)
            self.assertEqual(saved['sample_count'],3);self.assertEqual(saved['mock_pipeline']['samples'],0)
            self.assertEqual(result['counts']['restart'],1)

    async def test_mock_message_ids_are_unique_after_clear_and_reaction_has_no_message_id(self):
        import sys
        sys.path.insert(0,str(Path('tools').resolve()))
        from verify_stability_soak import SoakTransport
        from echomate_bot.runtime import Event
        from echomate_bot.actions import Action,Kind
        from datetime import datetime,timezone
        t=SoakTransport();event=Event(1,2,3,4,'합성 점검',datetime.now(timezone.utc))
        async def fresh():return True
        first=await t.execute(event,Action(Kind.TEXT,text='확인'),None,fresh)
        t.sent.clear()
        second=await t.execute(event,Action(Kind.TEXT,text='확인'),None,fresh)
        self.assertNotEqual(first,second)
        self.assertIsNone(await t.execute(event,Action(Kind.REACTION,asset='👍'),None,fresh))

    async def test_interrupted_soak_records_failure_not_a_shortened_pass(self):
        import sys
        sys.path.insert(0,str(Path('tools').resolve()))
        from verify_stability_soak import run
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            root=Path(folder)/'soak';task=asyncio.create_task(run(root,seconds=20,period=.01))
            await asyncio.sleep(.08);task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
            result=json.loads((root/'summary-private.json').read_text(encoding='utf-8'))
            self.assertFalse(result['passed']);self.assertIn('CancelledError',result['errors'])
            self.assertFalse(result['lingering_tasks'])

    async def test_mixed_operation_restarts_deletes_and_drains_without_network(self):
        import sys
        sys.path.insert(0,str(Path('tools').resolve()))
        from verify_stability_soak import run
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            result=await run(Path(folder)/'soak',seconds=2.5,period=.001,restart_interval=.4)
            self.assertTrue(result['passed'])
            self.assertGreater(result['counts']['independent_replies'],0)
            self.assertGreater(result['counts']['restart'],0)
            self.assertFalse(result['real_discord']);self.assertFalse(result['real_gpu'])
            self.assertEqual(result['lingering_tasks'],[])

    def test_optional_unavailable_counter_does_not_break_peak_recording(self):
        with MemoryRecorder(sample=lambda:dict(process_handles=None,process_private=123),interval=.001) as recorder:
            recorder.mark('test')
        self.assertEqual(recorder.peaks['process_private'],123)
        self.assertNotIn('process_handles',recorder.peaks)

    def test_windows_handle_and_system_lifetime_counters_are_named_explicitly(self):
        value=memory_snapshot()
        self.assertGreaterEqual(value['system_commit_peak_since_boot'],value['commit_used'])
        if value['process_handles'] is not None:self.assertGreater(value['process_handles'],0)
