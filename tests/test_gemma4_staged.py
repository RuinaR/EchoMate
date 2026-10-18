"""No-network regression tests for Gemma4 staged probe."""
import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "tools" / "probe_gemma4_12b.py"
SPEC = importlib.util.spec_from_file_location("gemma4_probe_staged", PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

class Gemma4StagedProbeTests(unittest.TestCase):
    def test_model_is_instruction_tuned(self):
        self.assertEqual(mod.MODEL, "google/gemma-4-12B-it")

    def test_download_requires_two_explicit_flags(self):
        result = mod.diagnose(allow_load=True, allow_download=False)
        self.assertEqual(result["category"], "explicit_download_consent_required")
        self.assertFalse(result["weight_download_allowed"])

    def test_errors_have_no_exception_message(self):
        self.assertEqual(mod.classify(ImportError("token=SECRET")), "library_incompatible")
        self.assertEqual(mod.classify(MemoryError("private sample")), "runtime_compatibility_failure")

if __name__ == "__main__":
    unittest.main()
