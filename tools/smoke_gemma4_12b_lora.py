"""Opt-in synthetic-only Gemma4 QLoRA GPU stability probe (no personal texts)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

MODEL = "google/gemma-4-12B-it"

def check(seq_len=32, enabled=False, steps=1, tokenizer_smoke=False):
    if not 16 <= seq_len <= 64:
        raise ValueError("seq_len must be 16..64")
    if not 1 <= steps <= 3:
        raise ValueError("steps must be 1..3")
    return {"model": MODEL, "status": "ready" if enabled else "not_run",
            "synthetic_only": True, "seq_len": seq_len, "steps": steps,
            "tokenizer_smoke": bool(tokenizer_smoke)}

def make_ids(seq_len, tokenizer=None):
    """No Discord content: use fixed generated tokens or a fixed synthetic Korean sentence."""
    import torch
    if tokenizer is None:
        return torch.full((1, seq_len), 10, device="cuda", dtype=torch.long)
    synthetic = "안녕! 오늘 게임 재밌다 ㅋㅋ 다음에 같이 해보자!"
    pieces = tokenizer(synthetic, add_special_tokens=True)["input_ids"]
    if not pieces or len(pieces) < 2:
        raise ValueError("synthetic tokenizer produced too few tokens")
    # Deliberately repeat already-tokenized synthetic text to exercise length and labels.
    ids = (pieces * ((seq_len + len(pieces) - 1) // len(pieces)))[:seq_len]
    return torch.tensor([ids], device="cuda", dtype=torch.long)

def run(seq_len=32, steps=1, tokenizer_smoke=False):
    import torch
    from transformers import BitsAndBytesConfig, AutoModelForMultimodalLM
    from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
    if not torch.cuda.is_available():
        return {"status": "failed", "stage": "cuda", "reason": "cuda_unavailable"}
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    model = None
    stage = "tokenizer"
    try:
        tokenizer = None
        if tokenizer_smoke:
            from transformers import AutoTokenizer
            # Explicit opt-in: may download tokenizer files, never model weights.
            tokenizer = AutoTokenizer.from_pretrained(MODEL)
        ids = make_ids(seq_len, tokenizer)
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                   bnb_4bit_use_double_quant=True,
                                   bnb_4bit_compute_dtype=torch.float16)
        stage = "model_load"
        model = AutoModelForMultimodalLM.from_pretrained(
            MODEL, quantization_config=quant, device_map={"": 0},
            dtype=torch.float16, local_files_only=True,
            attn_implementation="sdpa")
        stage = "peft"
        model = prepare_model_for_kbit_training(
            model, use_gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False})
        model = get_peft_model(model, LoraConfig(
            r=4, lora_alpha=8, target_modules=["q_proj", "v_proj"],
            lora_dropout=0.0, bias="none", task_type="CAUSAL_LM"))
        model.train()
        labels = ids.clone()
        labels[:, : min(8, seq_len - 2)] = -100
        attention_mask = torch.ones_like(ids)
        optimizer = torch.optim.AdamW(
            (p for p in model.parameters() if p.requires_grad), lr=1e-5)
        losses = []
        stage = "optimizer"
        for _ in range(steps):
            result = model(input_ids=ids, attention_mask=attention_mask,
                           labels=labels, use_cache=False)
            if not bool(torch.isfinite(result.loss).item()):
                return {"status": "failed", "stage": stage, "reason": "nonfinite_loss"}
            losses.append(round(float(result.loss.detach().item()), 4))
            result.loss.backward()
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            del result
        torch.cuda.synchronize()
        free, _ = torch.cuda.mem_get_info(0)
        return {"status": "ok", "model": MODEL, "synthetic_only": True,
                "seq_len": seq_len, "steps_completed": steps,
                "tokenizer_smoke": bool(tokenizer_smoke),
                "trainable_params": sum(p.numel() for p in model.parameters() if p.requires_grad),
                "last_loss": losses[-1], "losses": losses,
                "peak_allocated_mib": round(torch.cuda.max_memory_allocated()/1048576, 1),
                "free_after_mib": round(free/1048576, 1)}
    except Exception as exc:
        return {"status": "failed", "reason": "synthetic_lora_failed",
                "stage": stage, "error_type": type(exc).__name__}
    finally:
        del model
        torch.cuda.empty_cache()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--allow-synthetic-step", action="store_true")
    p.add_argument("--seq-len", type=int, default=32)
    p.add_argument("--steps", type=int, default=1)
    p.add_argument("--tokenizer-smoke", action="store_true")
    p.add_argument("--output", type=Path,
                   default=Path("local_data/gemma4-12b-lora-smoke.json"))
    args = p.parse_args()
    if "local_data" not in args.output.resolve().parts:
        p.error("output must be inside local_data")
    info = check(args.seq_len, args.allow_synthetic_step, args.steps,
                 args.tokenizer_smoke)
    report = run(args.seq_len, args.steps, args.tokenizer_smoke) if args.allow_synthetic_step else info
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Gemma4 12B LoRA:", report["status"], "stage:",
          report.get("stage", "complete"), "report:", args.output)
    return 0 if report["status"] in ("ok", "not_run") else 1

if __name__ == "__main__":
    raise SystemExit(main())
