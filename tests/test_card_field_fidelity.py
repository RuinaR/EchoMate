"""Stored fictional data availability, not a model-quality score."""
from copy import deepcopy
import unittest
from echomate_bot.character_card import augment,FIELDS
from echomate_bot.character_profiles import DEFAULT_PROFILE


class CardFieldFidelity(unittest.TestCase):
    def test_background_tail_and_stable_speech_are_not_keyword_gated(self):
        class Tokenizer:
            def apply_chat_template(self,messages,**kw):return [0]*sum(len(m['content']) for m in messages)
        profile=deepcopy(DEFAULT_PROFILE)
        profile['card'].update(background='가상 마을의 일상과 주변 경치를 관찰했다. '*8+'결국 등대지기가 된 이유는 길 잃은 배를 돕고 싶어서다.',
                               vocabulary='군더더기 없는 일상 어휘',opening='인사는 짧게 하고 상대 이야기를 기다린다.')
        messages=[dict(role='system',content='고정 정책'),dict(role='user',content='계속 이야기해 줘.')]
        before=deepcopy(messages)
        augmented,metric=augment(messages,profile,None,Tokenizer(),limit=12000,extra_limit=10000)
        for key in ('background','vocabulary','opening'):self.assertIn(profile['card'][key],augmented[0]['content'])
        self.assertEqual(messages,before);self.assertEqual(augmented[1:],messages[1:]);self.assertGreater(metric['tokens'],0)

    def test_small_budget_drops_whole_optional_data_without_cutting_source(self):
        class Tokenizer:
            def apply_chat_template(self,messages,**kw):return [0]*sum(len(m['content']) for m in messages)
        profile=deepcopy(DEFAULT_PROFILE);profile['card']['background']='앞부분. '*30+'뒤의 핵심 이유.'
        messages=[dict(role='system',content='정책'),dict(role='user',content='내 원문 전체')]
        result,metric=augment(messages,profile,None,Tokenizer(),limit=20,extra_limit=5)
        self.assertEqual(result,messages);self.assertEqual(metric['tokens'],0)
