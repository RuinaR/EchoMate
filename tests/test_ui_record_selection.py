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
from echomate_bot.character_profiles import DEFAULT_PROFILE


class RecordSelection(unittest.TestCase):
    def test_list_text_lines_and_partial_row_hit_area_follow_actual_dpi(self):
        from echomate_bot.desktop_ui import SelectionList
        for scale in (4/3,5/3,2):
            root=tk.Tk();root.withdraw();root.tk.call('tk','scaling',scale)
            callback=Mock();listing=SelectionList(root,callback)
            try:
                height=listing.row_height*2+10
                listing.place(x=0,y=0,width=300,height=height);root.update_idletasks()
                listing.set_items([dict(id=str(i),label='합성 목록 제목',hint='두 번째 설명 줄') for i in range(3)])
                boxes=[listing.bbox(item) for item in listing.find_all() if listing.type(item)=='text']
                self.assertEqual(len(boxes),4)
                for a,b in zip(boxes,boxes[1:]):self.assertLessEqual(a[3],b[1])
                listing.click(SimpleNamespace(x=20,y=height-1,state=0));callback.assert_not_called()
                listing.click(SimpleNamespace(x=20,y=listing.row_height+1,state=0))
                self.assertEqual(listing.selected,{'1'})
                listing.empty_hint='두 줄 안내\n목록을 확인해 주세요';listing.set_items([])
                box=next(listing.bbox(item) for item in listing.find_all() if listing.type(item)=='text')
                self.assertGreaterEqual(box[1],0);self.assertLessEqual(box[3],height)
            finally:
                listing.destroy();root.destroy();listing=None;root=None;gc.collect()

    def test_loaded_preview_still_disables_model_change_controls(self):
        root=tk.Tk();root.withdraw();controller=SimpleNamespace(updates=queue.Queue(),submit=Mock());app=DesktopApp(root,controller)
        try:
            app.snapshot=dict(cfg=deepcopy(DEFAULTS),servers=[],phase='미리보기',error='',connected=False,running=False,
                preview_busy=True,model_preparing=False,models=[dict(id='demo',name='합성 모델',path='models--google--gemma-4-12B-it/demo',format='Transformers',bytes=22*1024**3,compatible=True,reason='합성 파일 검사')])
            app.page='models';app.model_id='demo';app.render()
            self.assertFalse(any((x,y) in ((250,233),(520,233),(550,540)) for x,y,w,h,fn in app.hits))
            self.assertTrue(any((x,y)==(400,233) for x,y,w,h,fn in app.hits))
            app.snapshot['preview_busy']=False;app.render()
            self.assertTrue(any((x,y)==(550,540) for x,y,w,h,fn in app.hits))
        finally:
            app.destroy();app=None;root=None;gc.collect()

    def test_preview_rapid_click_and_close_use_same_window_ticket(self):
        import re
        root=tk.Tk();root.withdraw();controller=SimpleNamespace(updates=queue.Queue(),submit=Mock())
        app=DesktopApp(root,controller)
        try:
            app.snapshot=dict(cfg=deepcopy(DEFAULTS),servers=[],phase='정지',error='',connected=False,running=False)
            app.character_preview();root.update_idletasks()
            dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
            self.assertFalse(dialog.winfo_ismapped())
            canvas=next(w for w in dialog.winfo_children() if isinstance(w,tk.Canvas))
            command=re.search(r'\[([^ ]+) ',canvas.bind('<Button-1>'))[1]
            for _ in range(2):root.tk.call(command,'0','1','0','0','0','0','0','0','70','24','','0','','0',str(canvas),'4','0','0','0')
            self.assertEqual(controller.submit.call_count,1)
            ticket=controller.submit.call_args.kwargs['session'];self.assertTrue(ticket)
            dialog.destroy();root.update_idletasks()
            self.assertEqual(controller.submit.call_args.args,('preview_cancel',))
            self.assertEqual(controller.submit.call_args.kwargs,dict(session=ticket))
        finally:
            app.destroy();app=None;root=None;gc.collect()

    def test_profile_dialog_receives_async_snapshot_and_preserves_valid_selection(self):
        import time
        import re
        from echomate_bot.desktop_ui import SelectionList
        root=tk.Tk();root.withdraw()
        controller=SimpleNamespace(updates=queue.Queue(),submit=Mock());app=DesktopApp(root,controller)
        try:
            app.snapshot=dict(cfg=deepcopy(DEFAULTS),servers=[],phase='정지',error='',connected=False,running=False,profiles={})
            app.profile_library();root.update_idletasks()
            dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
            canvas=next(w for w in dialog.winfo_children() if isinstance(w,tk.Canvas))
            listing=next(w for w in canvas.winfo_children() if isinstance(w,SelectionList))
            self.assertEqual([r['id'] for r in listing.items],['default'])
            controller.submit.reset_mock()
            def click():
                # Unmapped windows do not receive generated pointer events.
                # Invoke Tk's registered event binding with an actual Tcl event
                # substitution, without mapping a window or sending OS input.
                command=re.search(r'\[([^ ]+) ',canvas.bind('<Button-1>'))[1]
                root.tk.call(command,'0','1','0','0','0','0','0','0','200','380','','0','','0',str(canvas),'4','0','0','0')
            click();root.update()
            controller.submit.assert_not_called()  # default is visibly nondeletable
            app.snapshot['profiles']={'default':dict(DEFAULT_PROFILE),'saved':dict(DEFAULT_PROFILE,name='합성 새 프로필')}
            deadline=time.monotonic()+1
            while len(listing.items)<2 and time.monotonic()<deadline:root.update();time.sleep(.02)
            self.assertEqual([r['id'] for r in listing.items],['default','saved'])
            listing.select_index(1,False)
            click();root.update()
            controller.submit.assert_not_called()
            confirmation=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and w is not dialog)
            confirmation._form_values['confirm'].set('삭제')
            from test_dialog_layout import invoke
            invoke(confirmation,'<Control-Return>')
            self.assertEqual(controller.submit.call_args.kwargs,dict(action='delete',key='saved'))
            self.assertFalse(confirmation.winfo_exists());self.assertTrue(dialog.winfo_exists())
        finally:
            app.destroy();app=None;root=None;gc.collect()

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
