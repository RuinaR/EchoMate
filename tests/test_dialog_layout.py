"""Owned, withdrawn Tk dialogs and Tcl bindings only; no native desktop input."""
from copy import deepcopy
import gc
import queue
import re
from types import SimpleNamespace
import tkinter as tk
import unittest
from unittest.mock import Mock
from echomate_bot.desktop_ui import DesktopApp
from echomate_bot.settings import DEFAULTS


def invoke(widget,sequence,event_type='2'):
    command=re.search(r'\[([^ ]+) ',widget.bind(sequence))[1]
    widget.tk.call(command,'0','1','0','0','13','0','0','0','0','0','','0','Return','13',str(widget),event_type,'0','0','0')


class DialogLayout(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.withdraw();self.root.tk.call('tk','scaling',2)
        self.callback_errors=[];self.root.report_callback_exception=lambda kind,value,tb:self.callback_errors.append(kind.__name__)
        self.controller=SimpleNamespace(updates=queue.Queue(),submit=Mock());self.app=DesktopApp(self.root,self.controller)
        self.app.snapshot=dict(cfg=deepcopy(DEFAULTS),servers=[],phase='테스트 상태',error='',connected=False,running=False)
    def tearDown(self):
        self.app.destroy();self.app=None;self.root=None;gc.collect()
        self.assertFalse(self.callback_errors)

    def test_readonly_dialog_has_no_write_action(self):
        submit=Mock();dialog=self.app.form('읽기 전용 정보',[('value','읽기 전용 값','변경하면 안 되는 값')],submit,read_only=True)
        self.root.update_idletasks();self.assertFalse(dialog.winfo_ismapped())
        canvas=next(w for w in dialog.winfo_children() if isinstance(w,tk.Canvas))
        entry=next(w for w in canvas.winfo_children() if isinstance(w,tk.Entry))
        self.assertEqual(entry.cget('state'),'readonly');entry.delete(0,'end');entry.insert(0,'덮어쓰기')
        self.assertEqual(entry.get(),'변경하면 안 되는 값')
        invoke(dialog,'<Control-Return>');submit.assert_not_called();self.assertFalse(dialog.winfo_exists())

    def test_large_form_scrolls_and_validation_keeps_values(self):
        submit=Mock(side_effect=ValueError('synthetic validation'))
        fields=[(str(i),'긴 설정 설명 '*8,'값 '+str(i)) for i in range(18)]
        dialog=self.app.form('많은 항목',fields,submit,'긴 항목은 스크롤로 확인해요.')
        canvas=next(w for w in dialog.winfo_children() if isinstance(w,tk.Canvas))
        self.root.update_idletasks();height=dialog.winfo_height()
        canvas.pack_forget();canvas.place(x=0,y=0,width=580,height=height);self.root.update_idletasks()
        entries=[w for w in canvas.winfo_children() if isinstance(w,tk.Entry)]
        self.assertEqual(len(entries),18)
        self.assertGreater(int(canvas.cget('scrollregion').split()[-1]),height)
        canvas.yview_moveto(1);self.assertGreater(canvas.yview()[0],0)
        invoke(dialog,'<Control-Return>');self.assertTrue(dialog.winfo_exists())
        self.assertEqual(entries[0].get(),'값 0')
        submit.side_effect=None;invoke(dialog,'<Control-Return>')
        self.assertEqual(submit.call_args.args[0]['17'],'값 17');self.assertFalse(dialog.winfo_exists())

    def test_header_and_long_model_details_do_not_overlap(self):
        app=self.app;app.canvas.pack_forget();app.canvas.place(x=0,y=0,width=1040,height=740)
        path='X:/Models/'+'long-folder-name/'*20+'weights'
        app.snapshot['models']=[dict(id='demo',name='합성 모델',path=path,format='Transformers',bytes=22*1024**3,compatible=True,reason='파일 검사 안내 '*20)]
        app.page='models';app.model_id='demo';self.root.update_idletasks();app.render()
        texts={app.canvas.itemcget(i,'text'):i for i in app.canvas.find_all() if app.canvas.type(i)=='text'}
        self.assertLessEqual(app.canvas.bbox(texts['내 PC의 AI 모델'])[3],app.canvas.bbox(texts['테스트 상태'])[1])
        self.assertNotIn(path,texts)
        for x,y,w,h,callback in app.hits:
            if (x,y)==(550,420):callback();break
        else:self.fail('Model detail action missing')
        dialog=next(w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel))
        canvas=next(w for w in dialog.winfo_children() if isinstance(w,tk.Canvas))
        self.assertIn(path,[w.get() for w in canvas.winfo_children() if isinstance(w,tk.Entry)])
        self.controller.submit.assert_not_called()
