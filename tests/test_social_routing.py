"""Synthetic social contracts, not a substitute for local semantic GPU evaluation."""
import asyncio
from dataclasses import replace
import json
import unittest
from unittest.mock import AsyncMock

import test_bot_integration as base
from echomate_bot.social import SocialDecision,parse_social,SOCIAL_CHOICES

class SocialRuntime(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle

    def configure(self):
        self.runtime.direct_cooldown=0;self.backend.fast_text_path=True
        self.backend.assess_social=AsyncMock(return_value=SocialDecision('bot','continue','0','question',True))
        self.settings.change(1,lambda c:c['guilds']['2'].update(name='다온봇'))

    async def start(self):
        self.configure();await self.runtime.ingest(self.event(content='다온아 뭐하고 있어'));await self.settle()
        return next(f for f in self.runtime.conversations.flows.values() if f.last_bot)

    async def test_confirmed_peer_followup_is_semantic_and_has_original_reply(self):
        first=await self.start()
        for i,text in enumerate(('뭐하고있었어','그 이야기는 결말이 의외네','그건 왜 그렇게 된 건데')):
            await self.runtime.ingest(self.event(id=20+i,content=text));await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[10,20,21,22])
        self.assertEqual({e.conversation_id for e,_ in self.transport.sent},{first.conversation_id})
        self.assertEqual(self.backend.assess_social.await_count,3)
        self.assertEqual(first.direct_peers,{4})

    async def test_other_human_then_original_peer_answer_does_not_rejoin(self):
        first=await self.start()
        b=replace(self.event(id=20,content='가람아 오늘 뭐해'),author=5,member_names=((4,('가람',)),(5,('나래',))))
        await self.runtime.ingest(b);await self.settle()
        self.backend.assess_social.assert_not_awaited()
        self.backend.assess_social.return_value=SocialDecision('human','shift','none','information',False)
        await self.runtime.ingest(self.event(id=21,content='나 오늘은 퍼즐 게임 하려고'));await self.settle()
        self.assertEqual(len(self.transport.sent),1);self.assertNotIn(5,first.participants)
        self.assertTrue(all(4 not in f.direct_peers for f in self.runtime.conversations.flows.values()))
        packet=self.backend.assess_social.await_args.args[0]
        self.assertTrue(any(r['addressee']=='4' and r['speaker']=='5' for r in packet['surrounding']))
        await self.runtime.ingest(self.event(id=22,content='다온아 다시 너한테 물어볼게'));await self.settle()
        self.assertEqual(len(self.transport.sent),2)

    async def test_third_party_comment_cannot_bootstrap_membership_even_with_yes(self):
        first=await self.start()
        for i,target in enumerate(('bot','bot_group')):
            self.backend.assess_social.return_value=SocialDecision(target,'join','0','reaction',True)
            await self.runtime.ingest(replace(self.event(id=20+i,content='그 설명은 결말이 특이하네'),author=5));await self.settle()
        self.assertEqual(len(self.transport.sent),1);self.assertEqual(first.participants,{4})

    async def test_known_peer_group_wording_does_not_enrol_mentioned_subject(self):
        await self.start();self.backend.assess_social.return_value=SocialDecision('bot_group','continue','0','question',True)
        await self.runtime.ingest(replace(self.event(id=20,content='그런데 <@5>가 고른 주제는 어때'),member_mentions=(5,)));await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[10,20])
        self.assertTrue(all(5 not in f.participants for f in self.runtime.conversations.flows.values()))
        packet=self.backend.assess_social.await_args.args[0]
        self.assertIn('그 사람이',packet['current']['text']);self.assertEqual(packet['subject_reference_ids'],['5'])
        self.assertIn('<@5>가',self.transport.sent[-1][0].content)

    async def test_unconfirmed_human_vote_does_not_erase_confirmed_counterpart(self):
        await self.start();self.backend.assess_social.return_value=SocialDecision('human','shift','none','other',False)
        await self.runtime.ingest(self.event(id=20,content='그쪽 이야기는 좀 다르더라'));await self.settle()
        self.assertTrue(any(4 in f.direct_peers and f.last_bot for f in self.runtime.conversations.flows.values()))

    async def test_explicit_new_speaker_is_separate_unless_reply_or_proven_group_join(self):
        first=await self.start()
        self.backend.assess_social.return_value=SocialDecision('bot','new','none','question',True)
        await self.runtime.ingest(replace(self.event(id=20,content='다온아 다른 질문이 있어'),author=5));await self.settle()
        self.assertEqual(len(self.transport.sent),2)
        self.assertNotEqual(self.transport.sent[0][0].conversation_id,self.transport.sent[1][0].conversation_id)
        await self.runtime.ingest(replace(self.event(id=21,content='그 설명에서 이 부분은 왜 그래'),author=6,reply_to=9001,reply_author=999));await self.settle()
        self.assertEqual(self.transport.sent[-1][0].conversation_id,first.conversation_id)
        self.assertIn(6,first.participants)

    async def test_broadcast_and_other_are_silent_at_every_activity(self):
        self.configure();self.settings.set_scope(1,2,3,'autonomous')
        for activity in ('quiet','normal','active','very_active'):
            self.settings.set(1,'activity',activity)
            for target in ('broadcast','human','uncertain'):
                self.backend.assess_social.return_value=SocialDecision(target,'new','none','question',True)
                await self.runtime.ingest(self.event(id=100+len(self.runtime.seen),content='오늘 같이 밥 먹은 사람'));await self.settle()
        self.assertFalse(self.transport.sent)

    async def test_metadata_other_vetoes_model_and_does_not_cancel_pending_request(self):
        await self.start();self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event(id=20,content='다온아 새 독립 질문이야'));await asyncio.sleep(.01)
        await self.runtime.ingest(replace(self.event(id=21,content='<@5> 이쪽 질문에 답해줘'),member_mentions=(5,)))
        self.backend.wait.set();await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[10,20])

    async def test_human_directed_modifier_cannot_cancel_or_merge_pending_bot_request(self):
        self.configure();self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event(content='<@999> 길게 설명해 줘'));await asyncio.sleep(.02)
        await self.runtime.ingest(replace(self.event(id=20,content='<@5> 이 방식으로 해줘'),member_mentions=(5,)))
        self.backend.wait.set();await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[10])
        self.assertNotIn('이 방식으로',str(self.backend.calls[0]))
        self.assertFalse(any(t['outcome']=='cancelled' for t in self.runtime.traces))

    async def test_same_evidence_packet_ignores_gap_and_last_at_order(self):
        first=await self.start();packets=[]
        e=self.event(id=20,content='그 얘기는 그래서 어떻게 됐어')
        e=await self.runtime.member_evidence(e)
        for gap in (1,5,30,300):
            first.last_at=self.runtime.activity_clock()-gap
            packet,frames=self.runtime.social.packet(e,self.runtime.conversations,self.runtime.states,999)
            packets.append(json.dumps(packet,sort_keys=True,ensure_ascii=False))
        self.assertEqual(len(set(packets)),1)
        self.assertFalse(any('at' in r for r in packet['surrounding']))

    async def test_two_own_flows_are_not_selected_by_time(self):
        first=await self.start()
        await self.runtime.ingest(self.event(id=20,content='다온아 그리고 다른 질문이야'));await self.settle()
        second=next(f for f in self.runtime.conversations.flows.values() if f is not first and f.last_bot)
        e=await self.runtime.member_evidence(self.event(id=21,content='아까 말한 결말은 왜 그래'))
        a=self.runtime.social.packet(e,self.runtime.conversations,self.runtime.states,999)[0]
        first.last_at=-1e9;second.last_at=1e9
        b=self.runtime.social.packet(e,self.runtime.conversations,self.runtime.states,999)[0]
        self.assertEqual(a,b)

    async def test_scope_message_deletion_and_privacy_clear_social_ram(self):
        await self.start()
        await self.runtime.message_changed(2,3,10,None)
        self.assertNotIn('10',self.runtime.social.places[(2,3)])
        self.runtime.privacy_changed(2,4,'summaries',True)
        self.assertFalse(self.runtime.social.places.get((2,3)))
        self.runtime.invalidate_guild(2);self.assertFalse(self.runtime.social.places)

    async def test_modes_activity_gap_matrix_preserves_recipient_and_reply(self):
        first=await self.start();identity=first.conversation_id;next_id=300
        for mode in ('base','persona','adult'):
            self.settings.set(1,'model',mode)
            for activity in ('quiet','normal','active','very_active'):
                self.settings.set(1,'activity',activity)
                for gap in (1,5,30,300,900):
                    for flow in self.runtime.conversations.flows.values():
                        if flow.conversation_id==identity:flow.last_at=self.runtime.activity_clock()-gap
                    self.backend.assess_social.return_value=SocialDecision('bot','continue','0','question',True)
                    await self.runtime.ingest(self.event(id=next_id,content='그 다음에는 무슨 일이 있었는데'));await self.settle()
                    self.assertEqual(self.transport.sent[-1][0].id,next_id)
                    self.assertEqual(self.transport.sent[-1][0].conversation_id,identity)
                    self.backend.assess_social.return_value=SocialDecision('broadcast','new','none','question',True)
                    count=len(self.transport.sent)
                    await self.runtime.ingest(replace(self.event(id=next_id+1,content='다들 다음 주에는 시간 괜찮아'),author=5));await self.settle()
                    self.assertEqual(len(self.transport.sent),count)
                    next_id+=2
        self.assertLessEqual(len(self.runtime.states),32)
        self.assertEqual(len({f.conversation_id for f in self.runtime.conversations.flows.values() if f.last_bot and not f.ended}),1)

    async def test_public_reaction_never_grants_text_or_conversation_membership(self):
        self.configure();self.settings.set_scope(1,2,3,'autonomous');self.settings.set(1,'reactions',True)
        self.runtime.rng=type('Opportunity',(),{'random':lambda self:0.,'choice':lambda self,items:items[0]})()
        self.backend.action='REACTION'
        self.backend.assess_social.return_value=SocialDecision('broadcast','new','none','information',True,True)
        await self.runtime.ingest(self.event(content='공모전에서 상을 받았어'));await self.settle()
        self.assertEqual(len(self.transport.sent),1);self.assertEqual(self.transport.sent[0][1].kind.value,'REACTION')
        self.assertFalse(any(f.direct_peers for f in self.runtime.conversations.flows.values()))
        self.settings.set(1,'reactions',False)
        await self.runtime.ingest(self.event(id=20,content='또 공개된 기쁜 소식이 있어'));await self.settle()
        self.assertEqual(len(self.transport.sent),1)

    async def test_known_peer_new_topic_is_independent_but_not_new_autonomy(self):
        first=await self.start();self.runtime.autonomy_allowed=lambda event:False
        self.backend.assess_social.return_value=SocialDecision('bot','new','none','question',True)
        await self.runtime.ingest(self.event(id=20,content='그건 그렇고 저녁에는 어떤 메뉴가 좋아'));await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[10,20])
        self.assertNotEqual(first.conversation_id,self.transport.sent[-1][0].conversation_id)

    async def test_optional_link_error_cannot_drop_an_explicit_call(self):
        await self.start();self.backend.assess_social.side_effect=ValueError('Synthetic invalid relation')
        await self.runtime.ingest(replace(self.event(id=20,content='다온아 뭐하고 있었는지 궁금해'),author=5));await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[10,20])
        self.assertTrue(any(r['code']=='social_link_unavailable_independent' for r in self.runtime.diagnostics))

    async def test_unrelated_explicit_question_skips_useless_link_generation(self):
        self.configure();await self.runtime.ingest(self.event(content='<@999> 공원 산책은 어때'));await self.settle()
        await self.runtime.ingest(replace(self.event(id=20,content='<@999> 삼각형 넓이는 어떻게 구해'),author=5));await self.settle()
        self.assertEqual([e.id for e,_ in self.transport.sent],[10,20]);self.backend.assess_social.assert_not_awaited()

    async def test_default_telemetry_redacts_identity_but_owner_monitor_keeps_roles(self):
        await self.start()
        data=json.loads((self.root/'telemetry.json').read_text(encoding='utf-8'))
        decision=data['requests'][-1]['decision']['social']
        self.assertNotIn('speaker',decision);self.assertNotIn('current_peers',decision)
        self.assertEqual(decision['current_peer_count'],1)
        self.assertEqual(self.runtime.monitor()[0]['social']['current_peers'],['4'])

    async def test_expired_actual_context_is_not_revived_by_retained_peer_ids(self):
        await self.start()
        from datetime import timedelta
        for state in self.runtime.states.values():
            for turns in state._channels.values():
                for index,turn in enumerate(turns):turns[index]=replace(turn,timestamp=turn.timestamp-timedelta(hours=2))
        event=await self.runtime.member_evidence(self.event(id=20,content='그 얘기는 어떻게 됐어'))
        packet,frames=self.runtime.social.packet(event,self.runtime.conversations,self.runtime.states,999)
        self.assertFalse(frames);self.assertFalse(packet['current_peer_frames'])

