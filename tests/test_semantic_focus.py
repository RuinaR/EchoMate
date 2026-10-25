"""Source qualifiers, archived epochs and optional context contracts."""
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
from echomate_bot.summary_fidelity import check_fidelity
from echomate_bot.summarization import Summarizer,validated_digest
from echomate_bot.gguf_backend import GGUFEngine
from echomate_bot.context import EXCERPT_PREFIX
import test_followup_release as fixtures
import test_local_chat as local_fixtures
from unittest.mock import AsyncMock


class Qualifiers(unittest.TestCase):
    def test_dropped_negation_condition_report_and_time_are_rejected(self):
        for source,evidence,target in [
            ('알림을 등록하지 않았다.','알림을 등록','알림을 등록했다'),
            ('만약 시간이 된다면 참석할 수도 있다.','시간이 된다면','참석하기로 결정했다'),
            ('친구가 저장했다고 전해 들었다.','저장했다고','기억 저장을 완료했다'),
            ('기억 조회에 실패했다.','기억 조회에 실패','기억 기록이 없어 조회에 실패했다'),
            ('어제는 이전 이름을 사용했다.','이전 이름을 사용','오늘 현재 이름을 사용했다')]:
            with self.subTest(source=source),self.assertRaises(ValueError):check_fidelity(target,evidence,source)
    def test_normal_and_qualified_paraphrases_and_game_title_survive(self):
        for source,evidence,target in [
            ('주말에는 산책을 하고 싶어','주말에는 산책','주말 산책을 희망함'),
            ('예약을 등록하지 않았다.','예약을 등록','알림 예약을 하지 않았다'),
            ('만약 시간이 되면 갈 수도 있어.','시간이 되면','시간이 허락할 경우 참석할 수도 있다'),
            ('이번 모임에서는 같이 운동하자','이번 모임에서는 같이','다음 모임에서 같이 운동하기로 제안했다'),
            ('모임에서 "카탄"을 같이 하자','모임에서 "카탄"','카탄을 함께 하자고 제안함')]:check_fidelity(target,evidence,source)


class ArchiveEpochs(unittest.IsolatedAsyncioTestCase):
    setUp=fixtures.DigestStoreQA.setUp
    tearDown=fixtures.DigestStoreQA.tearDown
    async def test_reconsent_does_not_reactivate_old_digest_epoch(self):
        result=await Summarizer(self.store,self.backend).generate(2,3,'flow',self.turns,persist=True)
        self.assertTrue(result['saved']);self.assertTrue(self.store.digests(2,4,3)[0]['usable'])
        self.store.set_consent(2,4,'summaries',False);self.store.set_consent(2,4,'summaries',True)
        rows=self.store.digests(2,4,3);self.assertEqual(len(rows),1);self.assertFalse(rows[0]['usable'])
    async def test_stale_archive_answer_resets_prior_guard_and_returns_no_text(self):
        s=Summarizer(self.store,self.backend);await s.generate(2,3,'flow',self.turns,persist=True)
        s.last_guard={'stale':'guard'};s.last_digest='old'
        event=SimpleNamespace(author=4,guild=2,channel=3,id=20,content='지난번 대화 요약',member_mentions=(),conversation_id='flow')
        self.assertIsNone(await s.answer(event,[],bot_id=999,fresh=lambda:False))
        self.assertIsNone(s.last_guard);self.assertIsNone(s.last_digest)
        valid=[True];consent=self.store.digest_consent
        def superseded(*args):valid[0]=False;return consent(*args)
        self.store.digest_consent=superseded
        event.content='지금 대화 요약'
        self.assertIsNone(await s.answer(event,self.turns[:1],bot_id=999,fresh=lambda:valid[0]))
    async def test_real_evidence_substring_cannot_certify_reversed_summary(self):
        turns=[replace(self.turns[0],content='나는 예약을 등록하지 않았다.'),self.turns[1]]
        raw=json.dumps(dict(items=[dict(kind='decision',source=turns[0].message_id,evidence='예약을 등록',text='예약을 등록했다')],ended=False))
        with self.assertRaises(ValueError):validated_digest(raw,turns)
        self.assertFalse(self.store.digests(2,4,3))
    async def test_conflicting_source_versions_are_not_silently_rebound(self):
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            validated_digest(self.raw,[*self.turns,replace(self.turns[-1],author_id='5')])
    async def test_reconsent_between_archive_selection_and_guard_does_not_rebind(self):
        s=Summarizer(self.store,self.backend);await s.generate(2,3,'flow',self.turns,persist=True)
        consent=self.store.digest_consent
        def changed(*args):
            self.store.set_consent(2,4,'summaries',False);self.store.set_consent(2,4,'summaries',True)
            return consent(*args)
        self.store.digest_consent=changed
        event=SimpleNamespace(author=4,guild=2,channel=3,id=20,content='지난번 대화 요약',member_mentions=(),conversation_id='flow')
        answer=await s.answer(event,[],bot_id=999)
        self.assertIn('동의가 바뀌',answer);self.assertIsNone(s.last_guard)


