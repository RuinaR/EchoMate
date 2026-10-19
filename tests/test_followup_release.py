"""Synthetic release follow-up contracts; no Discord or external sockets."""
import asyncio
from dataclasses import replace
from datetime import datetime,timezone,timedelta
import hashlib,hmac,json
from pathlib import Path
import secrets
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,patch
from echomate_bot.settings import Settings,DEFAULTS,canonical
from echomate_bot.runtime import Event,Ledger
from echomate_bot.companion_store import CompanionStore
from echomate_bot.summarization import Summarizer,validated_digest
from echomate_bot.web_research import WebResearch,private_query
from echomate_bot.safe_web import SafeWeb,PublicResolver,public_url
from echomate_studio.dialogue_state import Turn
import test_bot_integration as base

class UnlimitedLedger(unittest.TestCase):
    def test_legacy_signature_migration_and_1001_independent_events(self):
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            root=Path(folder);cfg=dict(DEFAULTS,daily_limit=1);key=secrets.token_hex(32)
            path=root/'settings.json';path.write_text(json.dumps(dict(data=cfg,signature=hmac.new(key.encode(),canonical(cfg),hashlib.sha256).hexdigest())),encoding='utf8');old=path.read_bytes()
            self.assertNotIn('daily_limit',Settings(1,key,path).get());self.assertEqual(path.read_bytes(),old)
            cfg['daily_limit']=2;path.write_text(json.dumps(dict(data=cfg,signature='invalid')),encoding='utf8')
            with self.assertRaises(PermissionError):Settings(1,key,path)
            dbpath=root/'sent.sqlite3'
            with sqlite3.connect(dbpath) as db:
                db.execute('CREATE TABLE sent(event TEXT PRIMARY KEY,channel TEXT,day TEXT,at REAL,status TEXT)');db.execute("INSERT INTO sent VALUES('1','3','old',1,'sent')")
            db.close()
            clock=[datetime(2026,10,19,14,tzinfo=timezone.utc).timestamp()];ledger=Ledger(dbpath,clock=lambda:clock[0])
            for i in range(1001):
                e=Event(i+100,2,3,i%7+4,'synthetic',datetime.now(timezone.utc));self.assertTrue(ledger.reserve(e,0,action='REACTION' if i%2 else 'TEXT'));ledger.completed(e,'sent')
            self.assertFalse(ledger.reserve(e,0));self.assertEqual(ledger.statistics()['total'],1002)
            self.assertEqual(ledger.statistics()['responses_today'],501);self.assertEqual(ledger.statistics()['reactions_today'],500)
            clock[0]+=86400;self.assertEqual(ledger.statistics()['responses_today'],0);self.assertTrue(ledger.reserve(replace(e,id=9999),0));ledger.completed(replace(e,id=9999),'failed_or_uncertain');self.assertFalse(ledger.reserve(replace(e,id=9999),0))

