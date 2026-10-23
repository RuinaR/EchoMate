"""Release activation, bounded UI refresh, and loader status contracts."""
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest

import test_input_controls as controls
from echomate_bot.ui_controls import CanvasFeedback


class ResumedUI(unittest.TestCase):
    setUp=controls.InputControls.setUp
    tearDown=controls.InputControls.tearDown

    def control(self):
        canvas=self.app.canvas;canvas.delete('all')
        callback=Mock();feedback=CanvasFeedback(canvas,activate_on_release=True)
        shape=canvas.create_rectangle(10,10,100,50)
        region=feedback.add((10,10,90,40),shape,callback=callback)
        return feedback,region,callback

    def test_press_is_visible_release_inside_once_and_drag_outside_cancels(self):
        feedback,region,callback=self.control();inside=SimpleNamespace(x=20,y=20)
        feedback.press(inside);self.assertEqual(region['state'],'pressed');callback.assert_not_called()
        feedback.release(inside);callback.assert_called_once()
        feedback.press(inside);feedback.motion(SimpleNamespace(x=150,y=20));feedback.release(SimpleNamespace(x=150,y=20))
        callback.assert_called_once()
        feedback.press(inside);region['enabled']=False;feedback.release(inside);callback.assert_called_once()

    def test_space_repeat_focus_loss_and_rebuilt_control_cannot_activate_stale_action(self):
        feedback,region,callback=self.control();feedback.index=0
        feedback.key_press(None);feedback.key_press(None);callback.assert_not_called()
        feedback.key_release(None);callback.assert_called_once()
        feedback.key_press(None);feedback.blur(None);feedback.key_release(None);callback.assert_called_once()
        feedback.press(SimpleNamespace(x=20,y=20));feedback.clear();feedback.release(SimpleNamespace(x=20,y=20));callback.assert_called_once()

    def test_poll_preserves_press_then_applies_latest_snapshot_without_idle_redraw(self):
        app=self.app;app.render();region=next(r for r in app.feedback.regions if r['enabled'])
        x,y,_,_=region['box'];app.press(SimpleNamespace(x=x+4,y=y+4))
        old=app.snapshot;new=dict(old,phase='새 단계');self.controller.updates.put(new)
        self.root.after_cancel(app.poll_id)
        with patch.object(app,'render',wraps=app.render) as render:
            app.poll();self.assertIs(app.snapshot,old);render.assert_not_called()
            app.feedback.blur(None);self.root.after_cancel(app.poll_id);app.poll()
            self.assertIs(app.snapshot,new);render.assert_called_once()
            self.root.after_cancel(app.poll_id);app.poll();render.assert_called_once()

    def test_async_action_cannot_be_submitted_twice_and_completion_releases_busy(self):
        app=self.app;app.render();future=Future();callback=Mock(return_value=future)
        app.button(400,180,140,34,'합성 작업',callback)
        click=SimpleNamespace(x=410,y=190)
        app.press(click);callback.assert_not_called();app.feedback.release(click)
        self.assertTrue(app.pending_actions)
        key=next(iter(app.pending_actions));app.invoke_action(callback,key);callback.assert_called_once()
        future.set_result(dict(ok=False,error='합성 실패'))
        self.root.after_cancel(app.poll_id);app.poll();self.assertFalse(app.pending_actions)

    def test_model_empty_state_uses_own_list_and_detail_area(self):
        app=self.app;app.page='models';app.snapshot.update(models=[]);app.model_id='removed';app.render()
        self.assertIsNone(app.model_id);self.assertFalse(app.model_list.selected)
        self.assertNotIn('연결 후',app.model_list.empty_hint)
        texts=[app.canvas.itemcget(i,'text') for i in app.canvas.find_all() if app.canvas.type(i)=='text']
        self.assertIn('선택한 모델의 상세 정보',texts)
        self.assertFalse(any('채널을 고른 뒤' in t for t in texts))


class LoaderStatus(unittest.TestCase):
    def test_failed_load_keeps_stage_observation_and_failure_after_cleanup(self):
        from echomate_bot.inference import LocalBackend
        backend=LocalBackend(adapter=None);seen=[];backend.load_observer=seen.append
        try:
            with patch('echomate_bot.model_registry.ModelRegistry.resolve',side_effect=ValueError('synthetic')),patch.object(backend,'unload') as cleanup:
                with self.assertRaises(ValueError):backend.load()
            self.assertEqual(seen,['registry_preflight']);self.assertEqual(backend.load_phase,'failed');cleanup.assert_called_once()
        finally:backend.executor.shutdown(wait=True)
