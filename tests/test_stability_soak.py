"""Elapsed mock operation and optional counter failures; never loads weights."""
import asyncio
from pathlib import Path
import tempfile
import unittest
import json

from echomate_bot.loader_memory import MemoryRecorder,memory_snapshot


class StabilitySoak(unittest.IsolatedAsyncioTestCase):
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
