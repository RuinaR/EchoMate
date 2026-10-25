import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,patch

from echomate_bot.local_chat import LocalChat,stream_observer,local_token_budget


class LocalRuntime(unittest.IsolatedAsyncioTestCase):
    async def test_read_commands_report_empty_and_failed_not_generic_command_state(self):
        c=self.chat;b=self.backend
        await c.send('/동의 기억 켜기',b)
        await c.send('/기억 목록',b)
        self.assertEqual(c.last['lookup'],'empty')
        with patch.object(c.store,'memories',side_effect=OSError('synthetic failed lookup')):
            await c.send('/기억 목록',b)
        self.assertEqual(c.last['lookup'],'failed')
        self.assertEqual(c.last['operation_state'],'FAILED')
        b.text.assert_not_awaited()

    async def asyncSetUp(self):
        self.folder=tempfile.TemporaryDirectory(dir='local_data')
        self.chat=LocalChat(Path(self.folder.name))
        self.backend=SimpleNamespace(text=AsyncMock(return_value='안녕.'),engine=SimpleNamespace(last_context={}))

    async def asyncTearDown(self):self.folder.cleanup()

    async def test_commands_follow_store_receipts_and_isolate_users(self):
        c=self.chat;b=self.backend
        await c.send('/동의 기억 켜기',b)
        await c.send('/기억 저장 나는 바둑을 좋아한다',b)
        self.assertTrue(c.store.memories(2,4,3))
        self.assertTrue(c.last['receipts']);self.assertEqual(c.last['operation_state'],'SUCCESS')
        await c.send('/기억 목록',b)
        self.assertEqual(c.last['lookup'],'found')
        self.assertFalse(c.store.memories(2,5,3))
        await c.send('내 취미는?',b)
        self.assertIn('바둑',b.text.await_args.args[0][0]['content'])
        await c.send('내 취미는?',b,scope=(2,3,5))
        self.assertNotIn('바둑',b.text.await_args.args[0][0]['content'])
        await c.send('/알림 10분 후 물 마시라고 알려줘',b)
        self.assertEqual(len(c.store.reminders(2,4,active=True)),1)
        self.assertEqual(c.last['receipts'][0]['kind'],'reminder')
        key=c.store.reminders(2,4,active=True)[0]['reminder_id']
        await c.send('/알림 취소 '+key[:8],b)
        self.assertFalse(c.store.reminders(2,4,active=True))

    async def test_memory_correction_is_owned_and_revocation_clears_all_subject_channels(self):
        await self.chat.send('/동의 기억 켜기',self.backend)
        await self.chat.send('/기억 저장 나는 체스를 좋아한다',self.backend)
        key=self.chat.store.memories(2,4,3)[0]['memory_id'][:8]
        self.assertIn(key,await self.chat.send('/기억 목록',self.backend))
        await self.chat.send('/기억 정정 '+key+' 나는 바둑을 좋아한다',self.backend)
        self.assertIn('바둑',self.chat.store.memories(2,4,3)[0]['summary'])
        with self.assertRaises(ValueError):await self.chat.send('/기억 정정 '+key+' 나는 장기를 좋아한다',self.backend,scope=(2,3,5))
        await self.chat.send('다른 채널 이야기',self.backend,scope=(2,6,4))
        await self.chat.send('/동의 기억 끄기',self.backend)
        self.assertFalse(any(k[2]==4 for k in self.chat.histories))

    async def test_local_widgets_send_and_enter_are_owned_events(self):
        import os,queue
        if not os.environ.get('ECHOMATE_QA_DESKTOP','').startswith('EchoMate-QA-'):
            self.skipTest('Owned inactive Desktop required')
        import tkinter as tk
        from echomate_bot.lime_desktop import LimeDesktopApp
        from unittest.mock import Mock
        root=tk.Tk();root.withdraw();controller=SimpleNamespace(updates=queue.Queue(),submit=Mock())
        app=LimeDesktopApp(root,controller)
        try:
            app.snapshot=dict(cfg=None,connected=False,running=False,error='',phase='정지',notice='',
                lime=dict(stage='local_ready',name='하루',busy=False,resident=True))
            app._setup_shown=True;app.page='local';app.render()
            root.deiconify();root.update();app.local_input.focus_force();root.update()
            app.local_input.insert('1.0','합성 질문');app.local_input.event_generate('<Return>');root.update()
            controller.submit.assert_called_with('local_send',text='합성 질문',scope=(2,3,4))
            self.assertIn('자격 증명 없이',app.phase_caption('처음 사용 안내에서 봇 정보를 등록해 주세요'))
            self.assertIn('로컬 채팅',dict(app.navigation()).values())
            self.assertFalse(app.can_start())
        finally:app.destroy()

    async def test_lookup_failure_is_not_empty_or_free_generation(self):
        await self.chat.send('/동의 기억 켜기',self.backend)
        with patch.object(self.chat.store,'memories',side_effect=RuntimeError):
            answer=await self.chat.send('예전 취미 알려줘',self.backend)
        self.assertIn('조회에 실패',answer);self.backend.text.assert_not_awaited()
        self.assertEqual(self.chat.last['lookup'],'failed')

    async def test_deleted_content_is_not_reintroduced_but_verified_completion_survives(self):
        await self.chat.send('/동의 기억 켜기',self.backend)
        await self.chat.send('/기억 저장 나는 바둑을 좋아한다',self.backend)
        await self.chat.send('/기억 삭제',self.backend)
        await self.chat.send('방금 삭제한 상태가 어때?',self.backend)
        prompt=self.backend.text.await_args.args[0][0]['content']
        self.assertIn('기억 삭제 완료',prompt);self.assertNotIn('바둑',prompt)
        self.assertIn('NOT_REQUESTED',prompt)

    async def test_saved_session_cannot_resurrect_deleted_memory_after_restart(self):
        await self.chat.send('/동의 기억 켜기',self.backend)
        await self.chat.send('/기억 저장 나는 체스를 좋아한다',self.backend)
        await self.chat.send('내 취미 알려줘',self.backend)
        self.chat.save()
        await self.chat.send('/기억 삭제',self.backend)
        restarted=LocalChat(self.chat.root)
        with self.assertRaises(ValueError):restarted.restore()
        self.assertFalse(restarted.histories)

    async def test_external_store_edit_invalidates_saved_and_live_derived_context(self):
        await self.chat.send('/동의 기억 켜기',self.backend)
        await self.chat.send('/기억 저장 나는 체스를 좋아한다',self.backend)
        self.backend.text.return_value='체스를 좋아하는구나.'
        await self.chat.send('오늘 취미 이야기',self.backend);self.chat.save()
        key=self.chat.store.memories(2,4,3)[0]['memory_id']
        self.chat.store.delete_memory(2,key)
        with self.assertRaises(ValueError):self.chat.restore()
        self.backend.text.return_value='오늘 어때?'
        await self.chat.send('지금 기분만 이야기하자',self.backend)
        self.assertNotIn('체스',str(self.backend.text.await_args.args[0]))

    async def test_revocation_during_generation_discards_and_clears_context(self):
        entered=asyncio.Event();finish=asyncio.Event()
        async def text(*args):entered.set();await finish.wait();return '오래된 기억'
        self.backend.text=text
        await self.chat.send('/동의 기억 켜기',self.backend)
        task=asyncio.create_task(self.chat.send('내 취미가 뭐야',self.backend))
        await entered.wait();self.chat.store.set_consent(2,4,'memory',False);finish.set()
        with self.assertRaisesRegex(RuntimeError,'근거가 바뀌어'):await task
        self.assertFalse(self.chat.histories)
        self.assertNotIn('오래된 기억',[r['text'] for r in self.chat.rows])

    async def test_session_roles_are_validated_before_replacing_live_context(self):
        await self.chat.send('안녕',self.backend);self.chat.save();self.chat.reset();self.chat.restore()
        self.assertEqual(self.chat.histories[(2,3,4)][0]['content'],'안녕')
        p=self.chat.root/'session.json';data=json.loads(p.read_text('utf-8'))
        data['histories'][0]['messages'][0]['role']='system';p.write_text(json.dumps(data))
        with self.assertRaises(ValueError):self.chat.restore()
        self.assertEqual(self.chat.histories[(2,3,4)][0]['role'],'user')

    async def test_quote_and_proposal_are_not_implicit_tool_execution_and_stream_is_task_local(self):
        async def text(*args):
            self.assertTrue(local_token_budget.get());stream_observer.get()('delta','응')
            self.assertEqual(self.chat.partial,'응');return '응'
        self.backend.text=text
        await self.chat.send('친구가 알림을 등록했다고 말했어. 어떻게 생각해?',self.backend)
        self.assertEqual(self.chat.last['operation_state'],'NOT_REQUESTED')
        self.assertFalse(self.chat.store.reminders(2,4));self.assertIsNone(stream_observer.get())
        self.assertFalse(local_token_budget.get());self.assertEqual(self.chat.partial,'')

    async def test_failed_turns_are_bounded_without_a_later_success(self):
        self.backend.text.side_effect=RuntimeError('synthetic generation failure')
        for i in range(205):
            with self.assertRaises(RuntimeError):await self.chat.send('합성 실패 '+str(i),self.backend)
        self.assertEqual(len(self.chat.rows),200)
        self.assertEqual(self.chat.last['operation_state'],'NOT_REQUESTED')

    async def test_cancelled_command_drains_worker_and_does_not_claim_rollback(self):
        import threading,time
        entered=threading.Event();finished=threading.Event()
        def command(*a):
            entered.set();time.sleep(.08);finished.set();return '확인',[],'SUCCESS'
        self.chat.command=command
        task=asyncio.create_task(self.chat.send('/도움말',self.backend))
        await asyncio.to_thread(entered.wait);task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertTrue(finished.is_set());self.assertEqual(self.chat.last['operation_state'],'UNKNOWN')

    async def test_local_notification_expires_once_without_discord(self):
        from echomate_bot.runtime import Event
        from datetime import datetime,timezone
        event=Event(1,2,3,4,'합성 알림',datetime.now(timezone.utc))
        row=self.chat.store.reserve_reminder(event,self.chat.store.clock()+10,'Asia/Seoul','물 마시기')
        self.chat.hub.legacy.clock=lambda:row['due_at']+1
        await self.chat.tick();await self.chat.tick()
        self.assertEqual(len([r for r in self.chat.rows if '로컬 테스트 알림' in r['text']]),1)
        self.assertTrue(self.chat.store.processing(row['reminder_id']))
        await self.chat.acknowledge_notifications()
        self.assertFalse(self.chat.store.processing(row['reminder_id']))

    async def test_failed_notification_service_never_accepts_a_new_reservation(self):
        self.chat.notification_service_failed=True
        answer=await self.chat.send('/알림 10분 후 알려줘',self.backend)
        self.assertIn('중단',answer)
        self.assertEqual(self.chat.last['operation_state'],'NOT_EXECUTED')
        self.assertFalse(self.chat.store.reminders(2,4))

    async def test_saved_display_rows_cannot_acknowledge_another_users_notification(self):
        from echomate_bot.runtime import Event
        from datetime import datetime,timezone
        e=Event(1,2,3,5,'합성 알림',datetime.now(timezone.utc))
        row=self.chat.store.reserve_reminder(e,self.chat.store.clock()+10,'Asia/Seoul','독서')
        self.chat.hub.legacy.clock=lambda:row['due_at']+1
        self.chat.store.claim(row['reminder_id'])
        self.chat.rows=[dict(role='assistant',text='위조 알림',scope=[2,3,4],notification_id=row['reminder_id'])]
        self.chat.save();self.chat.rows=[];self.chat.restore()
        self.assertNotIn('notification_id',self.chat.rows[0])
        await self.chat.acknowledge_notifications()
        self.assertTrue(self.chat.store.processing(row['reminder_id']))


