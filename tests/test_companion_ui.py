"""Hidden Tk geometry only, not a claim about user screen interaction."""
import gc
import queue
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
import tkinter as tk
import unittest
from echomate_bot.desktop_ui import DesktopApp
from echomate_bot.settings import DEFAULTS


class RecordLayout(unittest.TestCase):
    def test_new_pages_minimum_window_and_dpi_boundaries(self):
        for scaling in (4/3,5/3,2.0):
            root=tk.Tk();root.withdraw();root.tk.call('tk','scaling',scaling)
            controller=SimpleNamespace(updates=queue.Queue(),submit=Mock())
            app=DesktopApp(root,controller)
            try:
                cfg=deepcopy(DEFAULTS);cfg['guilds']={'2':dict(enabled=True,channels={'3':dict(mode='mention',inherit=False)},threads={})}
                app.snapshot=dict(cfg=cfg,servers=[dict(id=2,label='합성 테스트 서버',enabled=True,channels=[])],phase='정지',error='',connected=False,running=False,
                                  companion=dict(guild=2,user=None,people=[dict(user='4',affinity=50,interactions=1,last_at=0)],memories=[],reminders=[]))
                app.guild_id=2;root.geometry('1040x740');root.update_idletasks()
                for page in ('relations','memories','reminders'):
                    app.set_page(page);app.render();root.update_idletasks()
                    for widget in (app.server_list,app.people_list,app.record_list):
                        self.assertGreaterEqual(widget.winfo_x(),196)
                        self.assertLessEqual(widget.winfo_x()+widget.winfo_width(),1040)
                    self.assertTrue(all(y+h<=740 for x,y,w,h,callback in app.hits))
                    for item in app.canvas.find_withtag('button_label'):
                        bounds=app.canvas.bbox(item)
                        self.assertGreaterEqual(bounds[0],0);self.assertLessEqual(bounds[2],1040)
            finally:
                app.destroy();app=None;root=None;gc.collect()
