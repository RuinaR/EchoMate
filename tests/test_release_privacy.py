from echomate_bot.character_profiles import DEFAULT_PROFILE
"""Release contracts: isolated SQLite, fake transport, no external network."""
import asyncio
from dataclasses import replace
from datetime import datetime,timezone
import json
from pathlib import Path
import secrets
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,patch
from echomate_bot.companion_store import CompanionStore
from echomate_bot.companion import handle_request
from echomate_bot.settings import Settings,DEFAULTS
from echomate_bot.runtime import Event
from echomate_bot.output_policy import contains_code
from echomate_bot.research import PublicResearch
import test_bot_integration as base

class ConsentStorage(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='local_data');self.path=Path(self.temp.name)/'private.sqlite3';self.store=CompanionStore(self.path,clock=lambda:1000)
    def tearDown(self):self.temp.cleanup()
    def test_unfenced_source_is_blocked_but_natural_language_and_api_names_are_not(self):
        for text in ('fn main() { println!("hi"); }','SELECT name FROM users;','int main() { return 0; }','echo "hello"','이렇게 쓰면 돼: print("hello")','예시는 Console.WriteLine("hello"); 로 해.'):
            self.assertTrue(contains_code(text))
        for text in ('좋아~~~ 준비됐어.','SELECT는 자료를 조회할 때 쓰는 SQL 명령이야.','fn 키워드는 함수를 선언할 때 쓰여.','discord.Client와 파일명 main.py를 확인해 봐.'):
            self.assertFalse(contains_code(text))
    def event(self):return Event(100,2,3,4,'나는 지금 퍼즐 게임의 새 레벨을 천천히 만들고 있어.',datetime.fromtimestamp(1001,timezone.utc))
    def test_defaults_self_only_independent_and_server_scope(self):
        self.assertEqual(self.store.consent(2,1),dict(relationships=False,memory=False,summaries=False))
        with self.assertRaises(PermissionError):self.store.set_consent(2,1,'memory',True,subject=4)
        self.store.set_consent(2,4,'relationships',True)
        self.assertTrue(self.store.automatic_allowed(2,4));self.assertFalse(self.store.automatic_allowed(2,4,'memory'));self.assertFalse(self.store.automatic_allowed(8,4))
        self.store.set_consent(2,4,'relationships',False);self.store.relationship(2,4,100);self.assertFalse(self.store.users(2))
    def test_real_v4_migration_does_not_grant_owner_or_new_category(self):
        self.store.add_memory(2,4,3,'나는 퍼즐을 좋아해')
        with self.store.db() as db:
            db.execute('DROP TABLE consent_choices');db.execute('DROP TABLE conversation_summaries');db.execute('PRAGMA user_version=4')
            db.execute('INSERT INTO subject_consents VALUES(?,?,?)',('2','4',999));db.execute('INSERT INTO memory_optouts VALUES(?,?)',('2','4'))
        self.store=CompanionStore(self.path)
        self.assertEqual(self.store.consent(2,4),dict(relationships=True,memory=False,summaries=False));self.assertFalse(any(self.store.consent(2,1).values()))
        self.assertEqual(len(self.store.memories(2,4)),1)
    def test_extractive_summary_consent_version_scope_expiry_and_source_delete(self):
        e=self.event();self.assertFalse(self.store.save_summary(e,e.content,None))
        self.store.set_consent(2,4,'summaries',True);version=self.store.consent_version(2,4,'summaries')
        self.assertTrue(self.store.save_summary(e,e.content,version));self.assertTrue(self.store.summaries(2,4,3));self.assertFalse(self.store.summaries(2,5,3));self.assertFalse(self.store.summaries(2,4,8))
        self.assertFalse(self.store.save_summary(replace(e,id=101),'나는 친구의 비밀 이야기를 오늘 오래 들었어.',version))
        self.store.set_consent(2,4,'summaries',False)
        self.assertFalse(self.store.save_summary(replace(e,id=102),e.content,version));self.assertTrue(self.store.summaries(2,4,3))
        self.store.delete_source(2,100,known=False);self.assertFalse(self.store.summaries(2,4,3))
        self.store.set_consent(2,4,'summaries',True);self.assertFalse(self.store.save_summary(e,e.content,version))
    def test_delete_and_withdraw_are_distinct_and_pending_work_cannot_restore(self):
        self.store.set_consent(2,4,'memory',True);self.store.add_memory(2,4,3,'나는 퍼즐을 좋아해')
        self.store.set_consent(2,4,'memory',False);self.assertEqual(len(self.store.memories(2,4)),1)
        self.store.delete_personal(2,4,'memory');self.assertFalse(self.store.memories(2,4));self.assertFalse(self.store.consent(2,4)['memory'])
        self.store.set_consent(2,4,'summaries',True);e=self.event();v=self.store.consent_version(2,4,'summaries');self.store.save_summary(e,e.content,v)
        self.store.delete_personal(2,4,'summaries');self.assertFalse(self.store.summaries(2,4))
        self.assertFalse(self.store.save_summary(e,e.content,v))
        self.store.set_consent(2,4,'summaries',True)
        self.assertFalse(self.store.save_summary(e,e.content,self.store.consent_version(2,4,'summaries')))
    def test_withdrawal_between_extract_and_write_blocks_collection(self):
        self.store.set_consent(2,4,'memory',True);original=self.store.add_memory
        def race(*args,**kwargs):
            # Another store instance represents the Discord consent callback.
            CompanionStore(self.path,clock=lambda:1000).set_consent(2,4,'memory',False)
            return original(*args,**kwargs)
        with patch.object(self.store,'add_memory',side_effect=race):
            self.assertIsNone(self.store.extract(self.event(),'Asia/Seoul',text='나는 퍼즐 게임을 좋아해'))
        self.assertFalse(self.store.memories(2,4))
        with self.assertRaises(ValueError):self.store.set_affinity(2,4,70,require_consent=True)
        with self.assertRaises(ValueError):self.store.set_alias(2,3,4,'별빛',require_consent=True)
    def test_summary_unavailable_is_not_no_interaction_and_other_subject_is_denied(self):
        self.store.set_consent(2,4,'relationships',True);self.store.relationship(2,4,10)
        e=replace(self.event(),content='나와 대화한 내용 요약해 줘')
        self.assertIn('교류 기록은 있지만',handle_request(self.store,e,DEFAULTS,999))
        self.assertIn('조회 권한',handle_request(self.store,replace(e,content='12345678와 대화한 내용 요약해 줘'),DEFAULTS,999))

