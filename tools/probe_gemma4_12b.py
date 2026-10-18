"""Gemma 4 12B IT staged, privacy-safe local NF4 compatibility probe."""
from __future__ import annotations
import argparse
import importlib.metadata
import json
from pathlib import Path

MODEL = "google/gemma-4-12B-it"
FILES = ("config.json", "processor_config.json", "tokenizer_config.json")

def classify(exc):
    name = type(exc).__name__
    if name in ("GatedRepoError", "RepositoryNotFoundError", "HfHubHTTPError"):
        return "huggingface_access_or_network"
    if isinstance(exc, (ImportError, AttributeError)):
        return "library_incompatible"
    if name in ("OutOfMemoryError", "CUDAOutOfMemoryError"):
        return "cuda_out_of_memory"
    if isinstance(exc, OSError):
        return "filesystem_cache_or_network"
    return "runtime_compatibility_failure"

def diagnose(*, allow_download=False, allow_load=False):
    result = {"model": MODEL, "status": "preflight",
              "weight_download_allowed": bool(allow_download)}
    if allow_load and not allow_download:
        return {**result, "status": "blocked",
                "category": "explicit_download_consent_required"}
    for package in ("torch", "transformers", "accelerate", "bitsandbytes", "peft", "huggingface_hub"):
        try:
            result[package + "_version"] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package + "_version"] = None
    try:
        import torch
        from transformers import AutoConfig, AutoModelForMultimodalLM, BitsAndBytesConfig
        from huggingface_hub import hf_hub_download
        result["cuda_available"] = bool(torch.cuda.is_available())
        if not result["cuda_available"]:
            return {**result, "status": "blocked", "category": "cuda_unavailable"}
        free, total = torch.cuda.mem_get_info(0)
        result.update(free_before_mib=round(free / 1048576, 1),
                      total_mib=round(total / 1048576, 1))
    except Exception as exc:
        return {**result, "status": "blocked", "category": classify(exc),
                "stage": "runtime_import", "error_type": type(exc).__name__}
    try:
        # Small files only. No model checkpoint download in preflight.
        config_path = hf_hub_download(repo_id=MODEL, filename="config.json")
        cfg = AutoConfig.from_pretrained(str(Path(config_path).parent), local_files_only=True)
        result["config_model_type"] = cfg.model_type
        result["config_access"] = "ok"
    except Exception as exc:
        return {**result, "status": "blocked", "category": classify(exc),
                "stage": "config", "error_type": type(exc).__name__}
    if not allow_load:
        return {**result, "status": "ready_for_optional_load"}
    model = None
    try:
        torch.cuda.reset_peak_memory_stats()
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                   bnb_4bit_use_double_quant=True,
                                   bnb_4bit_compute_dtype=torch.float16)
        model = AutoModelForMultimodalLM.from_pretrained(
            MODEL, quantization_config=quant, device_map={"": 0},
            dtype=torch.float16, attn_implementation="sdpa")
        torch.cuda.synchronize()
        free, _ = torch.cuda.mem_get_info(0)
        result.update(status="ok", stage="nf4_load",
                      peak_allocated_mib=round(torch.cuda.max_memory_allocated(0)/1048576, 1),
                      free_after_mib=round(free/1048576, 1))
        return result
    except Exception as exc:
        return {**result, "status": "failed", "category": classify(exc),
                "stage": "nf4_load", "error_type": type(exc).__name__}
    finally:
        del model
        torch.cuda.empty_cache()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--allow-load", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("local_data/gemma4-12b-probe.json"))
    args = parser.parse_args()
    if "local_data" not in args.output.resolve().parts:
        parser.error("report output must be inside local_data")
    report = diagnose(allow_download=args.allow_download, allow_load=args.allow_load)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Gemma4 12B probe:", report["status"], "stage:", report.get("stage", "preflight"),
          "category:", report.get("category", "none"), "report:", args.output)
    return 0 if report["status"] in ("ready_for_optional_load", "ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())
