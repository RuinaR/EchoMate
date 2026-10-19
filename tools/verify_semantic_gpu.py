"""Offline CUDA + synthetic transport probe. Optional private fixtures stay local."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import time
from echomate_bot.settings import Settings,private_path,atomic_private_json,DEFAULTS
from echomate_bot.runtime import Runtime,Event
from echomate_bot.inference import LocalBackend
from echomate_bot.instance import InstanceLease
from echomate_studio.dialogue_state import DialogueState,Turn
from verify_parallel_gpu import Transport,Borrowed,settle

async def run(root,fixtures,skip_moods=False):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend();rows=[];moods=[];technical=[];sequence=[]
    protocol=json.loads(fixtures.read_text(encoding='utf-8-sig'))
    atomic_private_json(root/'protocol-private.json',protocol)
    for p in Path('src').rglob('*.py'):
        target=root/'source'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    old={};exec(subprocess.check_output(['git','show','66d0b02:src/echomate_bot/character.py']).decode('utf-8').replace('from .adult_policy import','from echomate_bot.adult_policy import'),old)
    try:
        await backend.ready()
        for mode in ('base',):
            if protocol.get('sequence'):
                settings=Settings(1,secrets.token_hex(32),root/f'{mode}-sequence-settings.json')
                settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True);settings.set(1,'model',mode)
                settings.change(1,lambda c:c['guilds']['2'].update(name=protocol['name']))
                transport=Transport();runtime=Runtime(settings,Borrowed(backend),transport,None,None,ledger_path=root/f'{mode}-sequence.sqlite3')
                runtime.direct_cooldown=0
                try:
                    now=datetime.now(timezone.utc);seed=Event(100,2,3,4,protocol['seed_user'],now)
                    flow,_=runtime.conversations.choose(seed,direct=True,pending=set())
                    runtime.conversations.observe(flow,seed);runtime.conversations.bot(flow,8000);flow.engaged=True
                    state=DialogueState(limit=100,max_age_seconds=3600);runtime.states[flow.key]=state
                    state.append(channel_id=3,thread_id=None,turn=Turn('100','4',seed.content,now))
                    state.append(channel_id=3,thread_id=None,turn=Turn('8000','999',protocol['seed_bot'],now,True,'100'))
                    for i,case in enumerate(protocol['sequence']):
                        before=len(transport.sent)
                        await runtime.ingest(Event(200+i,2,3,case['author'],case['text'],datetime.now(timezone.utc)))
                        await settle(runtime,backend)
                        response=len(transport.sent)>before
                        sequence.append(dict(mode=mode,case=i,passed=response==case['respond'],responded=response,
                            target=transport.sent[-1]['source'] if response else None,conversation_ids=len({f.conversation_id for f in runtime.conversations.flows.values()})))
                        atomic_private_json(root/f'{mode}-sequence-private.json',dict(results=sequence,responses=transport.sent,traces=runtime.traces))
                        print(json.dumps(sequence[-1]),flush=True)
                finally:await runtime.close()
            for index,case in enumerate(protocol['cases']):
                settings=Settings(1,secrets.token_hex(32),root/f'{mode}-{index}-settings.json')
                settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True);settings.set(1,'model',mode)
                settings.change(1,lambda c:c['guilds']['2'].update(name=protocol['name']))
                transport=Transport();runtime=Runtime(settings,Borrowed(backend),transport,None,None,ledger_path=root/f'{mode}-{index}.sqlite3')
                runtime.direct_cooldown=0
                try:
                    now=datetime.now(timezone.utc)
                    seed=Event(100,2,3,4,protocol['seed_user'],now)
                    flow,_=runtime.conversations.choose(seed,direct=True,pending=set())
                    runtime.conversations.observe(flow,seed);runtime.conversations.bot(flow,9001);flow.engaged=True
                    state=DialogueState(limit=100,max_age_seconds=3600);runtime.states[flow.key]=state
                    state.append(channel_id=3,thread_id=None,turn=Turn('100','4',seed.content,now))
                    state.append(channel_id=3,thread_id=None,turn=Turn('9001','999',protocol['seed_bot'],now,True,'100'))
                    start=time.monotonic()
                    await runtime.ingest(Event(200,2,3,case.get('author',4),case['text'],now))
                    await settle(runtime,backend)
                    response=bool(transport.sent)
                    row=dict(mode=mode,case=index,expected=case['respond'],responded=response,passed=response==case['respond'],
                             seconds=time.monotonic()-start,targets=[r['source'] for r in transport.sent],
                             responses=transport.sent,traces=runtime.traces,codes=[r['code'] for r in runtime.diagnostics])
                    rows.append(row);atomic_private_json(root/'responses-private.json',rows)
                    print(json.dumps({k:row[k] for k in ('mode','case','expected','responded','passed','seconds')}),flush=True)
                finally:await runtime.close()
            for mood in protocol.get('technical_moods',[]):
                from echomate_bot.adult_policy import turn_profile
                cfg=turn_profile(dict(DEFAULTS,model=mode,mood=mood),age_restricted=True)
                start=time.monotonic()
                try:
                    text=await backend.text([dict(role='user',content=protocol['technical_prompt'])],cfg)
                    item=dict(mode=mode,mood=mood,text=text,seconds=time.monotonic()-start,metric=dict(backend.metrics[-1]))
                except ValueError as exc:item=dict(mode=mode,mood=mood,error=type(exc).__name__)
                technical.append(item);atomic_private_json(root/'technical-private.json',technical)
            # Same input/weights/greedy and budget; old/new prompt only differs.
            for mood in (() if skip_moods else ('평온','기쁨','신남','우울','화남','피곤함','부끄러움')):
                from echomate_bot.character import instruction
                from echomate_bot.adult_policy import turn_profile
                cfg=turn_profile(dict(DEFAULTS,model=mode,mood=mood),age_restricted=True)
                pair={}
                for label,fn in (('old',old['instruction']),('new',instruction)):
                    start=time.monotonic()
                    messages=[dict(role='system',content=fn(cfg)),dict(role='user',content=protocol['mood_prompt'])]
                    try:
                        retries=0
                        try:text=await backend._job(messages,weight=cfg['model'],budget=192)
                        except ValueError as exc:
                            if str(exc)!='Unexpected output channel':raise
                            retries=1;messages[0]['content']+=' 분석·채널 표기 없이 사용자에게 보낼 자연스러운 한국어 답변만 새로 작성해.'
                            text=await backend._job(messages,weight=cfg['model'],budget=192)
                        pair[label]=dict(text=text,retries=retries,seconds=time.monotonic()-start,metric=dict(backend.metrics[-1]))
                    except ValueError as exc:pair[label]=dict(error=type(exc).__name__,seconds=time.monotonic()-start)
                moods.append(dict(mode=mode,mood=mood,**pair));atomic_private_json(root/'moods-private.json',moods)
            summary=dict(real_gpu=True,real_discord=False,source_commit='66d0b02 plus private source snapshot',
                         modes=[dict(mode=m,cases=sum(r['mode']==m for r in rows),passed=sum(r['mode']==m and r['passed'] for r in rows)) for m in ('base',)],
                         sequence=sequence,mood_pairs=len(moods),technical_cases=len(technical),metrics=backend.metrics)
            atomic_private_json(root/'summary.json',summary)
    finally:
        try:await backend.close()
        finally:lease.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--fixtures',required=True,type=Path);p.add_argument('--skip-moods',action='store_true');args=p.parse_args()
    asyncio.run(run(private_path(args.output),private_path(args.fixtures),args.skip_moods))
