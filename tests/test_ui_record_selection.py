"""Real withdrawn Tk widgets; synthetic records, never desktop input or Discord."""
from copy import deepcopy
import gc
import queue
from types import SimpleNamespace
import tkinter as tk
import unittest
from unittest.mock import Mock

from echomate_bot.desktop_ui import DesktopApp
from echomate_bot.settings import DEFAULTS


class RecordSelection(unittest.TestCase):
    def test_deleted_or_filtered_record_cannot_remain_an_action_target(self):
        for scale in (4/3,5/3,2):
            root=tk.Tk();root.withdraw();root.tk.call('tk','scaling',scale)
            controller=SimpleNamespace(updates=queue.Queue(),submit=Mock())
            app=DesktopApp(root,controller)
            try:
                cfg=deepcopy(DEFAULTS);cfg['guilds']={'2':dict(enabled=True,channels={},threads={})}
                record=dict(memory_id='m1',summary='합성 취향',kind='preference',status='active',expires_at=None)
                view=dict(guild=2,user='4',query='',kind=None,people=[],memories=[record],reminders=[])
                app.snapshot=dict(cfg=cfg,servers=[],phase='정지',error='',connected=False,running=False,companion=view)
                app.guild_id=2;app.record_user='4';app.page='memories';app.record_key='m1'
                app.render();root.update_idletasks()
                self.assertEqual(app.record_list.selected,{'m1'})
                self.assertEqual(app.record_key,'m1')
                # The backend snapshot still contains the previous query result.
                app.record_search='다른 조건';app.render()
                self.assertEqual(app.record_list.items,[])
                self.assertIsNone(app.record_key)
                self.assertEqual(app.record_list.selected,set())
                app.record_search='';app.record_key='m1';view['memories']=[];app.render()
                self.assertIsNone(app.record_key)
                # Disabled actions are omitted from the actual keyboard/click map.
                called=[];app.edit_record=lambda *a:called.append(True)
                app.render()
                for x,y,w,h,callback in app.hits:
                    if x==376 and y==max(740,app.canvas.winfo_height())-226:callback()
                self.assertFalse(called)
            finally:
                app.destroy();app=None;root=None;gc.collect()
