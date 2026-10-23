"""Synthetic card/retrieval/input boundaries; never operating data or Discord."""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from echomate_bot.character_card import empty_card,validate_card,select_material,augment,rough_policy
from echomate_bot.character_profiles import DEFAULT_PROFILE,PROFILE_V2_KEYS,validate_profile,presets
import test_ui_workflows as ui
from test_dialog_layout import invoke


class CardData(unittest.TestCase):
    def test_missing_card_in_v2_reads_without_mutation(self):
        old={k:deepcopy(v) for k,v in DEFAULT_PROFILE.items() if k in PROFILE_V2_KEYS}
        result=validate_profile(old);self.assertNotIn('card',old);self.assertEqual(result['card'],empty_card())
    def test_runtime_metadata_is_not_the_current_speakers_utterance(self):
        from echomate_bot.reality_boundary import grounded_reply
        from echomate_bot.settings import DEFAULTS
        context=[dict(role='user',content='[참여자 4] 간단히 계산해 줘\n[관측된 이벤트 메타데이터 / 실제 발언 인용이 아님] {"배경":"도서관"}'),dict(role='user',content='[대화 대상 참고 자료 / 실제 발언 아님] 배경 과거 도서관')]
        rows,current=select_material(presets()['supportive']['card'],context)
        self.assertEqual(current,'간단히 계산해 줘');self.assertFalse(rows['lore'])
        cfg=deepcopy(DEFAULTS);cfg['_current_utterance']='우리 실제로 같이 카페 갔을 때 네가 한 말 기억나?'
        self.assertIn('그런 기억이 있다고 할 수는 없어',grounded_reply(context,cfg))
    def test_presets_are_independent_fiction_not_live_memory(self):
        a=presets();self.assertEqual(len({p['card']['background'] for p in a.values()}),4)
        a['supportive']['card']['background']='changed';self.assertNotEqual(presets()['supportive']['card']['background'],'changed')
        for p in presets().values():validate_profile(p)
    def test_retrieval_requires_keys_never_includes_private_or_recurses(self):
        c=presets()['playful']['card'];c['lore']=[dict(id='secret',keys=['비밀'],priority=100,enabled=True,private=True,match='any',content='private'),dict(id='one',keys=['별'],priority=1,enabled=True,private=False,match='any',content='비밀 키워드 종이'),dict(id='two',keys=['종이'],priority=99,enabled=True,private=False,match='any',content='recursive')]
        chosen,_=select_material(c,[dict(role='user',content='별'),dict(role='assistant',content='종이')]);self.assertEqual([x['id'] for x in chosen['lore']],['one'])
        chosen,_=select_material(c,[dict(role='user',content='비밀')]);self.assertFalse(chosen['lore'])
    def test_all_keys_relation_and_example_copy_suppression(self):
        c=presets()['dry']['card'];c['lore'][0].update(keys=['배경','과거'],match='all')
        ex=c['examples'][0];ex['relation']='familiar'
        a,_=select_material(c,[dict(role='user',content='배경 걱정')]);self.assertFalse(a['lore']);self.assertFalse(a['examples'])
        a,_=select_material(c,[dict(role='user',content='배경 과거 걱정')],80);self.assertTrue(a['lore']);self.assertTrue(a['examples'])
        a,_=select_material(c,[dict(role='assistant',content=ex['assistant']),dict(role='user',content='걱정')],80);self.assertFalse(a['examples'])
    def test_bounds_ids_control_tokens_and_foreign_fields(self):
        for edit in (lambda c:c.update(background='x'*801),lambda c:c.update(unknown='x'),lambda c:c.update(edge='unbounded'),lambda c:c.update(background='<|system|>'),lambda c:c['lore'].append(deepcopy(c['lore'][0]))):
            c=presets()['dry']['card'];edit(c)
            with self.assertRaises(ValueError):validate_card(c)
    def test_exact_budget_never_changes_original_history(self):
        class Tokenizer:
            def apply_chat_template(self,ms,**kw):return list(range(sum(len(m['content']) for m in ms)))
        m=[dict(role='system',content='정책'),dict(role='user',content='배경 과거 걱정')];before=deepcopy(m)
        result,info=augment(m,presets()['dry'],None,Tokenizer(),limit=700,extra_limit=650)
        self.assertEqual(m,before);self.assertEqual(result[1:],m[1:]);self.assertLessEqual(sum(len(x['content']) for x in result),700);self.assertLessEqual(info['tokens'],650)
        result,info=augment(m,presets()['dry'],None,Tokenizer(),limit=20,extra_limit=10);self.assertEqual(result,m);self.assertEqual(info['tokens'],0)
    def test_rough_language_is_contextual_not_relation_authority(self):
        c=empty_card();c['edge']='banter'
        self.assertIn('명시적으로 요청',rough_policy(c,'가볍게 놀려 줘',None))
        self.assertIn('허락이 생기지 않아',rough_policy(c,'실수했네',100))
        self.assertIn('멈추고',rough_policy(c,'그만 놀려 불편해',100))

    def test_mapping_and_batched_token_ids_count_tokens_not_metadata_keys(self):
        class Tokenizer:
            def apply_chat_template(self,ms,**kw):return {'input_ids':[[1]*sum(len(m['content']) for m in ms)],'attention_mask':[]}
        m=[dict(role='system',content='정책'),dict(role='user',content='배경 과거')]
        result,info=augment(m,presets()['dry'],None,Tokenizer(),limit=900,extra_limit=800)
        actual=sum(len(x['content']) for x in result)-sum(len(x['content']) for x in m)
        self.assertEqual(info['tokens'],actual);self.assertLessEqual(actual,800)

    def test_large_valid_card_exports_and_imports_without_losing_rows(self):
        import tempfile
        from pathlib import Path
        from echomate_bot.character_profiles import ProfileStore
        p=deepcopy(DEFAULT_PROFILE);row=presets()['dry']['card']['lore'][0]
        p['card']['lore']=[dict(row,id='row-'+str(i),content='가상 마을의 이야기 '*50) for i in range(16)]
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            store=ProfileStore(Path(folder)/'characters.json',1,'k'*32);out=Path(folder)/'sample.json'
            store.export_value(p,out);self.assertGreater(out.stat().st_size,16384)
            store.import_file(1,'imported',out);self.assertEqual(store.list()['imported'],p)


