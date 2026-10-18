import importlib.util
import unittest
from pathlib import Path

PATH=Path(__file__).resolve().parents[1]/"tools"/"verify_training_stack.py"
spec=importlib.util.spec_from_file_location("verify_training_stack", PATH)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TrainingStackTests(unittest.TestCase):
    def test_all_imports_pass(self):
        self.assertEqual(module.check(lambda name: object()), [])
    def test_missing_dependency_is_reported(self):
        def importer(name):
            if name=="peft":
                raise ImportError("missing")
            return object()
        self.assertEqual(module.check(importer),[("peft","ImportError","missing")])
    def test_unexpected_import_error_is_reported(self):
        def importer(name):
            if name=="bitsandbytes":
                raise OSError("native DLL missing")
            return object()
        self.assertEqual(module.check(importer),[("bitsandbytes","OSError","native DLL missing")])
