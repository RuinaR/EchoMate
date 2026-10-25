"""Mode scope and mandatory risk boundaries; no live Discord."""
import unittest
from dataclasses import replace
from datetime import datetime,timezone
from unittest.mock import AsyncMock,patch
from echomate_bot.execution_modes import ExecutionMode,GateStatus,RULES,assess_mode,current_mode_reports,structural_direct_reason
import test_social_routing as social
import test_lime_desktop as desktop


class GatePolicy(unittest.TestCase):
    def test_missing_na_deferred_and_failed_mandatory_safety_never_pass(self):
        for status in GateStatus:
            evidence={r.key:GateStatus.PASS for r in RULES};evidence['privacy']=status
            self.assertEqual(assess_mode('DISCORD_DIRECT',evidence)['ready'],status==GateStatus.PASS)
            self.assertEqual(assess_mode('LOCAL_CHAT',evidence)['local_testing_available'],status==GateStatus.PASS)
        with self.assertRaises(ValueError):assess_mode('LOCAL_CHAT',{'typo':'PASS'})
        self.assertFalse(assess_mode('LOCAL_CHAT',{})['ready'])
    def test_autonomy_quality_is_not_a_local_or_direct_gate_but_risky_claims_are(self):
        evidence={r.key:GateStatus.PASS for r in RULES}
        evidence.update(audience=GateStatus.FAIL,conversation=GateStatus.FAIL,long_running=GateStatus.DEFERRED,live_discord=GateStatus.BLOCKED)
        self.assertTrue(assess_mode('LOCAL_CHAT',evidence)['ready'])
        direct=assess_mode('DISCORD_DIRECT',evidence,live_authorized=True)
        self.assertTrue(direct['ready']);self.assertEqual(direct['scope'],'OFFLINE READY');self.assertFalse(direct['live_allowed'])
        self.assertFalse(assess_mode('DISCORD_AUTONOMOUS',evidence)['ready'])
        evidence['high_risk_claims']=GateStatus.FAIL
        self.assertFalse(assess_mode('LOCAL_CHAT',evidence)['ready']);self.assertFalse(assess_mode('DISCORD_DIRECT',evidence)['ready'])
        evidence['high_risk_claims']=GateStatus.PASS;evidence['delivery']=GateStatus.FAIL
        self.assertFalse(assess_mode('DISCORD_DIRECT',evidence)['ready'])
    def test_live_evidence_and_authorization_are_independent(self):
        evidence={r.key:GateStatus.PASS for r in RULES}
        self.assertFalse(assess_mode('DISCORD_DIRECT',evidence,live_authorized=True)['live_allowed'])
        self.assertFalse(assess_mode('DISCORD_DIRECT',evidence,offline=False)['live_allowed'])
        self.assertTrue(assess_mode('DISCORD_DIRECT',evidence,offline=False,live_authorized=True)['live_allowed'])
        evidence['live_discord']=GateStatus.BLOCKED
        self.assertFalse(assess_mode('DISCORD_AUTONOMOUS',evidence)['ready'])
    def test_smoke_success_or_model_load_does_not_clear_known_factual_failures(self):
        reports=current_mode_reports(True)
        self.assertTrue(reports['LOCAL_CHAT']['local_testing_available'])
        self.assertTrue(all(not r['ready'] and not r['live_allowed'] for r in reports.values()))
        self.assertIn('high_risk_claims',reports['DISCORD_DIRECT']['blockers'])
        self.assertNotIn('audience',reports['DISCORD_DIRECT']['blockers'])
        self.assertFalse(current_mode_reports(False)['LOCAL_CHAT']['local_testing_available'])
    def test_direct_proof_requires_actual_target_and_unquoted_source(self):
        e=social.SocialRuntime.event(self,content='<@999> 확인해 줘')
        self.assertIsNone(structural_direct_reason(e,999))
        e=replace(e,member_mentions=(999,));self.assertEqual(structural_direct_reason(e,999),'bot_mention')
        for text in ('"<@999>"라고 썼어','하루야 확인해 줘','<@5> 너는 어때?'):
            self.assertIsNone(structural_direct_reason(replace(e,content=text),999))
        self.assertEqual(structural_direct_reason(replace(e,content='답장',reply_to=9001,reply_author=999),999),'bot_reply')


class DirectRuntime(unittest.IsolatedAsyncioTestCase):
    setUp=social.SocialRuntime.setUp
    asyncTearDown=social.SocialRuntime.asyncTearDown
    event=social.SocialRuntime.event
    settle=social.SocialRuntime.settle
    async def test_mentions_group_reply_and_no_call_never_invoke_audience_models(self):
        self.runtime.execution_mode=ExecutionMode.DISCORD_DIRECT
        self.runtime.direct_cooldown=0;self.runtime.direct_spam_window=0
        self.backend.fast_text_path=True
        for name in ('assess_social','link_direct','verify_target'):
            setattr(self.backend,name,AsyncMock(side_effect=AssertionError('Autonomous classifier forbidden')))
        for e in (replace(self.event(id=100,content='<@999> 첫 질문'),member_mentions=(999,)),
                  replace(self.event(id=101,content='<@999> <@5> 같이 물어볼게'),member_mentions=(999,5)),
                  replace(self.event(id=102,content='후속 설명 부탁'),reply_to=9001,reply_author=999)):
            await self.runtime.ingest(replace(e,timestamp=datetime.now(timezone.utc)));await self.settle()
        self.assertEqual([e.id for e,a in self.transport.sent],[100,101,102])
        for e in (self.event(id=103,content='그럼 더 설명해 줘'),replace(self.event(id=104,content='<@5> 너는 어때?'),member_mentions=(5,)),
                  replace(self.event(id=105,content='"<@999>"라고 말했대'),member_mentions=(999,))):
            await self.runtime.ingest(e);await self.settle()
        self.assertEqual(len(self.transport.sent),3)
        for name in ('assess_social','link_direct','verify_target'):getattr(self.backend,name).assert_not_awaited()
        self.assertEqual(self.runtime.failures,0)


class LiveController(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=desktop.Controller.asyncSetUp
    asyncTearDown=desktop.Controller.asyncTearDown
    async def test_direct_entry_cannot_start_live_even_if_smoke_passes(self):
        self.c.lime_backend=desktop.Model();self.c.lime_backend.capabilities_verified=True;self.c.lime['stage']='ready'
        with patch('echomate_bot.desktop.LocalController._run_bot',new_callable=AsyncMock) as live:
            self.assertFalse((await self.c.command('start'))['ok'])
            await self.c._run_bot();live.assert_not_awaited()
        with self.assertRaises(RuntimeError):await self.c.create_backend({})

class BackendInitialState(unittest.IsolatedAsyncioTestCase):
    async def test_unprobed_backend_is_explicitly_unqualified(self):
        from echomate_bot.inference import LocalBackend
        b=LocalBackend()
        try:self.assertFalse(b.capabilities_verified)
        finally:await b.close()
