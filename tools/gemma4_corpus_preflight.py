"""Private JSONL train/validation preflight: counts only, never prints content."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from collections import Counter
from difflib import SequenceMatcher

CONTACT = re.compile(r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|01[016789][ -]?\d{3,4}[ -]?\d{4}|(?<!\d)\d{8,}(?!\d))")
URL = re.compile(r"https?://\S+", re.I)

def normalize(s):
    return " ".join(s.casefold().split())

def read_unique(path, limit=300000):
    rows, counts, seen = [], Counter(), set()
    with Path(path).open(encoding="utf-8") as file:
        for i, line in enumerate(file):
            if i >= limit: raise ValueError("row limit exceeded")
            obj = json.loads(line)
            if not isinstance(obj,dict) or set(obj) != {"text"} or not isinstance(obj["text"],str):
                raise ValueError("invalid JSONL schema")
            s = normalize(obj["text"])
            counts["total"] += 1
            if not s: counts["empty"] += 1; continue
            if CONTACT.search(s) or URL.search(s): counts["identifier_or_url_hint"] += 1
            h = hashlib.sha256(s.encode("utf-8")).digest()
            if h in seen: counts["internal_duplicates"] += 1; continue
            seen.add(h)
            rows.append((h, s))
    return rows, counts

def audit(train, validation):
    train, validation = Path(train).resolve(), Path(validation).resolve()
    if train == validation or not train.is_file() or not validation.is_file():
        raise ValueError("separate existing files required")
    if any("local_data" not in p.parts for p in (train, validation)):
        raise ValueError("private paths required")
    a, ca = read_unique(train)
    b, cb = read_unique(validation)
    ah = {h for h,_ in a}
    overlap = sum(h in ah for h,_ in b)
    # Approximate near-duplicate detection with bounded, length-bucketed comparison.
    # Never claim near-duplicate detection exhaustive.
    bucket = {}
    for _,s in a:
        key = (len(s)//8, s[:12])
        bucket.setdefault(key, []).append(s)
    near = 0
    for h,s in b:
        if h in ah: continue
        candidates = []
        for delta in (-1,0,1):
            candidates.extend(bucket.get((len(s)//8+delta, s[:12]), [])[:128])
        if any(SequenceMatcher(None,s,t,autojunk=False).ratio()>=0.9 for t in candidates):
            near += 1
    blocked = overlap>0 or ca["identifier_or_url_hint"]>0 or cb["identifier_or_url_hint"]>0 or near>0 or not a or not b
    return {"status":"review_required" if blocked else "heuristic_preflight_clear",
        "training":dict(ca),"validation":dict(cb),
        "exact_cross_split_overlap":overlap,"approx_near_overlap":near,
        "not_a_training_authorization":True,
        "limitations":["No chronology or source provenance inferred from JSONL.",
                       "Identifiers and near duplicates are heuristic; third-party privacy and semantic leakage require human review.",
                       "A clear report never authorizes model training."]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--train",type=Path,default=Path("local_data/persona-dataset/persona-train.jsonl"))
    p.add_argument("--validation",type=Path,default=Path("local_data/persona-dataset/persona-validation.jsonl"))
    p.add_argument("--output",type=Path,default=Path("local_data/gemma4-corpus-preflight.json"))
    x=p.parse_args()
    if "local_data" not in x.output.resolve().parts:p.error("private output required")
    report=audit(x.train,x.validation)
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Corpus preflight:",report["status"],"report:",x.output)
    return 0 if report["status"]=="heuristic_preflight_clear" else 2

if __name__=="__main__":raise SystemExit(main())
