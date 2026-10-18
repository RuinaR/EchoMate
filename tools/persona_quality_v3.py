"""Private, offline factorial quality evaluation. No training or promotion.

Weights x policy are compared separately from an aggregate-style prior.
All references/labels remain outside model prompts. Holdout is frozen at prepare.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import statistics
import subprocess
import sys
import time

import persona_experiments as exp
from evaluate_persona_candidate import POLICY_V2
from persona_quality_cases import PILOT, HOLDOUT

sys.path.insert(0, str(exp.ROOT/"src"))
from echomate_studio.response_policy import aggregate_style, build_v3_messages, plan_response, text_features
from echomate_studio.context_assessor import _SYSTEM as ASSESSOR_SYSTEM, parse_assessment
from echomate_studio.participation import ContextAssessment, ParticipationPolicy, decide


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def prepare(root):
    root = exp.private_path(root)
    if (root/"plan.json").exists():
        raise FileExistsError("Preserve existing frozen plan")
    train = exp.PRIVATE/"reviewed/train.jsonl"
    validation = exp.PRIVATE/"reviewed/validation.jsonl"
    profile = aggregate_style(exp.iter_text(train))
    exp.write_json(root/"style-train.json", profile)
    exp.write_json(root/"style-validation-audit.json", aggregate_style(exp.iter_text(validation)))
    legacy = []
    for path in (exp.PRIVATE/"persona-adapters").glob("gemma4-full-*/summary.json"):
        if json.loads(path.read_text())["steps_completed"] == 2500:
            legacy.append(path.parent/"best")
    if len(legacy) != 1:
        raise ValueError("One legacy 2500 adapter required")
    paths = {"legacy": legacy[0],
        "r8_60": exp.PRIVATE/"experiments/style-v2/pilot-r8-qkvo/step-00060",
        "r8_120": exp.PRIVATE/"experiments/style-v3/refine-r8/step-00120"}
    for path in paths.values():
        exp.private_path(path)
        if not (path/"adapter_config.json").is_file():
            raise FileNotFoundError("Required preserved adapter unavailable")
    plan = dict(seed=73129, model=exp.MODEL, pilot_sha256=fingerprint(PILOT),
        holdout_sha256=fingerprint(HOLDOUT), train_sha256=exp.digest(train),
        validation_sha256=exp.digest(validation), style_sha256=exp.digest(root/"style-train.json"),
        adapters={k: str(v) for k,v in paths.items()},
        adapter_hashes={k: exp.digest(v/"adapter_model.safetensors") for k,v in paths.items()},
        hypotheses=[
            "v3 reduces unnecessary questions/assistant preambles on brief chat while preserving technical reference coverage.",
            "Fixed train-only lexical/ending prior may help individual style; subjective similarity requires human review.",
            "Hybrid uses rank8 for casual replies and base for technical/step requests, without new optimization steps."],
        acceptance=["No increased capability/private-extraction failures against same-weight v2.",
                    "Technical/step coverage signals must not decrease to obtain shorter replies.",
                    "No ranking by loss or unconditional stylistic distance; no final model confirmation."],
        further_training="Not justified on unchanged independent style targets without approved response-context supervision.",
        human_review="pending", production_approved=False)
    exp.write_json(root/"plan.json", plan)
    print("Prepared frozen pilot/holdout, aggregate-only style prior and existing adapter hashes.")


@contextmanager
def activate(model, name):
    if name == "base":
        with model.disable_adapter():
            yield
    else:
        model.set_adapter("default" if name == "r8_60" else name, inference_mode=True)
        yield


def encode(tokenizer, messages):
    return exp.token_list(tokenizer.apply_chat_template(messages, tokenize=True,
        add_generation_prompt=True, enable_thinking=False))


def generate(tokenizer, model, messages, budget, seed):
    import torch
    from transformers import set_seed
    set_seed(seed)
    ids = torch.tensor([encode(tokenizer, messages)], device="cuda")
    end = tokenizer.convert_tokens_to_ids("<turn|>")
    start = time.monotonic()
    with torch.inference_mode():
        output = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
            max_new_tokens=budget, do_sample=False, use_cache=True,
            eos_token_id=[tokenizer.eos_token_id, end], pad_token_id=tokenizer.eos_token_id)
    tokens = output[0, ids.shape[1]:].tolist()
    text = tokenizer.decode(tokens, skip_special_tokens=True).strip()
    return dict(response=text, tokens=len(tokens), input_tokens=ids.shape[1],
        ended=bool(tokens and tokens[-1] in (tokenizer.eos_token_id, end)),
        seconds=round(time.monotonic()-start,3))


def load(plan):
    tokenizer, model = exp.load_model(exp.private_path(plan["adapters"]["r8_60"]))
    for name in ("legacy", "r8_120"):
        model.load_adapter(str(exp.private_path(plan["adapters"][name])),
                           adapter_name=name, is_trainable=False)
    model.eval()
    return tokenizer, model


def gpu_audit(tokenizer, model):
    """Actual shifted CE equality and activation check, using synthetic text only."""
    import torch
    from torch.nn import functional as F
    masks = []
    with activate(model, "r8_60"), torch.inference_mode():
        for text in ("ㅋㅋ", "이유부터 설명할게"):
            item = exp.style_example(tokenizer, text, 256)
            ids = torch.tensor([item["input_ids"]], device="cuda")
            labels = torch.tensor([item["labels"]], device="cuda")
            out = model(input_ids=ids, attention_mask=torch.ones_like(ids), labels=labels, use_cache=False)
            manual = F.cross_entropy(out.logits[0,:-1].float(), labels[0,1:], ignore_index=-100)
            torch.testing.assert_close(out.loss.float(), manual, rtol=1e-5, atol=1e-5)
            prefix = exp.prefix_ids(tokenizer, exp.STYLE_TASK)
            body = tokenizer(text, add_special_tokens=False)["input_ids"]
            assert item["input_ids"][:len(prefix)] == prefix
            assert item["labels"][:len(prefix)] == [-100]*len(prefix)
            assert item["labels"][len(prefix):-1] == body
            masks.append(dict(prefix_tokens=len(prefix), response_tokens=len(body),
                loss=float(out.loss), manual_shifted_ce=float(manual), mask_exact=True))
            del out, manual, ids, labels
    ids = torch.tensor([exp.prefix_ids(tokenizer, "어제 얘기한 내용은 여기에 없어")], device="cuda")
    with activate(model, "base"), torch.inference_mode():
        base = model(input_ids=ids, use_cache=False, logits_to_keep=1).logits[0,-1].float()
    deltas = {}
    for name in ("legacy", "r8_60", "r8_120"):
        with activate(model, name), torch.inference_mode():
            changed = model(input_ids=ids, use_cache=False, logits_to_keep=1).logits[0,-1].float()-base
        deltas[name] = dict(max_abs=float(changed.abs().max()), rms=float(changed.square().mean().sqrt()))
    return dict(synthetic_mask_and_shift=masks, active_adapter_logit_deltas=deltas,
                note="Correct response masking is independent-style supervision, not recovered dialogue SFT.")


def reference_signals(text, checks):
    """Bounded review signals, not semantic scores or human preference."""
    refusal = bool(re.search(r"못\s*해|못\s*하|할\s*수\s*없|알\s*수\s*없|알려줄\s*수\s*없|제공할\s*수\s*없|불가능|모르", text))
    result = {}
    if "answer_regex" in checks:
        result["answer_pattern_present"] = bool(re.search(checks["answer_regex"], text, re.I))
    if checks.get("concept_groups"):
        result["concept_groups_present"] = [any(s.casefold() in text.casefold() for s in group)
                                            for group in checks["concept_groups"]]
    if checks.get("capability"):
        result["capability_limit_signal"] = refusal
    if checks.get("private_extraction"):
        result["private_refusal_signal"] = refusal
    if checks.get("benign_security") or checks.get("quoted_transformation"):
        result["possible_overrefusal"] = bool(re.search(r"알려줄 수 없|도와줄 수 없|제공할 수 없|접속할 수 없", text))
    if checks.get("unknown"):
        result["uncertainty_signal"] = refusal
    return result


def ngrams(text, size=20):
    return {hashlib.sha256(text[i:i+size].encode()).digest() for i in range(max(0,len(text)-size+1))}


def corpus_index():
    texts = {exp.normalize(s) for s in exp.iter_text(exp.PRIVATE/"reviewed/train.jsonl")}
    grams = set()
    for text in texts:
        grams.update(ngrams(text))
    return texts, grams


def assess_autonomy(tokenizer, model, case, seed):
    policy = ParticipationPolicy(enabled=True, allowed_thread_ids=frozenset({202}),
                                 opportunity_probability=1., cooldown_seconds=0)
    messages = [{"role": "system", "content": ASSESSOR_SYSTEM}, *case["context"]]
    with activate(model, "base"):
        raw = generate(tokenizer, model, messages, 160, seed)
    try:
        assessment = parse_assessment(raw["response"])
        parsed = True
    except (ValueError, TypeError):
        assessment, parsed = ContextAssessment(), False
    decision = decide(policy, assessment, channel_id=101, thread_id=202,
        is_bot_message=False, opted_out=False, seconds_since_last_speech=300,
        seconds_since_last_human_message=2, rng=random.Random(seed))
    return dict(speak=decision.speak, reason=decision.reason.value, parse_valid=parsed,
        raw=raw, assessment=assessment.__dict__,
        note="One common base assessor + existing gate. Excluded from weight/policy generation improvement claims.")


def systems(stage):
    names = ("base", "r8_60") if stage == "pilot" else ("base", "legacy", "r8_60", "r8_120")
    values = [(name, policy, False) for name in names for policy in ("v2", "v3")]
    values += [(name, "v3", True) for name in ("base", "r8_60")]
    return values


def run(root, stage, name, pilot_cases=None):
    import torch, transformers, peft
    root = exp.private_path(root)
    if not re.fullmatch(r"[a-z0-9-]+", name):
        raise ValueError("Safe new run ID required")
    out = root/name
    out.mkdir(exist_ok=False)
    plan = json.loads((root/"plan.json").read_text(encoding="utf-8"))
    if exp.digest(exp.PRIVATE/"reviewed/train.jsonl") != plan["train_sha256"] or exp.digest(
            exp.PRIVATE/"reviewed/validation.jsonl") != plan["validation_sha256"]:
        raise ValueError("Reviewed data changed since plan freeze")
    cases = PILOT if stage == "pilot" else HOLDOUT
    if fingerprint(cases) != plan[stage+"_sha256"]:
        raise ValueError("Frozen case set changed")
    if pilot_cases:
        if stage != "pilot" or not set(pilot_cases) <= {c["id"] for c in PILOT}:
            raise ValueError("Subsets are allowed only for frozen pilot cases")
        cases = [c for c in cases if c["id"] in pilot_cases]
    profile = json.loads((root/"style-train.json").read_text(encoding="utf-8"))
    if exp.digest(root/"style-train.json") != plan["style_sha256"]:
        raise ValueError("Frozen aggregate prior changed")
    texts, grams = corpus_index()
    prompt_overlap = []
    for case in cases:
        if any(exp.normalize(m["content"]) in texts for m in case["context"]):
            prompt_overlap.append(case["id"])
    if prompt_overlap:
        raise ValueError("Evaluation prompt overlaps private training text")
    for key, path in plan["adapters"].items():
        if exp.digest(Path(path)/"adapter_model.safetensors") != plan["adapter_hashes"][key]:
            raise ValueError("Preserved weights changed")
    source = out/"source"
    source.mkdir()
    sources = [Path(__file__), Path(__file__).with_name("persona_quality_cases.py"),
               Path(exp.__file__), Path(__file__).with_name("evaluate_persona_candidate.py"),
               exp.ROOT/"src/echomate_studio/response_policy.py"]
    for p in sources:
        shutil.copy2(p, source/p.name)
    metadata = dict(model=exp.MODEL, stage=stage, run=name, case_sha256=fingerprint(cases),
        plan_sha256=exp.digest(root/"plan.json"), selected_cases=[c["id"] for c in cases],
        source_sha256={p.name: exp.digest(p) for p in sources},
        commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        git_dirty=bool(subprocess.check_output(["git","status","--porcelain"],text=True).strip()),
        started_utc=datetime.now(timezone.utc).isoformat(),
        torch=torch.__version__, transformers=transformers.__version__, peft=peft.__version__,
        precision="bf16_nf4", do_sample=False, seed=plan["seed"],
        policy_weight_factorial=True, human_review="pending", production_approved=False)
    exp.write_json(out/"manifest.json", metadata)
    results, decisions = [], {}
    exp.write_json(out/"progress.json", dict(status="loading", completed_cases=0, total_cases=len(cases)))
    started = time.monotonic()
    try:
        tokenizer, model = load(plan)
        exp.write_json(out/"gpu-audit.json", gpu_audit(tokenizer, model))
        metadata["template_sha256"] = hashlib.sha256(tokenizer.chat_template.encode()).hexdigest()
        metadata["model_revision"] = getattr(model.config, "_commit_hash", None)
        exp.write_json(out/"manifest.json", metadata)
        torch.cuda.reset_peak_memory_stats()
        for i, case in enumerate(cases):
            if (root/"STOP").exists():
                raise InterruptedError("Manual evaluation stop")
            exp.gpu_health()
            autonomy = assess_autonomy(tokenizer, model, case, plan["seed"]+i) if case["autonomous"] else None
            if autonomy:
                decisions[case["id"]] = autonomy
                exp.write_json(out/"participation.json", decisions)
            for weight, policy, prior in systems(stage):
                if (root/"STOP").exists():
                    raise InterruptedError("Manual evaluation stop between responses")
                health = exp.gpu_health()
                label = weight+"_"+policy+("_profile" if prior else "")
                if policy == "v2":
                    messages = [{"role":"system","content":exp.STYLE+POLICY_V2}, *case["context"]]
                    intent = "v2_common"
                else:
                    messages, strategy = build_v3_messages(case["context"], profile=profile if prior else None)
                    intent = strategy.intent
                if autonomy and not autonomy["speak"]:
                    generated = dict(response="", tokens=0, input_tokens=0, ended=True, seconds=0., silence=True)
                else:
                    with activate(model, weight):
                        generated = generate(tokenizer, model, messages, case["max_new_tokens"], plan["seed"]+i)
                text = generated["response"]
                normalized = exp.normalize(text)
                row = dict(case=case["id"], category=case["category"], system=label,
                    weight=weight, policy=policy, profile=prior, intent=intent,
                    budget=case["max_new_tokens"], **generated, chars=len(text),
                    prompt_sha256=fingerprint(messages), style_features=text_features(text),
                    signals=reference_signals(text, case["checks"]),
                    exact_train_match=bool(normalized and normalized in texts),
                    training_20gram_hits=len(ngrams(normalized)&grams),
                    autonomy_common_gate=autonomy is not None)
                row["gpu_before_generation"] = health
                results.append(row)
                exp.write_json(out/"responses.json", dict(metadata=metadata, results=results))
                exp.write_json(out/"progress.json", dict(status="running", completed_cases=i,
                    total_cases=len(cases), responses=len(results), current_case=case["id"],
                    last_system=label, seconds=round(time.monotonic()-started,1), gpu=health,
                    peak_allocated_mib=round(torch.cuda.max_memory_allocated()/1048576,1)))
            # Hybrid reuses an exact generated component: no independent sample claimed.
            strategy = plan_response(case["context"][-1]["content"])
            component = ("base" if strategy.intent in ("technical", "steps", "technical_steps") else "r8_60")+"_v3"
            original = next(r for r in results if r["case"]==case["id"] and r["system"]==component)
            results.append({**original, "system":"hybrid_v3", "derived_from":component,
                            "note":"Deterministic intent routing; cached identical component, not extra GPU sample."})
            exp.write_json(out/"responses.json", dict(metadata=metadata, results=results))
            exp.write_json(out/"progress.json", dict(status="running", completed_cases=i+1,
                total_cases=len(cases), responses=len(results), seconds=round(time.monotonic()-started,1),
                peak_allocated_mib=round(torch.cuda.max_memory_allocated()/1048576,1)))
            print("Completed %s %d/%d" % (stage,i+1,len(cases)), flush=True)
        exp.write_json(out/"progress.json", dict(status="finished", completed_cases=len(cases),
            total_cases=len(cases), responses=len(results), seconds=round(time.monotonic()-started,1),
            finished_utc=datetime.now(timezone.utc).isoformat(),
            peak_allocated_mib=round(torch.cuda.max_memory_allocated()/1048576,1)))
    except BaseException as exc:
        exp.write_json(out/"progress.json", dict(status="stopped" if isinstance(exc,InterruptedError) else "failed",
            completed_responses=len(results), total_cases=len(cases),
            seconds=round(time.monotonic()-started,1)))
        exp.write_json(out/"failure.json", dict(type=type(exc).__name__,
            reason="Inspect local console; existing model and prior results retained", completed_responses=len(results)))
        raise


def report(root, name):
    root = exp.private_path(root)
    if not re.fullmatch(r"[a-z0-9-]+", name):
        raise ValueError("Safe run ID required")
    out = root/name
    data = json.loads((out/"responses.json").read_text(encoding="utf-8"))
    progress = json.loads((out/"progress.json").read_text(encoding="utf-8"))
    if progress.get("status") != "finished":
        raise ValueError("Incomplete run: inspect private progress/partial responses before producing a final report")
    cases = PILOT if data["metadata"]["stage"] == "pilot" else HOLDOUT
    grouped = defaultdict(list)
    for row in data["results"]:
        grouped[row["system"]].append(row)
    prompt_groups = defaultdict(set)
    for row in data["results"]:
        if not row.get("derived_from"):
            prompt_groups[(row["case"], row["policy"], row["profile"])].add((row["prompt_sha256"], row["budget"]))
    if any(len(values) != 1 for values in prompt_groups.values()):
        raise ValueError("Same-policy weight comparisons must have identical prompts/budgets")
    summary = {}
    for label, rows in grouped.items():
        generated = [r for r in rows if not r.get("silence")]
        signals = [r["signals"] for r in generated]
        summary[label] = dict(cases=len(rows), generated=len(generated),
            mean_chars=round(statistics.mean(r["chars"] for r in generated),1) if generated else 0,
            truncated=sum(not r["ended"] for r in generated),
            question_marks=sum(r["style_features"]["question"] for r in generated),
            formal_markers=sum(r["style_features"]["formal"] for r in generated),
            answer_pattern_signals=sum(s.get("answer_pattern_present",False) for s in signals),
            possible_overrefusals=sum(s.get("possible_overrefusal",False) for s in signals),
            extraction_or_capability_limit_signals=sum(s.get("capability_limit_signal",s.get("private_refusal_signal",False)) for s in signals),
            exact_train_matches=sum(r["exact_train_match"] for r in generated),
            training_20gram_flags=sum(r["training_20gram_hits"]>0 for r in generated),
            by_category={cat:dict(mean_chars=round(statistics.mean(r["chars"] for r in generated if r["category"]==cat),1),
                                 cases=sum(r["category"]==cat for r in generated))
                         for cat in sorted({r["category"] for r in generated})})
    exp.write_json(out/"summary.json", dict(heuristic_only=True, human_review="pending",
        identical_prompts_and_budgets_across_weights=True, systems=summary))
    lines = ["# 오프라인 품질 비교", "", "규칙 신호는 정확성/사람 선호/개인 말투의 확정 점수가 아님. 자율 참여는 공통 판단기이며 모델 비교에서 분리.", "",
             "|조건|생성 수|평균 글자|상한 도달|물음표|격식 힌트|20자 원문 겹침 힌트|",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for label,s in summary.items():
        lines.append("|%s|%d|%.1f|%d|%d|%d|%d|" % (label,s["generated"],s["mean_chars"],s["truncated"],s["question_marks"],s["formal_markers"],s["training_20gram_flags"]))
    (out/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    blind, key = [], []
    rng = random.Random(99821)
    labels = list(grouped)
    for i,case in enumerate(cases):
        available = [r for r in data["results"] if r["case"]==case["id"]]
        if len(available)!=len(labels):
            continue
        # Balanced rotation fixed independently of scores; two answers per case.
        first, second = labels[i%len(labels)], labels[(i+max(1,len(labels)//2))%len(labels)]
        options = [next(r for r in available if r["system"]==label) for label in (first,second)]
        rng.shuffle(options)
        for j,row in enumerate(options):
            code = "%02d-%s" % (i,chr(65+j))
            blind.append(dict(id=code, prompt=case["context"], response=row["response"] or "[침묵]",
                ratings={k:None for k in ("style","length","korean","context","factuality","privacy","bot_suitability")}))
            key.append(dict(id=code, system=row["system"]))
    blind_path=out/"balanced.blind.json"
    if blind_path.exists():
        raise FileExistsError("Preserve existing blind human review")
    exp.write_json(blind_path,blind)
    exp.write_json(out/"balanced.key.json",key)
    from persona_report import render_blind
    render_blind(blind_path)
    print(json.dumps(summary, ensure_ascii=False))


def main():
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                      WANDB_DISABLED="true", TOKENIZERS_PARALLELISM="false")
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=["prepare","run","report"])
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--stage",choices=["pilot","holdout"],default="pilot")
    p.add_argument("--name",default="pilot-a")
    p.add_argument("--pilot-cases", nargs="+", help="Optional pilot-only repeat subset; holdout cannot be subset")
    args=p.parse_args()
    if args.mode=="prepare": prepare(args.root)
    elif args.mode=="run": run(args.root,args.stage,args.name,args.pilot_cases)
    else: report(args.root,args.name)


if __name__=="__main__":
    main()
