"""Multi-turn contextual grounding evaluation with known expected facts.

No real Discord messages are required; all fixtures are synthetic.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import time
from .conversation import generate
from .style_profile import profile_to_style

SCENARIOS = (
    {"id": "unknown_meeting_time", "context": [
        {"role": "user", "content": "아까 몇 시에 만나기로 했지?"}],
     "expected": "시간이 제공되지 않음", "unknown_time": True},
    {"id": "known_meeting_time", "context": [
        {"role": "user", "content": "오늘 9시에 보스 가자"},
        {"role": "assistant", "content": "9시 좋아"},
        {"role": "user", "content": "아까 몇 시로 했더라?"}],
     "expected": "9시", "must_contain": "9시"},
    {"id": "change_of_plans", "context": [
        {"role": "user", "content": "오늘 9시에 보스 가자"},
        {"role": "assistant", "content": "오케이"},
        {"role": "user", "content": "아니다 10시로 바꾸자"},
        {"role": "assistant", "content": "알겠어"},
        {"role": "user", "content": "몇 시에 가기로 했어?"}],
     "expected": "10시(변경 후)", "must_contain": "10시"},
    {"id": "plain_laughter", "context": [
        {"role": "user", "content": "ㅋㅋㅋㅋ"}],
     "expected": "짧은 한국어 맞장구 또는 침묵"},
)

def quality_hints(scenario: dict, reply: str) -> list[str]:
    """Only heuristic flags; they are not a definitive judgment."""
    flags = []
    if not reply.strip():
        return ["empty_reply"]
    if scenario.get("must_contain") and scenario["must_contain"] not in reply:
        flags.append("missing_known_fact")
    if scenario.get("unknown_time") and re.search(r"(?:오전|오후|저녁|새벽)?\s*(?:[0-9]{1,2}|[한두세네다섯여섯일곱여덟아홉열])\s*시", reply):
        flags.append("fabricated_time_candidate")
    if re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", reply):
        flags.append("hanzi_present")
    return flags

def compare(models: list[str], profile: dict, *, generate_fn=generate) -> list[dict]:
    if len(models) != 2 or models[0] == models[1]:
        raise ValueError("two distinct models required")
    style = profile_to_style(profile)
    rows = []
    for i, scenario in enumerate(SCENARIOS):
        for model in (models if i % 2 == 0 else models[::-1]):
            started = time.perf_counter()
            try:
                answer = generate_fn(scenario["context"], model=model, style=style)
                error = None
            except Exception as exc:
                answer = ""
                error = type(exc).__name__
            rows.append({
                "scenario": scenario["id"], "expected": scenario["expected"],
                "model": model, "reply": answer, "elapsed_seconds": round(time.perf_counter()-started,3),
                "error": error, "quality_flags": quality_hints(scenario, answer) if not error else ["generation_error"]
            })
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs=2, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("local_data/context-comparison.json"))
    args = parser.parse_args()
    rows = compare(args.models, json.loads(args.profile.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"results": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in rows:
        print(f"{row['scenario']} | {row['model']} | {row['elapsed_seconds']:.2f}s | {row['reply'] or row['error']} | flags={row['quality_flags']}")
    print(f"Saved: {args.output}")

if __name__ == "__main__":
    main()
