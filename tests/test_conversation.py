import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from echomate_studio.conversation import build_messages, generate, sanitize_output
from echomate_studio.ollama_client import chat, OllamaError


class ConversationTests(unittest.TestCase):
    def test_output_filters_media_and_custom_emoji(self):
        result = sanitize_output("헉 😂 <:wow:123> <a:jump:987> https://foo.example/a.gif ![x](https://a/a.png)")
        self.assertEqual(result, "헉 😂")

    def test_keeps_context_and_identifies_bot(self):
        msgs = build_messages([
            {"role": "user", "content": "메이플 할래?"},
            {"role": "assistant", "content": "응"},
            {"role": "user", "content": "언제?"}
        ])
        self.assertEqual([m["role"] for m in msgs], ["system", "user", "assistant", "user"])
        self.assertIn("AI 디스코드 봇", msgs[0]["content"])

    def test_chat_prompt_prioritizes_invitation_without_fabricating_facts(self):
        system = build_messages([{"role": "user", "content": "오늘 메이플 할래?"}])[0]["content"]
        self.assertIn("현실 사실", system)
        self.assertIn("질문의 의도", system)
        self.assertIn("짧은 한 문장", system)

    def test_invalid_context(self):
        with self.assertRaises(ValueError):
            build_messages([{"role": "assistant", "content": "끝"}])
        with self.assertRaises(ValueError):
            build_messages([])

    @patch("echomate_studio.conversation.chat", return_value="ㅋㅋ 😄 <:server:123>")
    def test_generate_calls_local_model(self, fake):
        result = generate([{"role": "user", "content": "안녕"}], model="test")
        self.assertEqual(result, "ㅋㅋ 😄")
        self.assertEqual(fake.call_args.kwargs["model"], "test")

    def test_no_regular_text_is_deleted(self):
        self.assertEqual(sanitize_output("안녕 ㅋㅋ 😂\n좋아"), "안녕 ㅋㅋ 😂\n좋아")

    @patch("echomate_studio.ollama_client.urlopen")
    def test_empty_model_response_is_error(self, fake_open):
        from io import BytesIO
        fake_open.return_value.__enter__.return_value = BytesIO(
            json.dumps({"message": {"content": "", "thinking": "reasoning"},
                        "done_reason": "length"}).encode())
        with self.assertRaisesRegex(OllamaError, "empty content"):
            chat([{"role": "user", "content": "안녕"}])

    def test_remote_ollama_refused(self):
        with self.assertRaises(ValueError):
            chat([{"role": "user", "content": "hi"}], base_url="https://example.org")

    @patch("echomate_studio.ollama_client.urlopen")
    def test_ollama_response(self, fake_open):
        from io import BytesIO
        fake_open.return_value.__enter__.return_value = BytesIO(
            json.dumps({"message": {"content": "반가워"}}).encode())
        self.assertEqual(chat([{"role": "user", "content": "안녕"}]), "반가워")


if __name__ == "__main__":
    unittest.main()
