import ast
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "compare_gemma4_persona.py"


class Gemma4PersonaComparisonTests(unittest.TestCase):
    def test_syntax_and_private_output_guards(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        self.assertTrue(any(isinstance(node, ast.FunctionDef) and node.name == "compare" for node in tree.body))
        source = SOURCE.read_text(encoding="utf-8")
        for token in ("disable_adapter()", "do_sample=False", "local_files_only=True",
                      "adapter_config.json", "local_data", "max_new_tokens"):
            self.assertIn(token, source)

    def test_no_upload_or_discord_side_effect(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("requests.post(", source)
        self.assertNotIn("discord.Client", source)
        self.assertNotIn("push_to_hub", source)


if __name__ == "__main__":
    unittest.main()
