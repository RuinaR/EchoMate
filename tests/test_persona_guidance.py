from copy import deepcopy
import unittest
from echomate_bot.character import instruction
from echomate_bot.character_profiles import presets,SHARED_FIELDS
from echomate_bot.settings import DEFAULTS
from persona_guidance import neutral_messages


class NeutralBoundary(unittest.TestCase):
    def test_only_character_compiler_changes_not_policy_or_evidence(self):
        p=presets()['dry'];cfg=deepcopy(DEFAULTS);cfg.update(character_profile=p,_familiarity=80)
        cfg.update({k:p[k] for k in SHARED_FIELDS})
        messages=[dict(role='system',content=instruction(cfg)),dict(role='user',content='[검증된 실제 기억] 합성 자료'),dict(role='user',content='친구가 거짓말했어.')]
        before=deepcopy(messages);new=neutral_messages(messages,p)
        self.assertEqual(messages,before);self.assertEqual(messages[1:],new[1:])
        for text in ('프로그램','기억 저장','상대의 불편','친숙함'):
            self.assertEqual(text in messages[0]['content'],text in new[0]['content'])
        self.assertNotEqual(messages[0]['content'],new[0]['content'])

    def test_unknown_boundary_fails_closed(self):
        with self.assertRaises(ValueError):neutral_messages([dict(role='system',content='기타 정책')],presets()['dry'])
