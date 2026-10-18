"""Privacy-preserving aggregate writing style profile, not model training."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re

from .analyze import iter_json_array, normalize_text

LAUGH = re.compile(r"ㅋ{2,}")
CRY = re.compile(r"[ㅠㅜ]{2,}")
QUESTION = re.compile(r"\?+")
EXCLAIM = re.compile(r"!+")
UNICODE_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")

def build_profile(paths: list[Path], *, half_life_days: int = 365) -> dict:
    if not paths or half_life_days < 1:
        raise ValueError("at least one source and positive half-life required")
    # Channel file is separate; avoid ever storing raw text between iterations.
    stats = []
    newest = None
    seen = set()
    for path in paths:
        if path.resolve() in seen:
            raise ValueError("duplicate input file")
        seen.add(path.resolve())
        count = 0
        latest = None
        for item in iter_json_array(path):
            if not isinstance(item, dict) or not isinstance(item.get("Contents"), str) or not isinstance(item.get("Timestamp"), str):
                raise ValueError("invalid message record")
            ts = datetime.fromisoformat(item["Timestamp"].replace("Z", "+00:00"))
            if latest is None or ts > latest:
                latest = ts
            count += 1
        stats.append((path, count))
        if latest is not None:
            if newest is None:
                newest = latest
            elif (newest.tzinfo is None) != (latest.tzinfo is None):
                raise ValueError("mixed timezone types between files")
            elif latest > newest:
                newest = latest
    sums = Counter()
    counts = Counter()
    for path, _ in stats:
        for item in iter_json_array(path):
            msg = normalize_text(item["Contents"])
            if not msg:
                continue
            ts = datetime.fromisoformat(item["Timestamp"].replace("Z", "+00:00"))
            weight = 2 ** (-max(0, (newest - ts).total_seconds()) / (86400 * half_life_days))
            counts["messages"] += 1
            sums["weight"] += weight
            sums["length"] += weight * len(msg)
            for key, pattern in (("laugh", LAUGH), ("cry", CRY), ("question", QUESTION),
                                 ("exclaim", EXCLAIM), ("unicode_emoji", UNICODE_EMOJI)):
                sums[key] += weight * bool(pattern.search(msg))
    denominator = sums["weight"]
    def ratio(key):
        return round(sums[key] / denominator, 4) if denominator else 0.0
    return {
        "schema_version": 1,
        "source_channel_count": len(paths),
        "source_message_count": sum(n for _, n in stats),
        "text_message_count": counts["messages"],
        "half_life_days": half_life_days,
        "weighted_mean_chars": round(sums["length"] / denominator, 2) if denominator else 0,
        "patterns": {k: ratio(k) for k in ("laugh", "cry", "question", "exclaim", "unicode_emoji")},
        "privacy": "aggregate-only; no source messages or user identifiers",
    }

def profile_to_style(profile: dict) -> str:
    if profile.get("schema_version") != 1:
        raise ValueError("unsupported profile")
    length = profile["weighted_mean_chars"]
    patterns = profile["patterns"]
    fragments = ["자연스러운 한국어 반말 채팅체", "평범하고 담백한 반응이 기본", "대화의 의미와 흐름을 우선하고 없는 사실을 꾸며내지 않기", "질문이나 가벼운 제안에 서비스 상태를 추측하여 화제를 돌리지 않기"]
    if length < 16:
        fragments.append("보통 한 문장, 가능한 짧게. 필요한 설명은 생략하지 않기")
    elif length < 50:
        fragments.append("평소에는 간결한 한두 문장 위주")
    if patterns["laugh"] >= 0.1:
        fragments.append("가벼운 상황에서만 ㅋㅋ 같은 자연스러운 웃음 표현을 가끔 사용")
    if patterns["cry"] >= 0.05:
        fragments.append("상황에 맞을 때 ㅠㅠ 등의 감정 표현 사용")
    if patterns["unicode_emoji"] < 0.05:
        fragments.append("일반 유니코드 이모지는 거의 쓰지 않기. 의도적으로 추가하지 않기")
    return ". ".join(fragments) + "."

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--half-life-days", type=int, default=365)
    parser.add_argument("--output", type=Path, default=Path("local_data/style-profile.json"))
    args = parser.parse_args()
    profile = build_profile(args.files, half_life_days=args.half_life_days)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved aggregate profile to {args.output}")

if __name__ == "__main__":
    main()
