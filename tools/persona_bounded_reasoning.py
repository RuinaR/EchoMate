"""Offline bounded native thinking; expose final channel only, never tool calls.

No model-generated code is executed. Same total token ceiling as direct replies.
Only an authored pilot can qualify this optional inference candidate.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time

import persona_experiments as exp
sys.path.insert(0,str(exp.ROOT/"src"))
from echomate_studio.response_policy import build_v3_messages


def visible_final(raw: str) -> str:
    text=raw.replace("<turn|>","").replace("<eos>","").replace("<pad>","").strip()
    if any(s in text for s in ("<|","|>","<channel|>")):
        raise ValueError("Unexpected channel/tool output: do not expose")
    return text


def generate(tokenizer,model,messages,budget,seed):
    import torch
    from transformers import set_seed
    set_seed(seed)
    ids=exp.token_list(tokenizer.apply_chat_template(messages,tokenize=True,
        add_generation_prompt=True,enable_thinking=True))
    start=torch.tensor([ids],device="cuda")
    close=tokenizer.convert_tokens_to_ids("<channel|>")
    turn=tokenizer.convert_tokens_to_ids("<turn|>")
    if close==tokenizer.unk_token_id:
        raise ValueError("Native channel terminator unavailable")
    cap=min(192,budget//2)
    started=time.monotonic()
    with torch.inference_mode():
        output=model.generate(input_ids=start,attention_mask=torch.ones_like(start),
            max_new_tokens=cap,do_sample=False,use_cache=True,
            eos_token_id=[close,turn,tokenizer.eos_token_id],pad_token_id=tokenizer.eos_token_id)
    thought=output[0,len(ids):].tolist()
    raw=tokenizer.decode(thought,skip_special_tokens=False)
    if not raw.startswith("<|channel>thought\n"):
        # No thoughts may accidentally be displayed if the native format changes.
        return dict(response="",tokens=len(thought),input_tokens=len(ids),ended=False,
                    seconds=round(time.monotonic()-started,3),reasoning_parse_failed=True)
    forced=not thought or thought[-1]!=close
    if thought and thought[-1] in (turn,tokenizer.eos_token_id):
        thought=thought[:-1]
    if forced:
        thought.append(close)
    remaining=budget-len(thought)
    continuation=torch.tensor([ids+thought],device="cuda")
    with torch.inference_mode():
        final=model.generate(input_ids=continuation,attention_mask=torch.ones_like(continuation),
            max_new_tokens=remaining,do_sample=False,use_cache=True,
            eos_token_id=[turn,tokenizer.eos_token_id],pad_token_id=tokenizer.eos_token_id)
    answer_tokens=final[0,continuation.shape[1]:].tolist()
    answer_raw=tokenizer.decode(answer_tokens,skip_special_tokens=False)
    try:
        answer=visible_final(answer_raw)
        failed=False
    except ValueError:
        answer,failed="",True
    return dict(response=answer,tokens=len(thought)+len(answer_tokens),input_tokens=len(ids),
        ended=bool(answer_tokens and answer_tokens[-1] in (turn,tokenizer.eos_token_id)) and not failed,
        seconds=round(time.monotonic()-started,3),thought_tokens=len(thought),
        answer_tokens=len(answer_tokens),forced_channel_close=forced,reasoning_parse_failed=failed,
        note="Bounded private reasoning + visible answer share original token ceiling; two greedy calls, extra prefill cost.")


def pilot(root):
    import torch, transformers, peft, subprocess
    import sys
    sys.path.insert(0,str(exp.ROOT/"src"))
    import persona_quality_v3 as quality
    from persona_quality_cases import PILOT
    root=exp.private_path(root)
    out=root/"reasoning-pilot"
    out.mkdir(exist_ok=False)
    shutil.copy2(__file__,out/Path(__file__).name)
    case=next(c for c in PILOT if c["id"]=="p04")
    plan=json.loads((root/"plan.json").read_text(encoding="utf-8"))
    exp.write_json(out/"hypothesis.json",dict(
        hypothesis="Native bounded thinking may correct contradictory code-state conclusions without more style training.",
        success="Correct final state, no contradictory first conclusion, terminated final answer, no channel leakage.",
        budget=case["max_new_tokens"],thinking_cap=192,new_training_steps=0,
        failure_action="Do not add this path to holdout if pilot fails.",production_approved=False))
    for key,path in plan["adapters"].items():
        if exp.digest(exp.private_path(path)/"adapter_model.safetensors") != plan["adapter_hashes"][key]:
            raise ValueError("Preserved weights changed")
    exp.write_json(out/"manifest.json",dict(model=exp.MODEL,seed=plan["seed"]+3,
        torch=torch.__version__,transformers=transformers.__version__,peft=peft.__version__,
        commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        source_sha256=exp.digest(Path(__file__)),budget=case["max_new_tokens"],
        thinking_cap=192,precision="bf16_nf4",do_sample=False,weight="base"))
    exp.write_json(out/"progress.json",dict(status="loading"))
    tokenizer,model=quality.load(plan)
    torch.cuda.reset_peak_memory_stats()
    messages,_=build_v3_messages(case["context"])
    exp.gpu_health()
    exp.write_json(out/"progress.json",dict(status="generating"))
    with quality.activate(model,"base"):
        result=generate(tokenizer,model,messages,case["max_new_tokens"],plan["seed"]+3)
    exp.write_json(out/"response.json",dict(case=case["id"],**result,
        source_sha256=exp.digest(Path(__file__)),
        prompt_sha256=quality.fingerprint(messages),production_approved=False))
    exp.write_json(out/"progress.json",dict(status="finished",peak_allocated_mib=round(torch.cuda.max_memory_allocated()/1048576,1)))
    print("Bounded-thinking pilot saved privately; requires semantic review.")


if __name__=="__main__":
    import sys
    # Source package is local, no pip install or network operation.
    os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1",WANDB_DISABLED="true")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,required=True)
    args=parser.parse_args()
    target=exp.private_path(args.root)/"reasoning-pilot"
    existed=target.exists()
    try:
        pilot(args.root)
    except BaseException as exc:
        if not existed and target.exists():
            exp.write_json(target/"failure.json",dict(type=type(exc).__name__,reason="Inspect private log; old runs preserved"))
            exp.write_json(target/"progress.json",dict(status="failed"))
        raise
