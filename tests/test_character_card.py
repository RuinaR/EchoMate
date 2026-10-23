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
