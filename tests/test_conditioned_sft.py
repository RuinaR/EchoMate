import unittest
import json
from pathlib import Path
from prepare_conditioned_sft import ids,mask_target,supervised_pair,compile_case


class TargetMask(unittest.TestCase):
    def test_only_assistant_suffix_is_supervised(self):
        self.assertEqual(mask_target([2,4,7],[2,4,7,11,1]),[-100,-100,-100,11,1])
        for full in ([2,4,8,11],[2,4,7]):
            with self.assertRaises(ValueError):mask_target([2,4,7],full)
    def test_mapping_token_output_is_unwrapped_not_counted_as_fields(self):
        class Tokenizer:
            def apply_chat_template(self,*args,**kwargs):return dict(input_ids=[2,3,4,1],attention_mask=[1]*4)
        self.assertEqual(ids(Tokenizer(),[],False),[2,3,4,1])
    def test_asymmetric_generation_prefix_preserved_without_masking_target(self):
        class Tokenizer:
            all_special_tokens=['<reserved>']
            def encode(self,text,**kwargs):return list(text.encode())
            def apply_chat_template(self,ms,add_generation_prompt=False,tokenize=False,**kwargs):
                if add_generation_prompt:text='USER:model:EMPTY_THOUGHT'
                else:text='USER:model:'+ms[-1]['content']+':END'
                return dict(input_ids=self.encode(text)) if tokenize else text
        tok=Tokenizer();prompt,full,labels=supervised_pair(tok,[dict(role='user',content='question')],'answer')
        self.assertEqual(bytes(n for n in labels if n!=-100),b'answer:END')
        self.assertEqual(full[:len(prompt)],prompt)
        with self.assertRaises(ValueError):supervised_pair(tok,[],'<reserved>')


class ActualStateFormatting(unittest.IsolatedAsyncioTestCase):
    async def test_settings_scope_and_common_capability_layer_supply_fixture_facts(self):
        data=json.loads((Path(__file__).parent/'fixtures/conditioned_curriculum.json').read_text('utf-8'))
        class Tokenizer:
            def apply_chat_template(self,*args,**kwargs):return dict(input_ids=[1,2,3])
        messages=await compile_case(data['scenarios'][0],'gentle',data['characters'],Tokenizer())
        fact=next(m['content'] for m in messages if '읽기 전용 공개 기능 상태' in m['content'])
        view=json.loads(fact[fact.index('{'):])
        self.assertEqual(view['features']['reminders'],'ready');self.assertTrue(view['text_enabled'])
        self.assertEqual(set(view['unsupported']),{'stickers','media_send','voice','screen_control','code_output'})
        self.assertEqual(messages[-1]['content'],data['scenarios'][0]['user'])
    async def test_withdrawal_and_unavailable_store_do_not_look_ready(self):
        data=json.loads((Path(__file__).parent/'fixtures/conditioned_curriculum.json').read_text('utf-8'))
        class Tokenizer:
            def apply_chat_template(self,*args,**kwargs):return dict(input_ids=[1,2,3])
        for case_id,state in (('consent_withdrawn','consent_required'),('lookup_unavailable','failed')):
            case=next(r for r in data['scenarios'] if r['id']==case_id)
            messages=await compile_case(case,'gentle',data['characters'],Tokenizer())
            fact=next(m['content'] for m in messages if '읽기 전용 공개 기능 상태' in m['content'])
            self.assertEqual(json.loads(fact[fact.index('{'):])['features']['memory'],state)
