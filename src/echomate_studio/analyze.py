"""Local metadata-only analysis of single-author Discord message JSON.

No raw message text, mentions, or attachment URLs in reports.
Each input file is treated as a distinct channel.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import statistics

CUSTOM_EMOJI = re.compile(r"<a?:[A-Za-z0-9_]+:\d+>")
MENTION = re.compile(r"<[@#&][!&]?\d+>")
MEDIA_URL = re.compile(r"https?://\S+(?:\.gif|\.png|\.webp|\.jpe?g|\.mp4)(?:\?\S*)?", re.I)
URL = re.compile(r"https?://\S+", re.I)


def normalize_text(text: str) -> str:
    """Remove links/mentions/custom emoji; preserve Korean colloquial style and Unicode emoji."""
    for pattern in (CUSTOM_EMOJI, MENTION, MEDIA_URL, URL):
        text = pattern.sub(" ", text)
    return text.strip()


def analyze_file(path: Path, *, group_gap_seconds: int = 10, half_life_days: int = 365) -> dict:
    if group_gap_seconds < 0 or half_life_days <= 0:
        raise ValueError("gap must be >= 0 and half-life must be > 0")
    with path.open(encoding="utf-8") as f:
        records = json.load(f)
    if not isinstance(records, list):
        raise ValueError("expected a top-level JSON array")
    ids = set()
    valid = []
    duplicate = empty = custom = media = 0
    for i, record in enumerate(records):
        if not isinstance(record, dict) or not all(k in record for k in ("ID", "Timestamp", "Contents", "Attachments")):
            raise ValueError(f"invalid record at index {i}")
        mid = str(record["ID"])
        if mid in ids:
            duplicate += 1
            continue
        ids.add(mid)
        raw = record["Contents"]
        if not isinstance(raw, str):
            raise ValueError(f"invalid Contents at index {i}")
        dt = datetime.fromisoformat(record["Timestamp"].replace("Z", "+00:00"))
        custom += bool(CUSTOM_EMOJI.search(raw))
        media += bool(record["Attachments"] or MEDIA_URL.search(raw))
        cleaned = normalize_text(raw)
        if not cleaned:
            empty += 1
        valid.append((dt, cleaned))
    valid.sort(key=lambda p: p[0])
    lengths = [len(txt) for _, txt in valid if txt]
    latest = max((dt for dt, _ in valid), default=None)
    total_weight = weighted_chars = 0.0
    for dt, txt in valid:
        if not txt or latest is None:
            continue
        days = (latest - dt).total_seconds() / 86400
        weight = 2 ** (-days / half_life_days)
        total_weight += weight
        weighted_chars += len(txt) * weight
    groups = 0
    previous = None
    for dt, txt in valid:
        if not txt:
            previous = None
            continue
        if previous is None or (dt - previous).total_seconds() > group_gap_seconds:
            groups += 1
        previous = dt
    return {
        "source_label": path.stem,
        "source_sha256": sha256(path.read_bytes()).hexdigest(),
        "total_records": len(records),
        "unique_records": len(valid),
        "duplicate_ids_within_file": duplicate,
        "text_records_after_filter": len(lengths),
        "empty_or_filtered_records": empty,
        "messages_with_custom_emoji": custom,
        "messages_with_attachments_or_media_links": media,
        "earliest_timestamp": min((t for t, _ in valid), default=None).isoformat() if valid else None,
        "latest_timestamp": latest.isoformat() if latest else None,
        "median_length": statistics.median(lengths) if lengths else 0,
        "candidate_consecutive_groups": groups,
        "group_gap_seconds": group_gap_seconds,
        "half_life_days": half_life_days,
        "recency_weighted_mean_length": round(weighted_chars / total_weight, 3) if total_weight else 0,
        "caveat": "No other speakers; consecutive groups are hypotheses, not reconstructed conversations.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Discord own-message metadata analyzer")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--group-gap-seconds", type=int, default=10)
    parser.add_argument("--half-life-days", type=int, default=365)
    parser.add_argument("--output", type=Path, help="Aggregate report JSON path")
    args = parser.parse_args()
    reports = [analyze_file(p, group_gap_seconds=args.group_gap_seconds, half_life_days=args.half_life_days) for p in args.files]
    payload = json.dumps({"channels": reports}, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
