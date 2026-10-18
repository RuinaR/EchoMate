"""Opt-in Gemma 4 12B compatibility, gated download and 16GB NF4 probe.

Never silently downloads ~24GB model. Produces aggregate-only JSON diagnostics.
"""
import argparse
import json
from pathlib import Path

MODEL="google/gemma-4-12B-it"

def diagnose(*, allow_download=False, allow_load=False):
    import importlib.metadata
    result={"model":MODEL,"status":"preflight","weight_download_allowed":allow_download}
    try:
        from transformers import Gemma4ForConditionalGeneration, BitsAndBytesConfig
        result["transformers"]=importlib.metadata.version("transformers")
        result["class_available"]=True
    except (ImportError,AttributeError) as exc:
        result.update(status="blocked",category="transformers_gemma4_unavailable",error_type=type(exc).__name__)
        return result
    try:
        import torch
        result["cuda_available"]=torch.cuda.is_available()
        if result["cuda_available"]:
            free,total=torch.cuda.mem_get_info(0)
            result["free_before_mib"]=round(free/1048576,1)
            result["total_mib"]=round(total/1048576,1)
    except Exception as exc:
        result.update(status="blocked",category="cuda_probe_failed",error_type=type(exc).__name__)
        return result
    try:
        from huggingface_hub import hf_hub_download
        hf_hub_download(repo_id=MODEL,filename="config.json")
        result["config_access"]="ok"
    except Exception as exc:
        result.update(status="blocked",category="config_access_failed",error_type=type(exc).__name__)
        return result
    if not allow_load:
        result.update(status="ready_for_optional_load",note="Config verified, no weights loaded")
        return result
    if not allow_download:
        result.update(status="blocked",category="explicit_download_consent_required")
        return result
    if not result["cuda_available"]:
        result.update(status="blocked",category="cuda_unavailable")
        return result
    model=None
    try:
        quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16)
        model=Gemma4ForConditionalGeneration.from_pretrained(MODEL,quantization_config=quant,device_map={"":0},dtype=torch.float16,attn_implementation="sdpa")
        torch.cuda.synchronize()
        free,_=torch.cuda.mem_get_info(0)
        result.update(status="ok",free_after_mib=round(free/1048576,1),peak_allocated_mib=round(torch.cuda.max_memory_allocated(0)/1048576,1))
        return result
    except Exception as exc:
        result.update(status="failed",category="nf4_model_load_failed",error_type=type(exc).__name__)
        return result
    finally:
        del model
        if torch.cuda.is_available():torch.cuda.empty_cache()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--allow-download",action="store_true")
    p.add_argument("--allow-load",action="store_true")
    p.add_argument("--output",type=Path,default=Path("local_data/gemma4-12b-probe.json"))
    args=p.parse_args()
    report=diagnose(allow_download=args.allow_download,allow_load=args.allow_load)
    if "local_data" not in args.output.resolve().parts:
        p.error("report output must be inside local_data")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Gemma4 12B probe:",report["status"],"category:",report.get("category","none"),"report:",args.output)
    return 0 if report["status"] in ("ready_for_optional_load","ok") else 1

if __name__=="__main__":
    raise SystemExit(main())
