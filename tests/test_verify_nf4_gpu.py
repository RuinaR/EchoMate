import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

path=Path(__file__).resolve().parents[1]/"tools"/"verify_nf4_gpu.py"
spec=importlib.util.spec_from_file_location("nf4_gpu",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class NF4GpuTests(unittest.TestCase):
    def test_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            module.run_probe(None,None,width=65)
    def test_missing_cuda(self):
        torch=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:False))
        self.assertEqual(module.run_probe(torch,None)["reason"],"cuda_unavailable")
    def test_synthetic_probe_and_memory(self):
        class Tensor:
            shape=(2,128)
            def all(self):return self
            def item(self):return True
        class Linear:
            def __init__(self,*args,**kwargs):self.config=kwargs
            def to(self,device):return self
            def __call__(self,x):return Tensor()
        class Context:
            def __enter__(self):return None
            def __exit__(self,*args):return False
        cuda=SimpleNamespace(is_available=lambda:True,empty_cache=lambda:None,
              reset_peak_memory_stats=lambda d:None,synchronize=lambda d:None,
              get_device_name=lambda d:"Fake GPU",
              max_memory_allocated=lambda d:8*1048576,
              mem_get_info=lambda d:(64*1048576,128*1048576))
        torch=SimpleNamespace(cuda=cuda,float16="fp16",
              ones=lambda *a,**k:Tensor(),
              no_grad=lambda:Context(),
              isfinite=lambda v:Tensor())
        bnb=SimpleNamespace(nn=SimpleNamespace(Linear4bit=Linear))
        out=module.run_probe(torch,bnb)
        self.assertEqual(out["status"],"ok")
        self.assertEqual(out["peak_allocated_mib"],8)
        self.assertEqual(out["quant_type"],"nf4")
