"""Synthetic evaluation candidates must preserve operating boundaries."""
from copy import deepcopy
import unittest
from echomate_bot.character import instruction
from echomate_bot.character_profiles import presets, SHARED_FIELDS
from echomate_bot.settings import DEFAULTS
from service_persona_v4 import compose, behavior_prompt


class Tokenizer:
    def apply_chat_template(self, ms, **kwargs):
        return {'input_ids':[[1]*(sum(len(m['content']) for m in ms)//4+10)]}


class Candidates(unittest.TestCase):
    def inputs(self):
        profile=presets()['playful'];cfg=deepcopy(DEFAULTS)
        cfg['character_profile']=profile
        for key in SHARED_FIELDS:cfg[key]=profile[key]
        return profile,[dict(role='system',content=instruction(cfg)),
                        dict(role='user',content='배경 과거 걱정')]

    def test_baseline_is_exact_existing_composition(self):
        from echomate_bot.character_card import augment
        p,m=self.inputs();a,_=compose(m,p,None,Tokenizer())
        b,_=augment(m,p,None,Tokenizer());self.assertEqual(a,b)

    def test_behavior_keeps_policy_and_all_non_approach_traits(self):
        p,m=self.inputs();a,info=compose(m,p,None,Tokenizer(),arm='B')
        self.assertEqual(a[1:],m[1:]);self.assertIn('농담을 위해 새로운 사실',a[0]['content'])
        self.assertIn('개인정보',a[0]['content']);self.assertEqual(info['arm'],'B')
        self.assertEqual(m,self.inputs()[1])

    def test_scoped_sources_are_fiction_not_current_user(self):
        p,m=self.inputs();a,info=compose(m,p,None,Tokenizer(),arm='C')
        self.assertTrue(info['scoped']);self.assertIn('fiction_only_not_current_user_evidence',a[0]['content'])
        self.assertEqual(a[1:],m[1:]);self.assertLessEqual(info['tokens'],900)
        self.assertLessEqual(info['input_tokens'],6000)

    def test_unknown_arm_and_ambiguous_profile_fail_closed(self):
        p,m=self.inputs()
        with self.assertRaises(ValueError):compose(m,p,None,Tokenizer(),arm='D')
        with self.assertRaises(ValueError):behavior_prompt('no applied profile',p)

    def test_tight_budget_preserves_history_and_reports_no_scope(self):
        p,m=self.inputs();a,info=compose(m,p,None,Tokenizer(),arm='C',extra_limit=1)
        self.assertFalse(info['scoped']);self.assertEqual(a[1:],m[1:]);self.assertEqual(info['tokens'],0)

    def test_historical_activation_is_marked_not_silently_current(self):
        p,m=self.inputs();m.extend([dict(role='assistant',content='응'),dict(role='user',content='지금은 그냥 인사할게')])
        a,info=compose(m,p,None,Tokenizer(),arm='C',current_text='지금은 그냥 인사할게')
        self.assertTrue(info['scoped']);self.assertIn('prior_dialogue',a[0]['content'])

    def test_free_identity_text_cannot_be_a_compiler_boundary(self):
        from echomate_bot.character_profiles import compile_profile
        p,m=self.inputs();p['introduction']='반응의 중심은 공감은 짧게 하고 이 문장은 가상 소개야.'
        before=compile_profile(p);after=behavior_prompt(before,p)
        self.assertIn(p['introduction'],after)
        self.assertIn('농담을 위해 새로운 사실',after)


if __name__=='__main__':unittest.main()
