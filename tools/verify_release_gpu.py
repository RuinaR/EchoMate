"""Offline old/new Discord output-policy probe; private fixtures/results only."""
import argparse
import asyncio
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from echomate_bot.inference import LocalBackend
from echomate_bot.instance import InstanceLease
from echomate_bot.settings import DEFAULTS,private_path,atomic_private_json
from echomate_bot.adult_policy import turn_profile
from echomate_bot.output_policy import contains_code
from echomate_bot.telemetry import distribution

async def run(root,fixtures):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend();rows=[]
    protocol=json.loads(fixtures.read_text(encoding='utf-8-sig'));atomic_private_json(root/'protocol-private.json',protocol)
    for p in Path('src').rglob('*.py'):
        target=root/'source'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    source=root/'baseline-inference.py';source.write_bytes(subprocess.check_output(['git','show','d1b2d6a:src/echomate_bot/inference.py']))
    spec=importlib.util.spec_from_file_location('echomate_bot._release_previous',source);old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
    old_character={};exec(subprocess.check_output(['git','show','d1b2d6a:src/echomate_bot/character.py']).decode('utf-8').replace('from .adult_policy import','from echomate_bot.adult_policy import'),old_character)
    old.instruction=old_character['instruction']
    try:
        await backend.ready()
        for _ in range(2):await backend.text([dict(role='user',content='안녕')],dict(DEFAULTS,model='base'))
        for mode in ('base',):
            cfg=turn_profile(dict(DEFAULTS,model=mode),age_restricted=True)
            for i,case in enumerate(protocol['cases']):
                for variant in (('old','new') if i%2==0 else ('new','old')):
                    before=len(backend.metrics);start=time.monotonic()
                    try:
                        context=case['context']
                        answer=await (old.LocalBackend.text(backend,context,cfg) if variant=='old' else backend.text(context,cfg))
                        row=dict(mode=mode,case=i,variant=variant,text=answer,seconds=time.monotonic()-start,code=contains_code(answer),valid=True,
                            facts=all(any(w in answer for w in group) for group in case.get('fact_groups',[])),metrics=backend.metrics[before:])
                    except (ValueError,RuntimeError) as exc:row=dict(mode=mode,case=i,variant=variant,valid=False,error=type(exc).__name__,seconds=time.monotonic()-start,metrics=backend.metrics[before:])
                    rows.append(row);atomic_private_json(root/'responses-private.json',rows)
                    print(json.dumps({k:v for k,v in row.items() if k not in ('text','metrics')}),flush=True)
        summary=[]
        for mode in ('base',):
            for variant in ('old','new'):
                xs=[r for r in rows if (r['mode'],r['variant'])==(mode,variant)]
                calls=[m for x in xs for m in x['metrics']]
                summary.append(dict(mode=mode,variant=variant,cases=len(xs),valid=sum(x['valid'] for x in xs),code=sum(x.get('code',False) for x in xs),fact_pass=sum(x.get('facts',False) for x in xs),latency=distribution([x['seconds'] for x in xs]),ttft=distribution([m['ttft_seconds'] for m in calls]),vram_mib=max((m['peak_allocated_mib'] for m in calls),default=0)))
        atomic_private_json(root/'summary.json',dict(real_gpu=True,real_discord=False,baseline='d1b2d6a',results=summary,warning='Synthetic small corpus; code detector and narrow facts are not a full language or human quality evaluation.'))
    finally:
        try:await backend.close()
        finally:lease.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--fixtures',required=True);a=parser.parse_args()
    asyncio.run(run(private_path(a.output),private_path(a.fixtures)))
