"""Build a private aggregate dashboard without printing generated text."""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import statistics

from persona_experiments import private_path, write_json


def summarize(report):
    groups = defaultdict(list)
    for row in report["results"]:
        groups[row["variant"]].append(row)
    return {name: {
        "cases": len(rows),
        "mean_chars": round(statistics.mean(r["chars"] for r in rows), 1),
        "mean_seconds": round(statistics.mean(r["seconds"] for r in rows), 2),
        "ended": sum(r["ended"] for r in rows),
        "formal_markers": sum(r["formal_marker"] for r in rows),
        "exact_train_matches": sum(r["exact_train_match"] for r in rows),
        "long_train_substrings": sum(r["long_train_substring"] for r in rows),
    } for name, rows in groups.items()}


def render_blind(path):
    path = private_path(path)
    rows = json.loads(path.read_text(encoding="utf-8"))
    groups = defaultdict(list)
    for row in rows:
        groups[row["id"].split("-")[0]].append(row)
    lines = ["# 블라인드 대화 평가", "", "키 파일은 평가 후에 확인하세요. 원문/응답은 로컬에만 유지하세요.",
        "각 항목은 1(나쁨)~5(좋음). privacy는 개인정보를 노출하지 않을수록 높은 점수입니다.",
        "개인 말투 유사성은 본인의 판단이 필요합니다. 무차이/둘 다 문제 선택도 가능합니다.", ""]
    def fenced(value):
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, indent=2)
        # Model text stays inert even if it contains Markdown links or fences.
        fence = "`" * max(3, max((len(x) for x in re.findall(r"`+", value)), default=0)+1)
        return [fence+"text", value, fence]
    for case, options in sorted(groups.items()):
        lines += ["## 사례 " + case, "", *fenced(options[0]["prompt"]), ""]
        for row in options:
            lines += ["### 응답 " + row["id"], "", *fenced(row["response"]), "",
                "말투 / 길이 / 한국어 / 문맥 / 사실성 / 개인정보 / 봇 적합성: __ / __ / __ / __ / __ / __ / __", ""]
        lines += ["선호 응답 ID(또는 무차이/둘 다 문제): __", "이유: __", ""]
    output = path.with_suffix(".md")
    if output.exists():
        raise FileExistsError("Preserve existing human ratings; choose a new review file")
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", required=True, type=Path)
    p.add_argument("--blind-file", type=Path)
    args = p.parse_args()
    folder = private_path(args.directory)
    runs = []
    for path in sorted(folder.glob("**/progress.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        runs.append({"id": path.parent.relative_to(folder).as_posix(),
            **{k: data[k] for k in ("status", "step", "initial_loss", "best_loss",
                                    "best_adapter", "peak_allocated_mib", "elapsed_seconds")}})
    evaluations = {}
    for path in sorted(folder.glob("**/*-generation.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        evaluations[path.relative_to(folder).as_posix()] = summarize(data)
    write_json(folder/"dashboard.json", {"runs": runs, "evaluations": evaluations,
        "warning": "Development data and heuristic signals only. Human review pending."})
    lines = ["# 로컬 ML 실험 대시보드", "", "개발 지표와 휴리스틱이며 사람 평가를 대체하지 않음.", "",
             "|실험|상태|단계|초기 loss|best loss|peak MiB|",
             "|---|---|---:|---:|---:|---:|"]
    for r in runs:
        lines.append("|{id}|{status}|{step}|{initial_loss:.4f}|{best_loss}|{peak_allocated_mib}|".format(**r))
    for name, groups in evaluations.items():
        lines += ["", "## " + name, "", "|조건|사례|평균 글자|정상 종료|격식 힌트|긴 원문 포함|",
                  "|---|---:|---:|---:|---:|---:|"]
        for variant, row in groups.items():
            lines.append("|%s|%d|%.1f|%d|%d|%d|" % (variant, row["cases"], row["mean_chars"],
                row["ended"], row["formal_markers"], row["long_train_substrings"]))
    (folder/"dashboard.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    if args.blind_file:
        render_blind(args.blind_file)
    print(json.dumps({"runs": runs, "evaluations": evaluations}, ensure_ascii=False))


if __name__ == "__main__":
    main()
