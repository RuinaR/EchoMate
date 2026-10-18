import ast
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class Gemma4_12BToolsTests(unittest.TestCase):
    def test_probe_ast_and_explicit_optin(self):
        p=ROOT/"tools"/"probe_gemma4_12b.py"
        tree=ast.parse(p.read_text(encoding="utf-8"))
        self.assertTrue(any(isinstance(n,ast.FunctionDef) and n.name=="diagnose" for n in tree.body))
        self.assertIn('allow_download=False',p.read_text(encoding="utf-8"))
    def test_lora_ast_and_local_cache(self):
        p=ROOT/"tools"/"smoke_gemma4_12b_lora.py"
        ast.parse(p.read_text(encoding="utf-8"))
        self.assertIn("local_files_only=True",p.read_text(encoding="utf-8"))
    def test_lora_synthetic_token_only(self):
        p=ROOT/"tools"/"smoke_gemma4_12b_lora.py"
        s=p.read_text(encoding="utf-8")
        self.assertIn("torch.full",s)
        self.assertIn("synthetic_only",s)
    def test_model_id_consistent(self):
        for p in ["probe_gemma4_12b.py","smoke_gemma4_12b_lora.py"]:
            self.assertIn("google/gemma-4-12B-it",(ROOT/"tools"/p).read_text(encoding="utf-8"))
