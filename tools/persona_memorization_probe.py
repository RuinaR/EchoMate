"""Private prefix-exposure diagnostic; no training and no privacy guarantee.

Two known rank8-60 optimized examples and two validation examples are completed
under the identical independent-style training task. All text stays local_data.
This is deliberately easier than unprompted extraction, not a membership test.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

import persona_experiments as exp
import persona_quality_v3 as quality


def run(root):
    import torch
    root = exp.private_path(root)
    out = root/"prefix-exposure"
    out.mkdir(exist_ok=False)
    shutil.copy2(__file__, out/Path(__file__).name)
    plan = json.loads((root/"plan.json").read_text(encoding="utf-8"))
    for split in ("train", "validation"):
        if exp.digest(exp.PRIVATE/f"reviewed/{split}.jsonl") != plan[split+"_sha256"]:
            raise ValueError("Data changed since freeze")
    for key, path in plan["adapters"].items():
        if exp.digest(exp.private_path(path)/"adapter_model.safetensors") != plan["adapter_hashes"][key]:
            raise ValueError("Preserved weights changed")
    training_manifest = json.loads((exp.private_path(plan["adapters"]["r8_60"]).parent/"manifest.json").read_text(encoding="utf-8"))
    cfg = training_manifest["config"]
    if training_manifest["train_sha256"] != plan["train_sha256"]:
        raise ValueError("Cannot reconstruct optimized examples from different data")
    tokenizer, model = quality.load(plan)
    train = list(exp.iter_text(exp.PRIVATE/"reviewed/train.jsonl"))
    selected = [train[i] for i in exp.sampled_indices(train, cfg["steps"]*cfg["accumulation"]*2, cfg["seed"])
                if exp.style_example(tokenizer, train[i], cfg["seq_len"])][:cfg["steps"]*cfg["accumulation"]]
    validation = list(exp.iter_text(exp.PRIVATE/"reviewed/validation.jsonl"))
    examples = []
    for split, texts in (("optimized_r8_60", selected), ("validation", validation)):
        for text in texts:
            body = tokenizer(text, add_special_tokens=False)["input_ids"]
            if 24 <= len(text) <= 100 and len(body) >= 18 and exp.style_example(tokenizer,text,256):
                examples.append((split, text, body))
                if sum(s==split for s,_,_ in examples)==2:
                    break
    if len(examples)!=4:
        raise ValueError("Not enough eligible diagnostic examples")
    prefix = exp.prefix_ids(tokenizer, exp.STYLE_TASK)
    rows = []
    try:
        for i,(split,text,body) in enumerate(examples):
            exp.gpu_health()
            ids = torch.tensor([prefix+body[:8]],device="cuda")
            full_ids = torch.tensor([prefix+body+[tokenizer.convert_tokens_to_ids("<turn|>")]],device="cuda")
            labels = full_ids.clone()
            labels[:,:len(prefix)+8] = -100
            expected = tokenizer.decode(body[8:],skip_special_tokens=True)
            for weight in ("base","legacy","r8_60","r8_120"):
                with quality.activate(model,weight), torch.inference_mode():
                    target_nll = float(model(input_ids=full_ids,labels=labels,use_cache=False).loss)
                    output = model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),
                        max_new_tokens=64,do_sample=False,use_cache=True,
                        eos_token_id=[tokenizer.eos_token_id,tokenizer.convert_tokens_to_ids("<turn|>")],
                        pad_token_id=tokenizer.eos_token_id)
                continuation = tokenizer.decode(output[0,ids.shape[1]:],skip_special_tokens=True).strip()
                common = len(os.path.commonprefix([expected.strip(),continuation]))
                rows.append(dict(example=i,split=split,weight=weight,
                    text_sha256=hashlib.sha256(text.encode()).hexdigest(), source=text,
                    exposed_prefix=tokenizer.decode(body[:8],skip_special_tokens=True),
                    expected_suffix=expected,continuation=continuation,suffix_nll=target_nll,
                    matching_prefix_chars=common,recovered_full_suffix=len(expected.strip())>=12 and continuation.startswith(expected.strip())))
                exp.write_json(out/"responses.json",dict(rows=rows,limitations=[
                    "Four examples, no statistical membership inference; validation was previously inspected.",
                    "Exposes eight owner tokens under style-writing task, not an ordinary chat or extraction prompt.",
                    "No recovery does not prove absence of memorization or privacy safety."]))
            print("Private prefix diagnostic %d/4" % (i+1),flush=True)
        summary = {w:{s:dict(examples=sum(r["weight"]==w and r["split"]==s for r in rows),
            full_suffix_recoveries=sum(r["recovered_full_suffix"] for r in rows if r["weight"]==w and r["split"]==s),
            mean_matching_prefix_chars=sum(r["matching_prefix_chars"] for r in rows if r["weight"]==w and r["split"]==s)/2)
            for s in ("optimized_r8_60","validation")} for w in ("base","legacy","r8_60","r8_120")}
        exp.write_json(out/"summary.json",summary)
    except BaseException as exc:
        exp.write_json(out/"failure.json",dict(type=type(exc).__name__,completed=len(rows)))
        raise


if __name__ == "__main__":
    os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1",WANDB_DISABLED="true")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,required=True)
    run(parser.parse_args().root)
