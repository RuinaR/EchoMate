"""Human-boundary provenance; no live Discord or model required."""
from dataclasses import replace
from types import SimpleNamespace
import unittest
from echomate_bot.social import SocialRouter,SocialDecision
from echomate_bot.members import MemberRoles
import test_social_routing as routing


class ChoiceAndInput(unittest.TestCase):
    def test_named_return_requires_real_past_pair_and_no_human_or_collision(self):
        from copy import deepcopy
        from echomate_bot.named_return import return_view,return_choices,parse_return
        pending=dict(id='human',speaker='5',addressee='4',text='사람 질문')
        packet=dict(bot_id='999',current=dict(speaker='4',text='유나, 네 생각은 어때?',
            bot_identity=dict(effective_name='유나'),roles=dict(ambiguous=False)),
            pending_human_exchange=dict(source='human'),surrounding=[pending],frames=[dict(index='0',participants=['4'],
            turns=[dict(id='1',speaker='4',bot=False,text='실제 원래 요청'),dict(id='2',speaker='999',bot=True,reply='1',text='실제 답변')])])
        view=return_view(packet);self.assertEqual(list(view)[-1],'current')
        self.assertIn('resume_0',return_choices(view))
        self.assertEqual(parse_return('resume_0',view).relation,'resume')
        with self.assertRaises(ValueError):parse_return('resume_3',view)
        for text in ('친구가 유나라고 말했어','"유나, 네 생각은 어때?"라고 했어'):
            p=deepcopy(packet);p['current']['text']=text;self.assertIsNone(return_view(p))
        for field,value in [('bot_collision',True),('addressee','5'),('ambiguous',True)]:
            p=deepcopy(packet);p['current']['roles'][field]=value;self.assertIsNone(return_view(p))
        p=deepcopy(packet);p['frames'][0]['participants']=[];self.assertIsNone(return_view(p))
        p=deepcopy(packet);p['frames'][0]['turns'][1]['reply']='missing';self.assertIsNone(return_view(p))

    def test_only_existing_resume_membership_can_pass_pending_boundary(self):
        from echomate_bot.social import grounded_social_choices
        packet=dict(current=dict(speaker='4'),pending_human_exchange=dict(source='human'),
                    frames=[dict(index='0',participants=['4'],current_peers=[])])
        choices=grounded_social_choices(packet)
        self.assertIn('bot resume 0 question yes',choices)
        self.assertIn('bot resume 0 acknowledgement no',choices)
        self.assertTrue(any(c.startswith('human ') for c in choices))
        self.assertTrue(any(c.startswith('uncertain ') for c in choices))
        self.assertFalse(any(c.startswith('bot_group ') for c in choices))
        self.assertFalse(any(' join ' in c or ' continue ' in c for c in choices))
        packet['current']['speaker']='5'
        self.assertFalse(any(' resume ' in c for c in grounded_social_choices(packet)))
        packet['current']['speaker']='4';packet['pending_human_exchange']=None
        packet['frames'][0]['current_peers']=['4']
        self.assertIn('bot_group join 0 question yes',grounded_social_choices(packet))

    def test_current_last_and_minimum_references_preserve_source_bodies(self):
        import json
        from copy import deepcopy
        from echomate_bot.context_budget import current_last,compact_minimum
        row=dict(id='10',speaker='4',reply=None,text='실제 원문과 부정은 그대로 보존',bot=False)
        data=dict(current=dict(text='현재 질문',roles=dict(identity_actions_allowed=False,addressee=None),
                               bot_identity=dict(id='999',effective_name='유나',name_version=3,character_epoch=2)),
                  bot_id='999',pending_human_exchange=dict(source='20'),
                  frames=[dict(index='0',turns=[row])],surrounding=[dict(row)])
        old=deepcopy(data)
        ordered=current_last([dict(role='system',content='policy'),dict(role='user',content=json.dumps(data))])
        self.assertEqual(json.loads(ordered[1]['content']),old)
        self.assertEqual(list(json.loads(ordered[1]['content']))[-1],'current')
        result=compact_minimum(data)
        self.assertEqual(data,old)
        self.assertEqual(result['frames'][0]['turns'][0]['text'],row['text'])
        self.assertEqual(result['surrounding'][0]['text_source'],'10')
        self.assertEqual(result['current']['bot_identity'],dict(effective_name='유나'))
        # Conflicting source copies and the pending source never become refs.
        data['surrounding'][0]['text']='정정된 다른 내용'
        self.assertIn('text',compact_minimum(data)['surrounding'][0])
        data['surrounding'][0]['text']=row['text'];data['pending_human_exchange']['source']='10'
        self.assertIn('text',compact_minimum(data)['surrounding'][0])


