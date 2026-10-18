"""Local controls and GUI wiring; no Discord account, messages or GPU required."""
import asyncio
import queue
import secrets
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from echomate_bot.desktop import DesktopApp,LocalController
from echomate_bot.settings import Settings,scope


class DesktopControls(unittest.IsolatedAsyncioTestCase):
    async def test_local_owner_commands_are_scoped_and_preserve_history_on_mood(self):
        with tempfile.TemporaryDirectory(dir='local_data') as directory:
            controller=LocalController.__new__(LocalController)
            controller.settings=Settings(1,secrets.token_hex(32),Path(directory)/'settings.json')
            controller.bootstrap=dict(owner_id=1,admin_guilds=[2]);controller.client=None
            controller.job=None;controller.phase='test';controller.error='';controller.updates=queue.Queue(maxsize=8)
            await controller.command('scope',guild=2,channel=3,text_mode='autonomous',reaction_mode='silent',thread=False,inherit=True,enabled=True)
            await controller.command('settings',values=dict(enabled=True,mood='기쁨'))
            self.assertEqual(scope(controller.settings.get(),2,3,action='text'),'autonomous')
            self.assertEqual(scope(controller.settings.get(),2,3,action='reaction'),'silent')
            revision=controller.settings.revision
            await controller.command('scope',guild=9,channel=3,text_mode='autonomous',reaction_mode='autonomous',thread=False,inherit=False,enabled=True)
            self.assertEqual(controller.error,'PermissionError');self.assertEqual(controller.settings.revision,revision)
            await controller.command('settings',values=dict(owner_id=2))
            self.assertEqual(controller.error,'ValueError');self.assertEqual(controller.settings.revision,revision)


class DesktopWidgets(unittest.TestCase):
    def test_native_window_scope_selection_and_save_wiring(self):
        class Controller:
            def __init__(self):self.updates=queue.Queue();self.commands=[]
            def submit(self,operation,**kwargs):self.commands.append((operation,kwargs))
        with tempfile.TemporaryDirectory(dir='local_data') as directory:
            settings=Settings(1,secrets.token_hex(32),Path(directory)/'settings.json')
            settings.set_activity_scope(1,2,3,'autonomous','silent',inherit=True)
            root=tk.Tk();root.withdraw();controller=Controller()
            try:
                app=DesktopApp(root,controller)
                app.snapshot=dict(cfg=settings.get(),servers=[dict(id=2,label='test',enabled=True,channels=[dict(id=3,label='test-channel',thread=False)])],
                    connected=False,phase='test',error='',notice='')
                app.refresh_lists();app.channel_list.select_index(0,False)
                app.save_scope();app.set_value('activity','normal');root.update_idletasks()
                self.assertEqual(controller.commands[0][1]['text_mode'],'autonomous')
                self.assertEqual(controller.commands[0][1]['reaction_mode'],'silent')
                self.assertTrue(controller.commands[0][1]['inherit'])
                self.assertEqual(controller.commands[1][1]['values']['activity'],'normal')
            finally:root.destroy()

    def test_duplicate_instance_lock_is_released_after_close(self):
        from echomate_bot.instance import InstanceLease
        with tempfile.TemporaryDirectory(dir='local_data') as directory,patch('echomate_bot.instance.ROOT',Path(directory)):
            first=InstanceLease()
            try:
                with self.assertRaises(RuntimeError):InstanceLease()
            finally:first.close()
            second=InstanceLease();second.close()
