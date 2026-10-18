"""Local-only pretraining eligibility audit; no training set or message text exported.

This intentionally does not authorize model training or produce training samples.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import argparse
import json
import re
from .analyze import iter_json_array, normalize_text

CONTACT = re.compile(r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|01[016789][ -]?\d{3,4}[ -]?\d{4})")
DIGITS = re.compile(r"(?<!\d)\d{8,}(?!\d)")
REPETITION = re.compile(r"^(.)\1{5,}$")

def audit_eligibility(paths: list[Path]) -> dict:
    if not paths or len({p.resolve() for p in paths}) != len(paths):
        raise ValueError("unique input paths required")
    out = []
    for index, path in enumerate(paths, 1):
        reasons = Counter()
        seen = set()
        total = 0
        for record in iter_json_array(path):
            total += 1
            if not isinstance(record, dict) or not isinstance(record.get("Contents"), str):
                reasons["invalid_record"] += 1
                continue
            raw = record["Contents"]
            text = normalize_text(raw)
            if not text:
                reasons["empty_after_normalization"] += 1
            elif CONTACT.search(raw) or DIGITS.search(raw):
                reasons["potential_private_identifiers"] += 1
            elif len(text) > 500:
                reasons["oversized_message"] += 1
            elif REPETITION.fullmatch(text):
                reasons["repetition_only"] += 1
            elif len(text) < 3:
                reasons["too_short_to_evaluate"] += 1
            elif text in seen:
                reasons["exact_duplicate_in_channel"] += 1
            else:
                reasons["needs_human_review"] += 1
                seen.add(text)
        out.append({"channel_index": index, "total": total, "counts": dict(reasons)})
    return {"schema_version":1,"status":"review_only_no_training",
            "channels":out,
            "notes":["Candidate counts are not approved training samples.",
                     "Simple patterns cannot reliably detect all sensitive content.",
                     "No text, IDs, or timestamps are written to this report."]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("files",nargs="+",type=Path)
    parser.add_argument("--output",type=Path,default=Path("local_data/persona-eligibility.json"))
    args=parser.parse_args()
    result=audit_eligibility(args.files)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Saved aggregate pretraining audit:",args.output)
    print("No training data generated.")

if __name__=="__main__":
    main()