class Sources(unittest.TestCase):
    def test_scope_edit_restore_delete_and_confirm_invalidate_source_stamps(self):
        event=routing.SocialRuntime.event(self,id=20,content='사람에게 하는 말')
        event=replace(event,member_roles=MemberRoles(4,addressee=5))
        router=SocialRouter(clock=lambda:1.)
        router.observe(event);stamp=router.source_stamp(2,3,20)
        router.clear(2,channel=8);self.assertTrue(router.source_current(stamp))
        router.change(2,3,20,event.content);self.assertFalse(router.source_current(stamp))
        newer=router.source_stamp(2,3,20);router.confirm(event,999)
        self.assertFalse(router.source_current(newer))
        final=router.source_stamp(2,3,20);router.change(2,3,20,None)
        self.assertFalse(router.source_current(final))
        # A deleted/re-observed ID must not revive an old dependency even
        # when the clock has not advanced (coarse Windows clock tick).
        router.observe(event)
        self.assertFalse(router.source_current(stamp))

    def test_human_boundary_is_per_speaker_place_and_confirmed_return(self):
        router=SocialRouter();flows=SimpleNamespace(flows={})
        def event(mid,author=4,channel=3):return replace(routing.SocialRuntime.event(self,id=mid),author=author,channel=channel)
        human=replace(event(20,5),member_roles=MemberRoles(5,addressee=4))
        router.observe(human)
        self.assertEqual(router.packet(event(21),flows,{},999)[0]['pending_human_exchange']['source'],'20')
        self.assertIsNone(router.packet(event(21,channel=8),flows,{},999)[0]['pending_human_exchange'])
        self.assertIsNone(router.packet(event(21,author=6),flows,{},999)[0]['pending_human_exchange'])
        returned=event(22);router.observe(returned);router.confirm(returned,999)
        self.assertIsNone(router.packet(event(23),flows,{},999)[0]['pending_human_exchange'])


class RuntimeSources(unittest.IsolatedAsyncioTestCase):
    setUp=routing.SocialRuntime.setUp
    asyncTearDown=routing.SocialRuntime.asyncTearDown
    event=routing.SocialRuntime.event
    settle=routing.SocialRuntime.settle
    configure=routing.SocialRuntime.configure
    start=routing.SocialRuntime.start

    async def prepare(self):
        await self.start()
        await self.runtime.ingest(replace(self.event(id=20,content='<@4> 너는 어느 쪽이 좋아?'),author=5,member_mentions=(4,)))
        await self.settle()
        self.backend.assess_social.return_value=SocialDecision('bot','resume','0','question',True)

    async def test_pending_source_deleted_during_judgment_vetoes_old_decision(self):
        await self.prepare()
        async def judge(packet):
            self.assertEqual(packet['pending_human_exchange']['source'],'20')
            await self.runtime.message_changed(2,3,20,None)
            return SocialDecision('bot','resume','0','question',True)
        self.backend.assess_social.side_effect=judge
        await self.runtime.ingest(self.event(id=21,content='아까 네 설명에는 어떤 근거가 있어?'));await self.settle()
        self.assertEqual([e.id for e,a in self.transport.sent],[10])
        self.assertTrue(any(d['code']=='social_source_changed' for d in self.runtime.diagnostics))
        self.assertEqual(self.runtime.failures,0)
        self.assertEqual(self.runtime.traces[-1]['outcome'],'cancelled')

    async def test_permission_wait_cannot_rebind_old_packet_to_new_source(self):
        await self.prepare();self.settings.set(1,'reactions',True)
        packet=self.runtime.social.packet;permissions=self.transport.permissions;route=self.runtime.social_route
        armed=False;changed=False;in_route=False
        async def routed(*args,**kwargs):
            nonlocal in_route
            in_route=True
            try:return await route(*args,**kwargs)
            finally:in_route=False
        def observed(*args,**kwargs):
            nonlocal armed
            result=packet(*args,**kwargs)
            if in_route:armed=True
            return result
        async def change(event):
            nonlocal armed,changed
            if armed:
                armed=False;changed=True
                await self.runtime.message_changed(2,3,20,None)
            return await permissions(event)
        self.runtime.social.packet=observed;self.transport.permissions=change;self.runtime.social_route=routed
        self.backend.assess_social.reset_mock()
        await self.runtime.ingest(self.event(id=21,content='아까 설명은 어떤 기준이었어?'));await self.settle()
        self.assertTrue(changed)
        self.backend.assess_social.assert_not_awaited()
        self.assertEqual([e.id for e,a in self.transport.sent],[10])
        self.assertEqual(self.runtime.traces[-1]['outcome'],'cancelled')

    async def test_pending_source_edit_while_sending_vetoes_old_response(self):
        await self.prepare();execute=self.transport.execute
        async def changed(event,action,library,fresh):
            await self.runtime.message_changed(2,3,20,'수정된 사람 발언')
            self.assertFalse(await fresh())
            return await execute(event,action,library,fresh)
        self.transport.execute=changed
        await self.runtime.ingest(self.event(id=21,content='아까 네 설명에는 어떤 근거가 있어?'));await self.settle()
        self.assertEqual([e.id for e,a in self.transport.sent],[10])
        self.assertEqual(self.runtime.failures,0)
        self.assertEqual(self.runtime.traces[-1]['outcome'],'cancelled')
