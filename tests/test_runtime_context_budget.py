import tempfile
from pathlib import Path
import unittest
from unittest.mock import AsyncMock
from echomate_bot.gguf_backend import GGUFEngine,GGUFLocalBackend,runtime_text_budget
from echomate_bot.character_models import character


class Response:
    def __init__(self,data):self.data=data
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    def raise_for_status(self):pass
    async def json(self):return self.data


class Session:
    def post(self,url,json):
        if url.endswith('/apply-template'):return Response({'prompt':str(len(json['messages']))})
        return Response({'tokens':[1]*int(json['content'])*150})


class RuntimeBudget(unittest.IsolatedAsyncioTestCase):
    async def test_old_groups_removed_but_current_user_reply_and_facts_stay_in_order(self):
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            p=Path(folder);engine=GGUFEngine(p/'e',p/'m',p/'out');engine.session=Session();engine.url='http://127.0.0.1'
            history=[]
            for i in range(20):history.extend([dict(role='user',content=f'[참여자 4] old {i}'),dict(role='assistant',content=f'answer {i}')])
            fixed=[dict(role='system',content='policy'),dict(role='user',content='verified facts')]
            tail=[dict(role='user',content='[참여자 4] current'),dict(role='user',content='reply evidence'),dict(role='user',content='explicit current event')]
            result=await engine.fit_runtime_context([*fixed,*history,*tail],384)
            self.assertTrue(any(m['content'].startswith('[문맥 선택 상태') for m in result))
            result=[m for m in result if not m['content'].startswith('[문맥 선택 상태')]
            self.assertEqual(result[:2],fixed);self.assertEqual(result[-3:],tail)
            self.assertLessEqual(engine.last_context['input_tokens']+384+64,2048)
            remaining=result[2:-3];self.assertEqual(len(remaining)%2,0)
            for user,bot in zip(remaining[::2],remaining[1::2]):
                self.assertEqual(user['content'].split()[-1],bot['content'].split()[-1])
            self.assertGreater(engine.last_context['removed_exchanges'],0)
            with self.assertRaisesRegex(ValueError,'문맥 예산'):
                await engine.fit_runtime_context([dict(role='system',content='p')]+[dict(role='user',content='pinned fact') for _ in range(20)],384)

    async def test_runtime_budget_is_task_local_and_explicit_current_is_required(self):
        b=object.__new__(GGUFLocalBackend);b.name='하루';b.name_version=0;b.entry=character('lime')
        seen=[]
        async def job(messages,**kw):seen.append((runtime_text_budget.get(),messages));return '짧은 응원이에요.'
        b._job=job
        await b.text([dict(role='user',content='[대화 대상 참고 자료]')],{'_native_runtime_context':True,'_current_utterance':'오늘은 여기까지.'})
        self.assertTrue(seen[-1][0]);self.assertIn('오늘은 여기까지',seen[-1][1][-1]['content'])
        self.assertFalse(runtime_text_budget.get())
        with self.assertRaisesRegex(ValueError,'current source'):
            await b.text([dict(role='user',content='일상')],{'_native_runtime_context':True})