class LocalExecution(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=local_fixtures.LocalRuntime.asyncSetUp
    asyncTearDown=local_fixtures.LocalRuntime.asyncTearDown
    async def test_explicit_local_capability_and_request_use_command_help_without_execution(self):
        for text in ('실제로 예약할 수 있어?','내일 알려줘','내 기억 목록 보여줘'):
            answer=await self.chat.send(text,self.backend)
            self.assertIn('명령',answer);self.assertEqual(self.chat.last['response_origin'],'runtime')
            self.assertFalse(self.chat.last['context']);self.assertEqual(self.chat.last['operation_state'],'NOT_REQUESTED')
        self.backend.text.assert_not_awaited();self.assertFalse(self.chat.store.reminders(2,4))
        self.backend.grounded_reply=lambda text,state:'현재 이름은 하루야.' if '이름' in text else None
        answer=await self.chat.send('너 이름이 뭐야? 그리고 내일 알려줘',self.backend)
        self.assertIn('현재 이름은 하루',answer);self.assertIn('/알림',answer)
    async def test_reports_conditions_and_casual_futures_keep_generation(self):
        for text in ('친구가 알림 등록했다고 말했어. 어떻게 생각해?','나중에 같이 생각해 보자','만약 예약할 수 있어?'):
            await self.chat.send(text,self.backend)
        self.assertEqual(self.backend.text.await_count,3)
        self.backend.engine.last_context={'old_gpu_metric':True}
        await self.chat.send('/알림 목록',self.backend)
        self.assertEqual(self.chat.last['response_origin'],'runtime');self.assertEqual(self.chat.last['context'],{})


class OptionalContext(unittest.IsolatedAsyncioTestCase):
    async def test_summary_transmits_complete_source_including_late_correction(self):
        from echomate_bot.inference import LocalBackend
        from echomate_studio.dialogue_state import Turn
        from datetime import datetime,timezone
        backend=SimpleNamespace(processor=None,_job=AsyncMock(return_value='{}'))
        text='앞서 검토한 내용. '*65+'정정: 예약을 실행하지 않았고 확정하지도 않았어.'
        turn=Turn('10','4',text,datetime.now(timezone.utc))
        await LocalBackend.summarize_dialogue(backend,[turn])
        record=json.loads(backend._job.await_args.args[0][1]['content'])[0]
        self.assertEqual(record['text'],text)
        self.assertIn('실행하지 않았고',record['text'])
    async def test_optional_whole_excerpts_removed_but_required_sources_pinned(self):
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            p=Path(folder);e=GGUFEngine(p/'e',p/'m',p/'out');e.context=2048
            async def count(messages):return sum(len(m['content']) for m in messages)
            e.count_messages=count
            required=dict(source='reply',excerpt='반드시 보존할 실제 reply',required=True)
            extra=dict(source='old',excerpt='과거 발췌 '*260,required=False)
            messages=[dict(role='system',content='policy'),dict(role='user',content=EXCERPT_PREFIX+json.dumps([extra,required],ensure_ascii=False)),dict(role='user',content='현재 요청')]
            result=await e.fit_runtime_context(messages,384)
            self.assertIn('반드시 보존할 실제 reply',str(result));self.assertNotIn('과거 발췌',str(result))
            self.assertEqual(e.last_context['removed_excerpts'],1)
            self.assertIn('문맥 선택 상태',str(result));self.assertEqual(messages[-1],result[-1])
            self.assertIn('과거 발췌',str(messages))
            extra['required']=True;messages[1]['content']=EXCERPT_PREFIX+json.dumps([extra,required],ensure_ascii=False)
            with self.assertRaises(ValueError):await e.fit_runtime_context(messages,384)
