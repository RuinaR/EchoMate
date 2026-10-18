"""Explicit opt-in Gemma4 12B synthetic QLoRA step; never uses user data."""
import argparse
import json
from pathlib import Path

MODEL="google/gemma-4-12B-it"

def check(seq_len=32,enabled=False):
    if not 16<=seq_len<=64:raise ValueError("seq_len outside conservative 16..64 bounds")
    return {"model":MODEL,"status":"ready" if enabled else "not_run","synthetic_only":True,"seq_len":seq_len}

def run(seq_len=32):
    import torch
    from transformers import BitsAndBytesConfig,AutoModelForMultimodalLM
    from peft import LoraConfig,prepare_model_for_kbit_training,get_peft_model
    if not torch.cuda.is_available():return {"status":"failed","reason":"cuda_unavailable"}
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    model=None
    try:
        quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16)
        model=AutoModelForMultimodalLM.from_pretrained(MODEL,
            quantization_config=quant,device_map={"":0},dtype=torch.float16,
            local_files_only=True,attn_implementation="sdpa")
        model=prepare_model_for_kbit_training(model,use_gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant":False})
        model=get_peft_model(model,LoraConfig(r=4,lora_alpha=8,
            target_modules=["q_proj","v_proj"],lora_dropout=0.0,bias="none",task_type="CAUSAL_LM"))
        model.train()
        ids=torch.full((1,seq_len),10,device="cuda",dtype=torch.long)
        labels=ids.clone()
        labels[:,:-8]=-100
        opt=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=1e-5)
        result=model(input_ids=ids,attention_mask=torch.ones_like(ids),labels=labels,use_cache=False)
        if not bool(torch.isfinite(result.loss).item()):return {"status":"failed","reason":"nonfinite_loss"}
        result.loss.backward()
        opt.step()
        opt.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        free,_=torch.cuda.mem_get_info(0)
        return {"status":"ok","model":MODEL,"synthetic_only":True,"seq_len":seq_len,
            "trainable_params":sum(p.numel() for p in model.parameters() if p.requires_grad),
            "loss":round(float(result.loss.detach().item()),4),
            "peak_allocated_mib":round(torch.cuda.max_memory_allocated()/1048576,1),
            "free_after_mib":round(free/1048576,1)}
    except Exception as exc:
        return {"status":"failed","reason":"synthetic_lora_failed","error_type":type(exc).__name__}
    finally:
        del model
        torch.cuda.empty_cache()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--allow-synthetic-step",action="store_true")
    p.add_argument("--seq-len",type=int,default=32)
    p.add_argument("--output",type=Path,default=Path("local_data/gemma4-12b-lora-smoke.json"))
    args=p.parse_args()
    x=check(args.seq_len,args.allow_synthetic_step)
    if args.allow_synthetic_step:x=run(args.seq_len)
    if "local_data" not in args.output.resolve().parts:p.error("output must be in local_data")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(x,indent=2),encoding="utf-8")
    print("Gemma4 12B LoRA:",x["status"],"report:",args.output)
    return 0 if x["status"] in ("ok","not_run") else 1

if __name__=="__main__":
    raise SystemExit(main())
