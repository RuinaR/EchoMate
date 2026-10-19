"""Local CUDA + synthetic Discord only; supplied private protocols stay local."""
import argparse
import asyncio
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import random
import secrets
import shutil
import subprocess
import time

from echomate_bot.instance import InstanceLease
from echomate_bot.inference import LocalBackend
from echomate_bot.runtime import Runtime,Event
from echomate_bot.settings import Settings,private_path,atomic_private_json
from echomate_bot.telemetry import distribution
from echomate_studio.dialogue_state import DialogueState,Turn
from verify_parallel_gpu import Borrowed,Transport,settle

class Counting(Borrowed):
    def __init__(self,backend):super().__init__(backend);self.semantic_calls=0;self.packet_hashes=[];self.assessments=[]
    def __getattr__(self,key):
        value=super().__getattr__(key)
        if key not in ('assess_social','link_direct','assess_dialogue','assess_turn','classify','verify_target','continuity'):return value
        async def measured(*args,**kwargs):
            self.semantic_calls+=1
            if key=='assess_social':self.packet_hashes.append(hashlib.sha256(json.dumps(args[0],ensure_ascii=False,sort_keys=True).encode()).hexdigest())
            observation=None
            if key in ('assess_social','link_direct'):
                from copy import deepcopy
                observation=dict(method=key,packet=deepcopy(args[0]));self.assessments.append(observation)
            try:result=await value(*args,**kwargs)
            except Exception as exc:
                if observation is not None:observation['error']=type(exc).__name__
                raise
            if observation is not None:
                from dataclasses import asdict,is_dataclass
                observation['decision']=asdict(result) if is_dataclass(result) else result
            return result
        return measured

class ClassificationOnly(Counting):
    async def text(self,context,cfg):return '본 검사는 청자 판정과 원본 답장 연결만 확인하는 합성 응답이야.'
    async def propose(self,context,catalog):return json.dumps(dict(kind='REACTION',text='',asset=next(iter(catalog['reactions']))))

class SocialTransport(Transport):
    def __init__(self,reactions=False):super().__init__();self.reactions=reactions
    async def catalog(self,event,cache):return dict(reactions={'👍':'동의','🎉':'축하'} if self.reactions else {},stickers={})
    async def execute(self,event,action,library,fresh):
        if not await fresh():raise ValueError('Stale synthetic send')
        self.sent.append(dict(source=event.response_to or event.id,author=event.author,text=action.text,kind=action.kind.value,seconds=time.monotonic()-event.received_at))
        return None if action.kind.value=='REACTION' else 9000+len(self.sent)

