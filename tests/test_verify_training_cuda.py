import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

FILE=Path(__file__).resolve().parents[1]/"tools"/"verify_training_cuda.py"
spec=importlib.util.spec_from_file_location("verify_training_cuda",FILE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class VerifyTrainingCudaTests(unittest.TestCase):
    def test_cpu_only(self):
        torch=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:False),
                              version=SimpleNamespace(cuda=None))
        self.assertFalse(mod.verify(torch)[0])
    def test_gpu_operation(self):
        class Tensor:
            def __mul__(self,n):return self
            def sum(self):return self
            def item(self):return 6.0
        torch=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:True,get_device_name=lambda n:"Mock GPU"),
            version=SimpleNamespace(cuda="12.8"),__version__="2.9.1",
            tensor=lambda *args,**kwargs: Tensor())
        self.assertTrue(mod.verify(torch)[0])
    def test_bad_calculation(self):
        class Tensor:
            def __mul__(self,n):return self
            def sum(self):return self
            def item(self):return 0.0
        torch=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:True,get_device_name=lambda n:"Mock GPU"),
            version=SimpleNamespace(cuda="12.8"),__version__="2.9.1",
            tensor=lambda *args,**kwargs: Tensor())
        self.assertFalse(mod.verify(torch)[0])
