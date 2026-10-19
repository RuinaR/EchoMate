"""Offline manual-check isolation and network denial; no native app launch."""
import os
from pathlib import Path
from unittest.mock import patch
import unittest
from echomate_bot.user_check import configure_environment,controller_type

class UserCheck(unittest.TestCase):
    def test_existing_operating_modules_cannot_be_reused_for_offline_window(self):
        import tempfile
        import echomate_bot.settings  # Establish the operating-module precondition.
        from echomate_bot.user_check import main
        with tempfile.TemporaryDirectory(dir='local_data') as tmp,patch.dict(os.environ,{'ECHOMATE_CHECK_HOME':str(Path(tmp)/'fresh-check')}),patch('tkinter.Tk',side_effect=AssertionError('Window creation forbidden in guard test')):
            with self.assertRaisesRegex(RuntimeError,'fresh isolated process'):main()
            self.assertFalse((Path(tmp)/'fresh-check').exists())
    def test_unready_or_closed_controller_returns_explicit_failure_without_work(self):
        import asyncio,threading
        from echomate_bot.desktop import LocalController
        c=LocalController.__new__(LocalController);c.loop=None;c.closed=threading.Event()
        self.assertFalse(c.submit('start').result()['ok'])
        loop=asyncio.new_event_loop();loop.close();c.loop=loop
        self.assertFalse(c.submit('settings',values={}).result()['ok'])
    def test_default_data_home_is_separate_and_explicit_operating_path_is_denied(self):
        with patch.dict(os.environ,{},clear=False):
            os.environ.pop('ECHOMATE_CHECK_HOME',None)
            os.environ['ECHOMATE_DATA_HOME']=str(Path.cwd()/'local_data')
            home=configure_environment()
            self.assertEqual(home.name,'manual-check')
            self.assertNotEqual(home,(Path.cwd()/'local_data').resolve())
            self.assertEqual(os.environ['ECHOMATE_DATA_HOME'],str(home))
            os.environ['ECHOMATE_CHECK_HOME']=str(Path.cwd()/'local_data')
            with self.assertRaises(ValueError):configure_environment()

class OfflineCommands(unittest.IsolatedAsyncioTestCase):
    async def test_connection_inventory_and_visual_download_are_blocked_before_dispatch(self):
        class Base:
            def __init__(self):self.forwarded=[]
            def _publish(self):pass
            async def command(self,operation,**kw):self.forwarded.append(operation);return dict(ok=True)
        c=controller_type(Base)()
        for op,kw in [('start',{}),('refresh',{}),('visual_cache',{'refresh':True})]:
            self.assertFalse((await c.command(op,**kw))['ok'])
        self.assertFalse(c.forwarded)
        self.assertTrue((await c.command('settings',values={'mood':'평온'}))['ok'])
        self.assertEqual(c.forwarded,['settings'])
        self.assertIn('실제 Discord 아님',c.inventory[0]['label'])