async def run(args):
    # A preserved source tree has a different __file__; keep all probe outputs
    # in the real project's private root and use the same existing adapter.
    import echomate_bot.settings as settings_module
    import echomate_bot.instance as instance_module
    import echomate_bot.inference as inference_module
    settings_module.ROOT=Path.cwd()/'local_data'/'bot'
    instance_module.ROOT=settings_module.ROOT
    inference_module.ADAPTER=settings_module.ROOT.parent/'experiments/style-v2/pilot-r8-qkvo/step-00060'
    root=private_path(args.output);root.mkdir(parents=True,exist_ok=False)
    protocol=json.loads(private_path(args.protocol).read_text(encoding='utf-8-sig'))
    lease=InstanceLease();backend=LocalBackend(adapter=inference_module.ADAPTER if args.legacy_adapter else None,choice_cache=args.cache_choices);rows=[]
    source_root=Path(__import__('echomate_bot').__file__).parent.parent
    for p in source_root.rglob('*.py'):
        dest=root/'source'/p.relative_to(source_root);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    atomic_private_json(root/'manifest.json',dict(real_gpu=True,real_discord=False,seed=2026,generation=args.generate,
        legacy_adapter=args.legacy_adapter,code_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),protocol_hash=hashlib.sha256(Path(args.protocol).read_bytes()).hexdigest(),
        source_hashes={str(p.relative_to(source_root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_root.rglob('*.py')}))
    try:
        await backend.ready()
        await backend._job([dict(role='user',content='한국어로 짧게 인사해 줘')],weight='base',budget=16)
        for mode in args.modes.split(','):
            for index,case in enumerate(protocol['cases']):
                if mode not in case.get('only_modes',args.modes.split(',')):continue
                if backend.failed:raise RuntimeError('GPU safety failed; probe stopped')
                directory=root/f'{mode}-{index:03d}';directory.mkdir()
                settings=Settings(1,secrets.token_hex(32),directory/'settings.json')
                settings.set_scope(1,2,3,'autonomous');settings.set(1,'enabled',True);settings.set(1,'model',mode)
                settings.set(1,'activity',case.get('activity','very_active'))
                settings.set(1,'reactions',case.get('reactions',False))
                if 'profile' in case:settings.set(1,'character_profile',case['profile'])
                settings.change(1,lambda c:c['guilds']['2'].update(name=case.get('bot_name',protocol['bot_name'])))
                generated=case.get('generate',args.generate)
                transport=SocialTransport(case.get('reactions',False));serving=Counting(backend) if generated else ClassificationOnly(backend)
                runtime=Runtime(settings,serving,transport,None,None,
                    ledger_path=directory/'sent.sqlite3',rng=random.Random(2026))
                runtime.direct_cooldown=0;runtime.direct_spam_window=0;runtime.autonomy_idle_since=-1e9
                seeds={};now=datetime.now(timezone.utc);offset=case.get('gap',5)
                try:
                    for j,seed in enumerate(case.get('seeds',[])):
                        message=100+j*10;author=seed.get('author',4)
                        event=Event(message,2,3,author,seed['user'],now-timedelta(seconds=offset+10-j))
                        flow,_=runtime.conversations.choose(event,direct=True,pending=set())
                        runtime.conversations.observe(flow,event);runtime.conversations.bot(flow,message+1);flow.engaged=True
                        flow.last_at=runtime.activity_clock()-offset
                        if hasattr(flow,'direct_peers'):
                            flow.direct_peers.add(author);flow.last_recipient=author;flow.status='active';flow.link_evidence='synthetic_actual_reply'
                        if seed.get('ended'):
                            flow.ended=True;flow.engaged=False
                            if hasattr(flow,'status'):flow.status='ended'
                        state=DialogueState(limit=100,max_age_seconds=3600);runtime.states[flow.key]=state
                        state.append(channel_id=3,thread_id=None,turn=Turn(str(message),str(author),seed['user'],event.timestamp))
                        state.append(channel_id=3,thread_id=None,turn=Turn(str(message+1),'999',seed['bot'],event.timestamp+timedelta(seconds=1),True,str(message)))
                        seeds[seed.get('key',str(j))]=flow.conversation_id
                        if hasattr(runtime,'social'):
                            runtime.social.observe(event)
                    for uid,name in case.get('members',protocol['members']).items():runtime.members.observe(2,3,int(uid),(name,))
                    for uid,name in case.get('extra_members',{}).items():runtime.members.observe(2,3,int(uid),(name,))
                    for n,item in enumerate(case.get('before',[])):
                        await runtime.ingest(Event(150+n,2,3,item['author'],item['text'],now-timedelta(seconds=len(case.get('before',[]))-n),
                            reply_to=item.get('reply'),reply_author=item.get('reply_author'),member_mentions=tuple(item.get('mentions',()))))
                        await settle(runtime,backend)
                    item=case['event'];metrics_start=len(backend.metrics);semantic_start=serving.semantic_calls;packet_start=len(serving.packet_hashes);assessment_start=len(serving.assessments);started=time.monotonic()
                    await runtime.ingest(Event(200,2,3,item.get('author',4),item['text'],datetime.now(timezone.utc),reply_to=item.get('reply'),
                        reply_author=item.get('reply_author'),member_mentions=tuple(item.get('mentions',()))))
                    await settle(runtime,backend)
                    sent=[s for s in transport.sent if s['source']==200];trace=runtime.traces[-1] if runtime.traces else {}
                    flow_ids=[f.conversation_id for f in runtime.conversations.flows.values() if '200' in f.messages]
                    expected=case.get('flow');flow_ok=not sent or expected is None or bool(flow_ids and ((flow_ids[-1] not in seeds.values()) if expected=='new' else flow_ids[-1]==seeds[expected]))
                    kind_ok=not sent or not case.get('kind') or sent[0]['kind']==case['kind']
                    seed_active=any(f.conversation_id==seeds.get('a') and not f.ended for f in runtime.conversations.flows.values())
                    state_ok=(not case.get('keep_active') or seed_active) and (not case.get('expect_ended') or not seed_active)
                    row=dict(case=case['id'],category=case['category'],phase=case.get('phase','original'),mode=mode,generated=generated,expected=case['respond'],responded=bool(sent),
                        passed=(bool(sent)==case['respond'] and flow_ok and kind_ok and state_ok and len(sent)<=1),flow_ok=flow_ok,kind_ok=kind_ok,state_ok=state_ok,seconds=time.monotonic()-started,
                        semantic_calls=serving.semantic_calls-semantic_start,packet_hashes=serving.packet_hashes[packet_start:],
                        assessments=serving.assessments[assessment_start:],
                        physical_calls=len(backend.metrics[metrics_start:]),traces=runtime.traces,metrics=backend.metrics[metrics_start:],sent=transport.sent)
                    rows.append(row);atomic_private_json(root/'results-private.json',rows)
                    total=sum(mode in c.get('only_modes',args.modes.split(',')) for mode in args.modes.split(',') for c in protocol['cases'])
                    atomic_private_json(root/'progress.json',dict(completed=len(rows),passed=sum(r['passed'] for r in rows),total=total))
                finally:await runtime.close()
        summary=dict(real_gpu=True,real_discord=False,generation=any(r['generated'] for r in rows),mixed_generation=len({r['generated'] for r in rows})>1,cases=len(rows),passed=sum(r['passed'] for r in rows),
            categories={c:dict(n=sum(r['category']==c for r in rows),passed=sum(r['passed'] for r in rows if r['category']==c)) for c in {r['category'] for r in rows}},
            latency=distribution([r['seconds'] for r in rows]),mean_seconds=sum(r['seconds'] for r in rows)/max(1,len(rows)),
            physical_calls=sum(r['physical_calls'] for r in rows),queue_wait=distribution([m.get('queue_seconds',0) for r in rows for m in r['metrics']]),
            false_responses=sum(r['responded'] and not r['expected'] for r in rows),missed=sum(not r['responded'] and r['expected'] for r in rows),
            flow_errors=sum(not r['flow_ok'] for r in rows),peak_allocated_mib=max((m.get('peak_allocated_mib',0) for m in backend.metrics),default=0),
            peak_reserved_mib=max((m.get('peak_reserved_mib',0) for m in backend.metrics),default=0),scheduler=backend.scheduler.snapshot())
        atomic_private_json(root/'summary.json',summary)
        print(json.dumps({k:v for k,v in summary.items() if k!='scheduler'}))
    finally:await backend.close();lease.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--modes',default='base');parser.add_argument('--generate',action='store_true');parser.add_argument('--official-base',action='store_true');parser.add_argument('--legacy-adapter',action='store_true');parser.add_argument('--cache-choices',action='store_true')
    asyncio.run(run(parser.parse_args()))
