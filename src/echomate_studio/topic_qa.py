"""Synthetic, privacy-safe live Ollama evaluation of topic continuity."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from .dialogue_state import Turn
from .topic_assessor import assess_reply_topic

AT = datetime(2026, 10, 18, tzinfo=timezone.utc)
CASES = (
    ("boss_time_reply", "메이플 보스 몇 시로 할까?", "9시쯤 어때?", True, True),
    ("boss_time_change", "9시쯤 어때?", "10시로 바꾸자", True, True),
    ("topic_change", "보스는 9시 어때?", "근데 오늘 점심 뭐 먹었어?", True, False),
    ("same_game_followup", "오늘 사냥 어디서 할까?", "그럼 아르카나 어때?", True, True),
    ("other_person_reply", "오늘 보스 갈래?", "몇 시에?", False, False),
    ("unrelated_brief", "메이플 하러 가자", "ㅇㅋ", True, True),
)

def evaluate(*, model="gemma3:12b", judge=assess_reply_topic):
    results=[]
    for case_id, bot_said, human_said, to_bot, expected in CASES:
        turns=[
            Turn(f"{case_id}_b","bot",bot_said,AT,is_bot=True),
            Turn(f"{case_id}_h","human",human_said,AT,
                 reply_to=f"{case_id}_b" if to_bot else None),
        ]
        start=time.perf_counter()
        try:
            result=judge(turns,model=model)
            error=None
        except Exception as exc:
            result=False
            error=type(exc).__name__
        results.append({"case":case_id,"expected":expected,"actual":result,
                        "correct":result==expected and error is None,
                        "seconds":round(time.perf_counter()-start,3),
                        "error":error})
    return results

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",default="gemma3:12b")
    p.add_argument("--output",type=Path,default=Path("local_data/topic-qa.json"))
    args=p.parse_args()
    results=evaluate(model=args.model)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({"model":args.model,"results":results},ensure_ascii=False,indent=2),encoding="utf-8")
    for item in results:
        print(f"{item['case']}: expected={item['expected']} got={item['actual']} correct={item['correct']} {item['seconds']}s")
    print("Correct:",sum(x["correct"] for x in results),"/",len(results))
    print("Saved:",args.output)

if __name__=="__main__":
    main()
