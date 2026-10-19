from echomate_bot.character_profiles import DEFAULT_PROFILE
"""Synthetic guild identities; no external Discord access."""
import asyncio
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock
from types import SimpleNamespace
import queue
import secrets
from echomate_bot.members import MemberDirectory,corroboration,one_edit
from echomate_bot.runtime import Event
from echomate_bot.companion_store import CompanionStore
from echomate_bot.dialogue_intent import DialogueIntent
import test_bot_integration as base

def event(text,**kw):
    return Event(100,2,3,4,text,datetime.now(timezone.utc),**kw)

class MemberRecognition(unittest.TestCase):
    def setUp(self):
        self.directory=MemberDirectory()
        for uid,name in ((5,'가온mk2'),(6,'노을beta'),(7,'김도윤')):self.directory.observe(2,3,uid,(name,))
    def resolve(self,text,**kw):return self.directory.resolve(event(text,**kw),999)
    def test_exact_short_vocative_and_family_name_omission(self):
        for text,uid in (('가온mk2야',5),('가온아',5),('노을아 뭐해',6),('도윤아',7),('김도윤아',7)):
            with self.subTest(text=text):self.assertEqual(self.resolve(text).addressee,uid)
        for text in ('가온','가온이','도윤이'):
            roles=self.resolve(text);self.assertTrue(roles.candidates);self.assertIsNone(roles.addressee)
    def test_third_person_quotes_code_and_urls_do_not_address(self):
        for text in ('가온이는 잘해','가온이 오늘 왔어','"가온아"라고 불렀어','`노을아`','https://example.org/노을아'):
            self.assertIsNone(self.resolve(text).addressee,text)
    def test_homonyms_and_multiple_targets_abstain(self):
        self.directory.observe(2,3,8,('가온beta',))
        roles=self.resolve('가온아');self.assertIsNone(roles.addressee);self.assertTrue(roles.ambiguous)
        roles=self.resolve('가온아 <@5>',member_mentions=(5,));self.assertEqual(roles.addressee,5)
        self.assertIsNone(self.resolve('둘 다 와',member_mentions=(5,6)).addressee)
    def test_common_noun_and_typo_are_candidates_only(self):
        self.directory.observe(2,3,8,('바람',));self.assertIsNone(self.resolve('바람').addressee)
        self.directory.observe(2,3,9,('하늘소리',))
        r=self.resolve('하늘소라야');self.assertIsNone(r.addressee);self.assertTrue(any(c.evidence=='typo' for c in r.candidates))
        self.assertFalse(one_edit('가온','노을'));self.assertTrue(one_edit('abcd','abdc'))

    def test_known_vocative_without_space_and_second_person_are_not_third_person(self):
        for text in ('노을아너한테물어본거야','도윤아뭐라고생각해','가온 너는 어떻게 봐','노을beta 네가 말해 줘'):
            self.assertIsNotNone(self.resolve(text).addressee,text)
        for text in ('노을이는 그게 좋대','아까 노을아 뭐냐고 물었어','가온 너는 어떠냐고 말했어','"도윤아너한테물어본거야"'):
            self.assertIsNone(self.resolve(text).addressee,text)
    def test_speaker_audience_subject_and_actual_reply_are_separate(self):
        r=self.resolve('노을이는 어때',member_mentions=(5,),reply_to=80,reply_author=6)
        self.assertEqual((r.speaker,r.addressee,r.mentioned_people,r.reply_target,r.reply_author),(4,6,(5,),80,6))
        self.assertIsNone(self.resolve('그런데 <@5>가 설명한 뜻은 뭐야',member_mentions=(5,)).addressee)
        self.assertEqual(self.resolve('그 말 다시 설명해',reply_to=80,reply_author=6).addressee,6)
        self.assertFalse(r.facts()['identity_actions_allowed'])
    def test_guild_channel_isolation_nickname_refresh_and_expiry(self):
        self.assertFalse(self.directory.resolve(replace(event('노을아'),channel=8),999).candidates)
        self.assertFalse(self.directory.resolve(replace(event('노을아'),guild=9),999).candidates)
        self.directory.observe(2,3,6,('새별',));self.assertFalse(self.resolve('노을아').candidates)
        self.assertEqual(self.resolve('새별아').addressee,6)
        self.directory.clear(2,user=6);self.assertFalse(self.resolve('새별아').candidates)
        d=MemberDirectory(clock=lambda:0,limit=2)
        for uid in range(4):d.observe(2,3,uid,('구름',))
        self.assertEqual(len(d.people),2);d.clock=lambda:86401;d.prune();self.assertFalse(d.people)
    def test_evidence_requires_actual_anchor_and_quotes_do_not_learn(self):
        for text in ('노을아','"노을아"라고 불렀어','노을이는 잘해'):
            e=event(text,member_mentions=(6,) if '라고' in text else ())
            self.assertIsNone(corroboration(e,self.directory.resolve(e,999)))
        for e,expected in ((event('반짝아 <@6>',member_mentions=(6,)),(6,'반짝','mention')),
                           (event('반짝아 뭐해',reply_to=80,reply_author=6),(6,'반짝','reply')),
                           (event('나를 반짝이라고 불러줘'),(4,'반짝','self-report'))):
            self.assertEqual(corroboration(e,self.directory.resolve(e,999)),expected)
    def test_learned_candidates_do_not_auto_confirm_and_approved_collision_abstains(self):
        aliases=[dict(user='6',alias='반짝',status='candidate',confidence=.89)]
        r=self.directory.resolve(event('반짝아'),999,aliases);self.assertIsNone(r.addressee)
        aliases[0]['status']='confirmed';self.assertEqual(self.directory.resolve(event('반짝아'),999,aliases).addressee,6)
        aliases.append(dict(user='5',alias='반짝',status='confirmed',confidence=1))
        r=self.directory.resolve(event('반짝아'),999,aliases);self.assertIsNone(r.addressee);self.assertTrue(r.ambiguous)
        aliases=[dict(user='5',alias='가온',status='candidate',confidence=.5)]
        self.assertEqual(self.directory.resolve(event('가온아'),999,aliases).addressee,5)
    def test_bot_human_homonym_never_assigns_a_human_arbitrarily(self):
        r=self.directory.resolve(event('가온아'),999,bot_names=('가온봇',))
        self.assertIsNone(r.addressee);self.assertTrue(r.ambiguous)

