"""Check Hugging Face gated model access without downloading model weights.

Uses the current local HF token. Only checks a small public model config file.
Does not expose token or server-provided error text in its report.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

MODEL = "google/gemma-3-4b-it"

def check_access(get_file):
    try:
        get_file(repo_id=MODEL, filename="config.json")
    except Exception as exc:
        kind=type(exc).__name__
        msg=str(exc).lower()
        if "gated" in kind.lower() or "gated" in msg or "403" in msg or "401" in msg:
            category="access_denied_or_token_scope"
        elif "entrynotfound" in kind.lower() or "404" in msg:
            category="missing_config_or_repository"
        elif "connection" in msg or "timeout" in msg:
            category="network_failure"
        else:
            category="unknown"
        return {"status":"failed","category":category,"error_type":kind}
    return {"status":"ok","category":"authorized_for_config"}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("local_data/gemma-access.json"))
    args=parser.parse_args()
    try:
        from huggingface_hub import hf_hub_download
        result=check_access(hf_hub_download)
    except ImportError:
        result={"status":"failed","category":"huggingface_hub_missing"}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Gemma config access:",result["status"],result["category"])
    return 0 if result["status"]=="ok" else 1

if __name__=="__main__":
    raise SystemExit(main())
