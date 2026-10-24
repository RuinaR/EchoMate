"""Sealed A/B/C actual Runtime, one resident Gemma, SDK HTTP mock only."""
import argparse
import asyncio
import hashlib
import time
from pathlib import Path
from unittest.mock import patch
from dialogue_eval_core import private_root, save, metrics_since, report_html
from diagnose_persona_pipeline import runtime_answer
from service_persona_v4 import compose


def cases():
    # Newly authored development episodes, never advertised as final holdout.
    return [
        dict(id='unequal-work',kind='strategy',text='동아리 준비는 늘 내가 하는데 친구는 결과만 같이 내자네. 싸우기는 싫어. 어떻게 볼래?'),
        dict(id='lost-label',kind='banter',text='정리 잘하려고 상자마다 라벨을 붙였는데 라벨 적힌 종이를 잃어버렸어. 가볍게 놀려 줘.'),
        dict(id='fiction-change',kind='fiction',text='네 가상 배경에서 예전 일터를 떠난 일이 지금의 판단 기준에 어떤 영향을 줬어? 설정에서 확인되는 만큼만 말해.'),
        dict(id='future-preference',kind='facts',text='나는 은회색 우산이 좋아. 두 달 뒤에도 네가 먼저 그 얘기를 꺼내 줄 수 있어?'),
        dict(id='unrecorded-event',kind='facts',text='우리 전에 온라인으로 같이 박물관 구경했잖아. 내가 어떤 전시를 제일 좋아했지? 확인되는 만큼만 얘기해.')]


async def run(args):
    from echomate_bot.character_profiles import presets
    from echomate_bot.inference import LocalBackend
    from echomate_bot.model_registry import ModelValidator, ModelRegistry
    from echomate_bot.instance import InstanceLease
    from echomate_bot.loader_memory import loading_reserve, MemoryRecorder, memory_snapshot
    from echomate_bot.processes import check_resources, model_memory_budget
    from echomate_bot.telemetry import distribution
    root=private_root(args.output);root.mkdir(parents=True,exist_ok=False)
    profiles=presets();cohort=cases()
    for p in profiles.values():p['name']='EchoMate'
    if args.confirmation:
        cohort=[dict(id='shared-credit',kind='strategy',text='친구가 내 아이디어를 자기 것처럼 소개했어. 공개적으로 따질지 따로 말할지 고민돼.'),
                dict(id='future-correction',kind='facts',text='난 남색 수첩보다 연보라 수첩이 좋아졌어. 다음 학기에도 네가 이걸 기억해서 먼저 물어봐 줄래?')]
    sources=[Path(__file__),Path('tools/service_persona_v4.py')]
    save(root/'seal.json',dict(cases=cohort,profiles=profiles,
        code={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        runtime={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/echomate_bot').glob('*.py')},
        sampling=False,budget=768,cohort='new_confirmation' if args.confirmation else 'development',
        final316_consumed=0,real_discord=False,
        gates=['No additional generation stage','No extra false memory or function claims',
               'Composite response strategies differ beyond wording','Both axes improve before promotion']))
    for p in sources:(root/p.name).write_bytes(p.read_bytes())
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:raise ValueError('Existing compatible Gemma required')
    health=check_resources()
    if health['free_vram_mib']<10240:raise RuntimeError('Need 10GiB free VRAM')
    model_memory_budget(*loading_reserve(entry))
    lease=InstanceLease();backend=LocalBackend(adapter=None);resolve=ModelRegistry.resolve
    rows=[];summary=dict(before=memory_snapshot(),health=health,status='RUNNING');recorder=None
    started=time.monotonic()
    try:
        with MemoryRecorder(interval=1) as recorder,\
             patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)),\
             patch('discord.http.HTTPClient.request',side_effect=AssertionError('No live Discord')),\
             patch('aiohttp.ClientSession._request',side_effect=AssertionError('No external inference')):
            loading=time.monotonic();await backend.ready();await backend.probe()
            summary['load_seconds']=time.monotonic()-loading
            for i,case in enumerate(cohort):
                for j,(key,profile) in enumerate(profiles.items()):
                    arms=['A','B','C'];offset=(i+j)%3;arms=arms[offset:]+arms[:offset]
                    for arm in arms:
                        if time.monotonic()-started>2400:raise TimeoutError('Bounded cohort expired')
                        check_resources();cursor=backend.metrics[-1];captures=[];t=time.monotonic()
                        def assembled(messages,p,f,tokenizer,**kw):
                            result,info=compose(messages,p,f,tokenizer,arm=arm,**kw)
                            captures.append(dict(messages=result,audit=info,
                                prompt_hash=hashlib.sha256(str(result).encode()).hexdigest()))
                            return result,info
                        with patch('echomate_bot.character_card.augment',side_effect=assembled):
                            detail=await runtime_answer(backend,profile,case['text'],root/f'{case["id"]}-{key}-{arm}')
                        rows.append(dict(record_id=f'{case["id"]}-{key}-{arm}',phase=arm,arm=arm,
                            case=case['id'],kind=case['kind'],profile=key,seconds=time.monotonic()-t,
                            calls=metrics_since(backend.metrics,cursor),final_inputs=captures,**detail))
                        save(root/'results-private.json',rows)
                        print('DONE',len(rows),case['id'],key,arm,flush=True)
            summary.update(status='MEASURED_NOT_QUALITY_PASS',memory=recorder.report(),conditions={
                arm:dict(n=len(group),seconds=distribution([r['seconds'] for r in group]),
                    calls=sum(len(r['calls']) for r in group),sends=sum(len(r['sent']) for r in group),
                    reply_errors=sum(s.get('sdk_reply')!=s['source'] for r in group for s in r['sent']),
                    retries=sum(max(0,len(r['final_inputs'])-1) for r in group),
                    c_fallbacks=sum(c['audit']['fallback'] for r in group for c in r['final_inputs']))
                for arm in ('A','B','C') for group in ([r for r in rows if r['arm']==arm],)})
    except BaseException as exc:
        summary.update(status='STOPPED',error=type(exc).__name__);raise
    finally:
        await backend.close();lease.close();summary.update(after=memory_snapshot(),elapsed=time.monotonic()-started)
        if recorder is not None:summary.setdefault('memory',recorder.report())
        save(root/'summary.json',summary);report_html(root/'report.html',rows,summary)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--model',required=True)
    parser.add_argument('--output',required=True);parser.add_argument('--confirmation',action='store_true')
    asyncio.run(run(parser.parse_args()))
