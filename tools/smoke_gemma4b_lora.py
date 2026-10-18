"""Explicit opt-in Gemma 3 4B synthetic LoRA optimizer smoke test.

Loads already-cached model weights, no private data, no checkpoint writing.
"""
import argparse
import json
from pathlib import Path

MODEL="google/gemma-3-4b-it"

def preflight(*, allow_training=False, seq_len=32):
    if not 8 <= seq_len <= 64:
        raise ValueError("seq_len must be between 8 and 64")
    return {"status":"ready" if allow_training else "not_run",
            "model":MODEL,"synthetic_only":True,"seq_len":seq_len}

def run(*, seq_len=32):
    import torch
    from transformers import BitsAndBytesConfig, Gemma3ForConditionalGeneration
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    if not torch.cuda.is_available():
        return {"status":"failed","reason":"cuda_unavailable"}
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(0)
    model=None
    try:
        quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16)
        model=Gemma3ForConditionalGeneration.from_pretrained(MODEL,
            quantization_config=quant,device_map={"":0},dtype=torch.float16,
            attn_implementation="sdpa",local_files_only=True)
        model=prepare_model_for_kbit_training(model,use_gradient_checkpointing=True)
        model=get_peft_model(model,LoraConfig(r=4,lora_alpha=8,lora_dropout=0.0,
            target_modules=["q_proj","v_proj"],bias="none",task_type="CAUSAL_LM"))
        model.train()
        # Synthetic token IDs only; never load user text, tokenizer or datasets.
        ids=torch.full((1,seq_len),fill_value=10,dtype=torch.long,device="cuda")
        mask=torch.ones_like(ids)
        labels=ids.clone()
        labels[:,:-8]=-100
        opt=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=1e-5)
        out=model(input_ids=ids,attention_mask=mask,labels=labels,
                  use_cache=False)
        loss=out.loss
        if not bool(torch.isfinite(loss).item()):
            return {"status":"failed","reason":"nonfinite_loss"}
        loss.backward()
        opt.step()
        opt.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        return {"status":"ok","model":MODEL,"synthetic_only":True,
                "seq_len":seq_len,
                "trainable_params":sum(p.numel() for p in model.parameters() if p.requires_grad),
                "loss":round(float(loss.detach().item()),4),
                "peak_allocated_mib":round(torch.cuda.max_memory_allocated(0)/1048576,1),
                "free_after_mib":round(torch.cuda.mem_get_info(0)[0]/1048576,1)}
    except Exception as exc:
        return {"status":"failed","reason":"synthetic_training_failed",
                "error_type":type(exc).__name__}
    finally:
        del model
        torch.cuda.empty_cache()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--allow-synthetic-step",action="store_true")
    p.add_argument("--seq-len",type=int,default=32)
    p.add_argument("--output",type=Path,default=Path("local_data/gemma4b-lora-smoke.json"))
    args=p.parse_args()
    result=preflight(allow_training=args.allow_synthetic_step,seq_len=args.seq_len)
    if args.allow_synthetic_step:
        result=run(seq_len=args.seq_len)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print("Synthetic Gemma LoRA:",result["status"],"report:",args.output)
    return 0 if result["status"] in ("ok","not_run") else 1

if __name__=="__main__":
    raise SystemExit(main())
