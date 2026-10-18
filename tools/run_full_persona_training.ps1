# Local Windows PowerShell 5.1 - approved private Gemma4 long-run launcher.
param(
    [string]$Train = "local_data\reviewed\train.jsonl",
    [string]$Validation = "local_data\reviewed\validation.jsonl",
    [int]$Steps = 300,
    [int]$SeqLen = 128,
    [switch]$ConfirmRights,
    [switch]$ConfirmPrivacyReview,
    [switch]$ApprovePrivateTraining
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not ($ConfirmRights -and $ConfirmPrivacyReview -and $ApprovePrivateTraining)) {
    throw "Training not approved: three explicit confirmations required."
}
$py = Join-Path $PWD ".venv-gemma4\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing .venv-gemma4 Python." }
if (-not (Test-Path $Train) -or -not (Test-Path $Validation)) {
    throw "Reviewed train/validation JSONL not found. NOT-APPROVED archive must never be promoted automatically."
}
$stamp = [DateTime]::UtcNow.ToString("yyyyMMdd-HHmmss-fffffff")
$preflight = Join-Path $PWD ("local_data\full-preflight-" + $stamp + ".json")
& $py .\tools\gemma4_corpus_preflight.py --train $Train --validation $Validation --output $preflight
if ($LASTEXITCODE -ne 0) {
    throw "Private corpus preflight blocked training; inspect aggregate-only report: $preflight"
}
$out = Join-Path $PWD ("local_data\persona-adapters\gemma4-full-" + $stamp)
& $py .\tools\train_persona_gemma4_full.py --train $Train --validation $Validation --output $out --steps $Steps --seq-len $SeqLen --approve-private-training --confirm-rights --confirm-privacy-review
if ($LASTEXITCODE -ne 0) { throw "Local training failed. Inspect local-only run directory." }
Write-Host "Training metrics:" (Join-Path $out "summary.json")
