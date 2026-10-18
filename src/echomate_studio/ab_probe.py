"""Run repeatable warm/cold comparisons; diagnostic only, no automatic quality claims."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import statistics
import time
from .conversation import generate
from .reply_quality import inspect_reply
from .style_profile import profile_to_style


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model", default="qwen3.5:9b-q4_K_M")
    p.add_argument("--profile", type=Path, required=True)
    p.add_argument("--rounds", type=int, default=2)
    p.add_argument("--output", type=Path, default=Path("local_data/ab-results.json"))
    args=p.parse_args()
    if not 1 <= args.rounds <= 5:
        p.error("--rounds must be 1..5")
    profile=profile_to_style(json.loads(args.profile.read_text(encoding="utf-8")))
    prompts=["오늘 메이플 할래?", "오늘 보스 몇 시에 갈까?", "아이고 힘들다", "ㅋㅋㅋㅋ"]
    variants=[("baseline","짧고 자연스러운 한국어 채팅체, 과한 존댓말이나 장문은 피함"),
              ("profile",profile)]
    results=[]
    for repetition in range(args.rounds):
        for idx, question in enumerate(prompts):
            # Alternate which variant goes first to reduce model warm-up bias.
            ordered=variants if (repetition+idx)%2==0 else list(reversed(variants))
            for name,style in ordered:
                start=time.perf_counter()
                try:
                    answer=generate([{"role":"user","content":question}],model=args.model,style=style)
                    error=None
                except Exception as exc:
                    answer=""
                    error=type(exc).__name__
                elapsed=round(time.perf_counter()-start,3)
                results.append({"round":repetition+1,"prompt":question,"variant":name,
                                "reply":answer,"seconds":elapsed,"error":error,"quality_flags":inspect_reply(question,answer) if not error else ["generation_error"]})
                print(f"{name} | {question} | {elapsed:.2f}s | {answer or error}")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({"model":args.model,"results":results},
                       ensure_ascii=False,indent=2),encoding="utf-8")
    for name,_ in variants:
        times=[r["seconds"] for r in results if r["variant"]==name and not r["error"]]
        if times:
            print(f"{name}: median {statistics.median(times):.2f}s")
    print(f"saved {args.output}")


if __name__=="__main__":
    main()
