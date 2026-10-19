"""Source installs retain local_data; distributed installs use per-user storage."""
import os
import sys
from pathlib import Path

APP_HOME=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[2]
DATA_HOME=Path(os.environ.get('ECHOMATE_DATA_HOME') or (Path(os.environ.get('LOCALAPPDATA',Path.home()))/'EchoMate'/'local_data' if getattr(sys,'frozen',False) or os.environ.get('ECHOMATE_DISTRIBUTED')=='1' else APP_HOME/'local_data')).resolve()
MODEL_HOME=APP_HOME/'models'
