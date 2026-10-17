"""Local metadata-only analysis of single-author Discord message JSON.

Streaming JSON array reader: one channel per input file. No message text is
stored in reports or retained in the per-message analysis buffer.
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
MEDIA_URL = re.compile(r"https?://\S+?(?:\.gif|\.png|\.webp|\.jpe?g|\.mp4)(?:\?\S*)?(?=\s|$)", re.I)
URL = re.compile(r"https?://\S+", re.I)
CHUNK_SIZE = 131072


def normalize_text(text: str) -> str:
    """Filter user mentions and URLs; preserve Unicode emojis and casual spelling."""
    for pattern in (CUSTOM_EMOJI, MENTION, MEDIA_URL, URL):
        text = pattern.sub(" ", text)
    return text.strip()


def iter_json_array(path: Path):
    """Parse a JSON array incrementally without loading the entire array."""
    decoder = json.JSONDecoder()
    with path.open("r", encoding="utf-8-sig") as fh:
        buffer = ""
        pos = 0
        eof = False

        def fill():
            nonlocal buffer, pos, eof
            buffer = buffer[pos:]
            pos = 0
            chunk = fh.read(CHUNK_SIZE)
            if chunk:
                buffer += chunk
            else:
                eof = True

        def skip_ws():
            nonlocal pos
            while True:
                while pos < len(buffer) and buffer[pos].isspace():
                    pos += 1
                if pos < len(buffer) or eof:
                    return
                fill()

        fill()
        skip_ws()
        if pos == len(buffer) or buffer[pos] != "[":
            raise ValueError("expected a top-level JSON array")
        pos += 1
        expect_value = True
        had_item = False
        while True:
            skip_ws()
            if pos == len(buffer) and eof:
                raise ValueError("unterminated JSON array")
            if expect_value:
                if buffer[pos] == "]":
                    if had_item:
                        raise ValueError("trailing comma in JSON array")
                    pos += 1
                    break
                while True:
                    try:
                        value, end = decoder.raw_decode(buffer, pos)
                        pos = end
                        break
                    except json.JSONDecodeError as exc:
                        if eof:
                            raise ValueError(f"invalid JSON array item: {exc.msg}") from exc
                        fill()
                yield value
                had_item = True
                expect_value = False
            else:
                if buffer[pos] == "]":
                    pos += 1
                    break
                if buffer[pos] != ",":
                    raise ValueError("expected ',' or ']' between JSON array items")
                pos += 1
                expect_value = True
        skip_ws()
        if pos < len(buffer) or not eof:
            if buffer[pos:].strip() or fh.read().strip():
                raise ValueError("unexpected content after JSON array")


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def analyze_file(path: Path, *, group_gap_seconds: int = 10, half_life_days: int = 365) -> dict:
    if group_gap_seconds < 0 or half_life_days <= 0:
        raise ValueError("gap must be >= 0 and half-life must be > 0")
    ids = set()
    valid = []  # (timestamp, message_length): no raw contents retained.
    duplicate = empty = custom = media = total = 0
    for i, record in enumerate(iter_json_array(path)):
        total += 1
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
        timestamp = record["Timestamp"]
        if not isinstance(timestamp, str):
            raise ValueError(f"invalid Timestamp at index {i}")
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        custom += bool(CUSTOM_EMOJI.search(raw))
        media += bool(record["Attachments"] or MEDIA_URL.search(raw))
        cleaned_len = len(normalize_text(raw))
        if cleaned_len == 0:
            empty += 1
        valid.append((dt, cleaned_len))
    if valid:
        aware = valid[0][0].tzinfo is not None
        if any((dt.tzinfo is not None) != aware for dt, _ in valid):
            raise ValueError("mixed timezone-aware and naive timestamps in one file")
    valid.sort(key=lambda item: item[0])
    lengths = [n for _, n in valid if n]
    latest = valid[-1][0] if valid else None
    total_weight = weighted_chars = 0.0
    for dt, length in valid:
        if not length:
            continue
        days = (latest - dt).total_seconds() / 86400
        weight = 2 ** (-days / half_life_days)
        total_weight += weight
        weighted_chars += length * weight
    groups = 0
    previous = None
    for dt, length in valid:
        if not length:
            previous = None
            continue
        if previous is None or (dt - previous).total_seconds() > group_gap_seconds:
            groups += 1
        previous = dt
    return {
        "source_label": path.stem,
        "source_sha256": file_hash(path),
        "total_records": total,
        "unique_records": len(valid),
        "duplicate_ids_within_file": duplicate,
        "text_records_after_filter": len(lengths),
        "empty_or_filtered_records": empty,
        "messages_with_custom_emoji": custom,
        "messages_with_attachments_or_media_links": media,
        "earliest_timestamp": valid[0][0].isoformat() if valid else None,
        "latest_timestamp": latest.isoformat() if latest else None,
        "median_length": statistics.median(lengths) if lengths else 0,
        "candidate_consecutive_groups": groups,
        "group_gap_seconds": group_gap_seconds,
        "half_life_days": half_life_days,
        "recency_weighted_mean_length": round(weighted_chars / total_weight, 3) if total_weight else 0,
        "caveat": "No other speakers; consecutive groups are hypotheses, not reconstructed conversations.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local JSON channel metadata analyzer")
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
