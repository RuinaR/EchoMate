from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,patch
from echomate_bot.lookup_inquiries import memory_inquiry_answer
from echomate_bot.character_models import character
from echomate_bot.gguf_backend import GGUFLocalBackend


class LookupInquiry(unittest.TestCase):
    def test_capability_acknowledgement_does_not_steal_new_ordinary_question(self):
        from echomate_bot.capabilities import question
        self.assertFalse(question('미동의와 기록 부재를 구분했네. 비 오는 날 퍼즐을 하는 건 어때?'))
        self.assertFalse(question('동의 상태는 이해했어. 오늘 점심은 뭐가 좋을까?'))
        self.assertTrue(question('사진을 보냈어. 볼 수 있어?'))
        self.assertTrue(question('내 동의 상태가 뭐야?'))
    def test_state_is_not_promoted_to_event_absence_or_fake_lookup(self):
        text='우리 지난주 같이 바다에 간 기억이 있어?'
        for state,fragment in [('not_requested','조회하지'),('not_authorized','동의'),('failed','실패'),('empty','결과가 비어'),('invalidated','근거가 바뀌어')]:
            self.assertIn(fragment,memory_inquiry_answer(text,state))
        self.assertIsNone(memory_inquiry_answer(text,'found'))
        self.assertIsNone(memory_inquiry_answer(text,'unsupported'))

    def test_quotes_conditions_proposals_and_other_people_are_not_tool_queries(self):
        for text in ['친구가 "우리 지난주 같이 바다 간 기억이 있어?"라고 물었어.',
                     '만약 우리 같이 바다에 간 기억이 있다면?',
                     '우리 다음에 같이 생각해 보자.', '나는 바다를 좋아한다고 기억해 줘.',
                     '친구끼리 바다에 간 기억이 있어?', '기억이라는 소재로 농담해 줘.',
                     '소설 속 우리 같이 바다에 간 기억이 있어?']:
            self.assertIsNone(memory_inquiry_answer(text,'not_requested'))


class IntegratedLookup(unittest.IsolatedAsyncioTestCase):
    async def test_actual_backend_preserves_empty_failed_and_unqueried_without_model_vote(self):
        b=object.__new__(GGUFLocalBackend);b.name='하루';b.name_version=0;b.entry=character('lime')
        b._job=AsyncMock(return_value='친구와 같이 생각해 보자.')
        for state in ('failed','not_requested','not_authorized','empty'):
            answer=await b.text([dict(role='user',content='우리 전에 산책했던 거 기억나?')],{'_memory_lookup_state':state})
            self.assertIsNotNone(answer)
        b._job.assert_not_awaited()
        self.assertEqual(await b.text([dict(role='user',content='나중에 같이 생각해 보자.')],{}),'친구와 같이 생각해 보자.')