class RuntimeRelease(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle
    async def test_daily_count_never_blocks_new_requests(self):
        self.runtime.direct_cooldown=0
        with self.runtime.ledger.db() as db:
            now=__import__('time').time()
            db.executemany('INSERT INTO sent VALUES(?,?,?,?,?,?)',[(str(10000+i),'3',datetime.now(timezone.utc).date().isoformat(),now,'sent','TEXT') for i in range(1001)])
        for i in range(3):
            await self.runtime.ingest(self.event(id=11+i,content=f'<@999> 서로 다른 질문 {i}'));await self.settle()
        self.assertEqual(len(self.transport.sent),3);self.assertFalse(self.runtime.stopped)
        self.assertEqual(self.runtime.ledger.statistics()['successful'],1004)
    async def test_relation_updates_only_after_subject_choice_and_stops_on_withdrawal(self):
        self.runtime.direct_cooldown=0;store=CompanionStore(self.root/'private.sqlite3');self.runtime.companion=store
        await self.runtime.ingest(self.event());await self.settle();self.assertFalse(store.users(2))
        store.set_consent(2,4,'relationships',True)
        await self.runtime.ingest(self.event(id=11));await self.settle();self.assertEqual(store.users(2)[0]['interactions'],1)
        store.set_consent(2,4,'relationships',False)
        await self.runtime.ingest(self.event(id=12));await self.settle();self.assertEqual(store.users(2)[0]['interactions'],1)
    async def test_code_policy_final_boundary_all_profiles_and_input_code_understood(self):
        self.runtime.direct_cooldown=0;self.backend.text=AsyncMock(return_value='```python\nprint(1)\n```')
        for i,energy in enumerate((15,50,85)):
            mode='base'
            self.settings.set(1,'character_profile',dict(DEFAULT_PROFILE,energy=energy))
            self.settings.set(1,'model',mode)
            await self.runtime.ingest(self.event(id=30+i,content='<@999> def add(a,b): return a+b 이 함수 설명해 줘'));await self.settle()
        self.assertEqual(len(self.transport.sent),3)
        self.assertTrue(all(not contains_code(action.text) for _,action in self.transport.sent))
        self.assertIn('def add',str(self.backend.text.call_args.args))
    async def test_direct_reaction_avoids_text_generation_and_uses_original_source(self):
        self.settings.set(1,'reactions',True);self.runtime.direct_cooldown=0
        await self.runtime.ingest(self.event(content='<@999> 이 메시지에 👍 달아줘'));await self.settle()
        self.assertEqual(len(self.transport.sent),1);e,action=self.transport.sent[0]
        self.assertEqual(action.kind.value,'REACTION');self.assertEqual(action.asset,'👍');self.assertEqual(e.id,10);self.assertFalse(self.backend.calls)
    async def test_transient_reaction_failure_does_not_disable_emoji_for_future_requests(self):
        self.settings.set(1,'reactions',True);self.runtime.direct_cooldown=0
        original=self.transport.execute;self.transport.execute=AsyncMock(side_effect=PermissionError())
        await self.runtime.ingest(self.event(content='<@999> 이 메시지에 👍 달아줘'));await self.settle()
        self.assertFalse(self.runtime.blocked_assets);self.assertIn('send_failed',[d['code'] for d in self.runtime.diagnostics])
        self.transport.execute=original
        await self.runtime.ingest(self.event(id=11,content='<@999> 이 글에 👍 붙여줘'));await self.settle()
        self.assertEqual(len(self.transport.sent),1)
    async def test_explicit_program_creation_is_explained_without_gpu_in_every_profile(self):
        self.runtime.direct_cooldown=0
        for i,energy in enumerate((15,50,85)):
            mode='base'
            self.settings.set(1,'character_profile',dict(DEFAULT_PROFILE,energy=energy))
            self.settings.set(1,'model',mode)
            await self.runtime.ingest(self.event(id=60+i,content='<@999> Python으로 계산기 프로그램 만들어 줘'));await self.settle()
        self.assertEqual(len(self.transport.sent),3);self.assertFalse(self.backend.calls)
        self.assertTrue(all(not contains_code(a.text) and '코드' in a.text for _,a in self.transport.sent))
    async def test_unverified_url_is_not_sent_and_monitor_contains_no_message_content(self):
        self.backend.text=AsyncMock(return_value='확인했어 https://invented.example/path')
        await self.runtime.ingest(self.event());await self.settle()
        self.assertNotIn('https://',self.transport.sent[0][1].text)
        jobs=self.runtime.monitor();self.assertEqual(jobs[0]['status'],'sent');self.assertNotIn(self.event().content,json.dumps(jobs,ensure_ascii=False))

class PublicSourceQA(unittest.IsolatedAsyncioTestCase):
    async def test_http_redirect_size_and_failure_backoff(self):
        class Response:
            status=200
            def raise_for_status(self):pass
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            @property
            def content(self):return self
            async def iter_chunked(self,size):yield b'x'*1048577
        class Client:
            def __init__(self):self.calls=[];self.response=Response()
            def get(self,url,**kwargs):self.calls.append((url,kwargs));return self.response
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
        client=Client();clock=[100];research=PublicResearch(lambda:client,clock=lambda:clock[0])
        result=await research.lookup('discord.py 최신 버전',True)
        self.assertEqual(result['status'],'failed');self.assertEqual(result['error_type'],'ValueError')
        await research.lookup('개인적인 입력 discord.py 최신 버전',True);self.assertEqual(len(client.calls),1)
        self.assertEqual(client.calls[0][1],dict(allow_redirects=False))
        clock[0]+=31;client.response.status=302
        self.assertEqual((await research.lookup('discord.py 최신 버전',True))['status'],'failed');self.assertEqual(len(client.calls),2)
    async def test_unknown_disabled_failed_and_no_raw_query(self):
        research=PublicResearch();research._read=AsyncMock(return_value=dict(info=dict(version='2.7.1')))
        class Client:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
        research.factory=Client
        result=await research.lookup('개인별명123 discord.py 최신 버전 찾아봐',True)
        self.assertEqual(result['status'],'verified');self.assertNotIn('개인별명',str(research._read.call_args))
        self.assertEqual((await research.lookup('오늘 법률 뉴스',True))['status'],'unsupported')
        self.assertEqual((await research.lookup('discord.py 최신 버전',False))['status'],'disabled')
        research.cache.clear();research._read.return_value=dict(tag_name='v1',html_url='http://127.0.0.1/secret')
        self.assertEqual((await research.lookup('transformers 최신 버전',True))['status'],'failed')
        self.assertIsNone(await research.lookup('안녕',True))
    async def test_unsafe_endpoint_is_rejected_without_network(self):
        research=PublicResearch()
        with self.assertRaises(ValueError):await research._read(None,'http://169.254.169.254/latest/meta-data')

class DiscordConsent(unittest.IsolatedAsyncioTestCase):
    async def test_self_service_choices_and_stale_delete_selection_are_serialized(self):
        from echomate_bot.consent_ui import ConsentPanel
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            store=CompanionStore(Path(folder)/'private.sqlite3')
            runtime=SimpleNamespace(privacy_changed=lambda *a:None,members=SimpleNamespace(clear=lambda *a,**kw:None))
            panel=ConsentPanel(SimpleNamespace(companion=store,runtime=runtime),2,4,store.consent(2,4),store.data_counts(2,4))
            def interaction():return SimpleNamespace(guild_id=2,user=SimpleNamespace(id=4),response=SimpleNamespace(defer=AsyncMock(),send_message=AsyncMock()),edit_original_response=AsyncMock())
            try:
                with patch.object(runtime,'privacy_changed') as invalidated:
                    await panel.change(interaction(),'relationships');invalidated.assert_not_called()
                self.assertTrue(store.consent(2,4)['relationships']);self.assertFalse(store.consent(2,4)['memory'])
                store.set_consent(2,4,'memory',True);store.add_memory(2,4,3,'나는 퍼즐 게임을 좋아해')
                panel.selected='memory';panel.confirm=True
                await panel.lock.acquire();i=interaction();task=asyncio.create_task(panel.delete.callback(i))
                await asyncio.sleep(.01);panel.selected='relationships';panel.delete_revision+=1;panel.lock.release();await task
                self.assertTrue(store.memories(2,4));self.assertIn('선택이 바뀌었어',i.edit_original_response.call_args.kwargs['content'])
                panel.selected='memory';panel.confirm=True
                await panel.delete.callback(interaction());self.assertFalse(store.memories(2,4));self.assertTrue(store.consent(2,4)['relationships'])
            finally:panel.stop()
    async def test_one_local_command_no_sync_until_owner_approves_and_ephemeral_subject_guard(self):
        from echomate_bot.discord_app import EchoClient
        from echomate_bot.consent_ui import ConsentPanel,open_consent
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            cfg=Settings(1,secrets.token_hex(32),Path(folder)/'settings.json');cfg.set_scope(1,2,3,'mention')
            client=EchoClient(cfg,base.FakeBackend(),[2]);client.tree.sync=AsyncMock();client.tree.fetch_commands=AsyncMock(return_value=[])
            try:
                self.assertEqual([c.name for c in client.tree.get_commands()],['동의'])
                await client.setup_hook();client.tree.sync.assert_not_awaited()
                cfg.set(1,'command_sync_pending',True);await client.setup_hook();self.assertEqual(client.tree.sync.await_count,2);self.assertFalse(cfg.get()['command_sync_pending'])
                response=SimpleNamespace(defer=AsyncMock(),send_message=AsyncMock())
                i=SimpleNamespace(guild_id=2,user=SimpleNamespace(id=4),response=response,followup=SimpleNamespace(send=AsyncMock()))
                await open_consent(client,i);self.assertTrue(i.followup.send.call_args.kwargs['ephemeral'])
                panel=i.followup.send.call_args.kwargs['view'];self.assertIn('Windows PC',panel.notice())
                intruder=SimpleNamespace(guild_id=2,user=SimpleNamespace(id=1),response=response)
                self.assertFalse(await panel.interaction_check(intruder));self.assertFalse(any(client.companion.consent(2,4).values()));panel.stop()
            finally:await client.close()
