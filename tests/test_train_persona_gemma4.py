import importlib.util
import ast
import json
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "tools" / "train_persona_gemma4.py"
spec = importlib.util.spec_from_file_location("train_persona_gemma4", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Gemma4PersonaTrainerTests(unittest.TestCase):
    def test_trainer_parses_as_python(self):
        ast.parse(PATH.read_text(encoding="utf-8"), filename=str(PATH))


    def fixture(self, root):
        p = Path(root) / "local_data"
        p.mkdir()
        a, b = p/"a.jsonl", p/"b.jsonl"
        a.write_text(json.dumps({"text": "synthetic training sample"}) + "\n", encoding="utf-8")
        b.write_text(json.dumps({"text": "heldout synthetic sample"}) + "\n", encoding="utf-8")
        return a, b, p/"adapter"

    def test_all_three_approvals_required(self):
        with tempfile.TemporaryDirectory() as d:
            a,b,o=self.fixture(d)
            for kwargs in ({"approved": True}, {"rights_confirmed": True, "privacy_reviewed": True},
                           {"approved": True, "rights_confirmed": True}):
                with self.assertRaises(PermissionError):
                    mod.validate(a,b,o,**kwargs)

    def test_private_paths_and_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            a,b,o=self.fixture(d)
            flags=dict(approved=True,rights_confirmed=True,privacy_reviewed=True)
            self.assertEqual(mod.validate(a,b,o,**flags)[0], a.resolve())
            with self.assertRaises(ValueError):
                mod.validate(a,b,Path(d)/"public",**flags)
            with self.assertRaises(ValueError):
                mod.validate(a,b,o,max_steps=11,**flags)
            with self.assertRaises(ValueError):
                mod.validate(a,b,o,seq_len=128,**flags)
            o.mkdir()
            (o/"checkpoint.txt").write_text("exists")
            with self.assertRaises(ValueError):
                mod.validate(a,b,o,**flags)


    def test_short_samples_are_opt_in_and_never_concatenated(self):
        with tempfile.TemporaryDirectory() as d:
            a,b,o=self.fixture(d)
            a.write_text('{"text":"AA"}\n{"text":"longer distinct synthetic statement"}\n',encoding="utf-8")
            class FakeTokenizer:
                def __call__(self,text,**kwargs):
                    return {"input_ids": [1,2,3,4] if text=="AA" else list(range(9))}
            tok=FakeTokenizer()
            self.assertEqual(mod.select_ids(a,tok,32,2),[list(range(9))])
            self.assertEqual(mod.select_ids(a,tok,32,2,min_tokens=3),
                             [[1,2,3,4],list(range(9))])

    def test_even_sampling_covers_beginning_middle_and_end(self):
        with tempfile.TemporaryDirectory() as d:
            a,b,o=self.fixture(d)
            rows=[{"text":f"invented-example-{i:02d}"} for i in range(11)]
            a.write_text("".join(json.dumps(x)+"\\n" for x in rows),encoding="utf-8")
            class Tokenizer:
                def __call__(self,text,**kwargs):
                    return list(range(8)) + [int(text[-2:])]
            chosen=mod.select_ids(a,Tokenizer(),32,3)
            self.assertEqual([x[-1] for x in chosen],[0,3,7])

    def test_schema_strict_and_no_model_import(self):
        with tempfile.TemporaryDirectory() as d:
            a,b,o=self.fixture(d)
            self.assertEqual(len(list(mod.iter_text(a))),1)
            a.write_text(json.dumps({"prompt":"not a label"})+"\n",encoding="utf-8")
            with self.assertRaises(ValueError):
                list(mod.iter_text(a))

if __name__ == "__main__":
    unittest.main()
