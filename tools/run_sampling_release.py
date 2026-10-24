"""Sealed greedy/native sampling study; actual Runtime and SDK HTTP mock.

No final316, paid APIs, operating stores, downloads, automatic promotion or
best-of-N reranking. Two seeds report variability, not cherry-picked output.
"""
import argparse
import asyncio
import hashlib
from pathlib import Path
import time
from unittest.mock import patch
from dialogue_eval_core import private_root,save,report_html,metrics_since
from diagnose_persona_pipeline import runtime_answer
from sampling_diagnosis import sampling,SEEDS,PARAMETERS


def protocol():
    return [
        dict(id='radio',phase='quality',text='동네 벼룩시장에서 오래된 라디오를 봤어. 예쁘지만 고장났대. 구경만 할까 가져와 볼까? 네 생각을 두 문장으로 말해 줘.'),
        dict(id='process',phase='quality',text='친구가 결과는 비슷하니 과정은 대충 생략하자는데 나는 조금 찜찜해. 너라면 어떤 점부터 따져볼래? 두 문장으로 말해 줘.'),
        dict(id='future',phase='facts',text='나는 잎 모양 책갈피가 마음에 들어. 두 달 뒤쯤 네가 먼저 이 얘기를 꺼내 주면 좋겠어. 어떻게 생각해?'),
        dict(id='unconfirmed-past',phase='facts',text='지난번 카페에서 우리 둘이 고른 음료 있잖아. 네 건 뭐였지? 근거로 아는 것만 말해 줘.')]


async def run(args):
    from echomate_bot.inference import LocalBackend
    from echomate_bot.model_registry import ModelRegistry,ModelValidator
    from echomate_bot.character_profiles import presets
    from echomate_bot.loader_memory import loading_reserve,MemoryRecorder,memory_snapshot
    from echomate_bot.instance import InstanceLease
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.telemetry import distribution
    root=private_root(args.output);root.mkdir(parents=True,exist_ok=False)
    cases=protocol();people=presets()
    save(root/'seal.json',dict(cases=cases,profiles=people,seeds=SEEDS,sampling=PARAMETERS,greedy=dict(do_sample=False),
        versions={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path('tools/sampling_diagnosis.py'),*Path('src/echomate_bot').glob('*.py')]},
        gate='No factual/permission regressions; character strategy remains distinct across both seeds and new sources; no latency/memory regression. No judge-only adoption.',
        planned='48 Runtime messages; same input/profile/768 cap; one resident model; no extra semantic judge/best-of-N. Initial SLO is tracked separately, not a retroactive score.'))
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:raise ValueError('Existing compatible model required')
    health=check_resources()
    if health['free_vram_mib']<10240:raise RuntimeError('Need 10GiB free VRAM')
    model_memory_budget(*loading_reserve(entry));lease=InstanceLease();backend=LocalBackend(adapter=None)
    resolve=ModelRegistry.resolve;rows=[];started=time.monotonic();summary=dict(before=memory_snapshot(),health=health);recorder=None
    try:
        with MemoryRecorder(interval=1) as recorder,patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)),\
             patch('discord.http.HTTPClient.request',side_effect=AssertionError('No live Discord')),\
             patch('aiohttp.ClientSession._request',side_effect=AssertionError('No external HTTP')):
            t=time.monotonic();await backend.ready();await backend.probe();summary['load_seconds']=time.monotonic()-t
            for i,case in enumerate(cases):
                for j,(key,profile) in enumerate(people.items()):
                    arms=(None,*SEEDS) if (i+j)%2 else (*SEEDS,None)
                    for seed in arms:
                        if time.monotonic()-started>1500:raise TimeoutError('Bounded sampling study')
                        check_resources();cursor=backend.metrics[-1];t=time.monotonic();arm='greedy' if seed is None else str(seed)
                        with sampling(backend,seed):detail=await runtime_answer(backend,profile,case['text'],root/f'{case["id"]}-{key}-{arm}')
                        rows.append(dict(record_id=f'{case["id"]}-{key}-{arm}',case=case['id'],phase=case['phase'],profile=key,arm=arm,
                            seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor),**detail))
                        save(root/'results-private.json',rows);print('RESPONSE',len(rows),case['id'],key,arm,len(detail['sent']),flush=True)
                        if backend.failed:raise RuntimeError('Backend safety stop')
            summary.update(status='COMPLETED_NOT_RELEASE_PASS',conditions={arm:dict(n=len(g),seconds=distribution([r['seconds'] for r in g]),
                calls=sum(len(r['calls']) for r in g),sends=sum(len(r['sent']) for r in g),pending=sum(r['pending'] for r in g))
                for arm in ('greedy',*map(str,SEEDS)) for g in [[r for r in rows if r['arm']==arm]]})
    except BaseException as exc:
        summary.update(status='STOPPED',error=type(exc).__name__);raise
    finally:
        await backend.close();lease.close();summary.update(after=memory_snapshot(),elapsed=time.monotonic()-started)
        if recorder:summary['memory']=recorder.report()
        save(root/'summary.json',summary);report_html(root/'report.html',rows,summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--output',required=True)
    asyncio.run(run(p.parse_args()))
