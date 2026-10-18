"""Privacy-safe local corpus audit. Never persists message bodies, IDs or samples."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
from .analyze import iter_json_array, normalize_text

MENTION = re.compile(r"<@!?[0-9]+>")
URL = re.compile(r"https?://", re.I)
LONG_NUMBER = re.compile(r"(?<![0-9])[0-9]{8,}(?![0-9])")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
REPEATED = re.compile(r"^(.)\1{5,}$")
def audit(paths: list[Path]) -> dict:
    if not paths or len({p.resolve() for p in paths}) != len(paths):
        raise ValueError("unique source paths required")
    channels = []
    for path in paths:
        counts = Counter()
        values = Counter()
        previous = None
        reverse_sorted = True
        earliest = latest = None
        for row in iter_json_array(path):
            if not isinstance(row, dict) or not isinstance(row.get("Contents"),str) or not isinstance(row.get("Timestamp"),str):
                raise ValueError("invalid row")
            stamp = datetime.fromisoformat(row["Timestamp"].replace("Z","+00:00"))
            if previous is not None and stamp > previous:
                reverse_sorted = False
            if previous is not None and 0 <= (previous-stamp).total_seconds() <= 10:
                counts["adjacent_within_10_sec"] += 1
            previous = stamp
            earliest = stamp if earliest is None or stamp < earliest else earliest
            latest = stamp if latest is None or stamp > latest else latest
            raw = row["Contents"]
            normalized = normalize_text(raw)
            counts["records"] += 1
            counts["nonempty_raw"] += bool(raw.strip())
            counts["nonempty_after_normalize"] += bool(normalized)
            counts["mentions"] += bool(MENTION.search(raw))
            counts["urls"] += bool(URL.search(raw))
            counts["long_numbers"] += bool(LONG_NUMBER.search(raw))
            counts["email_shapes"] += bool(EMAIL.search(raw))
            counts["repeated_character_only"] += bool(REPEATED.fullmatch(normalized))
            if normalized:
                # String keys are transient local memory only and never serialized.
                values[normalized] += 1
        repeated_messages = sum(n for n in values.values() if n > 1)
        channels.append({
            "channel_index":len(channels)+1,
            "record_count":counts["records"],
            "nonempty_raw":counts["nonempty_raw"],
            "nonempty_after_normalize":counts["nonempty_after_normalize"],
            "distinct_normalized_messages":len(values),
            "repeated_normalized_message_occurrences":repeated_messages,
            "adjacent_within_10_sec":counts["adjacent_within_10_sec"],
            "potentially_sensitive_counts":{
                k:counts[k] for k in ("mentions","urls","long_numbers","email_shapes")
            },
            "repeated_character_only":counts["repeated_character_only"],
            "reverse_chronological":reverse_sorted,
            "earliest_date":earliest.date().isoformat() if earliest else None,
            "latest_date":latest.date().isoformat() if latest else None,
        })
    return {
        "schema_version":1,
        "mode":"metadata_only_no_training",
        "channel_count":len(channels),
        "channels":channels,
        "warnings":[
            "Each input is an independent channel; never join cross-channel messages.",
            "All messages originate from one speaker; adjacent messages are not question-answer supervision.",
            "Regex flags are candidates only, not reliable removal of every private or sensitive statement.",
            "No training rights are inferred from possession of a personal export."
        ],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("files",nargs="+",type=Path)
    p.add_argument("--output",type=Path,default=Path("local_data/corpus-audit.json"))
    args=p.parse_args()
    result=audit(args.files)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Saved metadata-only corpus audit:",args.output)

if __name__=="__main__":
    main()