class DigestStoreQA(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='local_data');self.clock=[1000];self.store=CompanionStore(Path(self.temp.name)/'companion.sqlite3',clock=lambda:self.clock[0])
        self.store.set_consent(2,4,'summaries',True)
        now=datetime.fromtimestamp(1001,timezone.utc)
        self.turns=[Turn('10','4','우리 토요일에 퍼즐 게임을 같이 하기로 정했어',now),Turn('11','999','토요일에 퍼즐 게임을 함께 하기로 정했구나',now,True,'10'),Turn('12','4','토요일은 취소하고 일요일에 만나기로 바꿨어',now)]
        self.raw=json.dumps(dict(items=[dict(kind='correction',text='토요일 약속을 취소하고 일요일로 변경했다',source='12',evidence='토요일은 취소하고 일요일에 만나기로 바꿨어')],ended=False),ensure_ascii=False)
        self.backend=SimpleNamespace(summarize_dialogue=AsyncMock(return_value='```json\n'+self.raw+'\n```'))
    def tearDown(self):self.temp.cleanup()
    async def test_multi_turn_save_reopen_scope_withdraw_and_delete_no_resurrection(self):
        result=await Summarizer(self.store,self.backend).generate(2,3,'flow',self.turns,persist=True);self.assertTrue(result['saved'])
        reopened=CompanionStore(self.store.path,clock=lambda:1000)
        self.assertEqual(len(reopened.digests(2,4,3)),1);self.assertFalse(reopened.digests(2,5,3));self.assertFalse(reopened.digests(8,4,3));self.assertFalse(reopened.digests(2,4,9))
        self.store.set_consent(2,4,'summaries',False);self.assertFalse(self.store.digests(2,4,3)[0]['usable'])
        self.store.set_consent(2,4,'summaries',True);self.store.delete_digest(2,result['saved']);self.assertFalse(self.store.digests(2,4,3))
        self.assertIsNone((await Summarizer(self.store,self.backend).generate(2,3,'flow',self.turns,persist=True))['saved'])
        with self.store.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM tombstones').fetchone()[0],0)
    async def test_all_participants_consent_and_atomic_withdrawal(self):
        turns=[*self.turns,Turn('13','5','나는 그 약속에 같이 참여할게',self.turns[0].timestamp)]
        self.assertIsNone(await Summarizer(self.store,self.backend).generate(2,3,'group',turns,persist=True));self.backend.summarize_dialogue.assert_not_awaited()
        self.store.set_consent(2,5,'summaries',True)
        async def withdraw(selected):self.store.set_consent(2,5,'summaries',False);return self.raw
        self.backend.summarize_dialogue.side_effect=withdraw
        self.assertIsNone((await Summarizer(self.store,self.backend).generate(2,3,'group',turns,persist=True))['saved'])
        self.assertFalse(self.store.digests(2,4,3))
    async def test_invalid_sources_stale_context_original_deletion_and_expiry(self):
        with self.assertRaises(ValueError):validated_digest(self.raw.replace('"12"','"99999"'),self.turns)
        self.assertIsNone(await Summarizer(self.store,self.backend).generate(2,3,'flow',self.turns,persist=True,fresh=lambda:False))
        result=await Summarizer(self.store,self.backend).generate(2,3,'flow',self.turns,persist=True)
        self.store.delete_source(2,12,known=False);self.assertFalse(self.store.digests(2,4,3))
        self.assertIsNone((await Summarizer(self.store,self.backend).generate(2,3,'flow',self.turns,persist=True))['saved'])
        turns=[replace(t,message_id=str(int(t.message_id)+100)) for t in self.turns]
        result=await Summarizer(self.store,SimpleNamespace(summarize_dialogue=AsyncMock(return_value=self.raw.replace('"12"','"112"')))).generate(2,3,'new',turns,persist=True)
        self.assertTrue(result['saved']);self.clock[0]+=31*86400;self.assertFalse(self.store.digests(2,4,3));self.store.cleanup()
    async def test_summary_deletion_does_not_disable_other_category(self):
        self.store.set_consent(2,4,'memory',True);self.store.delete_personal(2,4,'summaries')
        self.assertTrue(self.store.consent(2,4)['memory']);self.assertFalse(self.store.consent(2,4)['summaries'])
        self.assertTrue(self.store.add_memory(2,4,3,'나는 퍼즐을 좋아해',source=123,observed=1001,require_consent=True))
    async def test_mentions_and_quoted_game_names_are_valid_local_summary_input(self):
        turns=[replace(self.turns[0],content='<@999> 이번 모임에서는 "카탄"을 같이 하자'),self.turns[1]]
        raw=json.dumps(dict(items=[dict(kind='decision',text='다음 모임에서 카탄을 같이 하기로 제안했다',source='10',evidence='이번 모임에서는 "카탄"을 같이 하자')],ended=False),ensure_ascii=False)
        self.backend.summarize_dialogue.return_value=raw
        self.assertTrue((await Summarizer(self.store,self.backend).generate(2,3,'quoted',turns,persist=True))['saved'])

