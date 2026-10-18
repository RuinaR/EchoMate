import unittest
from pathlib import Path
from datetime import datetime,timezone
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.implicit_address import ImplicitAddress,parse_implicit_address
from echomate_studio.dialogue_state import DialogueState,Turn
from echomate_studio.participation import ParticipationPolicy,ContextAssessment
from echomate_studio.engagement import EngagementPolicy
from echomate_studio.turn_pipeline import evaluate_turn

class ImplicitAddressTests(unittest.TestCase):
    def test_strict_schema(self):
        self.assertEqual(parse_implicit_address('{"addressed_to_bot":true,"topic_continues":true}'),
                         ImplicitAddress(True,True))
        for s in ['{}','{"addressed_to_bot":"true","topic_continues":true}',
                  '{"addressed_to_bot":true,"topic_continues":true,"extra":1}','oops']:
            with self.assertRaises(ValueError): parse_implicit_address(s)

    def _turn(self, assessor):
        now=datetime(2026,10,18,tzinfo=timezone.utc)
        state=DialogueState()
        state.append(channel_id=1,thread_id=None,turn=Turn("b","bot","보스 갈래?",now,is_bot=True))
        state.append(channel_id=1,thread_id=None,turn=Turn("u","human","그럼 몇시?",now))
        return evaluate_turn(state=state,policy=ParticipationPolicy(enabled=True,
            allowed_channel_ids=frozenset({1}),opportunity_probability=0,cooldown_seconds=180),
            channel_id=1,thread_id=None,now=now,seconds_since_last_speech=5,
            seconds_since_last_human_message=0,
            assessor=lambda ctx: ContextAssessment(False,True,False),
            generator=lambda ctx:"9시 어때?",engagement_policy=EngagementPolicy(),
            implicit_assessor=assessor)
    def test_implicit_both_signals_needed(self):
        self.assertEqual(self._turn(lambda _: ImplicitAddress(True,True)).reason,"engaged_ready")
        self.assertEqual(self._turn(lambda _: ImplicitAddress(True,False)).reason,"cooldown")
        self.assertEqual(self._turn(lambda _: ImplicitAddress(False,True)).reason,"cooldown")
    def test_bad_assessor_fails_closed(self):
        def broken(_):raise RuntimeError("offline")
        self.assertEqual(self._turn(broken).reason,"cooldown")
        self.assertEqual(self._turn(lambda _: {"addressed_to_bot":True,"topic_continues":True}).reason,"cooldown")
