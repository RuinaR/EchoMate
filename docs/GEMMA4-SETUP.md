# Gemma 4 12B IT implementation gate — 2026-10-18

## Decision
Use `google/gemma-4-12B-it` as the initial conversation-ready model, not the untuned `google/gemma-4-12B`. Both are official ~23.9GB checkpoints; this is a starting hypothesis, not a validated superiority claim. Preserve working Gemma 3 4B tools and `.venv-train`.

Official documentation: https://huggingface.co/google/gemma-4-12B-it and https://huggingface.co/google/gemma-4-12B . Their Transformers example uses `AutoModelForMultimodalLM` rather than hard-coded `Gemma4ForConditionalGeneration`. The checkpoint generation config records a 5.10.0.dev0 environment. Test isolated stable Transformers >=5.10,<6 on Python 3.10.

## Local run (PowerShell)
```powershell
git pull origin main
.\tools\setup_gemma4_env.ps1
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
.\.venv-gemma4\Scripts\python.exe .\tools\probe_gemma4_12b.py
```
Only after small configuration access succeeds AND the user opts into ~23.9GB model download:
```powershell
.\.venv-gemma4\Scripts\python.exe .\tools\probe_gemma4_12b.py --allow-download --allow-load
```
The probe records safe category, stage, versions, and GPU memory in ignored `local_data/gemma4-12b-probe.json`. It omits exception strings to avoid credential disclosure. Only after NF4 loads should the synthetic LoRA path be reworked/validated against Gemma 4's actual multimodal interface and PEFT module mapping; the earlier Gemma 3 smoke result does not apply.

## Verification status
- Confirmed from user Windows report: 165 previous unit tests OK, but old Gemma4 probe failed to import under Transformers 4.57.6.
- This change supplies a separate installation script and replaces direct model class import with official multimodal auto class; **Windows environment installation, HF config preflight, NF4 checkpoint load and Gemma4 optimizer step remain unverified**.
- Original owner-exported Discord private messages are NOT used in any of these stages. Corpus rights, review and leakage testing remain independent blockers before actual personal-data fine-tuning.
