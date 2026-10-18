import importlib.util,json,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/"tools"/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
audit=load("corpus_preflight","gemma4_corpus_preflight.py")
reload=load("adapter_reload","probe_gemma4_adapter_reload.py")

class Gemma4BeforeOwnerTrainingTests(unittest.TestCase):
    def test_overlap_and_pii_block(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"local_data";p.mkdir()
            a,b=p/"train.jsonl",p/"valid.jsonl"
            a.write_text('{"text":"hello there original"}\n{"text":"contact test@example.com"}\n',encoding="utf-8")
            b.write_text('{"text":"hello there original"}\n',encoding="utf-8")
            result=audit.audit(a,b)
            self.assertEqual(result["status"],"review_required")
            self.assertEqual(result["exact_cross_split_overlap"],1)
            self.assertEqual(result["training"]["identifier_or_url_hint"],1)
            self.assertNotIn("hello there",json.dumps(result))

    def test_no_content_leak_and_schema(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"local_data";p.mkdir()
            a,b=p/"train.jsonl",p/"valid.jsonl"
            a.write_text('{"text":"one legitimate sample"}\n',encoding="utf-8")
            b.write_text('{"text":"another different phrase"}\n',encoding="utf-8")
            self.assertEqual(audit.audit(a,b)["status"],"heuristic_preflight_clear")
            b.write_text('{"prompt":"unsafe"}\n',encoding="utf-8")
            with self.assertRaises(ValueError):audit.audit(a,b)

    def test_adapter_metadata_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"local_data"/"adapter";p.mkdir(parents=True)
            (p/"adapter_model.safetensors").write_bytes(b"test-standin")
            c={"base_model_name_or_path":reload.MODEL,"r":4,"target_modules":["q_proj","v_proj"]}
            (p/"adapter_config.json").write_text(json.dumps(c),encoding="utf-8")
            self.assertEqual(reload.inspect_adapter(p),p.resolve())
            c["base_model_name_or_path"]="other"
            (p/"adapter_config.json").write_text(json.dumps(c),encoding="utf-8")
            with self.assertRaises(ValueError):reload.inspect_adapter(p)
