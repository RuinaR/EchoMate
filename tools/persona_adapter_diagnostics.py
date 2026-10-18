"""Local aggregate check that PEFT changes logits in actual inference formats."""
from __future__ import annotations
import argparse
from pathlib import Path

from persona_experiments import load_model, prefix_ids, private_path, write_json


def probe(tokenizer, model):
    import torch
    model.eval()
    details = []
    for name, ids in [("chat", prefix_ids(tokenizer, "오늘은 그냥 쉬고 싶다")),
                      ("raw_lm", tokenizer("오늘은 그냥 쉬고 싶다", add_special_tokens=True)["input_ids"])]:
        tokens = torch.tensor([ids], device="cuda")
        with torch.inference_mode():
            with model.disable_adapter():
                base = model(input_ids=tokens, use_cache=False, logits_to_keep=1).logits[0,-1].float()
            adapted = model(input_ids=tokens, use_cache=False, logits_to_keep=1).logits[0,-1].float()
        difference = adapted-base
        details.append({"format": name, "max_abs_logit_delta": float(difference.abs().max()),
            "rms_logit_delta": float(difference.square().mean().sqrt()),
            "top1_changed": int(base.argmax()) != int(adapted.argmax())})
    weights = [p.detach().float() for n,p in model.named_parameters() if ".lora_B." in n]
    return {"formats": details, "lora_b_nonzero_tensors": sum(bool(p.count_nonzero()) for p in weights),
        "lora_b_tensors": len(weights),
        "note": "Nonzero logit delta verifies forward application, not conversational quality."}


def main():
    import os
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adapter", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    output = private_path(args.output)
    if output.exists():
        raise FileExistsError("New probe output required")
    tokenizer, model = load_model(private_path(args.adapter))
    report = probe(tokenizer, model)
    write_json(output, report)
    print(report)


if __name__ == "__main__":
    main()