class AliasStore(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='local_data');self.path=Path(self.temp.name)/'companion.sqlite3';self.store=CompanionStore(self.path)
        for uid in (4,5,6):self.store.resume_subject(2,uid)
    def tearDown(self):self.temp.cleanup()
    def test_progressive_evidence_deduplicates_and_owner_can_confirm_remove(self):
        self.store.observe_alias(2,3,5,'반짝',10,4,'mention');first=self.store.aliases(2,3)[0]
        self.store.observe_alias(2,3,5,'반짝',10,4,'mention');self.assertEqual(self.store.aliases(2,3)[0]['observations'],1)
        self.store.observe_alias(2,3,5,'반짝',11,6,'reply');row=self.store.aliases(2,3)[0]
        self.assertGreater(row['confidence'],first['confidence']);self.assertEqual(row['status'],'candidate');self.assertEqual(row['witnesses'],2)
        self.store.set_alias(2,3,5,'반짝');self.assertEqual(self.store.aliases(2,3)[0]['confidence'],1)
        self.store.set_alias(2,3,5,'반짝','deleted');self.store.observe_alias(2,3,5,'반짝',12,4,'mention')
        self.assertEqual(self.store.aliases(2,3)[0]['status'],'deleted')
    def test_scope_forget_restart_migration_and_existing_memory_preserved(self):
        key=self.store.add_memory(2,4,3,'나는 퍼즐을 좋아해')
        with self.store.db() as db:
            db.execute('DROP TABLE alias_evidence');db.execute('DROP TABLE member_aliases');db.execute('PRAGMA user_version=3')
        self.store=CompanionStore(self.path);self.assertIsNone(self.store.error);self.assertEqual(self.store.memories(2,4)[0]['memory_id'],key);self.assertFalse(self.store.aliases(2,3))
        self.store.set_alias(2,3,5,'반짝');self.assertFalse(self.store.aliases(2,8));self.assertFalse(self.store.aliases(9,3))
        self.store=CompanionStore(self.path);self.assertEqual(len(self.store.aliases(2,3)),1)
        self.store.forget(2,5);self.assertFalse(self.store.aliases(2));self.store.observe_alias(2,3,5,'반짝',13,4,'reply');self.assertFalse(self.store.aliases(2))
    def test_stale_candidates_expire_confirmed_kept_and_ids_not_memory_keys(self):
        self.store.clock=lambda:100;self.store.observe_alias(2,3,5,'반짝',10,4,'mention');self.store.set_alias(2,3,6,'구름')
        self.store.clock=lambda:100+91*86400;self.assertEqual([r['user'] for r in self.store.aliases(2)],['6'])
        self.assertEqual(self.store.users(2),[]);self.assertEqual(self.store.memories(2),[]);self.assertEqual(self.store.reminders(2),[])
    def test_forget_erases_witness_evidence_and_owner_approval_is_reversible(self):
        self.store.observe_alias(2,3,5,'반짝',10,4,'mention');self.store.forget(2,4)
        self.assertEqual(self.store.aliases(2,3)[0]['observations'],0)
        self.store.set_alias(2,3,5,'반짝','deleted');self.store.set_alias(2,3,5,'반짝','confirmed')
        self.assertEqual(self.store.aliases(2,3)[0]['status'],'confirmed')
    def test_deleted_or_edited_source_revokes_only_its_alias_evidence(self):
        self.store.observe_alias(2,3,5,'반짝',10,4,'mention');self.store.observe_alias(2,3,5,'반짝',11,6,'reply')
        self.store.delete_source(2,10,known=False)
        self.assertEqual(self.store.aliases(2,3)[0]['observations'],1)

