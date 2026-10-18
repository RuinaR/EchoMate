"""Local-only approved single-speaker LM corpus builder.

Requires two deliberate acknowledgements. Nothing goes to GitHub or APIs.
Outputs private JSONL: protect its contents as confidential.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from collections import Counter
from .analyze import iter_json_array, normalize_text
from .persona_split_audit import timestamp_of, classify

def build(paths, output_dir, *, rights_confirmed=False, privacy_reviewed=False,
          validation_fraction=0.1):
    if not (rights_confirmed and privacy_reviewed):
        raise PermissionError("Confirm data-use rights and private-content review first")
    if not 0 < validation_fraction < 0.5:
        raise ValueError("invalid validation fraction")
    paths=[Path(p).resolve() for p in paths]
    if not paths or len(set(paths))!=len(paths):
        raise ValueError("unique input files required")
    output_dir=Path(output_dir).resolve()
    if not (output_dir.name=="local_data" or "local_data" in output_dir.parts):
        raise ValueError("output must be inside ignored local_data directory")
    for p in paths:
        if p==output_dir or output_dir in p.parents:
            raise ValueError("input must be outside output folder")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Refusing to overwrite existing private corpus output")
    # Global UTC cutoff, not independent per-channel cutoffs:
    # no older/younger cross-channel time interleaving across the split.
    timestamps=[]
    for p in paths:
        for record in iter_json_array(p):
            if isinstance(record,dict):
                stamp=timestamp_of(record)
                if stamp is not None:
                    timestamps.append(stamp)
    if not timestamps:
        raise ValueError("no valid timestamps")
    timestamps.sort()
    cutoff=timestamps[min(len(timestamps)-1,int(len(timestamps)*(1-validation_fraction)))]
    del timestamps
    # Always prioritize validation membership: remove any text present in held-out
    # time spans from training, including duplicates across channels.
    heldout=set()
    for p in paths:
        for r in iter_json_array(p):
            if not isinstance(r,dict) or (t:=timestamp_of(r)) is None or t<cutoff:
                continue
            tag,digest=classify(r)
            if tag=="candidate":
                heldout.add(digest)
    output_dir.mkdir(parents=True,exist_ok=True)
    train_path=output_dir/"persona-train.jsonl"
    val_path=output_dir/"persona-validation.jsonl"
    counts=Counter()
    train_seen=set()
    val_seen=set()
    try:
        with train_path.open("w",encoding="utf-8") as train, val_path.open("w",encoding="utf-8") as val:
            for p in paths:
                for r in iter_json_array(p):
                    if not isinstance(r,dict) or (t:=timestamp_of(r)) is None:
                        counts["invalid_timestamp"]+=1
                        continue
                    category,digest=classify(r)
                    if category!="candidate":
                        counts[category]+=1
                        continue
                    is_validation=t>=cutoff
                    if is_validation:
                        if digest in val_seen:
                            counts["validation_duplicate"]+=1
                            continue
                        val_seen.add(digest)
                        val.write(json.dumps({"text":normalize_text(r["Contents"])},ensure_ascii=False)+"\n")
                        counts["validation"]+=1
                    else:
                        if digest in heldout:
                            counts["cross_split_excluded"]+=1
                            continue
                        if digest in train_seen:
                            counts["training_duplicate"]+=1
                            continue
                        train_seen.add(digest)
                        train.write(json.dumps({"text":normalize_text(r["Contents"])},ensure_ascii=False)+"\n")
                        counts["training"]+=1
    except BaseException:
        train_path.unlink(missing_ok=True)
        val_path.unlink(missing_ok=True)
        raise
    # No raw strings, hashes, IDs or timestamp values in the report.
    report={"status":"built_local_only","counts":dict(counts),
            "validation_overlap_removed_from_training":True,
            "global_chronological_cutoff":True,
            "objective":"single_speaker_language_modeling_not_chat_sft",
            "limits":["Filtered text can still contain private context",
                      "Rights and privacy flags represent user review, not proof of legal permission"]}
    (output_dir/"persona-build-report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("files",nargs="+",type=Path)
    ap.add_argument("--output-dir",type=Path,default=Path("local_data/persona-dataset"))
    ap.add_argument("--confirm-rights",action="store_true")
    ap.add_argument("--confirm-privacy-review",action="store_true")
    args=ap.parse_args()
    result=build(args.files,args.output_dir,rights_confirmed=args.confirm_rights,
                 privacy_reviewed=args.confirm_privacy_review)
    print("Local-only corpus built. Candidate counts:",result["counts"])
    print("Keep the JSONL files private. Do not commit them.")

if __name__=="__main__":
    main()
