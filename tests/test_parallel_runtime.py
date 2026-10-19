"""Synthetic Discord flows + real SQLite; no network or model quality claims."""
import asyncio
from dataclasses import replace
import unittest
from unittest.mock import AsyncMock
import test_bot_integration as base
from echomate_bot.scheduler import GPUScheduler,Request,QueueRejected,RequestExpired
from echomate_studio.implicit_address import ImplicitAddress

class ParallelFlows(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle

    async def start_pair(self,*,same_user=False,second='민랑아, Python 오류 좀 봐 줘.',thread=False):
        self.runtime.direct_cooldown=0
        self.settings.change(1,lambda c:c['guilds']['2'].update(name='민랑mk2'))
        self.backend.wait=asyncio.Event()
        a=self.event(content='<@999> 게임 추천해줘.')
        b=replace(self.event(id=11,channel=8 if thread else 3,content=second,parent=3 if thread else None),author=4 if same_user else 5)
        if thread:self.settings.set_scope(1,2,8,'mention',thread=True)
        await self.runtime.ingest(a);await asyncio.sleep(.015);await self.runtime.ingest(b);await asyncio.sleep(.015)
        return a,b

    async def test_other_user_name_does_not_cancel_or_mix_context(self):
        await self.start_pair();self.assertEqual(len(self.runtime.tasks),2)
        self.backend.wait.set();await self.settle()
        self.assertEqual({e.id for e,_ in self.transport.sent},{10,11})
        self.assertNotIn('Python',str(self.backend.calls[0]));self.assertNotIn('게임 추천',str(self.backend.calls[1]))
        self.assertEqual(len(self.runtime.conversations.flows),2)

    async def test_guild_clear_handles_multiple_same_channel_flows_without_touching_other_guild(self):
        await self.start_pair();self.settings.set_scope(1,9,8,'mention')
        await self.runtime.ingest(replace(self.event(id=30,channel=8),guild=9,author=7))
        self.runtime.invalidate_guild(2);self.backend.wait.set();await self.settle()
        self.assertEqual([e.guild for e,_ in self.transport.sent],[9])
        self.assertTrue(all(f.guild==9 for f in self.runtime.conversations.flows.values()))

    async def test_same_user_independent_question_is_not_lost(self):
        await self.start_pair(same_user=True,second='그리고 내일 날씨도 알려줘.')
        self.backend.wait.set();await self.settle()
        self.assertEqual({e.response_to or e.id for e,_ in self.transport.sent},{10,11})

    async def test_supplement_merges_actual_prefix_and_pins_original_target(self):
        await self.start_pair(same_user=True,second='아, 협동 게임으로.')
        self.backend.wait.set();await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        event,_=self.transport.sent[0];self.assertEqual(event.response_to,10)
        self.assertIn('협동',str(self.backend.calls[-1]));self.assertIn('게임 추천',str(self.backend.calls[-1]))

    async def test_delete_original_cancels_only_its_request(self):
        await self.start_pair();await self.runtime.message_changed(2,3,10)
        self.backend.wait.set();await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[11])

    async def test_two_threads_and_duplicate_gateway_event(self):
        a,b=await self.start_pair(thread=True);await self.runtime.ingest(b)
        self.backend.wait.set();await self.settle()
        self.assertEqual({e.channel for e,_ in self.transport.sent},{3,8})
        self.assertEqual(len(self.transport.sent),2)

    async def test_three_people_explicit_reply_chain_share_actual_conversation(self):
        self.runtime.direct_cooldown=0
        await self.runtime.ingest(self.event());await self.settle()
        bot=self.transport.sent[-1][0].id # transport's returned message ID below
        for index,user in enumerate((5,6)):
            reply=9000+len(self.transport.sent)
            await self.runtime.ingest(replace(self.event(id=11+index,content='그 설명 조금 더 알려 줘.'),author=user,reply_to=reply));await self.settle()
        self.assertEqual(len(self.transport.sent),3)
        self.assertEqual(len({f.conversation_id for f in self.runtime.conversations.flows.values()}),1)
        self.assertEqual(next(iter(self.runtime.conversations.flows.values())).participants,{4,5,6})

    async def test_settings_change_vetoes_every_stale_send_without_erasing_flows(self):
        await self.start_pair();self.settings.set(1,'enabled',False)
        self.backend.wait.set();await self.settle();self.assertFalse(self.transport.sent)
        self.assertEqual(len(self.runtime.states),2)

    async def test_model_switch_preserves_both_waiting_requests(self):
        await self.start_pair();self.backend.prepare_mode=AsyncMock()
        self.backend.wait.set();await self.runtime.switch_model(1,'base');await self.settle()
        self.assertEqual({e.id for e,_ in self.transport.sent},{10,11})

    async def test_targeted_cancel_is_not_other_users_global_cancel(self):
        await self.start_pair()
        await self.runtime.ingest(self.event(id=12,content='요청 취소해'))
        self.backend.wait.set();await self.settle()
        self.assertEqual([e.author for e,_ in self.transport.sent],[5])

    async def test_direct_duplicate_and_burst_limit_survive_queueing(self):
        self.runtime.direct_spam_window=10;self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event())
        await self.runtime.ingest(self.event(id=11))
        for i in range(5):await self.runtime.ingest(self.event(id=20+i,content=f'<@999> 별개 질문 {i}'))
        self.assertEqual(len(self.runtime.tasks),6)
        self.assertEqual(sum(d['code']=='direct_spam_veto' for d in self.runtime.diagnostics),1)
        self.runtime.cancel_pending();self.backend.wait.set();await self.settle()

    async def test_code_case_and_whitespace_are_not_falsely_suppressed_as_duplicates(self):
        self.runtime.direct_spam_window=10;self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event(content='<@999> `Foo`와 `bar` 설명'))
        await self.runtime.ingest(self.event(id=11,content='<@999> `foo`와 `bar` 설명'))
        self.assertEqual(len(self.runtime.tasks),2)
        self.runtime.cancel_pending();self.backend.wait.set();await self.settle()

    async def test_local_activity_does_not_globally_block_other_channel_autonomy(self):
        self.runtime.direct_cooldown=0;await self.runtime.ingest(self.event());await self.settle()
        self.settings.set_scope(1,2,8,'autonomous');other=self.event(id=11,channel=8,content='재미있는 게임 이야기')
        self.assertEqual(self.runtime.activity_changed(),1)
        self.assertTrue(self.runtime.autonomy_allowed(other))
        self.assertFalse(self.runtime.autonomy_allowed(self.event(id=12,content='새 잡담')))
        self.assertLess(self.runtime.autonomy_probability(self.settings.get()),.2)

    async def test_ended_and_idle_flows_do_not_count_as_active_or_destroy_memory(self):
        now=[1000.];self.runtime.activity_clock=lambda:now[0];self.runtime.autonomy_idle_since=0
        await self.runtime.ingest(self.event());await self.settle();self.assertEqual(self.runtime.activity_changed(),1)
        self.settings.set(1,'cooldown',60)
        await self.runtime.ingest(self.event(id=11,content='대화 끝'));await self.settle()
        self.assertEqual(self.runtime.activity_changed(),0);self.assertFalse(self.runtime.autonomy_allowed(self.event(id=12)))
        now[0]+=61;self.assertTrue(self.runtime.autonomy_allowed(self.event(id=12)))
        self.assertTrue(self.runtime.states)
        await self.runtime.ingest(self.event(id=13,content='<@999> 다시 안녕'));await self.settle()
        self.assertEqual(self.runtime.activity_changed(),1)
        now[0]+=1000;self.assertEqual(self.runtime.activity_changed(),0)
        self.assertTrue(self.runtime.autonomy_allowed(self.event(id=14)))
        self.assertTrue(self.runtime.states)

    async def test_queue_load_reduces_only_autonomous_entry(self):
        fake=type('Load',(),{'pending':10,'limit':12})();self.backend.scheduler=fake
        self.assertFalse(self.runtime.autonomy_allowed(self.event()))
        await self.runtime.ingest(self.event());await self.settle()
        self.assertEqual(len(self.transport.sent),1)

    async def test_explicit_supplement_call_keeps_root_and_later_question_fifo(self):
        await self.start_pair(same_user=True,second='민랑아, 아 협동 게임으로.')
        await self.runtime.ingest(self.event(id=12,content='<@999> 그리고 별개 질문이야. 2 더하기 3은?'))
        self.backend.wait.set();await self.settle()
        self.assertEqual([e.response_to or e.id for e,_ in self.transport.sent],[10,12])
        self.assertIn('협동 게임',str(self.backend.calls[-2]))

    async def test_gateway_reconnect_retains_unsent_but_not_ambiguous_reserved_send(self):
        await self.start_pair();self.runtime.pause_gateway()
        self.backend.wait.set();await self.settle();self.assertFalse(self.transport.sent)
        self.assertEqual(len(self.runtime.deferred_events),2)
        self.assertTrue(self.runtime.ledger.reserve(self.runtime.deferred_events[3][0],0))
        await self.runtime.resume_gateway();await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[11])
        self.assertTrue(self.runtime.states)

    async def test_model_change_during_disconnect_keeps_deferred_requests_until_resume(self):
        await self.start_pair();self.runtime.pause_gateway();self.backend.wait.set();await self.settle()
        self.backend.prepare_mode=AsyncMock();await self.runtime.switch_model(1,'base')
        self.assertFalse(self.transport.sent);self.assertEqual(len(self.runtime.deferred_events),2)
        await self.runtime.resume_gateway();await self.settle()
        self.assertEqual({e.id for e,_ in self.transport.sent},{10,11})

    async def test_queue_capacity_waits_without_losing_distinct_direct_requests(self):
        from echomate_bot.inference import LocalBackend
        import threading,time
        backend=LocalBackend(max_pending=2);self.runtime.backend=backend;self.runtime.direct_cooldown=0
        owners=[];peak=[0];active=[0];lock=threading.Lock()
        def generate(messages,images,budget,weight,stop,choices=None):
            with lock:active[0]+=1;peak[0]=max(peak[0],active[0]);owners.append(threading.get_ident())
            try:time.sleep(.025);return '짧은 합성 답변이야.'
            finally:
                with lock:active[0]-=1
        backend._generate=generate
        for i in range(8):await self.runtime.ingest(replace(self.event(id=20+i,content=f'<@999> 독립 요청 {i}'),author=10+i))
        await self.settle()
        self.assertEqual(len(self.transport.sent),8);self.assertEqual(peak[0],1);self.assertEqual(len(set(owners)),1)
        self.assertEqual(backend.scheduler.counts['rejected'],0)
        self.assertEqual(backend.pending,0)

    async def test_close_releases_queued_turn_locks_without_orphan_tasks(self):
        await self.start_pair(same_user=True,second='<@999> 별개 질문을 처리해 줘.')
        await self.runtime.close()
        self.assertFalse(self.runtime.tasks);self.assertFalse(self.runtime.progress)
        self.assertFalse(self.transport.sent);self.assertEqual(len(self.runtime.states),0)

    async def test_shared_queued_request_sees_real_earlier_reply_before_its_actor_call(self):
        self.runtime.direct_cooldown=0;self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event());await asyncio.sleep(.01)
        await self.runtime.ingest(replace(self.event(id=11,content='<@999> 이어지는 질문이야.'),author=5,reply_to=10))
        self.backend.wait.set();await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[10,11])
        self.assertTrue(any(m['role']=='assistant' for m in self.backend.calls[-1]))
        self.assertEqual(self.backend.calls[-1][-1]['role'],'user')

    async def test_other_participant_cannot_cancel_pending_request_by_reply(self):
        self.runtime.direct_cooldown=0
        await self.runtime.ingest(self.event());await self.settle()
        await self.runtime.ingest(replace(self.event(id=11,content='<@999> 나도 질문할게'),author=5,reply_to=9001));await self.settle()
        self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event(id=12,content='<@999> 새 설명을 해 줘.'));await asyncio.sleep(.01)
        await self.runtime.ingest(replace(self.event(id=13,content='요청 취소해'),author=5,reply_to=12))
        self.backend.wait.set();await self.settle()
        self.assertIn(12,[e.id for e,_ in self.transport.sent])

    async def test_pending_requests_do_not_expire_into_idle_activity_count(self):
        now=[100.];self.runtime.activity_clock=lambda:now[0];self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event());await asyncio.sleep(.01);now[0]+=1000
        self.assertEqual(self.runtime.activity_changed(),1)
        self.runtime.cancel_pending();self.backend.wait.set();await self.settle()
        self.assertEqual(self.runtime.activity_changed(),0)

    async def test_group_fast_followup_rejects_other_addressee_and_unrelated_topic(self):
        from echomate_bot.routing import grounded_group_followup
        from echomate_studio.dialogue_state import Turn
        turns=[Turn('1','5','색은 보라로 변경했어.',self.event().timestamp),
               Turn('2','999','색을 보라로 바꾼 걸 확인했어.',self.event().timestamp,True,'1'),
               Turn('3','4','최종 색은 뭐였지?',self.event().timestamp)]
        good=self.event(content='최종 색은 뭐였지?')
        self.assertTrue(grounded_group_followup(turns,good,{4,5}))
        for text in ('철수야, 최종 색은 뭐였지?','<@6> 색은 뭐였지?','파이썬 오류는 뭐였지?','"최종 색은 뭐였지?"'):
            self.assertFalse(grounded_group_followup(turns,replace(good,content=text),{4,5}))

