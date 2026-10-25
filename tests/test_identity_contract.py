import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,patch
from echomate_bot.identity_contract import answer_identity
from echomate_bot.character_models import CharacterNames,character
from echomate_bot.gguf_backend import GGUFLocalBackend


class ReadOnlyIdentity(unittest.TestCase):
    def test_multiple_identity_clauses_preserve_admin_boundary_without_losing_other_requests(self):
        answer=answer_identity('너 이름이 뭐야? 그리고 앞으로 라임이라고 해.','하루','라임')
        self.assertIn('하루',answer);self.assertIn('관리자',answer)
        self.assertEqual(answer.count('지금 내 이름은'),1)
        self.assertIn('유나.2',answer_identity('너 유나.2이지?','유나.2','라임'))
        self.assertIsNone(answer_identity('너 이름이 뭐야? 그리고 내일 여행지는 어디가 좋을까?','하루','라임'))
        self.assertIsNone(answer_identity('친구가 "너 이름이 뭐야? 앞으로 라임이라고 해"라고 했어.','하루','라임'))
    def test_name_authority_handles_queries_assertions_and_requests(self):
        for text in ('너 이름이 뭐야?','원래 이름이 뭐니?','너 원래 라임 아니었어?',
                     '앞으로 다시 라임이라고 해.','너 라임이지?','아까 네가 라임이라고 했잖아.',
                     '<@999> 당신의 현재 이름을 알려 줘'):
            with self.subTest(text=text):
                value=answer_identity(text,'하루','라임')
                self.assertIsNotNone(value);self.assertIn('하루',value)
                self.assertNotIn('나는 라임',value)

    def test_no_keyword_filter_or_third_person_or_mixed_request_capture(self):
        for text in ('내 이름이 뭐야?','친구 이름은 라임이야.','민수가 "너 라임이지?"라고 했어.',
                     '라임 주스가 맛있어.','너 이름이 뭐야? 그리고 산책 장소도 추천해줘.',
                     '너 이름을 바꾸지 마.','너의 이름이 들어간 시를 써줘','나중에 같이 생각해 보자'):
            with self.subTest(text=text):self.assertIsNone(answer_identity(text,'하루','라임'))

    def test_persisted_versions_migrate_read_only_and_publish_atomically(self):
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            p=Path(folder)/'names.json';p.write_text(json.dumps({'schema':1,'names':{'lime':'하루'}}),encoding='utf-8')
            before=p.read_bytes();n=CharacterNames(p)
            self.assertEqual(n.version('lime'),0);self.assertEqual(p.read_bytes(),before)
            n.save('lime','새봄');self.assertEqual(n.version('lime'),1)
            n.save('lime','새봄');self.assertEqual(n.version('lime'),1)
            with patch('echomate_bot.character_models.atomic_private_json',side_effect=OSError):
                with self.assertRaises(OSError):n.save('lime','다른 이름')
            self.assertEqual(n.effective('lime'),'새봄');self.assertEqual(n.version('lime'),1)
            self.assertEqual(CharacterNames(p).version('lime'),1)


class GenerationIdentity(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_identity_response_keeps_existing_code_output_boundary(self):
        from echomate_bot.output_policy import FALLBACK
        b=object.__new__(GGUFLocalBackend);b.name='```private```';b.name_version=0;b.entry=character('lime')
        b._job=AsyncMock()
        self.assertEqual(await b.text([dict(role='user',content='너 이름이 뭐야?')],{}),FALLBACK)
        b._job.assert_not_awaited()

    async def test_identity_fact_never_calls_model_and_ordinary_text_still_does(self):
        b=object.__new__(GGUFLocalBackend);b.name='하루';b.name_version=2;b.entry=character('lime')
        b._job=AsyncMock(return_value='같이 생각해 보자.')
        result=await b.text([dict(role='user',content='너 라임이지?')],{})
        self.assertIn('하루',result);b._job.assert_not_awaited()
        self.assertEqual(await b.text([dict(role='user',content='산책을 갈까?')],{}),'같이 생각해 보자.')
        b._job.assert_awaited_once()

    async def test_name_change_during_generation_discards_old_answer(self):
        b=object.__new__(GGUFLocalBackend);b.name='하루';b.name_version=1;b.entry=character('lime')
        async def job(*a,**kw):b.name='새봄';b.name_version+=1;return '하루라고 불러.'
        b._job=job
        with self.assertRaisesRegex(RuntimeError,'identity changed'):
            await b.text([dict(role='user',content='인사해줘')],{})
