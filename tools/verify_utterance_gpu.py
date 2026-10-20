"""One resident Gemma, sealed synthetic event sequences, mock delivery only.

Run after CPU regressions. Never authenticates with Discord or opens operating
settings/DB. Detailed outputs belong under ignored local_data, not in Git.
"""
import argparse
import asyncio
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import secrets
import time
from unittest.mock import patch

from echomate_bot.runtime import Runtime,Event
from echomate_bot.inference import LocalBackend
from echomate_bot.instance import InstanceLease
from echomate_bot.model_registry import ModelRegistry,ModelValidator
from echomate_bot.settings import Settings,atomic_private_json
from echomate_bot.telemetry import summarize,distribution
from verify_social_gpu import Counting,SocialTransport
from verify_resumed_release_gpu import gpu_memory


def protocol():
    def e(mid,text,user=4,**kw):return dict(id=mid,text=text,user=user,**kw)
    return [
        dict(name='six_fragments',roots=[100],events=[e(100,'<@999>'),e(101,'작은 독서 모임을'),e(102,'새로 준비하고'),e(103,'참여 조건도'),e(104,'정하려고 하는데'),e(105,'쉬운 규칙 두 개를 한 문장으로 제안해줘')]),
        dict(name='interleaved_two_calls',roots=[200,210],events=[e(200,'<@999>'),e(210,'<@999>',5),e(201,'빵 만들기를'),e(211,'화분 가꾸기를',5),e(202,'처음 시작할 때 조언 하나만 해줘'),e(212,'처음 시작할 때 조언 하나만 해줘',5)]),
        dict(name='human_audience_switch',roots=[300],events=[e(300,'<@999>'),e(301,'같은 모임 소개를 한 문장으로 해줘'),e(302,'<@5> 너는 모임에 올 거야')]),
        dict(name='supplement_during_text',roots=[400],events=[e(400,'<@999> 초보자가 빵을 만들 때 순서를 설명해줘'),e(401,'아 근데',during_text=True),e(402,'오븐이 없는 경우로'),e(403,'한 문장으로 설명해줘')]),
        dict(name='concurrent_independent',roots=[500,501,502,503],events=[e(500+i,f'<@999> {i+2} 더하기 {i+3} 결과를 숫자만 알려줘',4+i) for i in range(4)]),
        dict(name='late_after_completion',roots=[600],events=[e(600,'<@999> 독서의 장점 하나를 짧게 말해줘'),e(601,'<@5> 아까 그 책 제목이 뭐였어',settle_before=True)]),
        dict(name='actual_reply_fragment',roots=[700,710],events=[e(700,'<@999> 모임 규칙 하나를 짧게 제안해줘'),e(710,'그 규칙을',reply=9001,settle_before=True),e(711,'처음 온 사람에게도'),e(712,'같이 적용하면 어떨지 한 문장으로 말해줘')]),
    ]


async def settle(runtime):
    while runtime.tasks or runtime.utterances.pending or runtime.utterances.emitting:
        tasks=list(runtime.tasks.values())+[r.task for r in runtime.utterances.pending.values()]+list(runtime.utterances.emitting)
        await asyncio.wait_for(asyncio.gather(*tasks,return_exceptions=True),180)


class Transport(SocialTransport):
    async def execute(self,event,action,library,fresh):
        result=await super().execute(event,action,library,fresh)
        self.sent[-1].update(parts=[p.id for p in event.raw_parts],last_fragment_seconds=time.monotonic()-event.raw_parts[-1].received_at,
            utterance=event.utterance_id,version=event.utterance_version,conversation=event.conversation_id)
        return result


async def run(args):
    root=Path(args.output).resolve()
    if not root.is_relative_to(Path('local_data').resolve()):raise ValueError('Private output only')
    root.mkdir(parents=True,exist_ok=False)
    cases=json.loads(Path(args.protocol).read_text(encoding='utf-8')) if args.protocol else protocol();atomic_private_json(root/'protocol.json',cases)
    atomic_private_json(root/'seal.json',dict(protocol=hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest(),
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/echomate_bot').glob('*.py')}))
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:raise ValueError('Existing local model incompatible')
    lease=InstanceLease();backend=LocalBackend(adapter=None);rows=[];traces=[];summary={}
    resolve=ModelRegistry.resolve
    try:
        summary['before']=gpu_memory();start=time.monotonic()
        with patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)):
            await backend.ready();await backend.probe()
            summary['load_seconds']=time.monotonic()-start;summary['ready']=gpu_memory()
            for case in cases:
                folder=root/case['name'];folder.mkdir()
                settings=Settings(1,secrets.token_hex(32),folder/'settings.json');settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True)
                settings.change(1,lambda c:c['guilds']['2'].update(name='라온봇'))
                borrowed=Counting(backend);transport=Transport();runtime=Runtime(settings,borrowed,transport,None,None,ledger_path=folder/'sent.sqlite3')
                runtime.direct_spam_window=0;runtime.direct_cooldown=0
                began=time.monotonic()
                try:
                    for raw in case['events']:
                        if raw.get('settle_before'):await settle(runtime)
                        if raw.get('during_text'):
                            deadline=time.monotonic()+30
                            while not any(r.get('stage')=='text' for r in runtime.progress.values()):
                                if time.monotonic()>deadline:raise TimeoutError('No generation stage')
                                await asyncio.sleep(.01)
                        await runtime.ingest(Event(raw['id'],2,3,raw['user'],raw['text'],datetime.now(timezone.utc)-timedelta(seconds=raw.get('age',0)),reply_to=raw.get('reply'),received_at=time.monotonic()-raw.get('age',0),
                            member_mentions=tuple(int(x) for x in __import__('re').findall(r'<@!?(\d+)>',raw['text']))))
                        await asyncio.sleep(.04)
                    await settle(runtime)
                    roots=[r['source'] for r in transport.sent]
                    row=dict(name=case['name'],passed=sorted(roots)==sorted(case['roots']),expected=case['roots'],actual=roots,
                        semantic_calls=borrowed.semantic_calls,elapsed=time.monotonic()-began,sent=transport.sent,traces=runtime.traces,
                        decisions=borrowed.assessments,pending=len(runtime.tasks)+len(runtime.utterances.pending))
                    traces.extend(runtime.traces);rows.append(row);atomic_private_json(folder/'result.json',row)
                finally:await runtime.close()
                atomic_private_json(root/'progress.json',dict(completed=len(rows),passed=sum(r['passed'] for r in rows)))
            summary.update(cases=len(rows),passed=sum(r['passed'] for r in rows),semantic_calls=sum(r['semantic_calls'] for r in rows),
                pipeline=summarize(traces),last_fragment_seconds=distribution([s['last_fragment_seconds'] for r in rows for s in r['sent']]),
                after=gpu_memory(),actual_discord=False)
    except BaseException as exc:
        summary['failure']=type(exc).__name__;raise
    finally:
        try:await backend.close();summary['closed']=gpu_memory()
        finally:lease.close();atomic_private_json(root/'summary.json',summary)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--model',required=True);parser.add_argument('--protocol')
    asyncio.run(run(parser.parse_args()))
