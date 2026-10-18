import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

p=Path(__file__).resolve().parents[1]/"tools"/"train_persona_lora.py"
spec=importlib.util.spec_from_file_location("train_persona_lora",p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PersonaTrainerTests(unittest.TestCase):
    def test_approval_required(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with self.assertRaises(PermissionError):
                mod.validate(p/"train.jsonl",p/"val.jsonl",p/"out")
    def test_input_output_must_stay_private(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            a=p/"local_data"/"train.jsonl";b=p/"local_data"/"val.jsonl"
            a.parent.mkdir()
            a.write_text('{"text":"one"}\n',encoding="utf-8")
            b.write_text('{"text":"two"}\n',encoding="utf-8")
            with self.assertRaises(ValueError):
                mod.validate(a,b,p/"public",approved=True)
            self.assertEqual(mod.validate(a,b,p/"local_data"/"adapter",approved=True)[0],a.resolve())
    def test_bounds_and_sample_format(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"local_data";p.mkdir()
            a=p/"a.jsonl";b=p/"b.jsonl"
            a.write_text(json.dumps({"text":"one"})+"\n",encoding="utf-8")
            b.write_text(json.dumps({"text":"two"})+"\n",encoding="utf-8")
            with self.assertRaises(ValueError):
                mod.validate(a,b,p/"adapter",approved=True,max_steps=1000)
            self.assertEqual(list(mod.iterate_text(a)),["one"])
            a.write_text(json.dumps({"prompt":"leak"})+"\n",encoding="utf-8")
            with self.assertRaises(ValueError):
                list(mod.iterate_text(a))
