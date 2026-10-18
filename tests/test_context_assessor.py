import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.context_assessor import assess, parse_assessment
from echomate_studio.ollama_client import OllamaError


class ContextAssessorTests(unittest.TestCase):
    def test_valid_response(self):
        a = parse_assessment('{"is_sensitive_moment":false,"has_useful_contribution":true,"interruption_is_appropriate":true}')
        self.assertFalse(a.is_sensitive_moment)
        self.assertTrue(a.has_useful_contribution)

    def test_fenced_json(self):
        a = parse_assessment('```json\n{"is_sensitive_moment":true,"has_useful_contribution":false,"interruption_is_appropriate":false}\n```')
        self.assertTrue(a.is_sensitive_moment)

    def test_reject_wrong_types_and_extra_fields(self):
        for text in ('{}', '{"is_sensitive_moment":0,"has_useful_contribution":true,"interruption_is_appropriate":true}',
                     '{"is_sensitive_moment":false,"has_useful_contribution":true,"interruption_is_appropriate":true,"foo":1}'):
            with self.assertRaises(ValueError):
                parse_assessment(text)

    @patch("echomate_studio.context_assessor.chat", side_effect=OllamaError("offline"))
    def test_ollama_failure_is_silence(self, mock):
        a = assess([{"role":"user","content":"어때?"}])
        self.assertFalse(a.has_useful_contribution)

    @patch("echomate_studio.context_assessor.chat", return_value="not JSON")
    def test_invalid_output_is_silence(self, mock):
        a = assess([{"role":"user","content":"hello"}])
        self.assertFalse(a.interruption_is_appropriate)

    @patch("echomate_studio.context_assessor.chat", return_value='{"is_sensitive_moment":false,"has_useful_contribution":true,"interruption_is_appropriate":true}')
    def test_context_is_passed_to_local_model(self, mock):
        context = [{"role":"user","content":"사람 A: 게임 ㄱ?"}]
        a = assess(context, model="test")
        self.assertTrue(a.has_useful_contribution)
        self.assertEqual(mock.call_args.args[0][-1], context[0])
        self.assertEqual(mock.call_args.kwargs["temperature"], 0.0)

    def test_empty_context_is_silence(self):
        self.assertFalse(assess([]).has_useful_contribution)