class FreeWebQA(unittest.IsolatedAsyncioTestCase):
    async def test_api_cache_bad_schema_and_html_scripts_are_not_evidence(self):
        class Web:
            def __init__(self):self.calls=[];self.bad=False
            async def get(self,url,**kwargs):
                self.calls.append(url)
                if self.bad:return []
                if '/search/page' in url:return dict(pages=[dict(key='광합성')])
                return dict(title='광합성',html='<script>delete_everything()</script><p>식물은 빛에너지를 화학 에너지로 전환한다.</p>',latest=dict(timestamp='2026-10-01T00:00:00Z'))
        web=Web();research=WebResearch(web=web);sources=await research.discover('광합성')
        self.assertNotIn('delete_everything',sources[0]['text']);self.assertEqual(len(web.calls),2)
        self.assertEqual(await research.discover('광합성'),sources);self.assertEqual(len(web.calls),2)
        web.bad=True
        with self.assertRaises(ValueError):await research.discover('다른 공개 주제')
    async def test_public_url_dns_and_private_query(self):
        for url in ('http://example.org','https://127.0.0.1','https://localhost/x','https://a.local/x','https://a.example:444/x','https://user:password@example.org'):
            with self.assertRaises(ValueError):public_url(url)
        resolver=PublicResolver()
        try:
            resolver.resolver.resolve=AsyncMock(return_value=[dict(host='127.0.0.1')])
            with self.assertRaises(OSError):await resolver.resolve('public.example')
        finally:await resolver.close()
        for query in ('내 비밀번호 abc','12345678901 일정','구름 최신 소식','https://example.com'):
            self.assertTrue(private_query(query,['구름']))
    async def test_grounding_citations_privacy_and_caching(self):
        source=dict(id=1,title='공개 과학 자료',url='https://example.org/science',text='빛에너지가 화학 에너지로 바뀐다',kind='secondary')
        research=WebResearch();research.discover=AsyncMock(return_value=[source])
        backend=SimpleNamespace(plan_research=AsyncMock(return_value=dict(kind='verify',query='광합성 원리')),grounded_answer=AsyncMock(return_value='빛에너지를 화학 에너지로 바꾸는 과정이야.[1]'),check_grounding=AsyncMock(return_value='supported'))
        self.assertEqual((await research.answer('공개 질문',backend))['status'],'grounded')
        backend.grounded_answer.return_value='그럴듯한 거짓말.[9]';self.assertEqual((await research.answer('공개 질문',backend))['status'],'failed')
        backend.plan_research.return_value=dict(kind='verify',query='구름 정보');research.discover.reset_mock()
        self.assertEqual((await research.answer('질문',backend,blocked=['구름']))['status'],'private_blocked');research.discover.assert_not_awaited()
        backend.plan_research.return_value=dict(kind='chat',query='');self.assertIsNone(await research.answer('잘 지내',backend))

