"""Offline A/B generation from a privately trained Gemma4 PEFT adapter.

Outputs contain generated text: keep them inside gitignored local_data.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

MODEL = "google/gemma-4-12B-it"
PROMPTS = (
    "오늘 뭐하고 놀까?",
    "ㅋㅋㅋㅋ 그게 뭐야",
    "요즘 할 만한 게임 있어?",
    "내일 몇 시에 만나기로 했더라?",
    "아 너무 졸리다",
    "오늘 진짜 너무 힘들었어",
    "게임하다가 갑자기 튕겼다",
    "나랑 메이플 할래?",
)

def check_local_paths(adapter: Path, output: Path):
    adapter = adapter.resolve()
    output = output.resolve()
    if "local_data" not in adapter.parts or not (adapter/"adapter_config.json").is_file():
        raise ValueError("Existing private adapter directory under local_data required")
    if "local_data" not in output.parts or output.suffix.lower() != ".json":
        raise ValueError("Output JSON must reside in gitignored local_data")
    if output.exists():
        raise FileExistsError("Use a new output file to avoid overwriting evaluation")
    return adapter, output

def encode(tokenizer, text, torch):
    messages = [{"role": "user", "content": [{"type": "text", "text": text}]}]
    encoded = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True,
        return_tensors="pt")
    # Transformers returns BatchEncoding (mapping, not a plain dict).
    # Some Gemma4 tokenizer versions return an object exposing input_ids.
    if hasattr(encoded, "input_ids"):
        encoded = encoded.input_ids
    elif hasattr(encoded, "keys"):
        encoded = encoded["input_ids"]
    if isinstance(encoded, list):
        encoded = torch.tensor(encoded, dtype=torch.long)
    if encoded.ndim == 1:
        encoded = encoded.unsqueeze(0)
    if encoded.ndim != 2:
        raise ValueError("Expected a rank-2 token tensor from chat template")
    return encoded.to("cuda")

def compare(adapter, output, *, max_new_tokens=64):
    import torch
    from transformers import AutoTokenizer, AutoModelForMultimodalLM, BitsAndBytesConfig
    from peft import PeftModel
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required")
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16)
    base = AutoModelForMultimodalLM.from_pretrained(
        MODEL, quantization_config=quant, device_map={"": 0},
        dtype=torch.float16, attn_implementation="sdpa",
        local_files_only=True)
    model = PeftModel.from_pretrained(base, str(adapter), is_trainable=False)
    model.eval()
    results = []
    for index, question in enumerate(PROMPTS, 1):
        ids = encode(tokenizer, question, torch)
        responses = {}
        for key in ("base", "trained"):
            with torch.inference_mode():
                if key == "base":
                    with model.disable_adapter():
                        generated = model.generate(input_ids=ids,
                            max_new_tokens=max_new_tokens,
                            do_sample=False, use_cache=True,
                            pad_token_id=tokenizer.eos_token_id)
                else:
                    generated = model.generate(input_ids=ids,
                        max_new_tokens=max_new_tokens,
                        do_sample=False, use_cache=True,
                        pad_token_id=tokenizer.eos_token_id)
            responses[key] = tokenizer.decode(
                generated[0, ids.shape[-1]:], skip_special_tokens=True).strip()
        results.append({"prompt": question, **responses})
        print("Compared %d/%d prompts" % (index, len(PROMPTS)), flush=True)
    report = {"model": MODEL, "adapter": str(adapter),
        "comparison": "same user prompts; base weights vs PEFT enabled; greedy generation",
        "note": "Generated text can contain memorized private information. Keep locally and redact before sharing.",
        "results": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Private A/B report:", output)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("local_data/gemma4-persona-ab.json"))
    parser.add_argument("--max-new-tokens", type=int, default=64)
    args = parser.parse_args()
    if not 16 <= args.max_new_tokens <= 128:
        parser.error("--max-new-tokens must be 16..128")
    adapter, output = check_local_paths(args.adapter, args.output)
    compare(adapter, output, max_new_tokens=args.max_new_tokens)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
