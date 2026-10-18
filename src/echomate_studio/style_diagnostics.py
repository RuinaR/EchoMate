"""Local-only aggregate style diagnostics; never export message text or identifiers."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re

from .analyze import iter_json_array, normalize_text

ENDING = {
    "question": re.compile(r"[?？]+\\s*$"),
    "exclamation": re.compile(r"[!！]+\\s*$"),
    "period": re.compile(r"[.。]+\\s*$"),
    "laughter": re.compile(r"[ㅋㅎ]{2,}\\s*$"),
    "crying": re.compile(r"[ㅠㅜ]{2,}\\s*$"),
    "ellipsis": re.compile(r"(?:…|\\.{2,})\\s*$"),
}
BANDS = ((0, 5), (6, 12), (13, 25), (26, 50), (51, None))


def _bucket(n: int) -> str:
    for low, high in BANDS:
        if n >= low and (high is None or n <= high):
            return f"{low}+" if high is None else f"{low}-{high}"
    raise AssertionError("unreachable")


def diagnostics(paths: list[Path], half_life_days: int = 365) -> dict:
    if not paths or half_life_days <= 0:
        raise ValueError("input files and positive half life required")
    seen = set()
    newest = None
    counts_by_file = []
    for path in paths:
        canonical = path.resolve()
        if canonical in seen:
            raise ValueError("duplicate file")
        seen.add(canonical)
        count = 0
        for item in iter_json_array(path):
            if not isinstance(item, dict) or not isinstance(item.get("Contents"), str) or not isinstance(item.get("Timestamp"), str):
                raise ValueError("invalid message")
            date = datetime.fromisoformat(item["Timestamp"].replace("Z", "+00:00"))
            if newest is None or date > newest:
                newest = date
            count += 1
        counts_by_file.append(count)
    hist = Counter()
    endings = Counter()
    total = 0.0
    messages = 0
    for path in paths:
        for item in iter_json_array(path):
            msg = normalize_text(item["Contents"])
            if not msg:
                continue
            when = datetime.fromisoformat(item["Timestamp"].replace("Z", "+00:00"))
            age_days = max(0, (newest - when).total_seconds()) / 86400
            weight = 2 ** (-age_days / half_life_days)
            total += weight
            messages += 1
            hist[_bucket(len(msg))] += weight
            # Nonexclusive: punctuation and emotional endings can co-occur.
            for label, pattern in ENDING.items():
                endings[label] += weight * bool(pattern.search(msg))
    def ratio(value):
        return round(value / total, 4) if total else 0.0
    return {
        "schema_version": 1,
        "scope": "aggregate_style_only",
        "channel_count": len(paths),
        "source_count": sum(counts_by_file),
        "text_count": messages,
        "half_life_days": half_life_days,
        "length_bands": {(_bucket(low)): ratio(hist[_bucket(low)]) for low, _ in BANDS},
        "ending_rates": {key: ratio(endings[key]) for key in ENDING},
        "privacy": "no raw texts, message IDs, timestamps, samples, or token frequency lists",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--half-life-days", type=int, default=365)
    p.add_argument("--output", type=Path, default=Path("local_data/style-diagnostics.json"))
    args = p.parse_args()
    report = diagnostics(args.files, args.half_life_days)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved aggregate diagnostics: {args.output}")


if __name__ == "__main__":
    main()
