"""Bounded one-model diagnosis: persona CFG, multi-turn, claim extraction.

All source dialogues/outputs, annotations and metrics stay in local_data. Live
HTTP is explicitly blocked. No operating stores or final316 are accessed.
"""
import argparse
import asyncio
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import secrets
import time
from unittest.mock import patch
from dialogue_eval_core import private_root,save,metrics_since,report_html
from diagnose_persona_pipeline import runtime_answer
from persona_guidance import guidance
from korean_claim_extraction import messages,parse,compare,aggregate,calibration


def protocol():
    return dict(open='친구가 같이 한 일의 공로를 혼자 한 것처럼 말했어. 따질까 그냥 넘길까 고민돼. 네 생각을 두세 문장으로 말해 줘.',
        turns=['동아리에서 내가 만든 안내문을 친구가 자기 작품이라고 말했어. 나도 괜히 싸우기는 싫어. 네 생각은 어때?',
               '설명을 요구했더니 친구가 장난이었다고 해. 내가 너무 예민한 거야? 짧게 말해 줘.',
               '오늘은 더 따질 힘이 없어. 놀리지는 말고, 지금 할 일 하나만 말해 줘.'],
        moods=['평온','화남','피곤함'],affinities=[20,80,80])


async def sequence(backend,profile,folder,spec):
    from echomate_bot.settings import Settings
    from echomate_bot.character_profiles import SHARED_FIELDS
    from echomate_bot.companion_store import CompanionStore
    from echomate_bot.runtime import Runtime,Event
    from verify_utterance_gpu import Transport,settle
    from verify_social_gpu import Counting
    folder.mkdir();settings=Settings(1,secrets.token_hex(32),folder/'settings.json')
    settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True);settings.set(1,'character_profile',profile)
    for k in SHARED_FIELDS:settings.set(1,k,profile[k])
    store=CompanionStore(folder/'memory.sqlite3');store.set_consent(2,4,'relationships',True)
    transport=Transport();await transport.start_sdk();borrowed=Counting(backend)
    runtime=Runtime(settings,borrowed,transport,None,None,companion=store,ledger_path=folder/'sent.sqlite3')
    runtime.direct_cooldown=0;runtime.direct_spam_window=0;captured=[];original=backend.text
    async def capture(context,cfg):
        captured.append(dict(context=deepcopy(context),cfg=deepcopy(cfg)))
        return await original(context,cfg)
    try:
        with patch.object(backend,'text',side_effect=capture):
            for i,text in enumerate(spec['turns']):
                settings.set(1,'mood',spec['moods'][i]);store.set_affinity(2,4,spec['affinities'][i])
                event=Event(100+i,2,3,4,'<@999> '+text,datetime.now(timezone.utc),member_mentions=(999,),
                    reply_to=9000+i if i else None,reply_author=999 if i else None)
                transport.register(event);await runtime.ingest(event);await settle(runtime)
        return dict(output='\n'.join(x['text'] for x in transport.sent),sent=transport.sent,captured=captured,
                    traces=runtime.traces,pending=len(runtime.tasks),sdk_reply_ok=all(s['sdk_reply']==100+i for i,s in enumerate(transport.sent)))
    finally:await runtime.close();await transport.sdk_client.close()