class FictionSummary(unittest.IsolatedAsyncioTestCase):
    async def test_physical_history_boundary_preserves_fiction_and_real_chat_history(self):
        from echomate_bot.reality_boundary import physical_recollection
        from echomate_bot.inference import LocalBackend
        from echomate_bot.settings import DEFAULTS
        from unittest.mock import AsyncMock
        for text in ('우리 실제로 같이 카페 갔을 때 네가 한 말 기억나?', '너랑 함께 밥 먹었을 때 기억해?', '지난번 너와 여행했을 때의 추억을 말해줘','너랑\n함께 밥\n먹었을 때\n기억나?'):
            self.assertTrue(physical_recollection(text))
        for text in ('우리 가상 설정에서 너랑 카페 갔던 기억을 이야기해줘','내가 친구랑 밥 먹었던 얘기 기억나?','너는 내가 Discord에 쓴 계획을 기억해?','설정 속 과거를 알려줘','A가 "너랑 같이 밥 먹었을 때 기억나?"라고 물었대. 왜일까?'):
            self.assertFalse(physical_recollection(text))
        backend=LocalBackend();backend._job=AsyncMock(side_effect=AssertionError('No generation for impossible experience'))
        try:
            result=await backend.text([dict(role='user',content='너랑 함께 산책했을 때 기억나?')],deepcopy(DEFAULTS));self.assertIn('그런 기억이 있다고 할 수는 없어',result);backend._job.assert_not_awaited()
        finally:await backend.close()

    async def test_fictional_bot_prose_is_not_persisted_as_real_user_memory(self):
        from datetime import datetime,timezone
        from echomate_studio.dialogue_state import Turn
        from echomate_bot.summarization import Summarizer
        from unittest.mock import AsyncMock
        turns=[Turn('1','4','주말에는 산책을 하고 싶어',datetime.now(timezone.utc)),Turn('2','999','가상 도서관을 복원했어',datetime.now(timezone.utc),is_bot=True,context_metadata='{"fictional_character":true}'),Turn('3','4','다음 주에는 공원으로 가볼까',datetime.now(timezone.utc))]
        backend=SimpleNamespace(summarize_dialogue=AsyncMock(return_value=json.dumps(dict(items=[dict(kind='plan',text='주말 산책을 희망함',source='1',evidence='주말에는 산책을')],ended=False))))
        store=SimpleNamespace(digest_consent=lambda *args:{'4':{}},save_digest=lambda *args:'saved')
        result=await Summarizer(store,backend).generate(2,3,'c',turns,persist=True)
        self.assertIsNotNone(result);self.assertEqual([t.message_id for t in backend.summarize_dialogue.call_args.args[0]],['1','3'])


