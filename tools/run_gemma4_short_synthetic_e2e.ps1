# ASCII-only PowerShell 5.1: synthetic short-sample GPU integration test.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$stamp = [DateTime]::UtcNow.ToString("yyyyMMdd-HHmmss-fffffff")
$root = Join-Path $PWD ("local_data\gemma4-short-synthetic-" + $stamp)
New-Item -ItemType Directory -Path $root -Force | Out-Null
$train = Join-Path $root "train.jsonl"
$valid = Join-Path $root "validation.jsonl"
$out = Join-Path $root "adapter"
$utf8 = New-Object System.Text.UTF8Encoding($false)
# Invented short snippets: no user content and no external API.
[System.IO.File]::WriteAllLines($train, [string[]]@(
    '{"text":"hi"}',
    '{"text":"ok"}'
), $utf8)
[System.IO.File]::WriteAllLines($valid, [string[]]@(
    '{"text":"yes"}'
), $utf8)
$py = Join-Path $PWD ".venv-gemma4\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing local Gemma4 Python environment." }
& $py .\tools\train_persona_gemma4.py --train $train --validation $valid --output $out --max-steps 2 --seq-len 32 --include-short-samples --approve-private-training --confirm-rights --confirm-privacy-review
if ($LASTEXITCODE -ne 0) { throw "Synthetic short-sample GPU QA failed." }
Write-Host "Synthetic-only short-example QA complete:" (Join-Path $out "training-summary.json")
