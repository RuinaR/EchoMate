"""Bounded verifier calibration + old/new Runtime SDK checks, one local Gemma.

Baseline Runtime is read from an explicit local commit. Current store APIs keep
their old no-receipt behavior for that overlay; this is not a full old checkout.
No live HTTP, credentials, operating stores, downloads or automatic adoption.
"""
import argparse
import asyncio
import hashlib
import importlib.metadata
from pathlib import Path
import re
import subprocess
import sys
import time
import types
from unittest.mock import patch
from dialogue_eval_core import private_root,save,metrics_since,report_html
from diagnose_persona_pipeline import runtime_answer
from operation_verifier_probe import calibration,confirmation,messages,gate


def baseline_runtime(revision):
    from echomate_bot.processes import background_options
    if not re.fullmatch(r'[a-f0-9]{40}',revision):raise ValueError('Explicit baseline commit SHA required')
    source=subprocess.check_output(['git','show',revision+':src/echomate_bot/runtime.py'],**background_options()).decode('utf-8')
    module=types.ModuleType('echomate_bot._grounding_baseline');module.__package__='echomate_bot'
    sys.modules[module.__name__]=module
    exec(compile(source,'sealed-baseline-runtime.py','exec'),module.__dict__)
    return module.Runtime,source


def setup_case(kind,refs):
    def setup(runtime,store,settings):
        store.set_consent(2,4,'relationships',True);store.set_affinity(2,4,75)
        if kind=='memory':store.set_consent(2,4,'memory',True)
        transport=runtime.transport;refs.append(transport);original=transport.http.get_message;changed=[]
        async def read(channel,mid):
            value=await original(channel,mid)
            if mid==100 and kind!='healthy' and not changed:
                changed.append(True)
                if kind=='memory':store.delete_personal(2,4,'memory')
                elif kind=='reminder':
                    row=store.reminders(2,4,active=True)[0]
                    store.change_reminder(2,4,row['reminder_id'],text='수정한 합성 알림')
                elif kind=='subject':store.set_consent(2,4,'relationships',False)
            return value
        transport.http.get_message=read
    return setup


