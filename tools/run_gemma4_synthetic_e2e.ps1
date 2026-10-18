# Fully synthetic local-only end-to-end Gemma4 trainer QA.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$root = Join-Path $PWD "local_data\gemma4-synthetic-e2e"
New-Item -ItemType Directory -Force -Path $root | Out-Null
$train = Join-Path $root "train.jsonl"
$valid = Join-Path $root "validation.jsonl"
$out = Join-Path $root "adapter"
if (Test-Path $out) { throw "Synthetic adapter destination already exists: $out. Do not overwrite existing results." }
$syntheticTrain = @(
    "안녕 오늘 게임 진짜 재밌었어 ㅋㅋ 다음에도 해보자",
    "아 이거 왜 이렇게 어렵냐 ㅋㅋ 그래도 조금만 더 해볼게"
)
$syntheticVal = @("오늘은 테스트하는 날이라서 새로운 문장을 하나 써봤어")
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($train, [string[]]@($syntheticTrain | ForEach-Object { @{text=$_} | ConvertTo-Json -Compress }), $utf8)
[System.IO.File]::WriteAllLines($valid, [string[]]@($syntheticVal | ForEach-Object { @{text=$_} | ConvertTo-Json -Compress }), $utf8)
$py = Join-Path $PWD ".venv-gemma4\Scripts\python.exe"
& $py .\tools\train_persona_gemma4.py --train $train --validation $valid --output $out --max-steps 2 --seq-len 32 --approve-private-training --confirm-rights --confirm-privacy-review
if ($LASTEXITCODE -ne 0) { throw "Gemma4 synthetic E2E failed; do not treat as real corpus clearance." }
Write-Host "Synthetic-only E2E done. Private aggregate report:" (Join-Path $out "training-summary.json")
