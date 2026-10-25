"""Scoped Runtime transitions with synthetic backends and no external HTTP."""
import asyncio
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_bot_integration as base
from echomate_bot.character_store import CharacterStores
from echomate_bot.character_models import character
from dataclasses import replace as copied


class Backend(base.FakeBackend):
    def __init__(self,character_id='lime'):
        super().__init__();self.character_id=character_id;self.name='유나';self.model=True
        self.closed=False;self.clean=True;self.load_failed=False;self.name_failed=False;self.loaded=False
        self.entry=copied(character('lime'),character_id=character_id,default_name='합성 캐릭터',base_dependency='synthetic base')
    async def ready(self):
        if self.load_failed:raise RuntimeError('synthetic load failure')
        self.loaded=True
    async def probe(self):pass
    async def probe_identity(self):
        if self.name_failed:raise RuntimeError('synthetic name failure')
    async def admission(self,entry):return True
    async def validate(self,entry):return True
    async def load(self,entry):await self.ready()
    async def generate(self,messages):return '합성 답변'
    async def cancel(self):pass
    async def unload(self):await self.close()
    async def health_check(self,entry,name):
        await self.probe_identity();await self.probe();self.name=name;return True
    async def close(self):self.closed=True;self.model=None
    async def reclaimed(self):return self.closed and self.clean
    async def rename(self,name):
        if self.name_failed:raise RuntimeError('synthetic name failure')
        self.name=name


