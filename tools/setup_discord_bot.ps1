$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = 'src'
& .\.venv-gemma4\Scripts\python.exe -m echomate_bot --setup
if ($LASTEXITCODE -ne 0) { throw 'Local bot setup failed.' }
