"""Fail-fast CUDA verification for the isolated EchoMate training environment."""
from __future__ import annotations
import sys

def verify(torch_module) -> tuple[bool, str]:
    if not torch_module.cuda.is_available():
        return False, "CUDA is unavailable in this Python environment"
    if not torch_module.version.cuda:
        return False, "CPU-only torch detected"
    try:
        tensor = torch_module.tensor([1.0, 2.0], device="cuda")
        result = float((tensor * 2).sum().item())
        if result != 6.0:
            return False, "CUDA tensor arithmetic unexpected"
        return True, f"CUDA torch={torch_module.__version__}, runtime={torch_module.version.cuda}, GPU={torch_module.cuda.get_device_name(0)}"
    except Exception as exc:
        return False, f"CUDA tensor test failed: {type(exc).__name__}"

def main():
    try:
        import torch
    except ImportError:
        print("PyTorch is not installed")
        return 1
    ok, message=verify(torch)
    print(message)
    return 0 if ok else 1

if __name__=="__main__":
    sys.exit(main())
