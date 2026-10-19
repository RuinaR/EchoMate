"""Offline isolated installation probe; optional GPU preview, never Discord."""
import json
from pathlib import Path
import sys

def run(output,gpu=False,model_path=None):
    import os,time
    if not os.environ.get('ECHOMATE_DATA_HOME'):raise RuntimeError('Installation probe requires an isolated ECHOMATE_DATA_HOME')
    if model_path and not gpu:raise ValueError('Model selection probe requires explicit GPU mode')
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
    preview_generated=False;preview_no_companion_writes=None
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
        if model_path:
            from .model_registry import ModelValidator
            entry=ModelValidator().validate(model_path)
            if not entry.compatible:raise ValueError('Packaged model structure invalid')
            controller.submit('models',roots=[str(Path(model_path).resolve())])
            until(lambda:any(m.id==entry.id for m in getattr(controller,'models',[])))
            controller.submit('settings',values={'model':entry.id})
            until(lambda:controller.settings.get()['model']==entry.id and not getattr(controller,'model_preparing',False),seconds=180)
        if gpu:
            # LocalController already owns the isolated installation's lease.
            controller.submit('preview',text='캐시가 무엇인지 두 문장으로 설명해 줘')
            until(lambda:getattr(controller,'preview_task',None) is not None,seconds=10)
            until(lambda:controller.preview_task.done(),seconds=180)
            preview=controller.preview_result
            preview_generated=bool(preview and not preview.startswith(('미리보기 실패','로컬에서 답변','미리보기를 취소')))
            if not preview_generated:raise RuntimeError('Packaged GPU preview failed')
            Path(output).with_suffix('.preview-private.json').write_text(json.dumps(dict(text=preview),ensure_ascii=False),encoding='utf-8')
            preview_no_companion_writes=not (controller.companion.users(2) or controller.companion.memories(2) or controller.companion.reminders(2))
            if not preview_no_companion_writes:raise AssertionError('Preview wrote companion data')
    finally:
        controller.submit('shutdown');until(controller.closed.is_set)
        app.destroy();app=None;root=None
        import gc;gc.collect()
    from .settings import Settings
    bootstrap=load_bootstrap(ROOT/'bootstrap.json')
    restored=Settings(bootstrap['owner_id'],bootstrap['signing_key'],ROOT/'settings.json').get()
    assert restored['character_profile']['energy']==25 and not restored['enabled']
    if model_path:assert restored['model']==entry.id
    result=dict(python=sys.version.split()[0],discord=discord.__version__,torch=torch.__version__,transformers=transformers.__version__,
                cuda_available=torch.cuda.is_available(),tk=True,gemma4_import=True,model_discovery=len(ModelRegistry().scan()),
                local_data_isolated=True,first_run=first_run,encrypted_setup=True,profile_saved=True,restart_settings=True,frontend_closed=True,
                discord_connected=False,weights_loaded=preview_generated,preview_generated=preview_generated,
                preview_no_companion_writes=preview_no_companion_writes)
    result['selected_model_verified']=bool(model_path)
    Path(output).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--gpu',action='store_true');p.add_argument('--model-path');a=p.parse_args()
    run(a.output,gpu=a.gpu,model_path=a.model_path)
