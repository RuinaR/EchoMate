"""Failure-path and diagnostic regressions, synthetic data only."""
import asyncio
import json
import queue
import secrets
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,AsyncMock

from echomate_bot.telemetry import Trace,active_trace,distribution,summarize,process_ram_mib
from echomate_bot.inference import LocalBackend
from echomate_bot.desktop import LocalController
from echomate_bot.settings import Settings
import test_bot_integration as integration


class NumericDiagnostics(unittest.TestCase):
    def test_percentiles_and_denominators_exclude_cancelled_from_response_latency(self):
        rows=[dict(seconds=x,outcome=o,calls=[],stages={'text':x},regenerations=0)
              for x,o in [(1,'sent'),(3,'sent'),(100,'cancelled'),(200,'failed')]]
        result=summarize(rows)
        self.assertEqual(result['response_seconds'],dict(n=2,p50=2.,p90=2.8,p95=2.9))
        self.assertEqual(result['outcomes']['cancelled'],1)
        self.assertIsNone(distribution([])['p95'])
        self.assertNotIn('nan',json.dumps(distribution([float('nan'),1])))


class ReleaseRuntime(unittest.IsolatedAsyncioTestCase):
    setUp=integration.BotIntegration.setUp
    asyncTearDown=integration.BotIntegration.asyncTearDown
    event=integration.BotIntegration.event
    settle=integration.BotIntegration.settle

    async def test_numeric_trace_contains_no_original_text_or_identity(self):
        await self.runtime.ingest(self.event(content='<@999> PRIVATE_SENTINEL'))
        await self.settle()
        report=json.loads((self.root/'telemetry.json').read_text(encoding='utf-8'))
        self.assertEqual(report['summary']['outcomes'],{'sent':1})
        raw=json.dumps(report)
        for secret in ('PRIVATE_SENTINEL','content','author','channel'):
            self.assertNotIn(secret,raw)
        self.assertIn('assessment',report['requests'][0]['stages'])

    async def test_cancelled_request_is_counted_and_never_sent(self):
        self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event())
        for _ in range(100):
            if self.backend.calls:break
            await asyncio.sleep(.001)
        self.runtime.invalidate(3)
        await self.settle()
        self.assertEqual(self.runtime.traces[-1]['outcome'],'cancelled')
        self.assertFalse(self.transport.sent)

    async def test_report_disk_failure_never_replays_successful_send(self):
        with patch('echomate_bot.settings.atomic_private_json',side_effect=OSError):
            await self.runtime.ingest(self.event());await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        await self.runtime.ingest(self.event());await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        self.assertIn('telemetry_write_failed',[r['code'] for r in self.runtime.diagnostics])


class WorkerTrace(unittest.IsolatedAsyncioTestCase):
    async def test_queue_and_context_are_preserved_across_worker(self):
        backend=LocalBackend();entered=threading.Event();release=threading.Event()
        def worker(*args):
            entered.set();release.wait(2);return 'synthetic'
        backend._generate=worker
        first=asyncio.create_task(backend._job([]))
        await asyncio.to_thread(entered.wait,1)
        trace=Trace();token=active_trace.set(trace)
        try:
            second=asyncio.create_task(backend._job([]))
            await asyncio.sleep(.04);release.set();await first;await second
            self.assertGreaterEqual(trace.calls[0]['queue_seconds'],.03)
            self.assertEqual(trace.calls[0]['outcome'],'completed')
            self.assertEqual(backend.pending,0)
        finally:
            active_trace.reset(token)
            await asyncio.to_thread(backend.executor.shutdown,True)


class CleanupAndStorage(unittest.IsolatedAsyncioTestCase):
    async def test_startup_failure_and_disk_failure_still_close_client(self):
        c=LocalController.__new__(LocalController)
        c.settings=None;c.bootstrap={'admin_guilds':[2]};c.phase='';c.error=''
        c.client=None;c.job=None;c.inventory=[];c.updates=queue.Queue(8)
        backend=SimpleNamespace(ready=AsyncMock(side_effect=ValueError),metrics=[])
        client=SimpleNamespace(backend=backend,close=AsyncMock())
        with patch('echomate_bot.inference.LocalBackend',return_value=backend),patch('echomate_bot.discord_app.EchoClient',return_value=client),patch('echomate_bot.settings.atomic_private_json',side_effect=OSError):
            await c._run_bot()
        client.close.assert_awaited_once();self.assertIsNone(c.client)
        self.assertEqual(c.error,'PerformanceWriteError')

    async def test_scope_and_guild_enable_are_one_atomic_transaction(self):
        with tempfile.TemporaryDirectory(dir='local_data') as directory:
            c=LocalController.__new__(LocalController)
            c.settings=Settings(1,secrets.token_hex(32),Path(directory)/'settings.json')
            c.bootstrap=dict(owner_id=1,admin_guilds=[2]);c.client=None;c.job=None
            c.phase='';c.error='';c.updates=queue.Queue(8)
            before=c.settings.revision
            await c.command('scope',guild=2,channel=3,text_mode='mention',reaction_mode='silent',thread=False,inherit=False,enabled=True)
            self.assertEqual(c.settings.revision,before+1)
            previous=c.settings.get()
            with patch('echomate_bot.settings.atomic_private_json',side_effect=OSError):
                await c.command('scope',guild=2,channel=3,text_mode='autonomous',reaction_mode='silent',thread=False,inherit=False,enabled=False)
            self.assertEqual(c.settings.get(),previous)