import test_bot_integration as bot
class RuntimeGrounding(unittest.IsolatedAsyncioTestCase):
    setUp=bot.BotIntegration.setUp
    asyncTearDown=bot.BotIntegration.asyncTearDown
    event=bot.BotIntegration.event
    settle=bot.BotIntegration.settle
    async def test_actual_event_overrides_later_model_reference_messages(self):
        from echomate_bot.inference import LocalBackend
        from unittest.mock import AsyncMock
        local=LocalBackend();local._job=AsyncMock(side_effect=AssertionError('No generation for impossible shared past'))
        text='<@999> 우리 실제로 같이 카페 갔을 때 네가 한 말 기억나?'
        async def generated(context,cfg):
            self.assertEqual(cfg['_current_utterance'],text)
            return await local.text(context,cfg)
        self.backend.text=generated
        try:
            await self.runtime.ingest(self.event(content=text));await self.settle()
            self.assertEqual(len(self.transport.sent),1)
            self.assertIn('그런 기억이 있다고 할 수는 없어',self.transport.sent[0][1].text);local._job.assert_not_awaited()
        finally:await local.close()


class CardWidgets(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=ui.UIWorkflows.asyncSetUp
    asyncTearDown=ui.UIWorkflows.asyncTearDown
    sync=ui.UIWorkflows.sync
    dialog=ui.UIWorkflows.dialog
    fill=ui.UIWorkflows.fill
    async def test_multiline_identity_save_cancel_stale_and_lore_crud(self):
        from echomate_bot.card_ui import edit_card,entries
        from echomate_bot.character_profiles import applied_profile
        self.app.page='character';before=deepcopy(self.c.settings.get())
        edit_card(self.app);self.fill(self.dialog(),['배경·정체성']);await self.sync();d=self.dialog()
        self.assertIn('background',d._form_controls);d._form_values['background'].set('가상 항구에서\n책을 고친다')
        invoke(d,'<Control-Return>');await self.sync();self.assertFalse(self.c.error)
        self.assertEqual(self.c.settings.get()['character_profile']['card']['background'],'가상 항구에서\n책을 고친다')
        edit_card(self.app);self.fill(self.dialog(),['배경·정체성']);await self.sync();d=self.dialog()
        d._form_values['background'].set('저장하지 않을 글');invoke(d,'<Escape>');await self.sync()
        self.assertNotEqual(self.c.settings.get()['character_profile']['card']['background'],'저장하지 않을 글')
        p=applied_profile(self.c.settings.get());entries(self.app,p,'lore');self.fill(self.dialog(),['추가','새 항목']);await self.sync()
        self.fill(self.dialog(),['도서관','70','사용','허구의 작은 도서관','허용','하나 이상']);await self.sync()
        self.assertEqual(len(self.c.settings.get()['character_profile']['card']['lore']),1)
        p=applied_profile(self.c.settings.get());key=p['card']['lore'][0]['id'];entries(self.app,p,'lore');self.fill(self.dialog(),['삭제',key]);await self.sync();self.fill(self.dialog(),['아니']);await self.sync()
        self.assertTrue(self.dialog().winfo_exists());self.assertEqual(len(self.c.settings.get()['character_profile']['card']['lore']),1)
        self.fill(self.dialog(),['삭제']);await self.sync();self.assertFalse(self.c.settings.get()['character_profile']['card']['lore'])
        p=applied_profile(self.c.settings.get());self.c.settings.set(1,'mood','신남')
        result=await self.c.command('settings',values={'character_profile':p},expected_profile=p);self.assertFalse(result['ok']);self.assertEqual(self.c.settings.get()['mood'],'신남')
        self.assertEqual(self.c.settings.get()['model'],before['model'])
