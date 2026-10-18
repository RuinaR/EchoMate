# ASCII-only Windows PowerShell 5.1 compatible synthetic Korean Gemma4 E2E QA.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$root = Join-Path $PWD "local_data\gemma4-synthetic-e2e"
New-Item -ItemType Directory -Force -Path $root | Out-Null
$train = Join-Path $root "train.jsonl"
$valid = Join-Path $root "validation.jsonl"
$out = Join-Path $root "adapter"
if (Test-Path $out) { throw "Synthetic adapter destination already exists: $out. Do not overwrite existing results." }
# Fixed invented Korean sentences are encoded so the PowerShell source remains ASCII.
function Decode-Utf8Base64([string]$encoded) {
    return [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($encoded))
}
$syntheticTrain = @(
    (Decode-Utf8Base64 "7JWI64WVIOyYpOuKmCDqsozsnoQg7KeE7KecIOyerOuwjOyXiOyWtCDjhYvjhYsg64uk7J2M7JeQ64+EIO2VtOuztOyekA=="),
    (Decode-Utf8Base64 "7JWEIOydtOqxsCDsmZwg7J2066CH6rKMIOyWtOugteuDkCDjhYvjhYsg6re4656Y64+EIOyhsOq4iOunjCDrjZQg7ZW067O86rKM")
)
$syntheticVal = @((Decode-Utf8Base64 "7Jik64qY7J2AIO2FjOyKpO2KuO2VmOuKlCDrgqDsnbTrnbzshJwg7IOI66Gc7Jq0IOusuOyepeydhCDtlZjrgpgg7I2o67Sk7Ja0"))
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($train, [string[]]@($syntheticTrain | ForEach-Object { @{text=$_} | ConvertTo-Json -Compress }), $utf8)
[System.IO.File]::WriteAllLines($valid, [string[]]@($syntheticVal | ForEach-Object { @{text=$_} | ConvertTo-Json -Compress }), $utf8)
$py = Join-Path $PWD ".venv-gemma4\Scripts\python.exe"
& $py .\tools\train_persona_gemma4.py --train $train --validation $valid --output $out --max-steps 2 --seq-len 32 --approve-private-training --confirm-rights --confirm-privacy-review
if ($LASTEXITCODE -ne 0) { throw "Gemma4 synthetic E2E failed; do not treat as real corpus clearance." }
Write-Host "Synthetic-only E2E done. Private aggregate report:" (Join-Path $out "training-summary.json")
