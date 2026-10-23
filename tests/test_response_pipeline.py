import asyncio
from copy import deepcopy
import json
import unittest
from unittest.mock import AsyncMock
import sqlite3
from echomate_bot.response_pipeline import parse_plan,TwoStage,planning_character
from echomate_bot.companion_store import CompanionStore
import test_bot_integration as base


def plan(**kw):
    p=dict(version=1,intent='recall',topic='색',evidence_requests=[dict(kind='memory',query='좋아하는')],strategy='clarify',uncertain_claims=['user_preference'])
    return dict(p,**kw)


class PlanContract(unittest.TestCase):
    def test_planner_reuses_applied_behavior_and_marks_card_excerpts(self):
        from echomate_bot.character_profiles import presets
        p=presets()['analytical'];p['card']['background']='가'*200
        value=planning_character(p)
        self.assertEqual(value['core']['warmth'],p['warmth'])
        self.assertIn('공감은 짧게',value['response_behavior'])
        self.assertFalse(value['fictional_excerpts']['background']['complete'])
        self.assertEqual(len(value['fictional_excerpts']['background']['excerpt']),160)

    def test_schema_rejects_authority_and_unbounded_or_duplicate_reads(self):
        self.assertEqual(parse_plan(json.dumps(plan())),plan())
        invalid=[plan(version=True),plan(user_id='5'),plan(strategy='reply_to_all'),plan(evidence_requests=[dict(kind='memory',query='x')]*2),
            plan(evidence_requests=[dict(kind='memory',query='x',user='5')]),plan(uncertain_claims=['anything']),plan(topic='x'*61)]
        for p in invalid:
            with self.subTest(p=p),self.assertRaises(ValueError):parse_plan(json.dumps(p))
        with self.assertRaises(ValueError):parse_plan('{"version":1,"version":1}')


class RuntimePlan(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle

    def install(self,p=None):
        self.observed=[];self.runtime.response_pipeline=TwoStage(observer=self.observed.append)
        self.backend._job=AsyncMock(return_value=json.dumps(p or plan()))
        self.runtime.companion=CompanionStore(self.root/'private.sqlite3')
        return self.runtime.companion

    async def test_actual_runtime_two_calls_no_write_or_reply_replacement(self):
        store=self.install();before=store.data_counts(2,4)
        await self.runtime.ingest(self.event(content='<@999> 내가 좋아하는 색이 뭐야?'));await self.settle()
        self.assertEqual(self.backend._job.await_count,1);self.assertEqual(len(self.backend.calls),1)
        self.assertEqual(len(self.transport.sent),1);self.assertEqual(self.transport.sent[0][0].id,10)
        self.assertEqual(before,store.data_counts(2,4));self.assertEqual(self.observed[0]['evidence']['memory']['status'],'unavailable')
        self.assertEqual(self.observed[0]['evidence']['operations']['status'],'not_checked')

    async def test_planner_keeps_existing_context_source_beyond_six_messages(self):
        self.install(plan(evidence_requests=[]));event=self.event()
        context=[dict(role='assistant' if i%2==0 else 'user',content='원본-'+str(i)) for i in range(12)]
        cfg=self.settings.get();cfg['_current_utterance']=event.content
        await self.runtime.response_pipeline.respond(self.runtime,event,context,cfg,fresh=AsyncMock(return_value=True),visual='not_provided')
        payload=json.loads(self.backend._job.call_args.args[0][1]['content'])
        self.assertEqual(payload['context'],context)
        self.assertEqual(context[0]['content'],'원본-0')

    async def test_scoped_memory_not_found_and_fiction_are_distinct(self):
        store=self.install(plan(evidence_requests=[dict(kind='memory',query='색'),dict(kind='fiction',query='')]))
        store.set_consent(2,4,'memory',True);store.set_consent(2,5,'memory',True)
        store.add_memory(2,5,3,'좋아하는 색은 금색')
        await self.runtime.ingest(self.event(content='<@999> 내가 좋아하는 색이 뭐야?'));await self.settle()
        evidence=self.observed[0]['evidence'];self.assertEqual(evidence['memory']['status'],'not_found')
        self.assertEqual(evidence['fiction']['status'],'fictional');self.assertNotIn('금색',str(evidence))

    async def test_invalid_plan_does_not_fall_back_to_unverified_generation(self):
        self.install();self.backend._job=AsyncMock(return_value='{"user_id":"5"}')
        await self.runtime.ingest(self.event());await self.settle()
        self.assertFalse(self.backend.calls);self.assertFalse(self.transport.sent)

    async def race(self,change):
        store=self.install();store.set_consent(2,4,'memory',True)
        key=store.add_memory(2,4,3,'좋아하는 색은 남색')
        entered=asyncio.Event();release=asyncio.Event()
        async def text(context,cfg):
            self.assertIn(key,str(context));entered.set();await release.wait();return '현재 기록에는 남색이야.'
        self.backend.text=text
        await self.runtime.ingest(self.event(content='<@999> 좋아하는 색이 뭐야?'))
        await asyncio.wait_for(entered.wait(),5);change(store,key);release.set();await self.settle()
        self.assertFalse(self.transport.sent)

    async def test_revoke_during_second_stage_blocks_send(self):
        await self.race(lambda s,k:s.set_consent(2,4,'memory',False))

    async def test_correct_during_second_stage_blocks_send(self):
        def update(s,k):
            with s.db() as db:db.execute('UPDATE memories SET summary=? WHERE memory_id=?',('색은 흰색',k))
        await self.race(update)

    async def test_cancel_during_first_stage_cleans_request(self):
        self.install();entered=asyncio.Event()
        async def wait(*a,**kw):entered.set();await asyncio.Future()
        self.backend._job=wait
        await self.runtime.ingest(self.event());await asyncio.wait_for(entered.wait(),5)
        await self.runtime.close();self.assertFalse(self.transport.sent);self.assertFalse(self.runtime.tasks)

    async def test_lookup_failure_does_not_generate_or_claim_success(self):
        store=self.install();store.set_consent(2,4,'memory',True)
        store.memories=lambda *a,**k:(_ for _ in ()).throw(sqlite3.OperationalError('synthetic'))
        await self.runtime.ingest(self.event());await self.settle()
        self.assertFalse(self.backend.calls);self.assertFalse(self.transport.sent)

    async def test_first_stage_timeout_has_no_unverified_fallback(self):
        self.install();self.backend._job=AsyncMock(side_effect=asyncio.TimeoutError())
        await self.runtime.ingest(self.event());await self.settle()
        self.assertFalse(self.backend.calls);self.assertFalse(self.transport.sent)

    async def test_new_evidence_invalidates_an_empty_search(self):
        store=self.install();store.set_consent(2,4,'memory',True)
        async def text(context,cfg):
            self.assertIn('not_found',str(context));store.add_memory(2,4,3,'좋아하는 색은 남색')
            return '지금 확인되는 기록은 없어.'
        self.backend.text=text
        await self.runtime.ingest(self.event());await self.settle();self.assertFalse(self.transport.sent)

    async def test_final_transport_rechecks_pipeline_snapshot(self):
        store=self.install();store.set_consent(2,4,'memory',True)
        execute=self.transport.execute
        async def late_change(event,action,library,fresh):
            store.set_consent(2,4,'memory',False)
            return await execute(event,action,library,fresh)
        self.transport.execute=late_change
        await self.runtime.ingest(self.event());await self.settle()
        self.assertFalse(self.transport.sent)
        self.assertIn('generation_evidence_changed',[r['code'] for r in self.runtime.diagnostics])


if __name__=='__main__':unittest.main()
