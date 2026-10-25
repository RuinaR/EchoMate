"""Lime controller ownership and UI wiring. GUI runs only on owned QA Desktop."""
import asyncio
import json
from pathlib import Path
import queue
import secrets
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from echomate_bot.character_models import CharacterNames
from echomate_bot.lime_desktop import LimeController, LimeDesktopApp
from echomate_bot.settings import Settings, DEFAULTS


class Model:
    def __init__(self, *args, name='라임', **kwargs):
        self.name=name;self.failed=False;self.engine=SimpleNamespace(failed=False)
        self.capabilities_verified=False;self.closed=False;self.clean=True
    async def ready(self):pass
    async def probe_identity(self):return True
    async def probe(self):self.capabilities_verified=True
    async def rename(self,name):self.name=name
    async def close(self):self.closed=True
    async def reclaimed(self):return self.closed and self.clean
    async def text(self,*args):return self.name+'이야.'


class Controller(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='local_data');self.root=Path(self.temp.name)
        with patch('echomate_bot.desktop.threading.Thread.start'):
            self.controller=LimeController(data_root=self.root/'lime')
        self.c=self.controller;self.c.lease=object();self.c.settings=None
        self.c._publish=Mock()
        self.c.installer.verify=AsyncMock(return_value=(self.root/'engine.exe',self.root/'lime.gguf'))
    async def asyncTearDown(self):
        await self.c._cancel_lime()
        if self.c.lime_backend:await self.c.lime_backend.close()
        self.temp.cleanup()

    async def test_install_and_name_do_not_require_discord_setup_or_touch_legacy_files(self):
        old=self.root/'settings.json';old.write_text('preserved')
        result=await self.c.command('lime_name',name='유나')
        self.assertTrue(result['ok']);self.assertEqual(self.c.names.effective('lime'),'유나')
        self.assertEqual(CharacterNames(self.c.data_root/'character-names.json').effective('lime'),'유나')
        self.assertEqual(old.read_text(),'preserved');self.assertFalse((self.c.data_root/'bootstrap.json').exists())

    async def test_real_backend_protocol_load_and_unload_are_ordered(self):
        with patch('echomate_bot.lime_desktop.GGUFLocalBackend',Model):
            self.assertTrue((await self.c.command('lime_load'))['ok'])
        self.assertEqual(self.c.lime['stage'],'ready')
        model=self.c.lime_backend
        self.assertFalse((await self.c.command('lime_load'))['ok'])
        # A failed duplicate request must not unload or replace the resident.
        self.assertIs(self.c.lime_backend,model);self.assertFalse(model.closed)
        self.assertTrue((await self.c.command('lime_unload'))['ok'])
        self.assertTrue(model.closed);self.assertIsNone(self.c.lime_backend)

    async def test_semantic_failure_never_publishes_ready_or_starts_discord(self):
        model=Model();model.probe=AsyncMock(side_effect=RuntimeError('Model recipient classification validation failed'))
        with patch('echomate_bot.lime_desktop.GGUFLocalBackend',return_value=model):
            result=await self.c.command('lime_load')
        self.assertFalse(result['ok']);self.assertTrue(model.closed)
        self.assertFalse(model.capabilities_verified);self.assertIsNone(self.c.lime_backend)
        self.assertEqual(self.c.lime['stage'],'failed')
        self.assertIn('청자 판단',self.c.lime['error'])
        with self.assertRaises(RuntimeError):await self.c.create_backend({})

    async def test_failed_cleanup_retains_model_and_refuses_second_load(self):
        model=Model();model.probe=AsyncMock(side_effect=RuntimeError('probe'))
        model.clean=False
        with patch('echomate_bot.lime_desktop.GGUFLocalBackend',return_value=model):
            self.assertFalse((await self.c.command('lime_load'))['ok'])
        self.assertIs(self.c.lime_backend,model)
        self.assertEqual(self.c.lime['stage'],'recovery_required')
        self.assertFalse((await self.c.command('lime_load'))['ok'])
        model.clean=True

    async def test_save_failure_rolls_back_live_model_name(self):
        self.c.lime_backend=Model(name='라임');self.c.lime_backend.capabilities_verified=True
        self.c.lime['stage']='ready'
        with patch.object(self.c.names,'save',side_effect=OSError):
            self.assertFalse((await self.c.command('lime_name',name='유나'))['ok'])
        self.assertEqual(self.c.lime_backend.name,'라임')
        self.assertEqual(self.c.names.effective('lime'),'라임')
        self.assertEqual(self.c.lime['stage'],'ready')

    async def test_character_store_is_v8_and_legacy_source_is_not_opened(self):
        self.c.data_root.mkdir(exist_ok=True)
        store=self.c.open_companion()
        self.assertEqual(store.character_id,'lime');self.assertEqual(store.schema_version,8)
        store.set_consent(2,4,'memory',True);store.add_memory(2,4,3,'나는 퍼즐을 좋아한다')
        self.assertTrue(self.c.open_companion().memories(2,4))
        self.assertFalse((self.root/'companion.sqlite3').exists())

    async def test_cancel_waits_for_worker_and_does_not_leave_false_ready(self):
        started=asyncio.Event();finished=asyncio.Event()
        async def install(**kwargs):
            started.set()
            try:await asyncio.Event().wait()
            finally:finished.set()
        self.c.installer.install=install
        task=asyncio.create_task(self.c.command('lime_install',accepted=True))
        await started.wait()
        self.assertTrue((await self.c.command('lime_cancel'))['ok'])
        self.assertTrue(finished.is_set())
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertFalse(self.c.lime['busy']);self.assertEqual(self.c.lime['stage'],'cancelled')


class LimeUI(unittest.TestCase):
    def test_pages_states_dpi_and_dialogs_on_owned_desktop(self):
        import os
        if not os.environ.get('ECHOMATE_QA_DESKTOP','').startswith('EchoMate-QA-'):
            self.skipTest('Owned inactive Desktop required')
        import tkinter as tk
        from copy import deepcopy
        for scale in (4/3,5/3,2):
            root=tk.Tk();root.withdraw();root.tk.call('tk','scaling',scale)
            c=SimpleNamespace(updates=queue.Queue(),submit=Mock())
            app=LimeDesktopApp(root,c)
            try:
                snapshot=dict(cfg=deepcopy(DEFAULTS),servers=[],running=False,connected=False,phase='정지',
                    error='',notice='',pending=0,contexts=0,latency=None,progress=[],jobs=[],models=[])
                self.assertNotIn('character',dict(app.navigation()));self.assertNotIn('labs',dict(app.navigation()))
                for stage in ('not_installed','downloading','ready','failed','recovery_required'):
                    app.snapshot=dict(snapshot,lime=dict(stage=stage,name='유나',busy=stage=='downloading',
                        resident=stage in ('ready','recovery_required'),done=200,total=400,
                        error='긴 합성 오류 안내 '*8 if stage=='failed' else None))
                    app.page='lime';app.render();root.update_idletasks()
                    self.assertTrue(all(x+w<=1040 and y+h<=740 for x,y,w,h,callback in app.hits))
                    self.assertEqual(app.can_start(),stage=='ready')
                with patch.object(app,'form') as form:
                    app.rename_dialog();callback=form.call_args.args[2];callback({'name':'하루'})
                    c.submit.assert_called_with('lime_name',name='하루')
                    app.install_dialog();form.call_args.args[2]({'agree':'아니오'})
                    c.submit.assert_called_with('lime_install',accepted=False)
            finally:
                app.destroy()
