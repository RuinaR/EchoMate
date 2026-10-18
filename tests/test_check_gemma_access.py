import importlib.util
import unittest
from pathlib import Path

p=Path(__file__).resolve().parents[1]/"tools"/"check_gemma_access.py"
spec=importlib.util.spec_from_file_location("check_gemma_access",p)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class GemmaAccessTests(unittest.TestCase):
    def test_success_only_checks_small_config(self):
        seen=[]
        out=module.check_access(lambda **kw: seen.append(kw))
        self.assertEqual(out["status"],"ok")
        self.assertEqual(seen,[{"repo_id":"google/gemma-3-4b-it","filename":"config.json"}])
    def test_gated_secret_not_logged(self):
        def denied(**kwargs):
            raise OSError("403 gated token=TOP_SECRET")
        out=module.check_access(denied)
        self.assertEqual(out["category"],"access_denied_or_token_scope")
        self.assertNotIn("TOP_SECRET",str(out))
