"""Offline installation probe; never logs in, loads weights or touches user DBs."""
import json
from pathlib import Path
import sys

def run(output):
    import os,time
    if not os.environ.get('ECHOMATE_DATA_HOME'):raise RuntimeError('Installation probe requires an isolated ECHOMATE_DATA_HOME')
    import tkinter as tk
    import discord,torch,transformers,bitsandbytes
    from transformers.models.gemma4_unified import Gemma4UnifiedForConditionalGeneration
    from .settings import ROOT,DEFAULTS,validate
    from .model_registry import ModelRegistry
    from .character_profiles import DEFAULT_PROFILE,compile_profile
    validate(dict(DEFAULTS));assert compile_profile(DEFAULT_PROFILE)
    # Exercise the packaged frontend/controller, encrypted first run and restart
    # without API access or any native desktop input.
    from .desktop import LocalController
    from .desktop_ui import DesktopApp
    from .character_profiles import DEFAULT_PROFILE
    from .onboarding import load_bootstrap
    first_run=not (ROOT/'bootstrap.json').exists()
    async def forbidden(*args,**kwargs):raise AssertionError('Network forbidden in distribution check')
    discord.Client.login=forbidden;discord.Client.start=forbidden
    root=tk.Tk();root.withdraw();controller=LocalController();app=DesktopApp(root,controller)
    def until(check,seconds=8):
        deadline=time.monotonic()+seconds
        while not check() and time.monotonic()<deadline:root.update();time.sleep(.02)
        if not check():raise RuntimeError('Isolated frontend stage timed out')
    try:
        until(lambda:controller.loop is not None and hasattr(controller,'settings'))
        if first_run:
            controller.submit('setup',owner='1',token='synthetic-installation-token-12345')
            until(lambda:controller.settings is not None)
        controller.submit('profiles',action='save',key='probe',value=dict(DEFAULT_PROFILE,name='설치 확인',energy=25))
        until(lambda:'probe' in getattr(controller,'profiles_view',{}))
        controller.submit('profiles',action='apply',key='probe')
        until(lambda:controller.settings.get()['character_profile'].get('energy')==25)
        controller.submit('models');until(lambda:bool(getattr(controller,'notice','')))
    finally:
        controller.submit('shutdown');until(controller.closed.is_set)
        app.destroy();app=None;root=None
        import gc;gc.collect()
    from .settings import Settings
    bootstrap=load_bootstrap(ROOT/'bootstrap.json')
    restored=Settings(bootstrap['owner_id'],bootstrap['signing_key'],ROOT/'settings.json').get()
    assert restored['character_profile']['energy']==25 and not restored['enabled']
    result=dict(python=sys.version.split()[0],discord=discord.__version__,torch=torch.__version__,transformers=transformers.__version__,
                cuda_available=torch.cuda.is_available(),tk=True,gemma4_import=True,model_discovery=len(ModelRegistry().scan()),
                local_data_isolated=True,first_run=first_run,encrypted_setup=True,profile_saved=True,restart_settings=True,frontend_closed=True,
                discord_connected=False,weights_loaded=False)
    Path(output).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':run(sys.argv[1])
