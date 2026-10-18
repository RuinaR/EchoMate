"""Prepare a bounded reproducible local queue; does not authorize or run training."""
import argparse
from pathlib import Path
import shutil
from persona_experiments import private_path, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    folder = private_path(args.output)
    folder.mkdir(parents=True, exist_ok=False)
    config = dict(train="local_data/reviewed/train.jsonl",
        validation="local_data/reviewed/validation.jsonl", steps=60, rank=4,
        seq_len=256, accumulation=2, validation_samples=32, eval_every=20,
        patience=2, lr=2e-5, dropout=.05, targets=["q_proj", "v_proj"],
        seed=3407, precision="bf16")
    write_json(folder/"plan.json", [
        dict(id="pilot-r4-qv", config=config),
        dict(id="pilot-r8-qkvo", config={**config, "rank": 8,
                                        "targets": ["q_proj", "k_proj", "v_proj", "o_proj"]})])
    source = folder/"source"
    source.mkdir()
    for name in ("persona_experiments.py", "train_persona_gemma4.py", "gemma4_corpus_preflight.py",
                 "evaluate_persona_candidate.py", "persona_adapter_diagnostics.py", "persona_report.py"):
        shutil.copy2(Path(__file__).with_name(name), source/name)
    print("Prepared plan only. Review local data authorization before running queue.")


if __name__ == "__main__":
    main()
