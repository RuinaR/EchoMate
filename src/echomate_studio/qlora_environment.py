"""Read-only local feasibility report for persona QLoRA.

Never installs packages, downloads weights, opens private messages or trains.
"""
from __future__ import annotations
import argparse
from importlib import metadata
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys

PACKAGES=("torch","transformers","peft","trl","accelerate","bitsandbytes","datasets")

def inspect(*, query_gpu: bool = False) -> dict:
    packages={}
    for name in PACKAGES:
        try:
            packages[name]=metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name]=None
    gpu={"status":"not_checked"}
    if query_gpu:
        command=shutil.which("nvidia-smi")
        if not command:
            gpu={"status":"nvidia_smi_missing"}
        else:
            try:
                run=subprocess.run([command,"--query-gpu=name,memory.total,memory.free,compute_cap",
                    "--format=csv,noheader,nounits"],capture_output=True,text=True,
                    timeout=10,check=False)
                gpu={"status":"ok" if run.returncode==0 else "query_failed",
                     "summary":run.stdout.strip()[:500] if run.returncode==0 else ""}
            except (subprocess.SubprocessError,OSError):
                gpu={"status":"query_failed"}
    return {
        "status":"diagnostic_only_no_training",
        "python":sys.version.split()[0],
        "platform":platform.system(),
        "packages":packages,
        "gpu":gpu,
        "training_environment_ready":False,
        "warnings":[
            "Package presence is not a CUDA training compatibility or memory test.",
            "Ollama GGUF inference weights cannot be used directly as QLoRA base weights.",
            "Confirm dataset rights and review private data before any training.",
        ],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--gpu",action="store_true",help="Run local nvidia-smi query")
    p.add_argument("--output",type=Path,default=Path("local_data/qlora-environment.json"))
    args=p.parse_args()
    result=inspect(query_gpu=args.gpu)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Local QLoRA environment diagnostic:",args.output)
    print("Packages present:",sum(v is not None for v in result["packages"].values()),"/",len(PACKAGES))
    print("No training or model download performed.")

if __name__=="__main__":
    main()
