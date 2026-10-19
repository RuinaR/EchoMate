"""Matched synthetic events against saved runtime/current runtime. No Discord I/O.

Fixtures and all generated content must remain in local_data. Judgment calls,
queue timings and output text are retained privately; stdout is aggregate only.
"""
import argparse
import asyncio
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import random
import secrets
import shutil
import subprocess
import sys
import time
from unittest.mock import patch
from echomate_bot.settings import Settings,private_path,atomic_private_json
from echomate_bot.runtime import Runtime,Event
from echomate_bot.inference import LocalBackend
from echomate_bot.instance import InstanceLease
from echomate_bot.companion_store import CompanionStore
from echomate_bot.telemetry import distribution
from echomate_studio.dialogue_state import DialogueState,Turn
from verify_parallel_gpu import Transport,Borrowed,settle

class Probe(Borrowed):
    def __init__(self,backend):super().__init__(backend);self.calls=dict(assessment=0,verification=0,text=0)
    async def assess_dialogue(self,*args,**kwargs):
        self.calls['assessment']+=1;return await self.backend.assess_dialogue(*args,**kwargs)
    async def verify_target(self,*args,**kwargs):
        self.calls['verification']+=1;return await self.backend.verify_target(*args,**kwargs)
    async def text(self,*args,**kwargs):
        self.calls['text']+=1;return await self.backend.text(*args,**kwargs)

async def run(root,fixtures,ref):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend();results=[]
    protocol=json.loads(fixtures.read_text(encoding='utf-8-sig'));atomic_private_json(root/'protocol-private.json',protocol)
    for p in Path('src').rglob('*.py'):
        target=root/'source'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    old_file=root/'baseline-runtime.py';old_file.write_bytes(subprocess.check_output(['git','show',ref+':src/echomate_bot/runtime.py']))
    spec=importlib.util.spec_from_file_location('echomate_bot._members_qa_baseline',old_file);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    old_intent={};exec(subprocess.check_output(['git','show',ref+':src/echomate_bot/dialogue_intent.py']).decode('utf-8'),old_intent)
    import echomate_bot.dialogue_intent as intent_module
    current_prompt=intent_module.PROMPT
    try:
        await backend.ready()
        # Exclude a warm-up pair from quality/performance aggregates.
        for _ in range(2):await backend.assess_dialogue([dict(role='user',content='안녕')])
        for mode in ('base',):
            for index,case in enumerate(protocol['cases']):
                for variant in (('baseline','current') if index%2==0 else ('current','baseline')):
                    folder=root/f'{mode}-{index}-{variant}';folder.mkdir()
                    settings=Settings(1,secrets.token_hex(32),folder/'settings.json');settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True);settings.set(1,'model',mode)
                    settings.change(1,lambda c:c['guilds']['2'].update(name=protocol['bot_name']))
                    transport=Transport();cls=module.Runtime if variant=='baseline' else Runtime
                    store=CompanionStore(folder/'companion.sqlite3')
                    for alias in protocol.get('aliases',()):store.set_alias(2,3,int(alias['user']),alias['alias'],alias['status'])
                    probe=Probe(backend);runtime=cls(settings,probe,transport,None,None,ledger_path=folder/'sent.sqlite3',rng=random.Random(2026),companion=store);runtime.direct_cooldown=0
                    now=datetime.now(timezone.utc)
                    seed=Event(100,2,3,4,protocol['seed_user'],now);flow,_=runtime.conversations.choose(seed,direct=True,pending=set());runtime.conversations.observe(flow,seed);runtime.conversations.bot(flow,8000);flow.engaged=True
                    state=DialogueState(limit=100,max_age_seconds=3600);runtime.states[flow.key]=state
                    state.append(channel_id=3,thread_id=None,turn=Turn('100','4',seed.content,now));state.append(channel_id=3,thread_id=None,turn=Turn('8000','999',protocol['seed_bot'],now,True,'100'))
                    names=tuple((uid,tuple(ns)) for uid,ns in protocol['members'])
                    e=Event(200,2,3,case.get('author',4),case['text'],now,member_names=names,member_mentions=tuple(case.get('mentions',())),reply_to=case.get('reply_to'),reply_author=case.get('reply_author'))
                    start=time.monotonic();metric_start=len(backend.metrics)
                    try:
                        with patch.object(intent_module,'PROMPT',old_intent['PROMPT'] if variant=='baseline' else current_prompt):
                            await runtime.ingest(e);await settle(runtime,backend)
                        responded=bool(transport.sent)
                        trace=runtime.traces[-1] if runtime.traces else {}
                        result=dict(mode=mode,index=index,variant=variant,expected=case['respond'],responded=responded,passed=responded==case['respond'],seconds=time.monotonic()-start,
                            responses=transport.sent,traces=runtime.traces,codes=[r['code'] for r in runtime.diagnostics],calls=dict(probe.calls),metrics=backend.metrics[metric_start:])
                        results.append(result);atomic_private_json(root/'results-private.json',results)
                        print(json.dumps(dict(mode=mode,index=index,variant=variant,passed=result['passed'],seconds=round(result['seconds'],3))),flush=True)
                    finally:await runtime.close()
        summaries=[]
        for mode in ('base',):
            for variant in ('baseline','current'):
                rows=[r for r in results if r['mode']==mode and r['variant']==variant]
                summaries.append(dict(mode=mode,variant=variant,count=len(rows),passed=sum(r['passed'] for r in rows),false_response=sum(r['responded'] and not r['expected'] for r in rows),miss=sum(not r['responded'] and r['expected'] for r in rows),latency=distribution([r['seconds'] for r in rows]),
                    semantic_calls=sum(r['calls']['assessment']+r['calls']['verification'] for r in rows),text_calls=sum(r['calls']['text'] for r in rows),max_vram_mib=max((m.get('peak_allocated_mib',0) for r in rows for m in r['metrics']),default=0)))
        atomic_private_json(root/'summary.json',dict(baseline_ref=ref,results=summaries,actual_discord=False,warning='Synthetic fixtures, one observation per case/mode/variant. Not human naturalness or matched prompt speed optimization.'))
        print(json.dumps(summaries),flush=True)
    finally:await backend.close();lease.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fixtures',required=True);parser.add_argument('--output',required=True);parser.add_argument('--baseline',default='5697cbd');args=parser.parse_args()
    asyncio.run(run(private_path(args.output),private_path(args.fixtures),args.baseline))
