param(
    [switch]$InstallTrainingLibraries,
    [switch]$SkipTorchInstall
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root '.venv-train'
$py = Join-Path $venv 'Scripts\python.exe'

if (-not (Test-Path $py)) {
    Write-Host 'Creating isolated training environment...'
    & py -3.10 -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create isolated Python 3.10 environment' }
}
if (-not (Test-Path $py)) { throw 'Training interpreter missing' }

if (-not $SkipTorchInstall) {
    & $py -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'pip setup failed' }
    # Official PyTorch CUDA 12.8 wheel channel.
    & $py -m pip install 'torch==2.9.1' --index-url https://download.pytorch.org/whl/cu128
    if ($LASTEXITCODE -ne 0) { throw 'CUDA PyTorch installation failed' }
}
& $py (Join-Path $PSScriptRoot 'verify_training_cuda.py')
if ($LASTEXITCODE -ne 0) { throw 'CUDA verification failed; refusing additional packages' }

if ($InstallTrainingLibraries) {
    # NumPy is not bundled in the fresh venv; required by common training paths.
    & $py -m pip install 'numpy>=1.26,<3' 'transformers>=4.51,<5' 'peft>=0.15,<1' 'trl>=0.19,<1' 'accelerate>=1,<2' 'bitsandbytes>=0.46,<1' 'datasets>=3,<5'
    if ($LASTEXITCODE -ne 0) { throw 'Training libraries installation failed' }
    & $py -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Package compatibility check failed' }
    & $py (Join-Path $PSScriptRoot 'verify_training_stack.py')
    if ($LASTEXITCODE -ne 0) { throw 'Training stack import check failed' }
}
Write-Host 'Isolated CUDA check completed. No model or private data downloaded.'
