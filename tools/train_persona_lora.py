"""Local-only Gemma3 4B NF4 LoRA fine-tuning runner for approved owner text.

Requires an existing reviewed private JSONL corpus and an explicit flag.
No remote training endpoints; base weights must already be cached.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

MODEL="google/gemma-3-4b-it"

def validate(train:Path, valid:Path, out:Path, *, approved=False, max_steps=20, seq_len=128):
    if not approved:
        raise PermissionError("Explicit private corpus approval is required")
    if not (1<=max_steps<=100 and 32<=seq_len<=512):
        raise ValueError("Training steps or sequence length exceeds conservative limits")
    train,valid,out=(Path(x).resolve() for x in (train,valid,out))
    if train==valid or not train.is_file() or not valid.is_file():
        raise ValueError("Separate existing training and validation JSONL files required")
    if "local_data" not in train.parts or "local_data" not in valid.parts or "local_data" not in out.parts:
        raise ValueError("Training files and adapters must remain in local_data")
    if out==train or out==valid:
        raise ValueError("Output must not overwrite corpus")
    return train,valid,out

def iterate_text(path:Path,limit=300000):
    with path.open(encoding="utf-8") as fh:
        for i,line in enumerate(fh):
            if i>=limit: raise ValueError("Dataset row limit exceeded")
            obj=json.loads(line)
            if not isinstance(obj,dict) or set(obj)!={"text"} or not isinstance(obj["text"],str):
                raise ValueError("Expected one private text field per line")
            if obj["text"].strip():
                yield obj["text"]

def run(train,valid,out,*,max_steps=20,seq_len=128):
    import torch
    from transformers import AutoTokenizer,BitsAndBytesConfig,Gemma3ForConditionalGeneration
    from peft import LoraConfig,get_peft_model,prepare_model_for_kbit_training
    if not torch.cuda.is_available():raise RuntimeError("CUDA unavailable")
    tokenizer=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    texts=iterate_text(train)
    validation=iterate_text(valid)
    # Preflight reads only a bounded local sample. Store neither examples nor decoded text.
    train_samples=[]
    for txt in texts:
        ids=tokenizer(txt,add_special_tokens=True,truncation=True,max_length=seq_len)["input_ids"]
        if len(ids)>=8:train_samples.append(ids)
        if len(train_samples)>=max_steps:break
    val_sample=None
    for txt in validation:
        candidate_ids=tokenizer(txt,add_special_tokens=True,truncation=True,max_length=seq_len)["input_ids"]
        if len(candidate_ids)>=8:
            val_sample=candidate_ids
            break
    if not train_samples or val_sample is None:raise ValueError("Insufficient usable private texts")
    if tokenizer.pad_token_id is None:raise ValueError("Tokenizer must define padding")
    quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16)
    model=Gemma3ForConditionalGeneration.from_pretrained(MODEL,quantization_config=quant,
        device_map={"":0},dtype=torch.float16,attn_implementation="sdpa",local_files_only=True)
    model=prepare_model_for_kbit_training(model,use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant":False})
    model=get_peft_model(model,LoraConfig(r=4,lora_alpha=8,lora_dropout=0.0,
        target_modules=["q_proj","v_proj"],bias="none",task_type="CAUSAL_LM"))
    optimizer=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=1e-5)
    def tensors(ids):
        tokens=torch.tensor([ids],device="cuda",dtype=torch.long)
        labels=tokens.clone()
        labels[:,:-1]=-100
        return dict(input_ids=tokens,attention_mask=torch.ones_like(tokens),labels=labels,use_cache=False)
    torch.cuda.reset_peak_memory_stats()
    model.eval()
    with torch.no_grad():
        baseline=float(model(**tensors(val_sample)).loss.item())
    losses=[]
    model.train()
    for ids in train_samples:
        result=model(**tensors(ids))
        if not bool(torch.isfinite(result.loss).item()):raise RuntimeError("Nonfinite training loss")
        result.loss.backward()
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        losses.append(round(float(result.loss.detach().item()),4))
    model.eval()
    with torch.no_grad():
        adapted=float(model(**tensors(val_sample)).loss.item())
    out.mkdir(parents=True,exist_ok=True)
    model.save_pretrained(out, safe_serialization=True)
    report={"status":"trained_local","model":MODEL,"steps":len(losses),"seq_len":seq_len,
            "validation_loss_base":round(baseline,4),"validation_loss_adapter":round(adapted,4),
            "last_training_loss":losses[-1],
            "peak_allocated_mib":round(torch.cuda.max_memory_allocated()/1048576,1),
            "warning":"Single-example validation is a smoke signal, not a rigorous A/B evaluation."}
    (out/"training-summary.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--train",type=Path,default=Path("local_data/persona-dataset/persona-train.jsonl"))
    p.add_argument("--validation",type=Path,default=Path("local_data/persona-dataset/persona-validation.jsonl"))
    p.add_argument("--output",type=Path,default=Path("local_data/persona-adapters/first"))
    p.add_argument("--max-steps",type=int,default=20)
    p.add_argument("--seq-len",type=int,default=128)
    p.add_argument("--approve-private-training",action="store_true")
    args=p.parse_args()
    train,valid,out=validate(args.train,args.validation,args.output,
        approved=args.approve_private_training,max_steps=args.max_steps,seq_len=args.seq_len)
    print("Training exclusively on approved local corpus; no cloud model API calls.")
    result=run(train,valid,out,max_steps=args.max_steps,seq_len=args.seq_len)
    print("Local LoRA adapter completed. Summary:",out/"training-summary.json")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
