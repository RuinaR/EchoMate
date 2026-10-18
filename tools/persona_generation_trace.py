"""Private forensic replay of a consumed holdout case, never a fresh score.

Wraps generate only to retain its output tokens before skip_special_tokens.
Does not change frozen prompts/weights/budgets or any saved evaluation response.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import persona_quality_v3 as q
from persona_quality_cases import HOLDOUT


def trace(root):
    import torch
    started=time.monotonic()
    root=q.exp.private_path(root)
    out=root/"h18-token-trace"
    out.mkdir(exist_ok=False)
    shutil.copy2(__file__,out/Path(__file__).name)
    launch=json.loads((root/"holdout-launch.json").read_text(encoding="utf-8"))
    if any(q.exp.digest(Path(p))!=h for p,h in launch["source_sha256"].items()):
        raise ValueError("Frozen inference sources changed; forensic replay cannot silently change conditions")
    plan=json.loads((root/"plan.json").read_text(encoding="utf-8"))
    profile=json.loads((root/"style-train.json").read_text(encoding="utf-8"))
    if q.exp.digest(root/"style-train.json")!=plan["style_sha256"]:
        raise ValueError("Frozen prior changed")
    for key,path in plan["adapters"].items():
        if q.exp.digest(q.exp.private_path(path)/"adapter_model.safetensors")!=plan["adapter_hashes"][key]:
            raise ValueError("Preserved weights changed")
    data=json.loads((root/"holdout-a/responses.json").read_text(encoding="utf-8"))
    case=next(c for c in HOLDOUT if c["id"]=="h18")
    q.exp.write_json(out/"manifest.json",dict(purpose="forensic replay, not new generalization or tuning",
        source_commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        frozen_source_commit=launch["source_commit"],source_sha256=q.exp.digest(Path(__file__)),
        started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        prompts_and_decoding="same frozen three-slot policy batch",production_approved=False))
    q.exp.write_json(out/"progress.json",dict(status="loading"))
    tokenizer,model=q.load(plan)
    torch.cuda.reset_peak_memory_stats()
    q.exp.write_json(out/"progress.json",dict(status="generating"))
    prompts=[[{"role":"system","content":q.exp.STYLE+q.POLICY_V2},*case["context"]],
        q.build_v3_messages(case["context"])[0],q.build_v3_messages(case["context"],profile=profile)[0]]
    width=max(len(q.encode(tokenizer,p)) for p in prompts)
    original=model.generate
    captured=[]
    def recording(**kwargs):
        result=original(**kwargs)
        captured.append(result.detach().cpu())
        return result
    model.generate=recording
    rows=[]
    try:
        for weight in ("base","r8_60"):
            if (root/"STOP").exists():
                raise InterruptedError("Manual forensic stop")
            q.exp.gpu_health()
            with q.activate(model,weight):
                outputs=q.generate_policy_batch(tokenizer,model,prompts,case["max_new_tokens"],
                    plan["seed"]+HOLDOUT.index(case),width)
            tokens=captured.pop()
            for slot,result in enumerate(outputs):
                label=weight+("_v2" if slot==0 else "_v3" if slot==1 else "_v3_profile")
                saved=next(r for r in data["results"] if r["case"]=="h18" and r["system"]==label)
                ids=tokens[slot,width:width+result["tokens"]].tolist()
                raw=tokenizer.decode(ids,skip_special_tokens=False)
                rows.append(dict(system=label,matches_saved_visible=result["response"]==saved["response"],
                    raw=raw,token_ids=ids,channel_open_count=raw.count("<|channel>"),
                    channel_close_count=raw.count("<channel|>"),visible_thought_word=result["response"].startswith("thought")))
            q.exp.write_json(out/"raw.json",rows)
    finally:
        model.generate=original
    q.exp.write_json(out/"summary.json",[{k:v for k,v in r.items() if k not in ("raw","token_ids")} for r in rows])
    q.exp.write_json(out/"progress.json",dict(status="finished",fresh_score=False,
        seconds=round(time.monotonic()-started,1),peak_allocated_mib=round(torch.cuda.max_memory_allocated()/1048576,1)))
    print("Forensic replay retained private raw tokens; no frozen output changed.")


if __name__=="__main__":
    os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1",WANDB_DISABLED="true")
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True)
    args=p.parse_args()
    target=q.exp.private_path(args.root)/"h18-token-trace"
    existed=target.exists()
    try:
        trace(args.root)
    except BaseException as exc:
        if not existed and target.exists():
            q.exp.write_json(target/"failure.json",dict(type=type(exc).__name__,reason="Inspect private log"))
            q.exp.write_json(target/"progress.json",dict(status="failed"))
        raise