class QueueFairness(unittest.IsolatedAsyncioTestCase):
    async def test_aging_beats_fresh_direct_request_and_is_single_consumer(self):
        now=[0.];queue=GPUScheduler(clock=lambda:now[0]);gate=asyncio.Event();order=[]
        async def job(name,wait=False):
            order.append(name)
            if wait:await gate.wait()
            return name
        def req(priority=0):return Request(priority=priority,created_at=now[0],deadline=999)
        first=asyncio.create_task(queue.submit(lambda:job('running',True),req()));await asyncio.sleep(0)
        low=asyncio.create_task(queue.submit(lambda:job('old-low'),req(3)));await asyncio.sleep(.01)
        now[0]=20
        high=asyncio.create_task(queue.submit(lambda:job('new-high'),req()));await asyncio.sleep(.01)
        gate.set();await asyncio.gather(first,low,high)
        self.assertEqual(order,['running','old-low','new-high']);await queue.close()

    async def test_quota_expiry_cancel_and_shutdown_release_every_future(self):
        queue=GPUScheduler(limit=3,per_user=1);gate=asyncio.Event()
        first=asyncio.create_task(queue.submit(gate.wait,Request(requester_user_id=1)));await asyncio.sleep(.01)
        with self.assertRaises(QueueRejected):await queue.submit(gate.wait,Request(requester_user_id=1))
        with self.assertRaises(RequestExpired):await queue.submit(gate.wait,Request(deadline=0))
        second=asyncio.create_task(queue.submit(gate.wait,Request(requester_user_id=2)));await asyncio.sleep(.01)
        second.cancel();await asyncio.gather(second,return_exceptions=True);await queue.close()
        await asyncio.gather(first,return_exceptions=True)
        self.assertEqual(queue.pending,0);self.assertEqual(queue.counts['rejected'],1)

    async def test_one_operation_failure_does_not_poison_other_users(self):
        queue=GPUScheduler();order=[]
        async def fail():raise ValueError('synthetic')
        async def ok():order.append('ok');return 7
        result=await asyncio.gather(queue.submit(fail),queue.submit(ok),return_exceptions=True)
        self.assertIsInstance(result[0],ValueError);self.assertEqual(result[1],7)
        self.assertEqual(order,['ok']);await queue.close()