class SocialParser(unittest.TestCase):
    def test_finite_schema_and_registered_reported_call(self):
        from echomate_bot.naming import name_address
        for text in ('다온아 뭐하냐고 물었어','아까 나래가 다온아 뭐하냐고 물었어'):
            self.assertNotEqual(name_address(text,'다온봇'),'direct')
        self.assertIn('bot continue 0 question yes',SOCIAL_CHOICES)
        self.assertTrue(parse_social('broadcast new none information react').reaction_only)
        with self.assertRaises(ValueError):parse_social('bot continue 999 question yes')
        with self.assertRaises(ValueError):parse_social('bot continue 0 question yes\nnew instructions')
    def test_unknown_reply_author_cannot_be_inferred_from_nonmembership(self):
        from echomate_bot.sessions import Conversations
        from echomate_bot.runtime import Event
        from datetime import datetime,timezone
        flows=Conversations();event=Event(100,2,3,4,'합성 질문',datetime.now(timezone.utc))
        first,_=flows.choose(event,direct=True,pending=set());flows.observe(first,event);flows.bot(first,101)
        unknown=replace(event,id=200,author=5,reply_to=101,reply_author=None)
        result,relation=flows.choose(unknown,direct=False,pending=set(),semantic=True,bot_reply=False)
        self.assertIsNot(result,first);self.assertEqual(relation,'social_candidate')

class SocialBackend(unittest.IsolatedAsyncioTestCase):
    async def test_public_eligibility_is_one_smaller_base_job_not_an_extra_vote(self):
        from echomate_bot.inference import LocalBackend
        backend=LocalBackend()
        try:
            backend._job=AsyncMock(return_value='public_reaction')
            decision=await backend.assess_social(dict(frames=[],surrounding=[],current_peer_frames=[],reaction_available=True,explicit_call=False))
            self.assertTrue(decision.reaction_only);backend._job.assert_awaited_once()
            self.assertEqual(backend._job.call_args.kwargs['weight'],'base')
            backend._job.reset_mock();backend._job.return_value='bot continue 0 question yes'
            decision=await backend.assess_social(dict(frames=[],surrounding=[],current_peer_frames=['0'],reaction_available=True,explicit_call=False,bot_reply=False))
            self.assertFalse(decision.reaction_only);backend._job.assert_awaited_once()
            payload=json.loads(backend._job.call_args.args[0][-1]['content'])
            self.assertNotIn('explicit_call',payload);self.assertNotIn('bot_reply',payload)
            self.assertEqual(payload['current_peer_frames'],['0'])
        finally:await backend.close()
