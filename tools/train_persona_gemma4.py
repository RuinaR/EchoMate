"""Gemma4 12B IT: conservative, offline, reviewed single-speaker QLoRA trainer.

No automatic corpus building or download. No Discord API. Writes private adapter only.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

MODEL = "google/gemma-4-12B-it"

def validate(train: Path, valid: Path, out: Path, *,
             approved=False, rights_confirmed=False, privacy_reviewed=False,
             max_steps=2, seq_len=32):
    if not (approved and rights_confirmed and privacy_reviewed):
        raise PermissionError("Explicit training, rights and privacy review approvals required")
    if not 1 <= max_steps <= 10 or not 16 <= seq_len <= 64:
        raise ValueError("Conservative bounds: steps=1..10, seq_len=16..64")
    train, valid, out = (Path(p).resolve() for p in (train, valid, out))
    if not train.is_file() or not valid.is_file() or train == valid:
        raise ValueError("Separate existing private train and validation JSONL required")
    if any("local_data" not in p.parts for p in (train, valid, out)):
        raise ValueError("All paths must reside inside ignored local_data")
    if out == train or out == valid or out in train.parents or out in valid.parents:
        raise ValueError("Adapter output must not overwrite or contain dataset files")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output directory must be new or empty")
    return train, valid, out

def iter_text(path: Path, limit=300000):
    with path.open(encoding="utf-8") as stream:
        for i, line in enumerate(stream):
            if i >= limit:
                raise ValueError("Corpus row limit exceeded")
            record = json.loads(line)
            if not isinstance(record, dict) or set(record) != {"text"} or not isinstance(record["text"], str):
                raise ValueError("Expected JSONL with exactly one text field")
            if record["text"].strip():
                yield record["text"]

def select_ids(path, tokenizer, seq_len, count, *, min_tokens=8):
    """Spread sample selection across corpus rather than taking its first rows."""
    if count < 1:
        return []
    # Count pass keeps large private corpora off in-memory buffers.
    eligible_count = 0
    for text in iter_text(path):
        ids = tokenizer(text, add_special_tokens=True, truncation=True,
                        max_length=seq_len)["input_ids"]
        if min_tokens <= len(ids) <= seq_len:
            eligible_count += 1
    if not eligible_count:
        return []
    target = min(count, eligible_count)
    positions = {(i * eligible_count) // target for i in range(target)}
    selected = []
    eligible_index = 0
    for text in iter_text(path):
        ids = tokenizer(text, add_special_tokens=True, truncation=True,
                        max_length=seq_len)["input_ids"]
        if min_tokens <= len(ids) <= seq_len:
            if eligible_index in positions:
                selected.append(ids)
                if len(selected) == target:
                    break
            eligible_index += 1
    return selected

def run(train, valid, out, *, max_steps=2, seq_len=32, include_short_samples=False):
    import torch
    from transformers import AutoTokenizer, AutoModelForMultimodalLM, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    # Each text is an independent LM example; never concatenate unrelated chats.
    min_tokens = 3 if include_short_samples else 8
    train_ids = select_ids(train, tokenizer, seq_len, max_steps, min_tokens=min_tokens)
    val_ids = select_ids(valid, tokenizer, seq_len, min(8, max_steps), min_tokens=min_tokens)
    if not train_ids or not val_ids:
        raise ValueError("Insufficient nontrivial train or validation examples")
    # Only aggregate counters and losses leave GPU; no decoded strings or token IDs logged.
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    model = None
    try:
        quant = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16)
        model = AutoModelForMultimodalLM.from_pretrained(
            MODEL, quantization_config=quant, device_map={"": 0},
            dtype=torch.float16, attn_implementation="sdpa",
            local_files_only=True)
        model = prepare_model_for_kbit_training(
            model, use_gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False})
        model = get_peft_model(model, LoraConfig(
            r=4, lora_alpha=8, target_modules=["q_proj", "v_proj"],
            lora_dropout=0.0, bias="none", task_type="CAUSAL_LM"))
        def inputs(ids):
            tokens = torch.tensor([ids], device="cuda", dtype=torch.long)
            labels = tokens.clone()
            labels[:, :1] = -100
            return dict(input_ids=tokens, attention_mask=torch.ones_like(tokens),
                        labels=labels, use_cache=False)
        model.eval()
        with torch.no_grad():
            before = sum(float(model(**inputs(ids)).loss.item()) for ids in val_ids) / len(val_ids)
        if not math.isfinite(before):
            raise RuntimeError("Nonfinite validation baseline")
        model.train()
        optimizer = torch.optim.AdamW(
            (p for p in model.parameters() if p.requires_grad), lr=1e-5)
        losses = []
        for ids in train_ids:
            res = model(**inputs(ids))
            if not bool(torch.isfinite(res.loss).item()):
                raise RuntimeError("Nonfinite training loss")
            res.loss.backward()
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            losses.append(round(float(res.loss.detach().item()), 4))
            del res
        model.eval()
        with torch.no_grad():
            after = sum(float(model(**inputs(ids)).loss.item()) for ids in val_ids) / len(val_ids)
        if not math.isfinite(after):
            raise RuntimeError("Nonfinite validation after")
        torch.cuda.synchronize()
        free, _ = torch.cuda.mem_get_info(0)
        report = {
            "status": "trained_local_smoke", "model": MODEL,
            "single_speaker_lm": True, "steps": len(losses), "seq_len": seq_len,
            "short_samples_enabled": bool(include_short_samples),
            "validation_samples": len(val_ids),
            "sampling": "deterministic_even_spread",
            "min_token_length": min_tokens,
            "trainable_params": sum(p.numel() for p in model.parameters() if p.requires_grad),
            "validation_loss_before_adapter_update": round(before, 4),
            "validation_loss_after_adapter_update": round(after, 4),
            "last_training_loss": losses[-1],
            "peak_allocated_mib": round(torch.cuda.max_memory_allocated()/1048576, 1),
            "free_after_mib": round(free/1048576, 1),
            "warning": "Few validation samples and steps are not a model-quality evaluation. Before value is an untrained adapter, not a separate untuned-base benchmark."
        }
        out.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(out, safe_serialization=True)
        (out/"training-summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    finally:
        del model
        torch.cuda.empty_cache()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, default=Path("local_data/persona-dataset/persona-train.jsonl"))
    ap.add_argument("--validation", type=Path, default=Path("local_data/persona-dataset/persona-validation.jsonl"))
    ap.add_argument("--output", type=Path, default=Path("local_data/persona-adapters/gemma4-first"))
    ap.add_argument("--max-steps", type=int, default=2)
    ap.add_argument("--seq-len", type=int, default=32)
    ap.add_argument("--include-short-samples", action="store_true",
                    help="Opt-in standalone short texts (>=3 token IDs), never join unrelated messages")
    ap.add_argument("--approve-private-training", action="store_true")
    ap.add_argument("--confirm-rights", action="store_true")
    ap.add_argument("--confirm-privacy-review", action="store_true")
    args = ap.parse_args()
    train, valid, out = validate(args.train, args.validation, args.output,
        approved=args.approve_private_training, rights_confirmed=args.confirm_rights,
        privacy_reviewed=args.confirm_privacy_review,
        max_steps=args.max_steps, seq_len=args.seq_len)
    print("Starting explicitly approved local-only Gemma4 training; no remote model API.")
    report = run(train, valid, out, max_steps=args.max_steps, seq_len=args.seq_len,
                 include_short_samples=args.include_short_samples)
    print("Training result:", report["status"], "Private report:", out/"training-summary.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