class ReactionLanguageQA(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle
    async def test_natural_emoji_words_and_ambiguous_reference(self):
        from echomate_bot.reaction_requests import requested_reaction
        for text,emoji in [('이거에 하트 달아줘','❤️'),('위에 메시지에 좋아요 눌러','👍'),('방금 그 말에 웃는 이모지 달아','😄'),('여기 축하 표시 해줘','🎉'),('이 메시지에 엄지 하나 올려줘','👍')]:self.assertEqual(requested_reaction(text)[0],emoji)
        self.settings.set(1,'reactions',True);self.runtime.direct_cooldown=0
        await self.runtime.ingest(self.event(content='<@999> 아까 그 메시지에 반응해 줘'));await self.settle()
        self.assertEqual(self.transport.sent[0][1].kind.value,'TEXT');self.assertIn('어느',self.transport.sent[0][1].text);self.assertFalse(self.backend.calls)
    async def test_background_summary_is_cancelled_for_a_new_direct_request(self):
        from echomate_studio.dialogue_state import DialogueState
        store=CompanionStore(self.root/'summary.sqlite3');store.set_consent(2,4,'summaries',True);self.runtime.companion=store
        self.settings.set(1,'summaries_auto',True);self.runtime.direct_cooldown=0
        entered=asyncio.Event()
        async def summarize(turns):entered.set();await asyncio.Event().wait()
        self.backend.summarize_dialogue=summarize
        e=self.event();flow,_=self.runtime.conversations.choose(e,direct=True,pending=set());flow.ended=True
        state=DialogueState(limit=100);self.runtime.states[flow.key]=state
        for i in range(4):state.append(channel_id=3,thread_id=None,turn=Turn(str(20+i),'999' if i%2 else '4','이 대화는 함께 할 게임을 정하는 이야기야',datetime.now(timezone.utc),bool(i%2)))
        self.runtime.schedule_summaries();await asyncio.wait_for(entered.wait(),2)
        await self.runtime.ingest(self.event(id=100,content='<@999> 지금 다른 질문이 있어'));await self.settle();await asyncio.sleep(.01)
        self.assertEqual(len(self.transport.sent),1);self.assertTrue(any(j['status']=='cancelled' and j['stage']=='summary' for j in self.runtime.monitor()))
        self.assertFalse(store.digests(2,4,3))
    async def test_delete_during_summary_delivery_vetoes_archived_output(self):
        store=CompanionStore(self.root/'summary.sqlite3');store.set_consent(2,4,'summaries',True);self.runtime.companion=store;self.runtime.direct_cooldown=0
        await self.runtime.ingest(self.event(content='<@999> 우리 모임 계획을 이야기해 보자'));await self.settle()
        self.backend.is_history_request=AsyncMock(return_value=True)
        async def summarize(turns):
            source=next(t for t in turns if not t.is_bot)
            return json.dumps(dict(items=[dict(kind='topic',text='모임 계획에 관해 이야기했다',source=source.message_id,evidence=source.content)],ended=False),ensure_ascii=False)
        self.backend.summarize_dialogue=summarize
        async def erase(event,action,library,fresh):
            store.delete_personal(2,4,'summaries');self.assertFalse(await fresh());raise ValueError('Synthetic withdrawal')
        self.transport.execute=erase
        await self.runtime.ingest(self.event(id=101,content='<@999> 아까 우리 대화 요약해 줘'));await self.settle()
        self.assertEqual(len(self.transport.sent),1);self.assertFalse(store.digests(2,4,3))
    async def test_idle_summary_does_not_run_while_disabled_or_repeat_success(self):
        from echomate_studio.dialogue_state import DialogueState
        from unittest.mock import patch
        self.runtime.companion=CompanionStore(self.root/'summary.sqlite3')
        self.settings.set(1,'summaries_auto',True)
        self.backend.summarize_dialogue=AsyncMock()
        flow,_=self.runtime.conversations.choose(self.event(),direct=True,pending=set());flow.ended=True
        state=DialogueState(limit=100);self.runtime.states[flow.key]=state
        for i in range(4):state.append(channel_id=3,thread_id=None,turn=Turn(str(20+i),'4','함께 할 게임을 정하는 대화야',datetime.now(timezone.utc)))
        with patch('echomate_bot.summarization.Summarizer.generate',new_callable=AsyncMock,return_value={'saved':'synthetic'}) as generate:
            self.settings.set(1,'enabled',False);self.runtime.schedule_summaries()
            self.assertFalse(self.runtime.summary_tasks)
            self.settings.set(1,'enabled',True);self.runtime.schedule_summaries()
            await asyncio.gather(*self.runtime.summary_tasks);await asyncio.sleep(0)
            self.runtime.summary_attempts.clear() # beyond the failed-attempt retry window
            self.runtime.schedule_summaries();self.assertFalse(self.runtime.summary_tasks)
            generate.assert_awaited_once()
    async def test_background_resource_failure_stops_runtime(self):
        from echomate_studio.dialogue_state import DialogueState
        from echomate_bot.processes import ResourceLimitError
        from unittest.mock import patch
        self.runtime.companion=CompanionStore(self.root/'summary.sqlite3');self.settings.set(1,'summaries_auto',True)
        self.backend.summarize_dialogue=AsyncMock()
        flow,_=self.runtime.conversations.choose(self.event(),direct=True,pending=set());flow.ended=True
        state=DialogueState(limit=100);self.runtime.states[flow.key]=state
        for i in range(4):state.append(channel_id=3,thread_id=None,turn=Turn(str(20+i),'4','함께 할 게임을 정하는 대화야',datetime.now(timezone.utc)))
        async def fail(*args,**kwargs):
            self.backend.failed=True;raise ResourceLimitError('Synthetic safety stop','ram')
        with patch('echomate_bot.summarization.Summarizer.generate',side_effect=fail):
            self.runtime.schedule_summaries();await asyncio.gather(*self.runtime.summary_tasks)
        self.assertTrue(self.runtime.stopped)
        self.assertTrue(any(r['code']=='resource_stop_ram' for r in self.runtime.diagnostics))