async def run(args):
    from echomate_bot.inference import LocalBackend
    from echomate_bot.model_registry import ModelRegistry,ModelValidator
    from echomate_bot.character_profiles import presets
    from echomate_bot.instance import InstanceLease
    from echomate_bot.loader_memory import loading_reserve,MemoryRecorder,memory_snapshot
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.telemetry import distribution
    root=private_root(args.output);root.mkdir(parents=True,exist_ok=False)
    actual=json.loads(private_root(args.actual_cases).read_text('utf-8'))
    cases=calibration()+actual;spec=protocol();people=presets()
    if args.focus:
        cases=calibration()[:2]  # Reproduce formatting, not tune extraction semantics.
        spec['open']='주말에 동네 문구점에 들렀는데 손바닥만 한 빈 공책이 눈에 들어왔어. 그냥 지나갈까 하나 사볼까? 두세 문장으로 네 생각을 말해 줘.'
        spec['future']='청록색 찻잔이 마음에 들어. 두 달쯤 지나서 네가 먼저 이 얘기를 꺼내 줘도 좋겠어. 가능할까?'
    save(root/'seal.json',dict(protocol=spec,profiles=people,claims=cases,scale=1.5,
        threshold='Extraction must have valid/exact full atoms on all calibration before any runtime consideration; no automatic adoption',
        baseline=args.baseline,files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path('tools/persona_guidance.py'),Path('tools/korean_claim_extraction.py'),*Path('src/echomate_bot').glob('*.py')]},
        safety='One existing resident model, no live HTTP, no operating files, no final316. CFG doubles per-token forwards, not a free one-call improvement.'))
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:raise ValueError('Validated existing model required')
    health=check_resources()
    if health['free_vram_mib']<11264:raise RuntimeError('Need 11GiB free VRAM for dual KV caches')
    model_memory_budget(*loading_reserve(entry))
    lease=InstanceLease();backend=LocalBackend(adapter=None);resolve=ModelRegistry.resolve
    rows=[];extracted=[];summary=dict(before=memory_snapshot(),health=health);started=time.monotonic();recorder=None
    try:
        with MemoryRecorder(interval=1) as recorder,patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)),\
             patch('discord.http.HTTPClient.request',side_effect=AssertionError('No live Discord')),\
             patch('aiohttp.ClientSession._request',side_effect=AssertionError('No external HTTP')):
            t=time.monotonic();await backend.ready();await backend.probe();summary['load_seconds']=time.monotonic()-t
            guidance_ok=True
            for i,(key,profile) in enumerate(people.items()):
                for scale in ((1.0,1.5) if i%2 else (1.5,1.0)):
                    check_resources();cursor=backend.metrics[-1];t=time.monotonic();calls=[]
                    try:
                        with guidance(backend,scale,calls):detail=await runtime_answer(backend,profile,spec['open'],root/f'open-{key}-{scale}')
                        if len(detail['sent'])!=1:raise RuntimeError('Missing open response')
                    except Exception as exc:
                        if backend.failed:raise
                        guidance_ok=False;detail=dict(output='',error=type(exc).__name__,pending=len(backend.scheduler.queues) if hasattr(backend.scheduler,'queues') else None)
                    rows.append(dict(record_id=f'open-{key}-{scale}',phase='open',profile=key,scale=scale,
                        seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor),forwards=calls,**detail))
                    save(root/'results-private.json',rows);print('OPEN',key,scale,detail.get('error','OK'),flush=True)
                    if not guidance_ok:break
                if not guidance_ok:break
            # Functional compatibility gate only, not persona-quality acceptance.
            if guidance_ok and not args.focus:
                for key in ('playful','dry'):
                    for scale in (1.0,1.5):
                        check_resources();cursor=backend.metrics[-1];t=time.monotonic();calls=[]
                        with guidance(backend,scale,calls):detail=await sequence(backend,people[key],root/f'sequence-{key}-{scale}',spec)
                        rows.append(dict(record_id=f'sequence-{key}-{scale}',phase='sequence',profile=key,scale=scale,
                            seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor),forwards=calls,**detail))
                        save(root/'results-private.json',rows);print('SEQUENCE',key,scale,flush=True)
            if guidance_ok and args.focus:
                for key in ('supportive','dry'):
                    for scale in (1.0,1.5):
                        check_resources();cursor=backend.metrics[-1];t=time.monotonic();calls=[]
                        with guidance(backend,scale,calls):detail=await runtime_answer(backend,people[key],spec['future'],root/f'future-{key}-{scale}')
                        rows.append(dict(record_id=f'future-{key}-{scale}',phase='future',profile=key,scale=scale,
                            seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor),forwards=calls,**detail))
                        save(root/'results-private.json',rows);print('FUTURE',key,scale,flush=True)
                from run_grounding_checks import baseline_runtime
                import echomate_bot.runtime as runtime_module
                old,_=baseline_runtime(args.baseline);current=runtime_module.Runtime
                for arm in ('old','new'):
                    def setup(runtime,store,settings):
                        store.set_consent(2,4,'memory',True);transport=runtime.transport;read=transport.http.get_message;changed=[]
                        async def changed_read(channel,mid):
                            result=await read(channel,mid)
                            if not changed:store.add_memory(2,4,3,'내 취향은 귤이야');changed.append(True)
                            return result
                        transport.http.get_message=changed_read
                    cursor=backend.metrics[-1];t=time.monotonic()
                    with patch.object(runtime_module,'Runtime',old if arm=='old' else current):
                        detail=await runtime_answer(backend,people['supportive'],'내 취향에 대해 말해 줘',root/f'memory-{arm}',configure=setup)
                    rows.append(dict(record_id=f'memory-{arm}',phase='memory-race',arm=arm,seconds=time.monotonic()-t,
                        calls=metrics_since(backend.metrics,cursor),**detail))
                    save(root/'results-private.json',rows);print('MEMORY',arm,len(detail['sent']),flush=True)
            # Different responsibility: parse claims first, compare evidence in code.
            for i,case in enumerate(cases):
                if time.monotonic()-started>1800:raise TimeoutError('Bounded experiment')
                check_resources();cursor=backend.metrics[-1];t=time.monotonic();result=dict(case=case)
                try:
                    raw=await backend._job(messages(case['text']),budget=384)
                    result['raw']=raw  # Preserve malformed output too.
                    atoms=parse(raw,case['text']);result.update(raw=raw,atoms=atoms,score=compare(case,atoms))
                except (ValueError,json.JSONDecodeError) as exc:result.update(score=None,error=type(exc).__name__)
                result.update(seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor));extracted.append(result)
                save(root/'extracted-private.json',extracted);print('EXTRACT',i+1,result.get('error','OK'),flush=True)
            summary.update(status='COMPLETED_NOT_RELEASE_PASS',guidance_compatible=guidance_ok,
                extraction=aggregate(extracted),extraction_by_source={name:aggregate([r for r in extracted if r['case']['id'].startswith('actual-')==is_actual]) for name,is_actual in [('synthetic',False),('actual',True)]},
                open_conditions={str(scale):dict(n=len(g),seconds=distribution([r['seconds'] for r in g])) for scale in (1.0,1.5) for g in [[r for r in rows if r['phase']=='open' and r['scale']==scale]]})
    except BaseException as exc:
        summary.update(status='STOPPED',error=type(exc).__name__);raise
    finally:
        await backend.close();lease.close();summary.update(after=memory_snapshot(),elapsed=time.monotonic()-started)
        if recorder:summary['memory']=recorder.report()
        save(root/'summary.json',summary);report_html(root/'report.html',rows,summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--output',required=True)
    p.add_argument('--actual-cases',required=True);p.add_argument('--baseline',required=True)
    p.add_argument('--focus',action='store_true',help='Separate low-stakes development and two raw-format reproductions; not independent final')
    asyncio.run(run(p.parse_args()))