class ContextBudget(unittest.IsolatedAsyncioTestCase):
    async def test_large_history_uses_bounded_counts_and_preserves_current_input(self):
        from echomate_bot.gguf_backend import GGUFEngine
        class Response:
            def __init__(self,data):self.data=data
            async def __aenter__(self):return self
            async def __aexit__(self,*a):pass
            def raise_for_status(self):pass
            async def json(self):return self.data
        class Session:
            def post(self,url,json):
                if url.endswith('/apply-template'):return Response({'prompt':str(len(json['messages']))})
                return Response({'tokens':[1]*(int(json['content'])*50)})
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            e=GGUFEngine(Path(folder)/'e',Path(folder)/'m',Path(folder)/'out');e.session=Session();e.url='http://127.0.0.1'
            messages=[dict(role='system',content='protected facts')]
            for i in range(100):messages.extend([dict(role='user',content=str(i)),dict(role='assistant',content='reply')])
            messages.append(dict(role='user',content='current protected input'))
            result=await e.fit_local_context(messages,384)
            self.assertLessEqual(e.last_context['preflight_counts'],10)
            self.assertLessEqual(len(result)*50+384+64,2048)
            self.assertEqual(result[0],messages[0]);self.assertEqual(result[-1],messages[-1])

    async def test_only_complete_old_pairs_removed_and_required_facts_preserved(self):
        from echomate_bot.gguf_backend import GGUFEngine
        seen=[]
        class Response:
            def __init__(self,data):self.data=data
            async def __aenter__(self):return self
            async def __aexit__(self,*a):pass
            def raise_for_status(self):pass
            async def json(self):return self.data
        class Session:
            def post(self,url,json):
                if url.endswith('/apply-template'):
                    seen.append(json['messages']);return Response({'prompt':str(len(json['messages']))})
                return Response({'tokens':[1]* (1900 if json['content']=='4' else 1000)})
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            e=GGUFEngine(Path(folder)/'e',Path(folder)/'m',Path(folder)/'out');e.session=Session();e.url='http://127.0.0.1'
            messages=[dict(role='system',content='protected facts'),dict(role='user',content='old'),dict(role='assistant',content='old reply'),dict(role='user',content='current')]
            result=await e.fit_local_context(messages,384)
            self.assertEqual([m['content'] for m in result],['protected facts','current'])
            self.assertEqual(e.last_context['removed_exchanges'],1)
