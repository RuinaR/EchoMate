"""Privacy-safe chronological split audit for single-speaker Discord exports.

Writes counts only. Does NOT export messages, hashes, samples or training files.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from .analyze import iter_json_array, normalize_text
from .persona_eligibility import CONTACT, DIGITS, REPETITION

def timestamp_of(record):
    value=record.get("Timestamp")
    if not isinstance(value,str):
        return None
    try:
        ts=datetime.fromisoformat(value.replace("Z","+00:00"))
        if ts.tzinfo is None:
            ts=ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    except ValueError:
        return None

def classify(record):
    if not isinstance(record,dict) or not isinstance(record.get("Contents"),str):
        return "invalid_record", None
    original=record["Contents"]
    text=normalize_text(original)
    if not text:
        return "empty", None
    if CONTACT.search(original) or DIGITS.search(original):
        return "identifier_hint", None
    if len(text)>500:
        return "too_long", None
    if REPETITION.fullmatch(text):
        return "single_character_repetition", None
    if len(text)<3:
        return "too_short", None
    return "candidate",hashlib.sha256(text.encode("utf-8")).digest()

def audit(paths,*,validation_fraction=0.1):
    if not 0<validation_fraction<0.5:
        raise ValueError("validation fraction must be between 0 and 0.5")
    if not paths or len({Path(p).resolve() for p in paths})!=len(paths):
        raise ValueError("unique file paths required")
    # Only timestamps and ephemeral digests retained in RAM, never written.
    timelines=[]
    for p in paths:
        times=[]
        for r in iter_json_array(Path(p)):
            if isinstance(r,dict):
                ts=timestamp_of(r)
                if ts is not None:
                    times.append(ts)
        if not times:
            raise ValueError("input contains no parseable timestamps")
        times.sort()
        cutoff=times[min(len(times)-1,int(len(times)*(1-validation_fraction)))]
        timelines.append(cutoff)
    counts=Counter()
    train_hashes=set()
    validation_hashes=set()
    for p,cutoff in zip(paths,timelines):
        for rec in iter_json_array(Path(p)):
            ts=timestamp_of(rec) if isinstance(rec,dict) else None
            if ts is None:
                counts["invalid_timestamp"]+=1
                continue
            category,digest=classify(rec)
            counts[category]+=1
            if digest is None:
                continue
            if ts<cutoff:
                if digest in train_hashes:
                    counts["training_duplicate"]+=1
                else:
                    train_hashes.add(digest)
                    counts["training_unique_candidates"]+=1
            else:
                if digest in validation_hashes:
                    counts["validation_duplicate"]+=1
                else:
                    validation_hashes.add(digest)
                    counts["validation_unique_candidates"]+=1
    overlap=len(train_hashes & validation_hashes)
    return {"status":"audit_only_no_training","schema_version":1,
            "input_files":len(paths),"validation_fraction_target":validation_fraction,
            "counts":dict(counts),"cross_split_duplicate_unique_texts":overlap,
            "validation_unique_after_overlap_removal":len(validation_hashes-train_hashes),
            "notes":["No user text, hashes, IDs, timestamps or samples are saved.",
                     "Per-file time cutoff; exact validation ratio may differ due to repeated timestamps.",
                     "These are unapproved candidates; human privacy review and data-rights clearance still required."]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("files",nargs="+",type=Path)
    parser.add_argument("--output",type=Path,default=Path("local_data/persona-split-audit.json"))
    args=parser.parse_args()
    output=audit(args.files)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Local chronological split audit saved:",args.output)
    print("No training samples generated.")

if __name__=="__main__":
    main()
