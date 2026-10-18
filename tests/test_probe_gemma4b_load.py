import importlib.util
import unittest
from pathlib import Path

p=Path(__file__).resolve().parents[1]/"tools"/"probe_gemma4b_load.py"
spec=importlib.util.spec_from_file_location("gemma4b_load_probe",p)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class GemmaLoadProbeTests(unittest.TestCase):
    def test_no_download_by_default(self):
        self.assertEqual(module.probe()["status"],"not_run")
        self.assertEqual(module.probe()["reason"],"explicit_download_opt_in_required")
    def test_reject_unreviewed_model_id(self):
        with self.assertRaises(ValueError):
            module.probe(model_id="untrusted/other-model")
