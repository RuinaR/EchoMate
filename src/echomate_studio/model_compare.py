"""Compare two local Ollama models with identical prompts and alternating order."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import statistics
import time
from .conversation import generate
from .reply_quality import inspect_reply
from .style_profile import profile_to_style

QUESTIONS = ("오늘 메이플 할래?", "오늘 보스 몇 시에 갈까?",
             "아이고 힘들다", "ㅋㅋㅋㅋ", "아까 몇 시에 만나기로 했지?")


def run_comparison(models: list[str], profile: dict, rounds: int = 2,
                   generate_fn=generate) -> list[dict]:
    if len(models) != 2 or models[0] == models[1] or not 1 <= rounds <= 5:
        raise ValueError("provide two distinct models and 1..5 rounds")
    style = profile_to_style(profile)
    results = []
    for repetition in range(rounds):
        for idx, prompt in enumerate(QUESTIONS):
            order = models if (repetition + idx) % 2 == 0 else models[::-1]
            for model in order:
                start = time.perf_counter()
                try:
                    reply = generate_fn([{"role": "user", "content": prompt}],
                                        model=model, style=style)
                    error = None
                except Exception as exc:
                    reply = ""
                    error = type(exc).__name__
                results.append({
                    "model": model, "round": repetition + 1, "prompt": prompt,
                    "reply": reply, "seconds": round(time.perf_counter() - start, 3),
                    "error": error,
                    "quality_flags": inspect_reply(prompt, reply) if error is None else ["generation_error"],
                })
    return results


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs=2, required=True)
    p.add_argument("--profile", type=Path, required=True)
    p.add_argument("--rounds", type=int, default=2)
    p.add_argument("--output", type=Path, default=Path("local_data/model-comparison.json"))
    args = p.parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    results = run_comparison(args.models, profile, args.rounds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"models": args.models, "results": results},
                           ensure_ascii=False, indent=2), encoding="utf-8")
    for row in results:
        print(f"{row['model']} | {row['prompt']} | {row['seconds']:.2f}s | {row['reply'] or row['error']}")
    for model in args.models:
        times = [r["seconds"] for r in results if r["model"] == model and not r["error"]]
        if times:
            print(f"{model} median: {statistics.median(times):.2f}s")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
