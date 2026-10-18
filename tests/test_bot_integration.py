"""Synthetic events only: real gateway/network/GPU remain separate QA layers."""
import asyncio
from copy import deepcopy
from datetime import datetime,timezone
from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
import secrets
import tempfile
import unittest
from PIL import Image

from echomate_bot.settings import Settings,DEFAULTS,scope
from echomate_bot.character import instruction,needs_rewrite
from echomate_bot.actions import Action,Kind,parse_action,validate_action
from echomate_bot.runtime import Runtime,Event
from echomate_bot.vision import VisualCache,frames,validate_url
from echomate_bot.media import MediaLibrary
from echomate_bot.inference import visible
from echomate_studio.participation import ContextAssessment
from echomate_studio.implicit_address import ImplicitAddress


class FakeBackend:
    def __init__(self):self.pending=0;self.failed=False;self.wait=None;self.calls=[];self.action='TEXT'
    async def classify(self,context):return ContextAssessment(False,True,True)
    async def continuity(self,context):return ImplicitAddress(True,True)
    async def text(self,context,cfg):
        self.calls.append(context)
        if self.wait:await self.wait.wait()
        return '응, 테스트 답변이야.'
    async def propose(self,context,catalog):
        self.catalog=catalog
        return json.dumps(dict(kind=self.action,text='',asset='👍' if self.action=='REACTION' else ''))
    async def visual(self,images,metadata):
        self.calls.append((images,metadata))
        return json.dumps(dict(objects=['빨간 도형'],emotion_candidates=[],action='정지',motion='판단 제한',uncertainty='합성 이미지',evidence=['빨간 픽셀']))
    async def close(self):pass


class FakeTransport:
    bot_id=999
    def __init__(self):self.sent=[];self.allow=True
    async def permissions(self,event):return dict(view=self.allow,send=self.allow,react=self.allow,attach=self.allow)
    async def catalog(self,event,cache):return dict(reactions={'👍':'동의'},stickers={})
    async def execute(self,event,action,library,fresh):
        if not await fresh():raise ValueError('stale')
        self.sent.append((event,action));return 9000+len(self.sent)


class BotIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='local_data')
        self.root=Path(self.temp.name)
        self.settings=Settings(1,secrets.token_hex(32),self.root/'settings.json')
        self.settings.set_scope(1,2,3,'mention')
        self.settings.set(1,'enabled',True)
        self.backend=FakeBackend();self.transport=FakeTransport()
        self.cache=VisualCache(self.root/'cache.sqlite3');self.library=MediaLibrary(self.settings,self.root/'library')
        self.runtime=Runtime(self.settings,self.backend,self.transport,self.cache,self.library,ledger_path=self.root/'ledger.sqlite3')
    async def asyncTearDown(self):
        await self.runtime.close();self.temp.cleanup()
    def event(self,id=10,channel=3,content='<@999> 안녕',parent=None):
        return Event(id,2,channel,4,content,datetime.now(timezone.utc),parent=parent)
    async def settle(self):
        await asyncio.gather(*list(self.runtime.tasks.values()),return_exceptions=True)
    async def test_actual_owner_ids_and_signed_storage(self):
        for user in (2,'1',True):
            with self.assertRaises(PermissionError):self.settings.set(user,'enabled',False)
        d=json.loads(self.settings.path.read_text(encoding='utf-8'));d['data']['enabled']=False
        self.settings.path.write_text(json.dumps(d),encoding='utf-8')
        with self.assertRaises(PermissionError):Settings(1,self.settings._key.decode(),self.settings.path)
    async def test_transient_windows_replace_lock_preserves_atomic_settings(self):
        from unittest.mock import patch
        original=Path.replace;attempts=[]
        def transient(path,target):
            attempts.append(path)
            if len(attempts)==1:raise PermissionError('transient sharing lock')
            return original(path,target)
        with patch.object(Path,'replace',transient):self.settings.set(1,'mood','기쁨')
        self.assertEqual(self.settings.get()['mood'],'기쁨')
        self.assertEqual(len(attempts),2)
    async def test_scope_defaults_thread_override_and_parent_inheritance(self):
        self.assertEqual(scope(self.settings.get(),2,7,3),'silent')
        self.settings.set_scope(1,2,3,'mention',inherit=True)
        self.assertEqual(scope(self.settings.get(),2,7,3),'mention')
        self.settings.set_scope(1,2,7,'silent',thread=True)
        self.assertEqual(scope(self.settings.get(),2,7,3),'silent')
        self.assertEqual(scope(self.settings.get(),8,3),'silent')
    async def test_mention_sends_once_and_persists_replay_guard(self):
        event=self.event();await self.runtime.ingest(event);await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        self.assertEqual(self.backend.catalog['allowed_actions'],['SILENCE','TEXT'])
        await self.runtime.ingest(event);await self.settle();self.assertEqual(len(self.transport.sent),1)
        self.assertFalse(self.runtime.ledger.reserve(event,100,0))
    async def test_disallowed_channel_bot_and_dm_do_not_infer(self):
        await self.runtime.ingest(self.event(channel=8));await self.settle()
        await self.runtime.ingest(replace(self.event(id=11),bot=True))
        await self.runtime.ingest(replace(self.event(id=12),guild=None))
        await self.runtime.ingest(replace(self.event(id=13),opted_out=True))
        self.assertEqual(self.backend.calls,[]);self.assertEqual(self.transport.sent,[])
    async def test_new_message_cancels_old_generation(self):
        self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event());await asyncio.sleep(.02)
        await self.runtime.ingest(self.event(id=11,content='<@999> 새 질문'))
        self.backend.wait.set();await self.settle()
        self.assertEqual([e.id for e,a in self.transport.sent],[11])
    async def test_unmentioned_same_author_retains_actual_pending_mention(self):
        self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event());await asyncio.sleep(.02)
        await self.runtime.ingest(self.event(id=11,content='이 내용도 함께 봐 줘'))
        self.backend.wait.set();await self.settle()
        self.assertEqual([e.id for e,a in self.transport.sent],[11])
        self.assertEqual(self.runtime.pending_mentions,{})
        self.assertTrue(self.backend.catalog['directed_to_bot'])
    async def test_pending_mention_never_transfers_to_other_speaker(self):
        self.backend.wait=asyncio.Event()
        await self.runtime.ingest(self.event());await asyncio.sleep(.02)
        await self.runtime.ingest(replace(self.event(id=11,content='다른 사람 이야기'),author=5))
        self.backend.wait.set();await self.settle()
        self.assertFalse(self.transport.sent);self.assertEqual(self.runtime.pending_mentions,{})
    async def test_config_change_and_permission_revoke_veto_send(self):
        self.backend.wait=asyncio.Event();await self.runtime.ingest(self.event());await asyncio.sleep(.02)
        self.transport.allow=False;self.backend.wait.set();await self.settle()
        self.assertFalse(self.transport.sent)
    async def test_settings_revision_veto_even_if_scope_still_allowed(self):
        self.backend.wait=asyncio.Event();await self.runtime.ingest(self.event());await asyncio.sleep(.02)
        self.settings.set(1,'mood','기쁨');self.backend.wait.set();await self.settle()
        self.assertFalse(self.transport.sent)
    async def test_engaged_reply_does_not_require_new_autonomy_chance(self):
        await self.runtime.ingest(self.event());await self.settle()
        with self.runtime.ledger.db() as db:db.execute('UPDATE sent SET at=at-10')
        self.settings.set(1,'cooldown',2)
        await self.runtime.ingest(self.event(id=11,content='그다음은 어떻게 해?'));await self.settle()
        self.assertEqual(len(self.transport.sent),2)
    async def test_reaction_only_never_sends_text(self):
        self.settings.set_scope(1,2,3,'reaction');self.settings.set(1,'reactions',True)
        self.backend.action='REACTION'
        await self.runtime.ingest(self.event());await self.settle()
        self.assertEqual(self.transport.sent[0][1].kind,Kind.REACTION)
        self.assertEqual(self.backend.calls,[])
    async def test_no_useful_text_can_still_get_contextually_appropriate_reaction(self):
        import random
        self.settings.set_scope(1,2,3,'autonomous');self.settings.set(1,'reactions',True)
        self.runtime.rng=random.Random(1);self.backend.action='REACTION'
        async def reaction_context(context):return ContextAssessment(False,False,True)
        self.backend.classify=reaction_context
        await self.runtime.ingest(self.event(content='좋은 소식이네'));await self.settle()
        self.assertEqual(self.transport.sent[0][1].kind,Kind.REACTION)
        self.assertFalse(self.backend.calls)
    async def test_unicode_quoted_code_url_are_not_destructively_stripped(self):
        self.assertFalse(needs_rewrite('`print("ㅋㅋ")`\n> ㅠㅠ\nhttps://example.org/ㅋㅋ',[]))
        self.assertTrue(needs_rewrite('맞아 ㅋㅋ',[]))
        self.assertIn('75%',instruction(DEFAULTS))
        with self.assertRaises(ValueError):visible('<|channel>thought\nprivate<channel|>final')
    async def test_ssrf_bytes_pixels_and_animation_samples(self):
        for url in ('http://cdn.discordapp.com/attachments/a','https://127.0.0.1/a','https://cdn.discordapp.com.evil/attachments/a','https://cdn.discordapp.com@evil/attachments/a','https://cdn.discordapp.com/../private'):
            with self.assertRaises(ValueError):validate_url(url)
        images=[Image.new('RGB',(20,20),c) for c in ('red','blue','green')]
        data=BytesIO();images[0].save(data,format='GIF',save_all=True,append_images=images[1:],duration=100)
        sampled,meta=frames(data.getvalue());self.assertEqual(len(sampled),3);self.assertEqual(meta['sampled'],[0,1,2])
        with self.assertRaises(Exception):frames(b'not an image')
    async def test_guild_cache_isolation_and_dedup(self):
        image=BytesIO();Image.new('RGB',(12,12),'red').save(image,format='PNG');data=image.getvalue()
        await self.cache.analyze(2,'emoji:5',data,self.backend)
        await self.cache.analyze(2,'emoji:5',data,self.backend)
        self.assertEqual(len(self.backend.calls),1)
        self.assertEqual(self.cache.descriptions(8),{})
        self.cache.retain(2,set(),'emoji:');self.assertEqual(self.cache.descriptions(2),{})
    async def test_inbound_asset_not_approved_and_media_tamper_denied(self):
        image=BytesIO();Image.new('RGB',(12,12),'red').save(image,format='PNG');data=image.getvalue()
        with self.assertRaises(PermissionError):await self.library.register(2,data,2,'tag','purpose',self.cache,self.backend)
        mid=await self.library.register(1,data,2,'tag','purpose',self.cache,self.backend)
        with self.assertRaises(PermissionError):self.library.resolve(mid,8)
        path=self.library.resolve(mid,2);path.write_bytes(b'changed')
        with self.assertRaises(PermissionError):self.library.resolve(mid,2)
    async def test_action_schema_rejects_extra_fields_and_unapproved_asset(self):
        with self.assertRaises(ValueError):parse_action('{"kind":"TEXT","text":"x","asset":"","api":"send"}')
        self.assertFalse(validate_action(Action(Kind.MEDIA,asset='unknown'),dict(DEFAULTS,media=True),'autonomous',{'view':True,'send':True,'attach':True},{},self.library,2))
    async def test_live_sdk_command_and_component_checks(self):
        from echomate_bot.discord_app import EchoClient,OwnerPanel
        from unittest.mock import AsyncMock,patch
        from types import SimpleNamespace
        import discord
        with patch('echomate_bot.discord_app.VisualCache',return_value=self.cache),patch('echomate_bot.discord_app.MediaLibrary',return_value=self.library),patch('echomate_bot.discord_app.Runtime',return_value=self.runtime):
            client=EchoClient(self.settings,self.backend,[2])
        response=SimpleNamespace(is_done=lambda:False,send_message=AsyncMock())
        intruder=SimpleNamespace(user=SimpleNamespace(id=4),guild_id=2,response=response)
        owner=SimpleNamespace(user=SimpleNamespace(id=1),guild_id=2,response=response)
        group=client.tree.get_commands(guild=discord.Object(2))[0]
        self.assertFalse(await group.interaction_check(intruder))
        self.assertTrue(await group.interaction_check(owner))
        panel=OwnerPanel(client)
        self.assertFalse(await panel.interaction_check(intruder))
        self.assertTrue(await panel.interaction_check(owner))
        response.send_message.assert_called_with('이 작업은 사용할 수 없어.',ephemeral=True)
        panel.stop()
    async def test_transport_rechecks_scope_before_each_output_and_sets_nonce(self):
        from echomate_bot.discord_app import DiscordTransport
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        current=SimpleNamespace(reply=AsyncMock(return_value=SimpleNamespace(id=44)),add_reaction=AsyncMock())
        channel=SimpleNamespace(fetch_message=AsyncMock(return_value=current))
        transport=DiscordTransport(SimpleNamespace(user=SimpleNamespace(id=999)))
        transport.channel=lambda event:channel
        checks=iter([True,True,False])
        async def fresh():return next(checks)
        with self.assertRaises(ValueError):
            await transport.execute(self.event(),Action(Kind.TEXT_REACTION,'내용','👍'),self.library,fresh)
        current.reply.assert_awaited_once()
        current.add_reaction.assert_not_awaited()
        self.assertEqual(current.reply.call_args.kwargs['nonce'],10)
    async def test_animation_work_limit_and_mood_bounds(self):
        from echomate_bot.character import effective_character
        self.settings.set(1,'auto_mood',True)
        cfg=self.settings.get()
        self.assertEqual(effective_character(cfg,'합격했어')['mood'],'기쁨')
        self.assertEqual(effective_character(DEFAULTS,'합격했어')['mood'],'평온')
        self.assertEqual(self.settings.get()['mood'],'평온')
        with self.assertRaises(ValueError):self.settings.set(1,'warmth',101)
        with self.assertRaises(ValueError):self.settings.set(1,'model','untrusted_remote')
    async def test_gpu_worker_queue_cancellation_retains_single_owner(self):
        from echomate_bot.inference import LocalBackend
        import threading,time
        backend=LocalBackend(max_pending=1);entered=threading.Event();stopped=threading.Event()
        def worker(messages,images,budget,weight,stop):
            entered.set()
            while not stop.is_set():time.sleep(.005)
            stopped.set();raise InterruptedError('cancelled')
        backend._generate=worker
        task=asyncio.create_task(backend._job([]))
        while not entered.is_set():await asyncio.sleep(.005)
        with self.assertRaises(RuntimeError):await backend._job([])
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertTrue(stopped.is_set());self.assertEqual(backend.pending,0)
        backend.executor.shutdown(wait=True)
    async def test_download_redirect_and_stream_size_fail_closed(self):
        from echomate_bot.vision import download,MAX_BYTES
        class Response:
            status=302;content_length=0
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
        class Session:
            def get(self,*args,**kwargs):
                self.kwargs=kwargs;return Response()
        session=Session()
        with self.assertRaises(ValueError):await download('https://cdn.discordapp.com/attachments/1/test.png',session)
        self.assertFalse(session.kwargs['allow_redirects'])
    async def test_device_failure_and_deleted_thread_invalidate_pending_turn(self):
        self.backend.wait=asyncio.Event();await self.runtime.ingest(self.event());await asyncio.sleep(.02)
        self.runtime.invalidate(3);self.backend.wait.set();await self.settle()
        self.assertFalse(self.transport.sent)
        self.backend.failed=True
        async def fail(context):raise RuntimeError('device failure injected, no real allocation')
        self.backend.classify=fail
        await self.runtime.ingest(self.event(id=11));await self.settle()
        self.assertTrue(self.runtime.stopped)
    async def test_injected_cuda_oom_disables_backend_without_real_gpu_allocation(self):
        import torch,threading
        from types import SimpleNamespace
        from unittest.mock import patch,Mock
        from echomate_bot.inference import LocalBackend
        class Tokenizer:
            eos_token_id=0
            def apply_chat_template(self,*args,**kwargs):return {'input_ids':torch.tensor([[1,2]])}
            def convert_tokens_to_ids(self,token):return 3
        backend=LocalBackend();backend.load=lambda:None;backend.health=lambda:None
        backend.processor=SimpleNamespace(tokenizer=Tokenizer())
        backend.model=SimpleNamespace(generate=Mock(side_effect=torch.cuda.OutOfMemoryError('synthetic OOM, no allocation')))
        with patch.object(torch.Tensor,'to',lambda tensor,*args,**kwargs:tensor),patch.object(torch.cuda,'reset_peak_memory_stats'),patch.object(torch.cuda,'empty_cache') as empty:
            with self.assertRaisesRegex(RuntimeError,'inference disabled'):
                backend._generate([],None,20,'persona',threading.Event())
            empty.assert_called_once()
        self.assertTrue(backend.failed)
        with self.assertRaises(RuntimeError):await backend._job([])
        backend.executor.shutdown(wait=True)
    async def test_repeated_failures_disable_runtime(self):
        async def fail(context):raise RuntimeError('synthetic')
        self.backend.classify=fail
        for i in range(3):await self.runtime.ingest(self.event(id=20+i));await self.settle()
        self.assertTrue(self.runtime.stopped)
