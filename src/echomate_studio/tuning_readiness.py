"""Offline fine-tuning readiness check. Never trains on or exports source messages.

This tool produces only metadata. Training requires a separate data-rights review.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

SUPPORTED_SOURCES = ("official-personal-data-package", "api-export", "unknown")
SENSITIVE = ("credential", "contact", "health", "financial", "third-party-identifiers")

def assess_readiness(*, source_kind: str, permission_confirmed: bool,
                     owner_reviewed: bool, gpu_vram_gb: float | None = None) -> dict:
    if source_kind not in SUPPORTED_SOURCES:
        raise ValueError("unknown source kind")
    if gpu_vram_gb is not None and gpu_vram_gb <= 0:
        raise ValueError("VRAM must be positive")
    checks = {
        "source_identified": source_kind != "unknown",
        "rights_reviewed": bool(permission_confirmed),
        "owner_reviewed": bool(owner_reviewed),
        "training_data_screened": False,
        "train_validation_split": False,
        "compatible_base_weights_ready": False,
        "qlora_environment_ready": False,
        "baseline_quality_comparison_ready": False,
    }
    # API content requires express Discord permission; user consent alone is not enough.
    if source_kind == "api-export":
        checks["rights_reviewed"] = False
    return {
        "schema_version": 1,
        "requested_method": "QLoRA",
        "target_family": "Gemma 3",
        "status": "not_ready",
        "blocking_checks": [k for k, ok in checks.items() if not ok],
        "checks": checks,
        "gpu_vram_gb": gpu_vram_gb,
        "sensitive_categories_to_screen": list(SENSITIVE),
        "note": "No messages read or exported; no training started.",
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-kind", choices=SUPPORTED_SOURCES, required=True)
    p.add_argument("--permission-confirmed", action="store_true",
                   help="Use only after independently verifying source-specific AI-training rights")
    p.add_argument("--owner-reviewed", action="store_true")
    p.add_argument("--gpu-vram-gb", type=float)
    p.add_argument("--output", type=Path, default=Path("local_data/tuning-readiness.json"))
    args=p.parse_args()
    result=assess_readiness(source_kind=args.source_kind,
                            permission_confirmed=args.permission_confirmed,
                            owner_reviewed=args.owner_reviewed,
                            gpu_vram_gb=args.gpu_vram_gb)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Training not started. Readiness report saved:", args.output)
    print("Remaining gates:", ", ".join(result["blocking_checks"]))

if __name__=="__main__":
    main()
