# Persona training research (2026-10-18)

## Primary studies and implementations
- LoRA — Hu et al. (2021): https://arxiv.org/abs/2106.09685 . Freeze base weights and train low-rank adapters.
- QLoRA — Dettmers et al. (2023): https://arxiv.org/abs/2305.14314 . NF4, double quantization and memory-efficient adapter training.
- DoRA — Liu et al. (ICML 2024): https://proceedings.mlr.press/v235/liu24bn.html . Optional later comparison, not baseline.
- Unintended memorization — Carlini et al. (USENIX Security 2019): https://research.google/pubs/the-secret-sharer-evaluating-and-testing-unintended-memorization-in-neural-networks/ . Rare strings can be memorized and extracted.
- Hugging Face TRL SFT Trainer: https://huggingface.co/docs/trl/main/sft_trainer . Plain language modeling differs from prompt-completion and assistant-only dialogue training.
- Hugging Face PEFT LoRA: https://huggingface.co/docs/peft/main/package_reference/lora . Compare validated q_proj/v_proj adapters with all-linear only after baseline.

## Recommended EchoMate protocol
1. Objective: adapt the language style of ONE owner-speaker, not fake multi-speaker instruction tuning. Never reinterpret adjacent same-speaker messages as question/answer pairs.
2. Data: owner-exported two Discord channels, 304,997 messages; previous chronological dedup audit found 164,662 training unique candidates and 18,226 clean validation unique candidates. These counts are not approved samples.
3. Preserve health, sexual, and aggressive/profane language as user-specified style; do not exclude solely by topic. Separately protect secrets, personal identifiers, third-party information and malformed text.
4. Before training, review source permission and third-party privacy, construct approved local-only samples and chronological evaluation data without exact or near-duplicate leakage.
5. A: baseline Gemma 3 4B + style prompt. B: NF4 q/v rank-4 LoRA on approved owner-language-modeling data. Optional C: tune LoRA rank/layer targets. Optional D: DoRA only if justified by A/B.
6. Keep VRAM tests conservative. Confirmed: RTX 4070 Ti SUPER, 32-token synthetic Gemma3 4B LoRA one optimizer step; peak PyTorch allocation 5660.7 MiB. Longer contexts remain untested.
7. Evaluate authentic Korean tone, dialogue coherence, role/recipient handling, hallucination, repeated output, unwanted verbatim memorization, privacy leaks, and emoji/text/silence decision with held-out examples.
8. Do not upload private messages or training artifacts to public GitHub; do not claim the generated adapter is better without blind baseline comparisons.

## Limits
- LoRA/QLoRA studies support efficient tuning methods, not a guarantee of faithful personal voice cloning or improved conversation performance.
- API-obtained Discord message restriction and an owner-requested Data Package are not interchangeable legal categories. Source-use rights and third-party privacy still require review.
- Actual owner-data training has not started.

## Implementation milestone
- The single-speaker, chronological exact-deduplicated dataset builder is in src/echomate_studio/persona_dataset.py with two explicit approval gates. Near-duplicate and contextual private data detection still need improvement. No owner-message training yet.
