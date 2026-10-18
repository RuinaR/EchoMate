# Separate Gemma 4 environment. Never changes .venv-train.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$python = "py"
& $python -3.10 -m venv .venv-gemma4
if ($LASTEXITCODE -ne 0) { throw "Python 3.10 venv creation failed" }
$exe = Join-Path $PWD ".venv-gemma4\Scripts\python.exe"
& $exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
& $exe -m pip install "torch==2.9.1" --index-url https://download.pytorch.org/whl/cu128
if ($LASTEXITCODE -ne 0) { throw "CUDA PyTorch installation failed" }
& $exe -m pip install "transformers>=5.10,<6" "accelerate>=1.15" "bitsandbytes>=0.50.2" "peft>=0.21.2" "huggingface_hub>=0.35" numpy pillow
if ($LASTEXITCODE -ne 0) { throw "Gemma4 dependency installation failed" }
& $exe -m pip check
if ($LASTEXITCODE -ne 0) { throw "Dependency conflict" }
& $exe -c "import torch; from transformers import AutoConfig, AutoModelForMultimodalLM, BitsAndBytesConfig; import peft, bitsandbytes; print('CUDA:', torch.cuda.is_available(), 'Torch:', torch.__version__)"
if ($LASTEXITCODE -ne 0) { throw "Gemma4 import smoke failed" }
Write-Host "Gemma4 environment installed separately. No weights downloaded."
