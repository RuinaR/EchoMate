@echo off
cd /d "%~dp0"
set "PYTHONPATH=src"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
start "" ".venv-gemma4\Scripts\pythonw.exe" -m echomate_bot.desktop
