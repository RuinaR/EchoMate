"""Aggregate-only dry run for a local single-speaker private corpus.

Never creates JSONL, prints content, IDs, text hashes or timestamps.
This report is NOT permission to fine-tune.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from echomate_studio.analyze import iter_json_array, normalize_text
from echomate_studio.persona_split_audit import classify, timestamp_of

def preview(paths, *, validation_fraction=0.1, preserve_two_char=False):
    if not 0 < validation_fraction < 0.5:
        raise ValueError("invalid validation fraction")
    files=[Path(p).resolve() for p in paths]
    if not files or len(set(files)) != len(files):
        raise ValueError("unique input files required")
    times=[]
    for path in files:
        for rec in iter_json_array(path):
            if isinstance(rec,dict):
                stamp=timestamp_of(rec)
                if stamp is not None:
                    times.append(stamp)
    if not times:
        raise ValueError("no valid timestamps")
    times.sort()
    cutoff=times[min(len(times)-1,int(len(times)*(1-validation_fraction)))]
    del times
    def eligible(rec):
        tag,digest=classify(rec)
        if preserve_two_char and tag=="too_short":
            text=normalize_text(rec["Contents"])
            if len(text)==2:
                return "candidate",hashlib.sha256(text.encode("utf-8")).digest()
        return tag,digest

    heldout=set()
    for path in files:
        for rec in iter_json_array(path):
            if not isinstance(rec,dict):
                continue
            t=timestamp_of(rec)
            if t is not None and t>=cutoff:
                tag,digest=eligible(rec)
                if tag=="candidate":
                    heldout.add(digest)
    counts=Counter()
    train_seen=set()
    val_seen=set()
    for path in files:
        for rec in iter_json_array(path):
            if not isinstance(rec,dict) or (t:=timestamp_of(rec)) is None:
                counts["invalid_timestamp"]+=1
                continue
            tag,digest=eligible(rec)
            if tag!="candidate":
                counts[tag]+=1
                continue
            if t>=cutoff:
                if digest in val_seen:
                    counts["validation_duplicate"]+=1
                else:
                    val_seen.add(digest)
                    counts["validation_candidates"]+=1
            elif digest in heldout:
                counts["cross_split_excluded"]+=1
            elif digest in train_seen:
                counts["training_duplicate"]+=1
            else:
                train_seen.add(digest)
                counts["training_candidates"]+=1
    return {
        "status":"aggregate_preview_only_no_training",
        "input_files":len(files),
        "global_chronological_cutoff":True,
        "two_char_option":bool(preserve_two_char),
        "counts":dict(counts),
        "limitations":[
            "Candidates are NOT reviewed or authorized training examples.",
            "Contextual privacy, legal rights, and near-duplicates require separate review.",
            "No texts, timestamps, IDs or hashes are emitted."
        ]
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("files",nargs="+",type=Path)
    parser.add_argument("--preserve-two-char",action="store_true")
    parser.add_argument("--output",type=Path,default=Path("local_data/persona-candidate-preview.json"))
    args=parser.parse_args()
    out=args.output.resolve()
    if "local_data" not in out.parts:
        parser.error("report must stay under local_data")
    if out.exists():
        parser.error("refusing to overwrite an existing local report")
    result=preview(args.files,preserve_two_char=args.preserve_two_char)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Count-only candidate preview:",out)
    print("No corpus created and no private data authorized for training.")

if __name__=="__main__":
    main()
