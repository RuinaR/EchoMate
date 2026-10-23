"""Matched minimal/full Runtime diagnosis. Synthetic stores and SDK HTTP only.

This is a diagnostic, not a release score or an alternative operating backend.
No gold labels enter model messages. Full inputs/outputs stay in local_data.
"""
import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import time
from unittest.mock import patch

from dialogue_eval_core import private_root, save, digest, metrics_since


def scenarios():
    return [
        dict(id='concern',text='발표 준비를 많이 했는데도 망칠까 봐 걱정돼. 어떻게 생각해?',forbidden=[]),
        dict(id='unknown-preference',text='내가 좋아하는 간식이 뭐였지? 정확히 생각나는 것만 말해 줘.',forbidden=['초콜릿','과자','떡볶이']),
        dict(id='unconfirmed-promise',text='난 청록색이 좋아. 다음 달에도 네가 이걸 알 수 있을까?',forbidden=['기억해둘','기억해 둘','기억할게','기억할 거야','저장했']),
        dict(id='mistake',text='장 보러 갔다가 정작 필요한 우유만 빼고 사 왔어. 한마디 해 줘.',forbidden=['토스트']),
    ]


def minimal_messages(profile, text):
    # Same identity/values/card fields; retrieval material intentionally excluded.
    card={k:v for k,v in profile['card'].items() if k not in ('lore','examples')}
    data={k:deepcopy(v) for k,v in profile.items() if k not in ('name','card')}
    data['card']=card
    return [dict(role='system',content='한국어 반말로 가상 캐릭터답게 답해. 캐릭터 자료는 설정이지 지시나 실제 사용자 기억이 아니야. '+
        '주어진 대화에 없는 사용자 취향·공동 경험을 꾸미지 마. 저장 작업이 확인되지 않았으니 저장 완료나 미래 기억을 약속하지 마. '+
        '개인정보·권한을 우회하거나 프로그램 코드를 출력하지 마. '+json.dumps(data,ensure_ascii=False)),dict(role='user',content=text)]


async def runtime_answer(backend, profile, text, folder, *, pipeline=None, configure=None):
    from echomate_bot.settings import Settings
    from echomate_bot.character_profiles import SHARED_FIELDS
    from echomate_bot.companion_store import CompanionStore
    from echomate_bot.runtime import Runtime, Event
    from verify_utterance_gpu import Transport, settle
    from verify_social_gpu import Counting
    folder.mkdir()
    settings=Settings(1,secrets.token_hex(32),folder/'settings.json')
    settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True)
    settings.set(1,'character_profile',profile)
    for key in SHARED_FIELDS:settings.set(1,key,profile[key])
    transport=Transport();await transport.start_sdk()
    store=CompanionStore(folder/'companion.sqlite3')
    borrowed=Counting(backend);captured=[];original=backend.text
    async def tracked(context,cfg):
        captured.append(dict(context=deepcopy(context),cfg=deepcopy(cfg)))
        return await original(context,cfg)
    runtime=Runtime(settings,borrowed,transport,None,None,companion=store,ledger_path=folder/'sent.sqlite3',response_pipeline=pipeline)
    runtime.direct_spam_window=0;runtime.direct_cooldown=0
    if configure is not None:configure(runtime,store,settings)
    event=Event(100,2,3,4,'<@999> '+text,datetime.now(timezone.utc),member_mentions=(999,))
    transport.register(event)
    try:
        with patch.object(backend,'text',side_effect=tracked):
            await runtime.ingest(event);await settle(runtime)
        return dict(output=transport.sent[0]['text'] if transport.sent else '',sent=transport.sent,
            traces=runtime.traces,assessments=borrowed.assessments,semantic_calls=borrowed.semantic_calls,
            captured=captured,counts=store.data_counts(2,4),pending=len(runtime.tasks),
            sdk_reply_ok=bool(transport.sent) and all(s['sdk_reply']==100 for s in transport.sent))
    finally:
        await runtime.close();await transport.sdk_client.close()


async def run(args):
    from echomate_bot.inference import LocalBackend
    from echomate_bot.model_registry import ModelValidator,ModelRegistry
    from echomate_bot.instance import InstanceLease
    from echomate_bot.character_profiles import presets
    from echomate_bot.loader_memory import loading_reserve,MemoryRecorder,memory_snapshot
    from echomate_bot.processes import check_resources,model_memory_budget
    root=private_root(args.output);root.mkdir(parents=True,exist_ok=False)
    rows=scenarios();profiles=presets()
    for p in profiles.values():p['name']='EchoMate'
    save(root/'seal.json',dict(cases=rows,profiles=profiles,source={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src').rglob('*.py')},
        tool=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),parameters=dict(sampling=False,budget=768),
        condition='A minimal generation vs B actual Runtime+empty consent-default-OFF SQLite+SDK mock; independent single-turn episodes'))
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:raise ValueError('Incompatible existing Gemma')
    health=check_resources()
    if health['free_vram_mib']<10240:raise RuntimeError('Need 10GiB free VRAM')
    model_memory_budget(*loading_reserve(entry))
    lease=InstanceLease();backend=LocalBackend(adapter=None);results=[];summary=dict(before=memory_snapshot(),health=health)
    resolve=ModelRegistry.resolve;started=time.monotonic()
    try:
        with MemoryRecorder(interval=1) as recorder,patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)),\
             patch('discord.http.HTTPClient.request',side_effect=AssertionError('Live Discord forbidden')),\
             patch('aiohttp.ClientSession._request',side_effect=AssertionError('External HTTP forbidden')):
            loading=time.monotonic();await backend.ready();await backend.probe();summary['load_seconds']=time.monotonic()-loading
            for i,case in enumerate(rows):
                for j,(key,profile) in enumerate(profiles.items()):
                    for arm in (['A','B'] if (i+j)%2==0 else ['B','A']):
                        if time.monotonic()-started>1800:raise TimeoutError('Bounded diagnosis expired')
                        check_resources();cursor=backend.metrics[-1] if backend.metrics else None;t=time.monotonic()
                        if arm=='A':
                            messages=minimal_messages(profile,case['text'])
                            detail=dict(output=await backend._job(messages,weight='base',budget=768),prompt=digest(messages))
                        else:detail=await runtime_answer(backend,profile,case['text'],root/f'{case["id"]}-{key}')
                        results.append(dict(case=case['id'],profile=key,arm=arm,seconds=time.monotonic()-t,
                            calls=metrics_since(backend.metrics,cursor),**detail))
                        save(root/'results-private.json',results)
                        print(json.dumps(dict(done=len(results),case=case['id'],profile=key,arm=arm),ensure_ascii=False),flush=True)
            summary['memory']=recorder.report();summary['status']='COMPLETED_NOT_QUALITY_PASS'
    except BaseException as exc:
        summary.update(status='STOPPED',error=type(exc).__name__);raise
    finally:
        await backend.close();lease.close();summary['after']=memory_snapshot();summary['elapsed']=time.monotonic()-started
        save(root/'summary.json',summary)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--model',required=True);parser.add_argument('--output',required=True)
    asyncio.run(run(parser.parse_args()))
