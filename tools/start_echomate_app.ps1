param([switch]$Legacy)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = 'src'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$entryModule = if ($Legacy) { 'echomate_bot.desktop' } else { 'echomate_bot.lime_desktop' }
Start-Process -FilePath '.\.venv-gemma4\Scripts\pythonw.exe' -ArgumentList '-m',$entryModule -WorkingDirectory (Get-Location).Path -WindowStyle Normal