class MemberRuntime(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle
    def configure(self):
        self.runtime.direct_cooldown=0;self.backend.fast_text_path=True
        self.settings.change(1,lambda c:c['guilds']['2'].update(name='다온봇'))
        self.backend.assess_dialogue=AsyncMock(return_value=DialogueIntent('reaction','bot','continue',True))
        self.runtime.members.observe(2,3,5,('가온mk2',))
    async def test_other_human_call_does_not_reach_gpu_all_profiles_but_bot_call_survives(self):
        self.configure()
        for i,energy in enumerate((15,50,85)):
            mode='base'
            self.settings.set(1,'character_profile',dict(DEFAULT_PROFILE,energy=energy))
            self.settings.set(1,'model',mode)
            await self.runtime.ingest(self.event(id=20+3*i,content='다온아 이야기 해줘'));await self.settle()
            await self.runtime.ingest(self.event(id=21+3*i,content='가온아 이거 어때'));await self.settle()
            self.assertEqual(self.runtime.activity_changed(),0)
            await self.runtime.ingest(self.event(id=22+3*i,content='다온아 가온이는 어떤 뜻이야'));await self.settle()
        self.assertEqual(len(self.transport.sent),6);self.backend.assess_dialogue.assert_not_awaited()
        self.assertEqual(sum(r['code']=='member_other_addressee' for r in self.runtime.diagnostics),3)
    async def test_reply_to_human_separates_roles_and_group_topic_remains_semantic(self):
        self.configure();await self.runtime.ingest(self.event(content='다온아'));await self.settle()
        await self.runtime.ingest(replace(self.event(id=20,content='그거 어떻게해'),reply_to=80,reply_author=5));await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        await self.runtime.ingest(self.event(id=21,content='가온이도 네 이야기가 좋대'));await self.settle()
        facts=self.backend.assess_dialogue.call_args.kwargs['facts']['member_roles']
        self.assertEqual(facts['speaker'],'4');self.assertIsNone(facts['addressee']);self.assertEqual(len(self.transport.sent),2)
    async def test_confirmed_alias_does_not_read_other_subject_memory(self):
        self.configure();store=CompanionStore(Path(self.temp.name)/'members.sqlite3');self.runtime.companion=store
        store.set_consent(2,5,'relationships',True);store.set_alias(2,3,5,'반짝');store.add_memory(2,5,3,'나는 체스를 좋아해')
        await self.runtime.ingest(self.event(content='다온아 반짝의 기억 알려줘'));await self.settle()
        self.assertTrue(self.backend.calls);self.assertFalse(any('체스' in str(c) for c in self.backend.calls))
    async def test_progressive_learning_requires_subject_consent_and_never_changes_affinity(self):
        self.configure();store=CompanionStore(self.root/'members.sqlite3');self.runtime.companion=store
        e=replace(self.event(content='반짝아 <@5>'),member_mentions=(5,))
        await self.runtime.ingest(e);await self.settle();self.assertFalse(store.aliases(2))
        store.resume_subject(2,5)
        await self.runtime.ingest(replace(e,id=20,timestamp=datetime.now(timezone.utc)));await self.settle()
        self.assertEqual(store.aliases(2)[0]['status'],'candidate');self.assertEqual(store.users(2),[])
    async def test_ambiguous_people_are_given_to_semantics_without_selecting_identity(self):
        self.configure();self.runtime.members.observe(2,3,6,('가온beta',))
        await self.runtime.ingest(self.event(content='다온아'));await self.settle()
        self.backend.assess_dialogue.return_value=DialogueIntent('question','uncertain','new',False)
        await self.runtime.ingest(self.event(id=21,content='가온아 그건 어때'));await self.settle()
        facts=self.backend.assess_dialogue.call_args.kwargs['facts']['member_roles']
        self.assertTrue(facts['ambiguous']);self.assertIsNone(facts['addressee']);self.assertEqual(len(self.transport.sent),1)
    async def test_owner_human_alias_colliding_with_bot_is_not_a_guaranteed_invitation(self):
        self.configure();store=CompanionStore(self.root/'members.sqlite3');self.runtime.companion=store
        store.set_consent(2,5,'relationships',True);store.set_alias(2,3,5,'다온')
        self.backend.assess_dialogue.return_value=DialogueIntent('other','uncertain','new',False)
        await self.runtime.ingest(self.event(content='다온아'));await self.settle()
        self.assertFalse(self.transport.sent);self.backend.assess_dialogue.assert_awaited_once()
        await self.runtime.ingest(self.event(id=21,content='<@999> 다온아'));await self.settle()
        self.assertEqual(len(self.transport.sent),1)
    async def test_restart_looks_up_only_matching_approved_subject_and_caches_failures(self):
        self.configure();store=CompanionStore(self.root/'members.sqlite3');self.runtime.companion=store
        store.set_consent(2,8,'relationships',True);store.set_consent(2,9,'relationships',True)
        store.set_alias(2,3,8,'별빛');store.set_alias(2,3,9,'미확인','candidate')
        self.transport.member_lookup=AsyncMock(return_value=[(8,('새별mk2',))])
        for i in range(2):
            await self.runtime.ingest(self.event(id=30+i,content='별빛아 이거 봐'));await self.settle()
        self.transport.member_lookup.assert_awaited_once();self.assertEqual(self.transport.member_lookup.call_args.args[1],[8]);self.assertFalse(self.transport.sent)
        self.runtime.members.clear(2,user=8);self.transport.member_lookup.reset_mock();self.transport.member_lookup.return_value=[]
        for i in range(2):
            await self.runtime.ingest(self.event(id=40+i,content='별빛아'));await self.settle()
        self.transport.member_lookup.assert_awaited_once()
        await self.runtime.ingest(self.event(id=45,content='미확인아'));await self.settle()
        self.transport.member_lookup.assert_awaited_once()

class AliasOwnerControls(unittest.IsolatedAsyncioTestCase):
    async def test_controller_authorizes_owner_and_checks_alias_channel(self):
        from echomate_bot.desktop import LocalController
        from echomate_bot.settings import Settings
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            c=LocalController.__new__(LocalController);c.settings=Settings(1,secrets.token_hex(32),Path(folder)/'settings.json');c.settings.set_scope(1,2,3,'mention')
            c.bootstrap=dict(owner_id=1,admin_guilds=[2]);c.client=None;c.job=None;c.phase='test';c.error='';c.updates=queue.Queue(maxsize=8)
            c.companion=CompanionStore(Path(folder)/'members.sqlite3');c.companion.set_consent(2,5,'relationships',True)
            await c.command('companion',action='member_alias',guild=2,user='5',channel='3',alias='반짝',status='confirmed')
            self.assertFalse(c.error);self.assertEqual(c.companion.aliases(2,3)[0]['status'],'confirmed')
            await c.command('companion',action='member_alias',guild=2,user='5',channel='8',alias='새별',status='confirmed')
            self.assertEqual(c.error,'설정값이나 설치 파일을 확인해 주세요');self.assertEqual(len(c.companion.aliases(2)),1)
            c.bootstrap['owner_id']=9
            await c.command('companion',action='member_alias',guild=2,user='5',channel='3',alias='반짝',status='deleted')
            self.assertEqual(c.error,'PermissionError');self.assertEqual(c.companion.aliases(2,3)[0]['status'],'confirmed')
