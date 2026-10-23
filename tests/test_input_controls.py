"""Owned withdrawn widgets and Tcl bindings; no native desktop input."""
from concurrent.futures import Future
from copy import deepcopy
import gc
import queue
import time
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from echomate_bot.desktop_ui import DesktopApp,SelectionList
from echomate_bot.settings import DEFAULTS
from echomate_bot.ui_controls import RangeControl,SegmentControl,CanvasFeedback,range_field
from test_dialog_layout import invoke


class InputControls(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.withdraw();self.errors=[]
        self.root.report_callback_exception=lambda kind,value,tb:self.errors.append(kind.__name__)
        self.controller=SimpleNamespace(updates=queue.Queue(),submit=Mock())
        self.app=DesktopApp(self.root,self.controller)
        self.app.snapshot=dict(cfg=deepcopy(DEFAULTS),servers=[],phase='합성 검사',error='',connected=False,running=False)
        self.app.page='character'
    def tearDown(self):
        self.app.destroy();self.app=None;self.root=None;gc.collect();self.assertFalse(self.errors)
    def advanced(self):
        self.app.advanced_profile();self.root.update_idletasks()
        d=next(w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel))
        self.assertFalse(d.winfo_ismapped());return d
    def test_advanced_uses_six_ranges_two_finite_choices_and_actual_policy(self):
        d=self.advanced();controls=d._form_controls
        self.assertEqual(sum(isinstance(w,RangeControl) for w in controls.values()),6)
        self.assertEqual(set(controls),{'calmness','honesty','exclamation','emoji','length','swearing','curiosity','skepticism'})
        self.assertEqual(sum(isinstance(w,SegmentControl) for w in controls.values()),2)
        self.assertFalse(any(isinstance(w,tk.Entry) for w in d.winfo_children()[0].winfo_children()))
        self.assertEqual(controls['length'].choices,('짧게','상황에 맞게'))
        self.assertEqual(controls['swearing'].choices,('끔','가벼운 감탄만'))
        controls['length'].set('짧게');controls['swearing'].set('가벼운 감탄만')
        controls['calmness'].set(87);invoke(d,'<Control-Return>')
        profile=self.controller.submit.call_args.kwargs['values']['character_profile']
        self.assertEqual(profile['length'],'short');self.assertTrue(profile['swearing']);self.assertEqual(profile['calmness'],87)
    def test_slider_keyboard_tcl_bindings_boundaries_and_invalid_values(self):
        d=self.advanced();w=d._form_controls['calmness']
        invoke(w,'<Home>');self.assertEqual(w.value(),0)
        invoke(w,'<Right>');self.assertEqual(w.value(),1)
        invoke(w,'<Prior>');self.assertEqual(w.value(),11)
        invoke(w,'<End>');invoke(w,'<Right>');self.assertEqual(w.value(),100)
        for value in (-1,101,float('nan')):
            with self.assertRaises(ValueError):w.set(value)
        d._form_values['calmness'].set('999');invoke(d,'<Control-Return>')
        self.assertTrue(d.winfo_exists());self.controller.submit.assert_not_called()
        d._form_values['calmness'].set('1.5');invoke(d,'<Control-Return>');self.controller.submit.assert_not_called()
    def test_slider_drag_segment_keys_and_cancel_do_not_store_drafts(self):
        d=self.advanced();w=d._form_controls['emoji'];w.configure(width=535)
        w.click(SimpleNamespace(x=200));self.assertTrue(w.pressed)
        w.drag(SimpleNamespace(x=999));self.assertEqual(w.value(),100)
        w.drag(SimpleNamespace(x=-100));self.assertEqual(w.value(),0)
        w.release(None);self.assertFalse(w.pressed)
        segment=d._form_controls['length'];invoke(segment,'<Home>');self.assertEqual(segment.variable.get(),'짧게')
        invoke(segment,'<Right>');self.assertEqual(segment.variable.get(),'상황에 맞게')
        with self.assertRaises(ValueError):segment.set('장문 강제')
        invoke(d,'<Escape>');self.controller.submit.assert_not_called()
    def test_pending_save_disables_inputs_retry_preserves_drafts(self):
        future=Future();self.controller.submit.return_value=future
        d=self.advanced();w=d._form_controls['calmness'];w.set(89)
        invoke(d,'<Control-Return>');self.root.update_idletasks()
        self.assertTrue(d._pending_save);self.assertFalse(w.enabled())
        invoke(w,'<Left>');self.assertEqual(w.value(),89)
        self.assertTrue(all(not r['enabled'] for r in d._form_feedback.regions))
        invoke(d,'<Control-Return>');self.assertEqual(self.controller.submit.call_count,1)
        future.set_result(dict(ok=False,error='합성 쓰기 실패'));time.sleep(.07);self.root.update()
        self.assertFalse(d._pending_save);self.assertTrue(w.enabled());self.assertEqual(w.value(),89)
        self.assertTrue(all(r['enabled'] for r in d._form_feedback.regions))
    def test_feedback_hover_pressed_selected_disabled_danger_and_focus(self):
        canvas=self.app.canvas;self.app.render();feedback=self.app.feedback
        normal=next(r for r in feedback.regions if r['enabled'] and not r['selected'] and not r['primary'])
        x,y,_,_=normal['box'];feedback.motion(SimpleNamespace(x=x+3,y=y+3));self.assertEqual(normal['state'],'hover')
        feedback.press(SimpleNamespace(x=x+3,y=y+3));self.assertEqual(normal['state'],'pressed')
        with patch.dict(normal,callback=Mock()):
            feedback.release(SimpleNamespace(x=x+3,y=y+3));self.assertEqual(normal['state'],'hover')
        with patch.object(canvas,'focus_get',return_value=canvas):
            feedback.index=feedback.regions.index(normal);feedback.paint()
            self.assertEqual(canvas.itemcget(normal['background'],'width'),'2.0')
        feedback.leave(None);selected=next(r for r in feedback.regions if r['selected'])
        self.assertEqual(selected['state'],'selected')
        disabled=next(r for r in feedback.regions if not r['enabled']);self.assertEqual(disabled['state'],'disabled')
        d=self.app.form('기록 삭제',[],lambda v:None)
        self.assertTrue(d._form_feedback.regions[-1]['danger'])
    def test_large_range_auxiliary_number_rejects_out_of_range_input(self):
        d=self.app.form('초 단위',[('seconds','지연 시간','60')],lambda v:None,controls={'seconds':range_field(maximum=86400)})
        w=d._form_controls['seconds'];self.assertIsNotNone(w.number)
        w.number.delete(0,'end');w.number.insert(0,'86401');self.assertNotEqual(w.variable.get(),'86401')
        for bad in ('²','９','9'*5000,'-1','1.5'):
            w.number.delete(0,'end');w.number.insert(0,bad);self.assertEqual(w.variable.get(),'')
        invoke(w,'<Right>');self.assertEqual(w.value(),1)
        w.number.delete(0,'end');w.number.insert(0,'300');self.assertEqual(w.value(),300)
        w.set_enabled(False);self.assertEqual(w.number.cget('state'),'disabled')
    def test_list_selected_hover_pressed_disabled_and_keyboard(self):
        listing=SelectionList(self.app.canvas,Mock());listing.place(x=0,y=0,width=250,height=150)
        listing.set_items([dict(id='a',label='선택 항목'),dict(id='b',label='다른 항목')]);self.root.update_idletasks()
        listing.select_index(0,False);listing.hover(SimpleNamespace(x=20,y=70));self.assertEqual(listing.hover_index,1)
        listing.click(SimpleNamespace(x=20,y=70,state=0));self.assertTrue(listing.pressed);self.assertEqual(listing.selected,{'b'})
        listing.release(None);listing.configure(state='disabled');listing.select_index(0,False);self.assertEqual(listing.selected,{'b'})
        listing.configure(state='normal');invoke(listing,'<Up>');self.assertEqual(listing.selected,{'a'})
    def test_popup_layout_at_all_supported_scales_and_scrolling(self):
        for scaling in (4/3,5/3,2):
            self.root.tk.call('tk','scaling',scaling)
            with patch.object(self.root,'winfo_screenheight',return_value=760):d=self.advanced()
            canvas=d.winfo_children()[0]
            canvas.pack_forget();canvas.place(x=0,y=0,width=580,height=d.winfo_height());self.root.update_idletasks()
            for window in [i for i in canvas.find_all() if canvas.type(i)=='window']:
                left,top,right,bottom=canvas.bbox(window);self.assertGreaterEqual(left,0);self.assertLessEqual(right,580)
            for control in d._form_controls.values():
                # Offscreen Canvas windows can report 1x1 until scrolled into view.
                window=next(i for i in canvas.find_all() if canvas.type(i)=='window' and canvas.itemcget(i,'window')==str(control))
                top=canvas.coords(window)[1];canvas.yview_moveto(top/float(canvas.cget('scrollregion').split()[-1]));self.root.update_idletasks()
                control.redraw()
                for item in control.find_all():
                    if control.type(item)=='text':
                        left,top,right,bottom=control.bbox(item)
                        self.assertGreaterEqual(left,-1);self.assertLessEqual(right,float(control.cget('width'))+1)
                        self.assertGreaterEqual(top,-1);self.assertLessEqual(bottom,float(control.cget('height'))+2)
            region=list(map(float,canvas.cget('scrollregion').split()));self.assertGreater(region[3],d.winfo_height())
            canvas.yview_moveto(1);self.assertGreater(canvas.yview()[0],0);invoke(d,'<Escape>')
