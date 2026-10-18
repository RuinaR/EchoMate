"""Explicitly opted-in local Gemma 3 NF4 load and VRAM probe.

Requires prior acceptance of Google's Gemma license and local HF authentication.
Never reads Discord data; never trains or uploads anything.
"""
from __future__ import annotations
import argparse
import gc
import json
from pathlib import Path

MODEL_ID = "google/gemma-3-4b-it"

def classify_error(exc):
    """Categorize locally without putting sensitive URLs/tokens in reports."""
    value = str(exc).lower()
    if any(term in value for term in ("gated", "403", "access to model", "restricted repository",
                                      "not authorized", "401", "unauthorized")):
        return "model_access_not_granted"
    if any(term in value for term in ("404", "repository not found", "not found on hugging face")):
        return "model_repository_not_found_or_hidden"
    if any(term in value for term in ("connection", "timeout", "ssl", "network", "proxy")):
        return "network_or_tls_failure"
    if any(term in value for term in ("no space left", "disk full", "not enough space")):
        return "disk_space_failure"
    if "out of memory" in value:
        return "gpu_or_ram_out_of_memory"
    if any(term in value for term in ("missing", "not installed", "cannot import", "dll load")):
        return "missing_or_incompatible_dependency"
    return "unclassified_load_error"

def probe(*, allow_download=False, model_id=MODEL_ID, output=None):
    if model_id != MODEL_ID:
        raise ValueError("Only the reviewed Gemma 3 4B model is allowed")
    if not allow_download:
        return {"status":"not_run","reason":"explicit_download_opt_in_required","model":model_id}
    import torch
    from transformers import BitsAndBytesConfig, Gemma3ForConditionalGeneration
    if not torch.cuda.is_available():
        return {"status":"failed","reason":"cuda_unavailable","model":model_id}
    free_before,total=torch.cuda.mem_get_info(0)
    result={"status":"failed","model":model_id,
            "free_before_mib":round(free_before/1048576,1),
            "total_mib":round(total/1048576,1)}
    model=None
    try:
        cfg=BitsAndBytesConfig(load_in_4bit=True,
            bnb_4bit_quant_type="nf4",bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16)
        model=Gemma3ForConditionalGeneration.from_pretrained(
            model_id,quantization_config=cfg,device_map={"":0},
            dtype=torch.float16,attn_implementation="sdpa")
        torch.cuda.synchronize()
        free_after,_=torch.cuda.mem_get_info(0)
        result.update(status="ok",free_after_mib=round(free_after/1048576,1),
                      vram_delta_mib=round((free_before-free_after)/1048576,1),
                      peak_allocated_mib=round(torch.cuda.max_memory_allocated(0)/1048576,1))
    except Exception as exc:
        result.update(status="failed",error_type=type(exc).__name__,
                      reason="model_load_failed", failure_category=classify_error(exc))
    finally:
        del model
        gc.collect()
        torch.cuda.empty_cache()
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--allow-download",action="store_true",
                    help="Permit official model weights download; requires license acceptance")
    ap.add_argument("--output",type=Path,default=Path("local_data/gemma4b-vram.json"))
    args=ap.parse_args()
    result=probe(allow_download=args.allow_download)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print("Gemma 3 NF4 load:",result["status"],"report:",args.output)
    return 0 if result["status"] in ("ok","not_run") else 1

if __name__=="__main__":
    raise SystemExit(main())