class Transitions(unittest.IsolatedAsyncioTestCase):
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle
    async def asyncTearDown(self):
        self.old.clean=True
        self.runtime.backend.clean=True
        await base.BotIntegration.asyncTearDown(self)
    def setUp(self):
        base.BotIntegration.setUp(self)
        self.hub=CharacterStores.create(self.root/'characters.sqlite3')
        self.store=self.runtime.companion=self.hub.for_character('lime')
        self.old=self.backend=self.runtime.backend=Backend()
        self.runtime.direct_cooldown=0

    async def test_switch_closes_old_model_before_new_and_preserves_stored_memory(self):
        self.store.add_memory(2,4,3,'나는 퍼즐을 좋아한다')
        candidate=Backend('yaho');target=self.hub.for_character('yaho')
        ready=candidate.ready
        async def checked():
            self.assertTrue(self.old.closed)
            await ready()
        candidate.ready=checked
        await self.runtime.switch_character(1,candidate,target)
        self.assertIs(self.runtime.backend,candidate);self.assertIs(self.runtime.companion,target)
        self.assertEqual(self.runtime.character_transition_state,'Ready')
        self.assertTrue(self.store.memories(2,4));self.assertFalse(target.memories(2,4))

    async def test_inflight_and_fragmented_old_events_do_not_replay(self):
        self.old.wait=asyncio.Event()
        await self.runtime.ingest(self.event(content='<@999> 안녕'))
        for _ in range(200):
            if self.old.calls:break
            await asyncio.sleep(.01)
        self.assertTrue(self.old.calls)
        stale=replace(self.event(id=21),character_epoch=self.runtime.model_generation_epoch)
        await self.runtime.switch_character(1,Backend('yaho'),self.hub.for_character('yaho'))
        self.assertFalse(self.transport.sent)
        await self.runtime.ingest(stale)
        self.assertFalse(self.runtime.tasks)
        await self.runtime.ingest(self.event(id=22))
        await self.settle()
        self.assertEqual([e.id for e,a in self.transport.sent],[22])

    async def test_pending_fragments_are_cleared_on_rename(self):
        await self.runtime.ingest(self.event(content='<@999>'))
        self.assertTrue(self.runtime.utterances.pending)
        before=self.runtime.model_generation_epoch
        await self.runtime.rename_character(1,'하루')
        self.assertEqual(self.old.name,'하루')
        self.assertGreater(self.runtime.model_generation_epoch,before)
        self.assertFalse(self.runtime.utterances.pending)
        self.assertFalse(self.transport.sent)

    async def test_failed_unload_does_not_load_candidate_or_resume(self):
        self.old.clean=False;candidate=Backend('yaho')
        with self.assertRaises(RuntimeError):await self.runtime.switch_character(1,candidate,self.hub.for_character('yaho'))
        self.assertFalse(candidate.loaded)
        self.assertTrue(self.runtime.changing_model)
        self.assertEqual(self.runtime.character_transition_state,'RecoveryRequired')

    async def test_failed_name_probe_does_not_claim_previous_model_restored(self):
        candidate=Backend('yaho');candidate.name_failed=True
        with self.assertRaises(RuntimeError):await self.runtime.switch_character(1,candidate,self.hub.for_character('yaho'))
        self.assertTrue(self.old.closed)
        self.assertIs(self.runtime.backend,candidate)
        self.assertTrue(self.runtime.changing_model)
        await self.runtime.ingest(self.event())
        self.assertFalse(self.transport.sent)

    async def test_owner_and_namespace_mismatch_rejected_before_disruption(self):
        with self.assertRaises(PermissionError):await self.runtime.rename_character(4,'다른 이름')
        with self.assertRaises(ValueError):await self.runtime.switch_character(1,Backend('yaho'),self.store)
        self.assertFalse(self.old.closed)
        self.assertEqual(self.runtime.model_generation_epoch,0)

    async def test_failed_memory_read_never_reports_empty_or_uses_generator(self):
        with patch.object(self.store,'memories',side_effect=RuntimeError('synthetic failure')):
            await self.runtime.ingest(self.event(content='<@999> 내 기억 목록 보여줘'))
            await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        text=self.transport.sent[0][1].text
        self.assertIn('조회에 실패',text);self.assertIn('없다는 뜻은 아니야',text)
        self.assertFalse(self.old.calls)

    async def test_automatic_lookup_failure_cannot_fall_through_to_free_generation(self):
        self.store.set_consent(2,4,'memory',True)
        with patch.object(self.store,'memories',side_effect=RuntimeError('unavailable')):
            await self.runtime.ingest(self.event(content='<@999> 전에 내가 좋아한다고 한 취미가 뭐였지?'))
            await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        self.assertIn('조회에 실패',self.transport.sent[0][1].text)
        self.assertIn('없다는 뜻은 아니야',self.transport.sent[0][1].text)
        self.assertFalse(self.old.calls)

    async def test_no_consent_skips_automatic_lookup_and_never_claims_empty(self):
        seen=[]
        async def text(context,cfg):
            seen.append(cfg['_memory_lookup_state']);return '안녕.'
        self.old.text=text
        with patch.object(self.store,'memories',side_effect=AssertionError('Unconsented read')):
            await self.runtime.ingest(self.event());await self.settle()
        self.assertEqual(seen,['not_authorized'])
        self.assertEqual(len(self.transport.sent),1)

    async def test_successful_empty_and_found_lookup_are_distinct_generation_states(self):
        self.store.set_consent(2,4,'memory',True)
        seen=[]
        async def text(context,cfg):
            seen.append(cfg['_memory_lookup_state']);return '확인했어.'
        self.old.text=text
        await self.runtime.ingest(self.event(content='<@999> 내 취향을 참고해 줄래?'));await self.settle()
        self.store.add_memory(2,4,3,'나는 퍼즐 게임을 좋아한다')
        await self.runtime.ingest(self.event(id=24,content='<@999> 퍼즐 게임에 대해 이야기해 줘'));await self.settle()
        self.assertEqual(seen,['empty','found'])

    async def test_consent_granted_after_initial_check_does_not_turn_skipped_read_into_empty(self):
        seen=[];original=self.store.consent_version
        def grant_then_version(*args):
            self.store.set_consent(2,4,'memory',True)
            return original(*args)
        async def text(context,cfg):
            seen.append(cfg['_memory_lookup_state']);return '지금은 조회하지 않았어.'
        self.old.text=text
        with patch.object(self.store,'consent_version',side_effect=grant_then_version),patch.object(self.store,'memories',side_effect=AssertionError('Skipped read')):
            await self.runtime.ingest(self.event());await self.settle()
        # The existing subject epoch guard cancels before generation when the
        # actual consent changes; skipped queries still must not be executed.
        self.assertEqual(seen,[])
        self.assertFalse(self.transport.sent)

    async def test_access_recovers_after_initial_denial_skipped_read_is_not_empty(self):
        self.store.set_consent(2,4,'memory',True)
        original=self.runtime.automatic_subject_allowed;checks=0;seen=[]
        async def allowed(guild,user,category='relationships'):
            nonlocal checks
            if category=='memory':
                checks+=1
                if checks==1:return False
            return await original(guild,user,category)
        async def text(context,cfg):
            seen.append(cfg['_memory_lookup_state']);return '이번에는 조회하지 않았어.'
        self.old.text=text
        with patch.object(self.runtime,'automatic_subject_allowed',side_effect=allowed),patch.object(self.store,'memories',side_effect=AssertionError('Skipped read')):
            await self.runtime.ingest(self.event());await self.settle()
        self.assertEqual(seen,['not_requested'])

    async def test_cancel_ignoring_generation_cannot_hang_switch_or_load_next(self):
        entered=asyncio.Event();release=asyncio.Event()
        async def stubborn(context,cfg):
            entered.set()
            try:await release.wait()
            except asyncio.CancelledError:await release.wait()
            return '오래된 합성 답변'
        self.old.text=stubborn
        self.runtime.character_quiesce_timeout=.05
        await self.runtime.ingest(self.event())
        await asyncio.wait_for(entered.wait(),2)
        candidate=Backend('yaho')
        try:
            with self.assertRaises(TimeoutError):
                await self.runtime.switch_character(1,candidate,self.hub.for_character('yaho'))
            self.assertFalse(candidate.loaded);self.assertFalse(self.old.closed)
            self.assertTrue(self.runtime.character_draining)
            self.assertEqual(self.runtime.character_transition_state,'RecoveryRequired')
        finally:
            release.set();await self.settle()
        self.assertFalse(self.transport.sent)
