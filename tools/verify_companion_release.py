"""Fresh synthetic call/mention negatives and matched GPU route A/B. No Discord."""
import argparse
import asyncio
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import random
import secrets
import shutil
import time
from echomate_bot.settings import Settings,private_path,atomic_private_json
from echomate_bot.runtime import Runtime,Event
from echomate_bot.instance import InstanceLease
from echomate_bot.inference import LocalBackend
from echomate_bot.companion_store import CompanionStore
from echomate_bot.telemetry import distribution
from echomate_studio.dialogue_state import DialogueState,Turn
from verify_adult_conversation import Transport

CALLS=[
 ('보람mk3, 한 문장으로 인사해 줘.',True),('보람아, 짧게 인사해 줘.',True),
 ('두리야, 한 문장으로 인사해 줘.',True),('야 보람, 한 문장으로 답해 줘.',True),
 ('<@999> 한 문장으로 인사해 줘.',True),
 ('“보람아”라는 말을 인용했어.',False),('보람mk30이라는 다른 이름이야.',False),
 ('보라미아는 다른 사람이야.',False),('보람은 성취감이라는 뜻도 있어.',False),
 ('보람, 너 말고 B한테 묻는 거야. 언제 출발할 거야?',False),
 ('두리야, 여기서 두리는 봇이 아니라 다른 사람이야.',False),
 ('https://example.com/보람아',False),
]


async def run(root):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend();transport=Transport()
    settings=Settings(1,secrets.token_hex(32),root/'settings.json');settings.set(1,'enabled',True)
    store=CompanionStore(root/'companion.sqlite3');runtime=Runtime(settings,backend,transport,None,None,ledger_path=root/'ledger.sqlite3',rng=random.Random(2026),companion=store)
    rows=[];benchmark=[]
    atomic_private_json(root/'manifest.json',dict(synthetic=True,real_discord=False,seed=2026,calls=CALLS,
        repeats=5,warmup_pairs=1,context='Same synthetic user + bot request for an arithmetic expression',
        caution='Fresh name checks are not a population accuracy estimate; source fixtures are not real Discord logs'))
    for source in [*Path('src/echomate_bot').glob('*.py'),Path('src/echomate_studio/dialogue_state.py'),Path('tools/verify_companion_release.py')]:
        target=root/'source'/source;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    async def ask(event):
        with runtime.ledger.db() as db:db.execute('UPDATE sent SET at=at-3')
        before=len(transport.sent);started=time.perf_counter()
        await runtime.ingest(event);await asyncio.gather(*list(runtime.tasks.values()),return_exceptions=True)
        return time.perf_counter()-started,transport.sent[before:]
    try:
        await backend.ready()
        import torch
        torch.manual_seed(2026)
        for mode_index,mode in enumerate(('base','persona','adult')):
            channel=80+mode_index;settings.set_scope(1,2,channel,'mention')
            def names(c):c['guilds']['2'].update(name='보람mk3',aliases=['두리'],timezone='Asia/Seoul')
            settings.change(1,names);await runtime.switch_model(1,mode)
            for index,(text,expected) in enumerate(CALLS):
                runtime.invalidate(channel)
                elapsed,sent=await ask(Event(10000+mode_index*100+index,2,channel,4,text,datetime.now(timezone.utc)))
                rows.append(dict(mode=mode,case=index,expected=expected,outputs=len(sent),passed=bool(sent)==expected,response=[r['text'] for r in sent],seconds=elapsed))
                atomic_private_json(root/'fresh-responses-private.json',rows)
                print(json.dumps(dict(phase='fresh',mode=mode,case=index,outputs=len(sent),passed=bool(sent)==expected)),flush=True)
            for repeat in range(6):
                # Alternate order; first pair is warmup and excluded from summaries.
                for enabled in ((False,True) if repeat%2==0 else (True,False)):
                    runtime.invalidate(channel);runtime.followup_fast_path=enabled;store.set_affinity(2,4,50)
                    state=DialogueState(limit=100);now=datetime.now(timezone.utc)
                    state.append(channel_id=channel,thread_id=None,turn=Turn('seed-human','4','계산 문제를 하나 물어봐도 돼?',now-timedelta(seconds=3)))
                    state.append(channel_id=channel,thread_id=None,turn=Turn('seed-bot','999','응, 계산할 식을 말해 줘.',now-timedelta(seconds=2),is_bot=True,reply_to='seed-human'))
                    runtime.states[channel]=state
                    elapsed,sent=await ask(Event(20000+mode_index*100+repeat*2+int(enabled),2,channel,4,'3 더하기 4의 답만 알려줘.',now))
                    trace=runtime.traces[-1];calls=trace['calls'];actor=calls[-1] if sent and calls else {}
                    benchmark.append(dict(mode=mode,repeat=repeat,fast=enabled,warmup=repeat==0,seconds=elapsed,outputs=len(sent),calls=len(calls),
                        actor_input_tokens=actor.get('input_tokens'),actor_output_tokens=actor.get('output_tokens'),response=[r['text'] for r in sent],trace=trace))
                    atomic_private_json(root/'route-ab-private.json',benchmark)
                    print(json.dumps(dict(phase='ab',mode=mode,repeat=repeat,fast=enabled,calls=len(calls),outputs=len(sent))),flush=True)
            runtime.followup_fast_path=True
        summary=dict(real_gpu=True,real_discord=False,fresh={},route_ab={})
        for mode in ('base','persona','adult'):
            entries=[r for r in rows if r['mode']==mode]
            summary['fresh'][mode]=dict(total=len(entries),matched=sum(r['passed'] for r in entries),false_positive_cases=[r['case'] for r in entries if not r['expected'] and r['outputs']],missed_call_cases=[r['case'] for r in entries if r['expected'] and not r['outputs']])
            b=[r for r in benchmark if r['mode']==mode and not r['warmup']]
            pairs=[([r for r in b if r['repeat']==i and not r['fast']][0],[r for r in b if r['repeat']==i and r['fast']][0]) for i in range(1,6)]
            summary['route_ab'][mode]=dict(baseline=distribution([r['seconds'] for r in b if not r['fast']]),fast=distribution([r['seconds'] for r in b if r['fast']]),
                matching_actor_input_pairs=sum(a['actor_input_tokens']==c['actor_input_tokens'] and a['actor_input_tokens'] is not None for a,c in pairs),
                matching_response_pairs=sum(a['response']==c['response'] and bool(a['response']) for a,c in pairs),
                calls_before=[a['calls'] for a,c in pairs],calls_after=[c['calls'] for a,c in pairs])
        atomic_private_json(root/'summary.json',summary);print(json.dumps(summary),flush=True)
    finally:
        try:await runtime.close()
        finally:lease.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    asyncio.run(run(private_path(parser.parse_args().output)))
