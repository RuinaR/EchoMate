"""Conservative longer Gemma4 QLoRA protocol. Local reviewed JSONL only.

Checkpoint snapshots are adapter-only for rollback, not exact optimizer resume.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

from train_persona_gemma4 import MODEL, iter_text, select_ids, validate

def train(args):
    import torch
    from transformers import AutoTokenizer, AutoModelForMultimodalLM, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required")
    tokenizer=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    train_ids=select_ids(args.train,tokenizer,args.seq_len,args.steps,min_tokens=3)
    valid_ids=select_ids(args.validation,tokenizer,args.seq_len,args.validation_samples,min_tokens=3)
    if len(train_ids)<args.steps or len(valid_ids)<args.validation_samples:
        raise ValueError("Insufficient eligible examples; reduce requested steps / validation count")
    quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",
                            bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16)
    model=AutoModelForMultimodalLM.from_pretrained(
        MODEL,quantization_config=quant,device_map={"":0},dtype=torch.float16,
        attn_implementation="sdpa",local_files_only=True)
    model=prepare_model_for_kbit_training(
        model,use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant":False})
    model=get_peft_model(model,LoraConfig(
        r=4,lora_alpha=8,target_modules=["q_proj","v_proj"],lora_dropout=0.0,
        bias="none",task_type="CAUSAL_LM"))
    optimizer=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=args.lr)
    def inputs(ids):
        token=torch.tensor([ids],device="cuda",dtype=torch.long)
        labels=token.clone()
        labels[:,:1]=-100
        return {"input_ids":token,"attention_mask":torch.ones_like(token),
                "labels":labels,"use_cache":False}
    def evaluate():
        model.eval()
        losses=[]
        with torch.no_grad():
            for ids in valid_ids:
                loss=float(model(**inputs(ids)).loss.detach().item())
                if not math.isfinite(loss):
                    raise RuntimeError("Nonfinite validation loss")
                losses.append(loss)
        model.train()
        return sum(losses)/len(losses)

    args.output.mkdir(parents=True,exist_ok=False)
    metrics=[]
    best=float("inf")
    best_step=0
    stale=0
    try:
        torch.cuda.reset_peak_memory_stats()
        initial=evaluate()
        for step,ids in enumerate(train_ids,1):
            model.train()
            out=model(**inputs(ids))
            if not bool(torch.isfinite(out.loss).item()):
                raise RuntimeError("Nonfinite training loss")
            out.loss.backward()
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            loss=float(out.loss.detach().item())
            del out
            if step==1 or step%args.eval_every==0 or step==args.steps:
                val=evaluate()
                improved=val+args.min_delta<best
                if improved:
                    best=val
                    best_step=step
                    stale=0
                    model.save_pretrained(args.output/"best",safe_serialization=True)
                else:
                    stale+=1
                metrics.append({"step":step,"train_loss":round(loss,5),
                                "validation_loss":round(val,5),
                                "improved":improved})
                if args.checkpoint_every and step%args.checkpoint_every==0:
                    model.save_pretrained(args.output/("step-%05d"%step),
                                          safe_serialization=True)
                # Write aggregate-only progress after every evaluation, so unattended
                # runs have inspectable metrics even if interrupted.
                (args.output/"metrics.json").write_text(
                    json.dumps(metrics,indent=2,ensure_ascii=False),encoding="utf-8")
                print("Evaluation step %d/%d, heldout_loss=%.5f, best_step=%d" %
                      (step,args.steps,val,best_step),flush=True)
                if stale>=args.patience:
                    break
        report={"status":"finished" if step==args.steps else "early_stopped","model":MODEL,
                "steps_completed":step,"planned_steps":args.steps,
                "best_step":best_step,"validation_baseline":round(initial,5),
                "best_validation_loss":round(best,5),
                "validation_samples":len(valid_ids),
                "peak_allocated_mib":round(torch.cuda.max_memory_allocated()/1048576,1),
                "epochs":1,"optimizer_resume_supported":False,
                "notes":"Adapter snapshots contain weights only, not optimizer state. "
                        "Holdout losses are not a human style rating. Source permission is required."}
        (args.output/"summary.json").write_text(
            json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
        (args.output/"metrics.json").write_text(
            json.dumps(metrics,indent=2,ensure_ascii=False),encoding="utf-8")
        return report
    except BaseException:
        (args.output/"FAILED-INSPECT-LOCALLY.txt").write_text(
            "Training interrupted. Inspect private checkpoints; no exact resume supported.",
            encoding="utf-8")
        raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--train",type=Path,required=True)
    p.add_argument("--validation",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--steps",type=int,default=300)
    p.add_argument("--seq-len",type=int,default=128)
    p.add_argument("--lr",type=float,default=1e-5)
    p.add_argument("--validation-samples",type=int,default=16)
    p.add_argument("--eval-every",type=int,default=25)
    p.add_argument("--checkpoint-every",type=int,default=100)
    p.add_argument("--patience",type=int,default=5)
    p.add_argument("--min-delta",type=float,default=0.001)
    p.add_argument("--approve-private-training",action="store_true")
    p.add_argument("--confirm-rights",action="store_true")
    p.add_argument("--confirm-privacy-review",action="store_true")
    args=p.parse_args()
    if not 20<=args.steps<=3000 or not 32<=args.seq_len<=256:
        p.error("steps must be 20..3000 and seq_len 32..256")
    if not 0<args.lr<=0.0001 or not 4<=args.validation_samples<=64:
        p.error("invalid learning rate or validation count")
    if not 1<=args.eval_every<=args.steps or not 1<=args.patience<=30:
        p.error("invalid evaluation frequency or patience")
    if not 0<=args.checkpoint_every<=args.steps or args.min_delta<0:
        p.error("invalid checkpoint frequency or min delta")
    train_path,valid_path,out=validate(args.train,args.validation,args.output,
        approved=args.approve_private_training,
        rights_confirmed=args.confirm_rights,
        privacy_reviewed=args.confirm_privacy_review,
        max_steps=2,seq_len=32)
    if out.exists():
        p.error("output must not exist; use a new local directory")
    args.train,args.validation,args.output=train_path,valid_path,out
    print("Starting approved LOCAL Gemma4 QLoRA protocol; no upload.")
    result=train(args)
    print("Run completed:",result["status"],"summary:",out/"summary.json")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
