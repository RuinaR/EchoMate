$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = 'src'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
& .\.venv-gemma4\Scripts\python.exe -m echomate_bot
if ($LASTEXITCODE -ne 0) { throw 'Bot stopped; see local setup guide.' }
