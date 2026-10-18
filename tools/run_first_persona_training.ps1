# PowerShell 5.1 / local-only first-owner-corpus training, never uploads data.
param(
    [string]$Train = "local_data\persona-dataset\persona-train.jsonl",
    [string]$Validation = "local_data\persona-dataset\persona-validation.jsonl",
    [switch]$ConfirmRights,
    [switch]$ConfirmPrivacyReview,
    [switch]$ApprovePrivateTraining
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not ($ConfirmRights -and $ConfirmPrivacyReview -and $ApprovePrivateTraining)) {
    throw "Explicit rights, contextual privacy review and training approval switches are all required."
}
$py = Join-Path $PWD ".venv-gemma4\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing local Gemma4 environment." }
if (-not (Test-Path $Train) -or -not (Test-Path $Validation)) {
    throw "Approved private local train/validation JSONL not found. No source data is built automatically."
}
$stamp = [DateTime]::UtcNow.ToString("yyyyMMdd-HHmmss-fffffff")
$report = Join-Path $PWD ("local_data\gemma4-corpus-preflight-" + $stamp + ".json")
& $py .\tools\gemma4_corpus_preflight.py --train $Train --validation $Validation --output $report
if ($LASTEXITCODE -ne 0) { throw "Preflight requires review. No private training was started. Inspect aggregate report locally: $report" }
$out = Join-Path $PWD ("local_data\persona-adapters\gemma4-first-" + $stamp)
& $py .\tools\train_persona_gemma4.py --train $Train --validation $Validation --output $out --max-steps 2 --seq-len 32 --include-short-samples --approve-private-training --confirm-rights --confirm-privacy-review
if ($LASTEXITCODE -ne 0) { throw "Local training failed. See private run artifacts; do not publish adapter." }
Write-Host "Local first-run adapter saved:" $out
