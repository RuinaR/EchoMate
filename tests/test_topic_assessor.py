import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.dialogue_state import Turn
from echomate_studio.topic_assessor import parse_topic_continuity, assess_reply_topic

NOW=datetime(2026,10,18,tzinfo=timezone.utc)
class TopicAssessorTests(unittest.TestCase):
    def test_strict_json(self):
        self.assertTrue(parse_topic_continuity('{"topic_continues":true}'))
        self.assertFalse(parse_topic_continuity('{"topic_continues":false}'))
        for text in ('{"topic_continues":"true"}','{"topic_continues":true,"extra":1}',"yes"):
            with self.assertRaises(ValueError):
                parse_topic_continuity(text)
    def test_local_verified_reply(self):
        turns=[Turn("bot","bot","보스 언제 가?",NOW,True),
               Turn("user","human","9시에 가자",NOW,False,"bot")]
        with patch("echomate_studio.topic_assessor.chat",return_value='{"topic_continues":true}') as mocked:
            self.assertTrue(assess_reply_topic(turns))
            self.assertEqual(mocked.call_args.kwargs["model"],"gemma3:12b")
    def test_unverified_reply_never_calls_model(self):
        turns=[Turn("user","human","9시에 가자",NOW,False,"other")]
        with patch("echomate_studio.topic_assessor.chat") as mocked:
            self.assertFalse(assess_reply_topic(turns))
            mocked.assert_not_called()
    def test_model_error_fails_closed(self):
        turns=[Turn("bot","bot","안녕",NOW,True),Turn("u","human","뭐해",NOW,False,"bot")]
        with patch("echomate_studio.topic_assessor.chat",side_effect=ValueError("bad")):
            self.assertFalse(assess_reply_topic(turns))
