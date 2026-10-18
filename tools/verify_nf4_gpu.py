"""Local, synthetic GPU NF4 verification. No model downloads or private data."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def run_probe(torch, bnb, *, device="cuda:0", width=128):
    if width < 64 or width % 64:
        raise ValueError("width must be a positive multiple of 64, at least 64")
    if not torch.cuda.is_available():
        return {"status":"failed","reason":"cuda_unavailable"}
    try:
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(device)
        # Linear4bit quantizes when moved to CUDA; NF4 is the QLoRA format.
        layer=bnb.nn.Linear4bit(width,width,bias=False,compute_dtype=torch.float16,
                                 compress_statistics=True,quant_type="nf4")
        layer=layer.to(device)
        x=torch.ones((2,width),device=device,dtype=torch.float16)
        with torch.no_grad():
            y=layer(x)
            torch.cuda.synchronize(device)
        if y.shape != (2,width) or not bool(torch.isfinite(y).all().item()):
            return {"status":"failed","reason":"invalid_result"}
        return {"status":"ok","device":str(torch.cuda.get_device_name(device)),
                "quant_type":"nf4","shape":[2,width],
                "peak_allocated_mib":round(torch.cuda.max_memory_allocated(device)/1048576,2),
                "free_mib_after":round(torch.cuda.mem_get_info(device)[0]/1048576,2)}
    except Exception as e:
        return {"status":"failed","reason":"gpu_operation_failed","error_type":type(e).__name__}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("local_data/nf4-gpu-probe.json"))
    args=parser.parse_args()
    try:
        import torch
        import bitsandbytes as bnb
        result=run_probe(torch,bnb)
    except Exception as e:
        result={"status":"failed","reason":"import_failed","error_type":type(e).__name__}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("NF4 GPU verification:",result["status"],"report:",args.output)
    return 0 if result["status"]=="ok" else 1

if __name__=="__main__":
    raise SystemExit(main())
