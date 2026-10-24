"""Sealed field-availability A/B. One existing model, SDK HTTP mock only.

Tests omitted fictional facts, not a validated autonomous persona judge. Old
augment comes from an explicit trusted local Git SHA; no untrusted code loads.
"""
import argparse
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import types
from unittest.mock import patch
from dialogue_eval_core import private_root,save,metrics_since,report_html
from diagnose_persona_pipeline import runtime_answer


def profiles():
    from echomate_bot.character_profiles import presets
    result=presets()
    ends={
        'supportive':('거절할 권리를 무시한 강제 봉사 배치 때문에 떠났다.','강제','부드러운 일상 어휘. 상대가 안 해도 괜찮다는 선택을 먼저 열어 준다.'),
        'playful':('실패작을 전시하지 못하게 한 경연 규정 때문에 떠났다.','실패작','친근한 구어체. 정답보다 엉뚱한 시도 하나를 먼저 제안한다.'),
        'analytical':('원본 관측 수치를 삭제하라는 지시 때문에 떠났다.','수치','정확하고 짧은 일상 어휘. 확인한 것과 추측을 구분한다.'),
        'dry':('고장 난 의자를 포장만 바꿔 팔라는 요구 때문에 떠났다.','의자','꾸밈없는 구어체. 멋있는 말보다 실제로 작동하는지 먼저 묻는다.')}
    for key,p in result.items():
        p['name']='EchoMate';c=p['card'];c['lore']=[];c['examples']=[]
        c['background']=('허구의 강변 마을에서 공동 작업장을 운영했다. 마을 사람들은 낮에는 각자의 일을 하고 저녁에는 작은 광장에 모였다. '
            '처음에는 창문을 닦고 물건을 분류하고 방문객의 이야기를 듣는 평범한 날들이 계속되었다. '
            '일을 그만둔 결정적 계기는 '+ends[key][0])
        assert c['background'].index(ends[key][0])>100
        c['vocabulary']=ends[key][2];c['opening']='상투적인 인사 없이 지금 상대가 말한 구체적인 부분에 바로 반응한다.'
    return result,{k:v[1] for k,v in ends.items()}


def cases():
    return dict(
        background='네 가상 설정에서 그 작업장을 그만둔 결정적인 이유가 뭐야? 설정에 있는 것만 한두 문장으로 말해 줘.',
        strategy='모임에서 다들 멋진 계획만 세우고 아무것도 안 하네. 나는 회의도 지쳤어. 네 생각을 짧게 말해 줘.',
        unknown='내가 좋아하는 음식이 뭐였더라? 지금 근거로 아는 것만 말해 줘.',
        confirmation='그 가상 마을에서 다시 일하자고 제안받으면 어떤 조건부터 확인할 거야? 두 문장 이내로 말해 줘.')


def old_augment(revision):
    from echomate_bot.processes import background_options
    if not re.fullmatch('[a-f0-9]{40}',revision):raise ValueError('Explicit local baseline SHA required')
    source=subprocess.check_output(['git','show',revision+':src/echomate_bot/character_card.py'],**background_options()).decode('utf-8')
    module=types.ModuleType('echomate_bot._old_card');module.__package__='echomate_bot'
    exec(compile(source,'sealed-old-card.py','exec'),module.__dict__)
    return module.augment,source


async def run(args):
    from echomate_bot.inference import LocalBackend
    from echomate_bot.model_registry import ModelRegistry,ModelValidator
    from echomate_bot.instance import InstanceLease
    from echomate_bot.loader_memory import loading_reserve,MemoryRecorder,memory_snapshot
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.telemetry import distribution
    import echomate_bot.character_card as card
    root=private_root(args.output);root.mkdir(parents=True,exist_ok=False)
    old,source=old_augment(args.baseline);new=card.augment;people,expected=profiles();questions=cases()
    save(root/'seal.json',dict(baseline=args.baseline,profiles=people,cases=questions,expected=expected,
        source={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),*Path('src/echomate_bot').glob('*.py')]},
        conditions='Only augment payload fields differ; all other Runtime/Store APIs current. Not full previous checkout.',
        extension_gate='development background exact anchors improve, candidate>=3/4; otherwise no confirmation/unknown expansion',
        limits='Fictional source availability only. No automatic persona/naturalness certification. Final316 untouched.'))
    (root/'baseline-card.py').write_text(source,encoding='utf-8')
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:raise ValueError('Existing compatible model required')
    health=check_resources()
    if health['free_vram_mib']<10240:raise RuntimeError('Need 10GiB free VRAM')
    model_memory_budget(*loading_reserve(entry))
    lease=InstanceLease();backend=LocalBackend(adapter=None);resolve=ModelRegistry.resolve
    rows=[];summary=dict(before=memory_snapshot(),health=health);started=time.monotonic();recorder=None
    try:
        with MemoryRecorder(interval=1) as recorder,patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)),\
             patch('discord.http.HTTPClient.request',side_effect=AssertionError('No live Discord')),\
             patch('aiohttp.ClientSession._request',side_effect=AssertionError('No external HTTP')):
            t=time.monotonic();await backend.ready();await backend.probe();summary['load_seconds']=time.monotonic()-t
            async def episode(phase,kind,key,index):
                for arm in (('old','new') if index%2 else ('new','old')):
                    if time.monotonic()-started>1500:raise TimeoutError('Bounded evaluation')
                    check_resources();cursor=backend.metrics[-1];t=time.monotonic()
                    with patch.object(card,'augment',old if arm=='old' else new):
                        detail=await runtime_answer(backend,people[key],questions[kind],root/f'{phase}-{kind}-{key}-{arm}')
                    rows.append(dict(record_id=f'{phase}-{kind}-{key}-{arm}',phase=phase,kind=kind,profile=key,arm=arm,
                        seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor),anchor=expected[key] in detail['output'],**detail))
                    save(root/'results-private.json',rows);print('EPISODE',len(rows),kind,key,arm,flush=True)
            for i,key in enumerate(people):
                for kind in ('background','strategy'):await episode('development',kind,key,i)
            counts={arm:sum(r['anchor'] for r in rows if r['kind']=='background' and r['arm']==arm) for arm in ('old','new')}
            summary['background_anchors']=counts
            if counts['new']>=3 and counts['new']>counts['old']:
                for i,key in enumerate(people):
                    for kind in ('confirmation','unknown'):await episode('confirmation',kind,key,i)
            summary.update(status='COMPLETED_NOT_RELEASE_PASS',conditions={arm:dict(n=len(g),seconds=distribution([r['seconds'] for r in g]),
                calls=sum(len(r['calls']) for r in g),sdk_reply_errors=sum(not r['sdk_reply_ok'] for r in g),pending=sum(r['pending'] for r in g))
                for arm in ('old','new') for g in [[r for r in rows if r['arm']==arm]]})
    except BaseException as exc:
        summary.update(status='STOPPED',error=type(exc).__name__);raise
    finally:
        await backend.close();lease.close();summary.update(after=memory_snapshot(),elapsed=time.monotonic()-started)
        if recorder:summary['memory']=recorder.report()
        save(root/'summary.json',summary);report_html(root/'report.html',rows,summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--output',required=True);p.add_argument('--baseline',required=True)
    asyncio.run(run(p.parse_args()))