async def run(args):
    from echomate_bot.inference import LocalBackend
    from echomate_bot.model_registry import ModelRegistry,ModelValidator
    from echomate_bot.character_profiles import presets
    from echomate_bot.instance import InstanceLease
    from echomate_bot.loader_memory import loading_reserve,MemoryRecorder,memory_snapshot
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.telemetry import distribution
    root=private_root(args.output);root.mkdir(parents=True,exist_ok=False)
    old,source=baseline_runtime(args.baseline);cohort=calibration()
    (root/'baseline-runtime.py').write_text(source,encoding='utf-8')
    save(root/'seal.json',dict(baseline=args.baseline,baseline_condition='old Runtime overlay; current backward-compatible store without receipts',
        calibration=cohort,confirmation=confirmation(),gate='accuracy>=.90; unsafe misses=0; false vetoes=0; label permutation agreement>=.90',
        files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path('tools/operation_verifier_probe.py'),*Path('src/echomate_bot').glob('*.py')]},
        versions={name:importlib.metadata.version(name) for name in ('torch','transformers','bitsandbytes','discord.py')},
        healthy='처음 보는 사람들과 작은 모임을 시작할 때 어색함을 풀 아이디어 하나만 말해 줘. 두 문장 이내로.',
        safety='No live network; same one resident existing Gemma; final316 not accessed'))
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:raise ValueError('Existing validated Gemma required')
    health=check_resources()
    if health['free_vram_mib']<10240:raise RuntimeError('Need 10GiB free VRAM')
    model_memory_budget(*loading_reserve(entry))
    lease=InstanceLease();backend=LocalBackend(adapter=None);resolve=ModelRegistry.resolve
    rows=[];judged=[];recorder=None;start=time.monotonic();summary=dict(before=memory_snapshot(),health=health,status='RUNNING')
    try:
        with MemoryRecorder(interval=1) as recorder,\
             patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)),\
             patch('discord.http.HTTPClient.request',side_effect=AssertionError('No live Discord')),\
             patch('aiohttp.ClientSession._request',side_effect=AssertionError('No external inference')):
            t=time.monotonic();await backend.ready();await backend.probe();summary['load_seconds']=time.monotonic()-t
            for i,case in enumerate(cohort):
                for order in (i%2,1-i%2):
                    if time.monotonic()-start>1200:raise TimeoutError('Bounded experiment')
                    check_resources();ms,mapping=messages(case,order);cursor=backend.metrics[-1];t=time.monotonic()
                    label=(await backend._job(ms,weight='base',budget=8,choices=('A','B','C'))).strip()
                    row=dict(record_id=f'calibration-{case["id"]}-{order}',phase='calibration',case=case['id'],order=order,
                        gold=case['gold'],predicted=mapping.get(label,'invalid'),output=label,
                        seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor))
                    judged.append(row);rows.append(row);save(root/'results-private.json',rows)
                print('CALIBRATED',i+1,flush=True)
            summary['verifier_gate']=gate(judged)
            if summary['verifier_gate']['eligible']:
                checked=[]
                for case in confirmation():
                    for order in (0,1):
                        check_resources();ms,mapping=messages(case,order);cursor=backend.metrics[-1];t=time.monotonic()
                        label=(await backend._job(ms,weight='base',budget=8,choices=('A','B','C'))).strip()
                        row=dict(record_id=f'confirmation-{case["id"]}-{order}',phase='confirmation',case=case['id'],order=order,
                            gold=case['gold'],predicted=mapping.get(label,'invalid'),output=label,seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor))
                        checked.append(row);rows.append(row);save(root/'results-private.json',rows)
                summary['confirmation_gate']=gate(checked,phase='confirmation')
            # No feedback tuning: failed calibration cannot become a runtime veto.
            summary['verifier_runtime_enabled']=False
            profiles=presets();healthy='처음 보는 사람들과 작은 모임을 시작할 때 어색함을 풀 아이디어 하나만 말해 줘. 두 문장 이내로.'
            import echomate_bot.runtime as runtime_module
            for i,(key,profile) in enumerate(profiles.items()):
                for arm in (('old','new') if i%2==0 else ('new','old')):
                    refs=[];cursor=backend.metrics[-1];t=time.monotonic()
                    with patch.object(runtime_module,'Runtime',old if arm=='old' else runtime_module.Runtime):
                        detail=await runtime_answer(backend,profile,healthy,root/f'healthy-{key}-{arm}',configure=setup_case('healthy',refs))
                    rows.append(dict(record_id=f'healthy-{key}-{arm}',phase='healthy',arm=arm,profile=key,kind='healthy',
                        seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor),sdk_http_sends=len(refs[0].http.sends),**detail))
                    save(root/'results-private.json',rows);print('HEALTHY',key,arm,flush=True)
            for kind,text in [('memory','나는 노란 머그를 좋아해. 기억해 줘'),
                              ('reminder','20분 뒤에 물 마시라고 알려줘'),('subject',healthy)]:
                for arm in ('old','new'):
                    refs=[];cursor=backend.metrics[-1];t=time.monotonic()
                    with patch.object(runtime_module,'Runtime',old if arm=='old' else runtime_module.Runtime):
                        detail=await runtime_answer(backend,profiles['playful'],text,root/f'race-{kind}-{arm}',configure=setup_case(kind,refs))
                    rows.append(dict(record_id=f'race-{kind}-{arm}',phase='race',arm=arm,kind=kind,
                        seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor),sdk_http_sends=len(refs[0].http.sends),**detail))
                    save(root/'results-private.json',rows);print('RACE',kind,arm,flush=True)
            healthy_rows=[r for r in rows if r['phase']=='healthy']
            summary.update(status='COMPLETED_NOT_RELEASE_PASS',conditions={arm:dict(
                n=len(group),seconds=distribution([r['seconds'] for r in group]),calls=sum(len(r['calls']) for r in group))
                for arm in ('old','new') for group in ([r for r in healthy_rows if r['arm']==arm],)},
                preservation={key:dict(inputs_equal=a['captured']==b['captured'],outputs_equal=a['output']==b['output'])
                    for key in profiles for a,b in [tuple(next(r for r in healthy_rows if r['profile']==key and r['arm']==arm) for arm in ('old','new'))]})
    except BaseException as exc:
        summary.update(status='STOPPED',error=type(exc).__name__);raise
    finally:
        await backend.close();lease.close();summary.update(after=memory_snapshot(),elapsed=time.monotonic()-start)
        if recorder is not None:summary['memory']=recorder.report()
        save(root/'summary.json',summary);report_html(root/'report.html',rows,summary)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--model',required=True)
    parser.add_argument('--output',required=True);parser.add_argument('--baseline',required=True)
    asyncio.run(run(parser.parse_args()))
