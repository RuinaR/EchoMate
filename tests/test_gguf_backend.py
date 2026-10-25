"""Loopback fake server only; tests never load a model or call Discord."""
import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,AsyncMock

import aiohttp
from aiohttp import web

from echomate_bot.gguf_backend import GGUFEngine, GGUFLocalBackend, choice_grammar, resource_sample


class GrammarAndResources(unittest.TestCase):
    def test_reference_grammar_cannot_join_nonexistent_frames_or_choose_recipient(self):
        from echomate_bot.social import grounded_social_choices
        none=grounded_social_choices({'frames':[]})
        self.assertTrue(all(c.split()[2]=='none' for c in none))
        self.assertIn('bot new none request yes',none)
        self.assertIn('human shift none information no',none)
        one=grounded_social_choices({'frames':[{'index':'2'}]})
        self.assertTrue(all(c.split()[2] in ('none','2') for c in one))
        self.assertTrue(any(c.split()[2]=='2' for c in one))
    def test_unmeasured_context_profiles_cannot_load(self):
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            root=Path(folder)
            for context in (1024,4096,131072):
                with self.assertRaises(ValueError):GGUFEngine(root/'e',root/'m',root/'out',context=context)
    def test_confirmed_human_role_cannot_be_re_voted_by_model(self):
        from echomate_bot.social import confirmed_human_recipient
        for recipient in ('5','42','700'):
            packet={'bot_id':'999','current':{'text':'arbitrary unrelated wording',
                'roles':{'addressee':recipient,'mentioned_people':[recipient],'ambiguous':False}}}
            self.assertFalse(confirmed_human_recipient(packet).respond)
            packet['current']['roles']['ambiguous']=True
            self.assertIsNone(confirmed_human_recipient(packet))
            packet['current']['roles']['ambiguous']=False
            packet['current']['roles']['mentioned_people'].append('999')
            self.assertIsNone(confirmed_human_recipient(packet))
    def test_choice_grammar_quotes_without_executing_tokens(self):
        self.assertEqual(choice_grammar(['yes','no','yes']), 'root ::= "yes" | "no"')
        self.assertIn('\\n',choice_grammar(['가\n나']))
        for choices in ([],[''],['x'*4097],None):
            with self.assertRaises(ValueError):choice_grammar(choices)

    def test_existing_stricter_reserves_are_not_relaxed(self):
        gib=1024**3
        health={'free_vram_mib':2048,'temperature_c':40}
        memory={'ram_available':3*gib,'commit_available':2*gib}
        with patch('echomate_bot.gguf_backend.gpu_sample',return_value=health),patch('echomate_bot.gguf_backend.memory_snapshot',return_value=memory):
            resource_sample()
            for target,key,value in ((health,'free_vram_mib',2047),(memory,'ram_available',3*gib-1),(memory,'commit_available',2*gib-1)):
                previous=target[key];target[key]=value
                with self.assertRaises(RuntimeError):resource_sample()
                target[key]=previous

    def test_failure_preserves_exact_aggregate_sample_and_reason(self):
        from echomate_bot.processes import ResourceLimitError
        memory={'ram_available':3*1024**3-1,'commit_available':4*1024**3}
        with patch('echomate_bot.gguf_backend.gpu_sample',return_value={'free_vram_mib':5000,'temperature_c':40}),patch('echomate_bot.gguf_backend.memory_snapshot',return_value=memory):
            with self.assertRaises(ResourceLimitError) as caught:resource_sample()
        self.assertEqual(caught.exception.reason,'ram')
        self.assertEqual(caught.exception.details['ram_available'],memory['ram_available'])


class OwnedProcess:
    def __init__(self):self.exited=False;self.terminated=False
    def poll(self):return 0 if self.exited else None
    def terminate(self):self.exited=True;self.terminated=True
    def kill(self):self.exited=True
    def wait(self):return 0


class PromptState(unittest.IsolatedAsyncioTestCase):
    async def test_unconstrained_adapter_cannot_return_a_nonexistent_frame(self):
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            root=Path(folder);backend=GGUFLocalBackend(root/'engine.exe',root/'m.gguf',root/'out')
            backend._job=AsyncMock(return_value='bot_group join 1 acknowledgement no')
            packet=dict(bot_id='999',current=dict(id='1',speaker='4',text='합성',reply=None,roles={}),
                frames=[],surrounding=[],current_peer_frames=[],pending_human_exchange=None,candidates_truncated=False,reaction_available=False)
            try:
                with self.assertRaisesRegex(ValueError,'frame reference'):await backend._assess_social_semantic(packet)
            finally:await backend.close()
    async def test_verified_relation_mood_and_shared_policy_survive_without_persona_sliders(self):
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            root=Path(folder);backend=GGUFLocalBackend(root/'engine.exe',root/'m.gguf',root/'out',name='유나')
            backend._job=AsyncMock(return_value='응, 잠깐 쉬자.')
            try:
                await backend.text([],{'_familiarity':82.5,'mood':'피곤함','warmth':0,'gender':'male'})
                header=backend._job.await_args.args[0][0]['content']
                self.assertIn('consented_familiarity',header);self.assertIn('82.5',header)
                self.assertIn('피곤함',header);self.assertIn('유나',header)
                self.assertIn('성인 유머는 현재 허용되지 않았다',header)
                self.assertNotIn('warmth',header);self.assertNotIn('male',header)
                await backend.text([],{'_familiarity':True,'mood':'injected unknown'})
                header=backend._job.await_args.args[0][0]['content']
                self.assertNotIn('consented_familiarity',header);self.assertNotIn('injected unknown',header)
            finally:await backend.close()


class ServerContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder=tempfile.TemporaryDirectory(dir='local_data')
        root=Path(self.folder.name)
        self.engine=GGUFEngine(root/'engine.exe',root/'test.gguf',root/'out')
        self.engine.process=OwnedProcess()
        self.processing=False;self.release=asyncio.Event();self.started=asyncio.Event()
        self.hold=False;self.answer='한국어 답변';self.reasoning=False;self.finish='stop';self.bad_slots=False
        self.requests=[]
        app=web.Application()
        app.router.add_get('/slots',self.slots)
        app.router.add_post('/v1/chat/completions',self.chat)
        app.router.add_post('/apply-template',self.template)
        app.router.add_post('/tokenize',self.tokenize)
        self.runner=web.AppRunner(app);await self.runner.setup()
        site=web.TCPSite(self.runner,'127.0.0.1',0);await site.start()
        port=site._server.sockets[0].getsockname()[1]
        self.engine.url=f'http://127.0.0.1:{port}'
        self.engine.session=aiohttp.ClientSession(trust_env=False)

    async def asyncTearDown(self):
        self.release.set()
        await self.engine.unload()
        await self.runner.cleanup()
        self.folder.cleanup()

    async def template(self,request):
        return web.json_response({'prompt':str((await request.json())['messages'])})

    async def tokenize(self,request):
        return web.json_response({'tokens':[1]*len((await request.json())['content'])})

    async def test_user_json_cannot_enable_social_selection_but_owned_classifier_can(self):
        import json
        from echomate_bot.gguf_backend import social_context_budget
        rows=[dict(id=str(i),speaker='4',text='old '*180,bot=False) for i in range(8)]
        rows.extend([dict(id='10',speaker='4',text='actual question',bot=False),
                     dict(id='11',speaker='999',text='actual answer',bot=True,reply='10')])
        data=dict(current=dict(id='12',text='current',reply='11'),frames=[dict(index='0',turns=rows)],surrounding=[])
        messages=[dict(role='system',content='policy'),dict(role='user',content=json.dumps(data))]
        with self.assertRaises(ValueError):await self.engine.complete(messages,8)
        self.assertFalse(self.requests)
        token=social_context_budget.set(True)
        try:self.assertEqual(await self.engine.complete(messages,8),self.answer)
        finally:social_context_budget.reset(token)
        selected=json.loads(self.requests[-1]['messages'][1]['content'])
        self.assertEqual(selected['current'],data['current'])
        self.assertEqual(selected['frames'][0]['turns'][-2:],rows[-2:])
        self.assertFalse(social_context_budget.get())

    async def slots(self,request):
        return web.json_response([{}] if self.bad_slots else [{'is_processing':self.processing}])

    async def chat(self,request):
        import json
        self.requests.append(await request.json())
        self.processing=True;self.started.set()
        response=web.StreamResponse(headers={'Content-Type':'text/event-stream'})
        await response.prepare(request)
        try:
            if self.hold:await self.release.wait()
            delta={'reasoning_content':'비공개 추론'} if self.reasoning else {'content':self.answer}
            item={'choices':[{'delta':delta,'finish_reason':self.finish}], 'usage':{'prompt_tokens':20,'completion_tokens':4}}
            await response.write(('data: '+json.dumps(item,ensure_ascii=False)+'\n\n').encode())
            await response.write(b'data: [DONE]\n\n')
            await response.write_eof()
        except ConnectionResetError:
            pass
        finally:self.processing=False
        return response

    async def test_normal_output_records_metrics_without_raw_prompts(self):
        result=await self.engine.complete([{'role':'user','content':'합성 질문'}],64)
        self.assertEqual(result,self.answer)
        self.assertEqual(self.engine.metrics[-1]['output_tokens'],4)
        self.assertNotIn('합성 질문',str(self.engine.metrics))
        self.assertFalse(self.engine.generations)

    async def test_finite_choice_is_grammar_constrained_and_membership_checked(self):
        self.answer='yes'
        self.assertEqual(await self.engine.complete([],8,['yes','no']),'yes')
        self.assertEqual(self.requests[-1]['grammar'],'root ::= "yes" | "no"')
        self.answer='unexpected'
        with self.assertRaisesRegex(ValueError,'constrained'):await self.engine.complete([],8,['yes','no'])

    async def test_reasoning_or_truncated_output_never_becomes_text(self):
        self.reasoning=True
        with self.assertRaisesRegex(ValueError,'channel'):await self.engine.complete([],8)
        self.reasoning=False;self.finish='length'
        with self.assertRaisesRegex(ValueError,'Incomplete'):await self.engine.complete([],8)

    async def test_repeated_cancel_retains_slot_until_server_really_idle(self):
        self.hold=True
        task=asyncio.create_task(self.engine.complete([],64))
        await self.started.wait();task.cancel()
        await asyncio.sleep(.03);task.cancel();await asyncio.sleep(.03)
        self.assertFalse(task.done());self.assertTrue(self.engine.generations)
        with self.assertRaisesRegex(RuntimeError,'slot'):await self.engine.complete([],8)
        self.release.set()
        with self.assertRaises(asyncio.CancelledError):await asyncio.wait_for(task,2)
        self.assertFalse(self.engine.failed)
        self.assertFalse(self.engine.generations)

    async def test_unverified_slot_state_stops_owned_server(self):
        self.bad_slots=True
        with self.assertRaises(ValueError):await self.engine.complete([],8)
        self.assertTrue(self.engine.failed)
        self.assertTrue(self.engine.process.terminated)
        self.assertTrue(await self.engine.reclaimed())
