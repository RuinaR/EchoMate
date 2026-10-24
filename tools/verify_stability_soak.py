"""Elapsed-time mixed local soak. No Discord client, live DB or network access.

Mock semantics test lifecycle, not language quality. Sparse optional GPU probes
use a borrowed resident backend so no second model or GPU worker is created.
All content-bearing outputs remain below a fresh local_data directory.
"""
import argparse
import asyncio
from collections import Counter
from datetime import datetime,timezone,timedelta
import gc
import json
from pathlib import Path
import random
import secrets
import sqlite3
import threading
import time
from itertools import count

from echomate_bot.companion_store import CompanionStore
from echomate_bot.loader_memory import memory_snapshot
from echomate_bot.runtime import Runtime,Event
from echomate_bot.scheduler import GPUScheduler,Request,RequestExpired
from echomate_bot.settings import Settings,private_path,atomic_private_json
from echomate_bot.social import SocialDecision
from echomate_bot.telemetry import summarize
from echomate_studio.dialogue_state import Turn
from verify_parallel_gpu import Borrowed,Transport,settle


class MockBackend:
    fast_text_path=True
    failed=False
    def __init__(self):self.scheduler=GPUScheduler();self.metrics=[]
    @property
    def pending(self):return self.scheduler.pending
    async def text(self,context,cfg):
        async def generate():
            await asyncio.sleep(.002)
            return '응, 확인했어.'
        return await self.scheduler.submit(generate,wait_for_capacity=True)
    async def assess_social(self,packet):
        peers=packet['current_peer_frames']
        return SocialDecision('bot','continue',peers[0],'reaction',True) if peers else SocialDecision('uncertain','uncertain','none','other',False)
    async def close(self):await self.scheduler.close()


class SoakTransport(Transport):
    message_ids=count(9000000)
    async def catalog(self,event,cache):return dict(reactions={'👍':'동의'},stickers={})
    async def execute(self,event,action,library,fresh):
        if not await fresh():raise ValueError('Stale synthetic send')
        self.sent.append(dict(source=event.response_to or event.id,author=event.author,text=action.text,kind=action.kind.value,seconds=time.monotonic()-event.received_at))
        return None if action.kind.value=='REACTION' else next(self.message_ids)


def batch_matches(sent,expected):
    """Different users may finish preparation in either order, never swap IDs.

    Fair queue order starts at queue admission, not asynchronous event arrival.
    Exact multiplicity AND the source-to-author binding remain mandatory.
    """
    return (Counter(x['source'] for x in sent)==Counter(expected.keys()) and
            all(x['author']==expected.get(x['source']) and x['kind']=='TEXT' for x in sent))


async def capacity_probe(root,backend):
    """32 completed synthetic histories, then one actual GPU reply at capacity."""
    root=private_path(root);root.mkdir(parents=True,exist_ok=False)
    cfg=Settings(1,secrets.token_hex(32),root/'settings.json');cfg.set(1,'enabled',True);cfg.set_scope(1,2,3,'autonomous')
    mock=MockBackend();transport=SoakTransport();runtime=Runtime(cfg,Borrowed(mock),transport,None,None,ledger_path=root/'sent.sqlite3')
    runtime.direct_cooldown=0;runtime.direct_spam_window=0
    try:
        for i in range(32):
            await runtime.ingest(Event(3000+i,2,3,4,f'<@999> 별개 점검 {i}번에 짧게 인사해 줘',datetime.now(timezone.utc),member_mentions=(999,)))
            await settle(runtime,mock)
        runtime.backend=Borrowed(backend)
        await runtime.ingest(Event(3100,2,3,4,'<@999> 별개 질문 8 더하기 7의 답을 숫자로만 말해 줘',datetime.now(timezone.utc),member_mentions=(999,)))
        await settle(runtime,backend)
        passed=([x['source'] for x in transport.sent]==[*range(3000,3032),3100] and '15' in transport.sent[-1]['text'] and len(runtime.states)==32)
        result=dict(passed=passed,fixture_replies=32,real_gpu_replies=1,states=len(runtime.states),traces=runtime.traces,outputs=transport.sent)
        atomic_private_json(root/'results-private.json',result)
        return {k:v for k,v in result.items() if k not in ('traces','outputs')}
    finally:await runtime.close();await mock.close()


async def run(root,seconds=1200,backend=None,gpu_interval=120,period=1,restart_interval=60):
    if not 0<seconds<=86400 or period<=0 or gpu_interval<1 or restart_interval<=0:raise ValueError('Invalid soak duration')
    root=private_path(root);root.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();counts=Counter();samples=[];traces=[];gpu_rows=[];errors=[]
    key=secrets.token_hex(32);settings=Settings(1,key,root/'settings.json')
    settings.set(1,'enabled',True);settings.set(1,'reactions',True)
    for channel in (3,4,5):settings.set_scope(1,2,channel,'autonomous',thread=channel==5)
    store=CompanionStore(root/'companion.sqlite3')
    for uid in range(4,12):
        for category in ('relationships','memory','summaries'):store.set_consent(2,uid,category,True)
    mock=MockBackend();transport=SoakTransport();runtime=None
    def make_runtime():
        value=Runtime(settings,Borrowed(mock),transport,None,None,ledger_path=root/'sent.sqlite3',rng=random.Random(2026),companion=store)
        value.direct_cooldown=0;value.direct_spam_window=0
        return value
    runtime=make_runtime();i=0;next_gpu=0.;next_sample=0.;next_restart=restart_interval
    initial_tasks=set(asyncio.all_tasks());initial_threads=threading.active_count()
    try:
        while time.monotonic()-started<seconds:
            elapsed=time.monotonic()-started;i+=1
            base=10000+i*20;channel=(3,4,5)[i%3];uid=4+i%8
            event=Event(base,2,channel,uid,f'<@999> 점검 {i}번의 짧은 인사를 해 줘',datetime.now(timezone.utc),parent=4 if channel==5 else None,member_mentions=(999,))
            begin=len(transport.sent)
            # Independent same-user/other-user direct requests retain sources.
            await runtime.ingest(event)
            await runtime.ingest(Event(base+1,2,channel,4+(i+1)%8,f'<@999> 별개 점검 {i}번에 한 문장으로 인사해 줘',datetime.now(timezone.utc),parent=event.parent,member_mentions=(999,)))
            await settle(runtime,mock)
            await runtime.ingest(event) # completed Gateway duplicate
            denied=Event(base+2,2,99,uid,'<@999> 허용하지 않은 곳',datetime.now(timezone.utc),member_mentions=(999,))
            await runtime.ingest(denied);await settle(runtime,mock)
            sent=transport.sent[begin:];sources=[x['source'] for x in sent]
            if not batch_matches(sent,{base:uid,base+1:4+(i+1)%8}):
                atomic_private_json(root/'failure-private.json',dict(expected=[base,base+1],actual=sources,traces=runtime.traces,diagnostics=runtime.diagnostics))
                raise AssertionError('Duplicate, missing or wrong reply target')
            counts['independent_replies']+=2;counts['duplicate_and_scope_veto']+=2
            store.relationship(2,uid,base,observed=event.timestamp.timestamp());counts['relationship_event']+=1
            if i%5==0:
                reaction=Event(base+3,2,channel,uid,'<@999> 이 메시지에 👍 반응 달아줘',datetime.now(timezone.utc),parent=event.parent,member_mentions=(999,))
                await runtime.ingest(reaction);await settle(runtime,mock)
                if transport.sent[-1].get('kind')!='REACTION':raise AssertionError('Reaction request did not reach executor')
                counts['reaction']+=1
            if i%10==0:
                # Stored digests require actual fixture turns newer than consent.
                stamp=datetime.now(timezone.utc)
                turn=Turn(str(base+4),str(uid),'나는 종이접기를 배우고 있어',stamp)
                versions=store.digest_consent(2,{uid})
                digest=store.save_digest(2,channel,'soak-'+str(uid),dict(items=[dict(text='종이접기를 배우고 있다는 본인의 설명',sources=[str(base+4)])]),[turn],versions)
                if not digest:raise AssertionError('Consented digest not saved')
                counts['digest']+=1
                store.set_consent(2,uid,'summaries',False)
                if store.save_digest(2,channel,'stale',dict(items=[dict(text='오래된 작업에서 저장하려는 내용',sources=[str(base+4)])]),[turn],versions):raise AssertionError('Stale consent accepted')
                store.delete_personal(2,uid,'summaries')
                if store.digests(2,uid):raise AssertionError('Deleted digest reappeared')
                store.set_consent(2,uid,'summaries',True);counts['revoke_delete_veto']+=1
                store.add_memory(2,uid,channel,'종이접기를 좋아해','preference',source=base+5,observed=stamp.timestamp(),require_consent=True)
                store.delete_personal(2,uid,'memory');store.set_consent(2,uid,'memory',True)
                if store.add_memory(2,uid,channel,'삭제 뒤 오래된 작업의 정보','explicit',source=base+6,observed=stamp.timestamp(),require_consent=True):raise AssertionError('Deleted memory recreated by stale job')
                counts['memory_delete']+=1
            if i%15==0:
                reminder=store.reserve_reminder(event,time.time()+60,'UTC','합성 점검 알림')
                store.change_reminder(2,uid,reminder['reminder_id'],cancel=True)
                counts['reminder_cancel']+=1
                with sqlite3.connect(store.path) as locked:
                    locked.execute('BEGIN IMMEDIATE')
                    try:store.set_consent(2,uid,'relationships',True)
                    except sqlite3.OperationalError:counts['db_lock_recovered']+=1
                    else:raise AssertionError('SQLite write lock not exercised')
                    locked.rollback()
                store.set_consent(2,uid,'relationships',True)
            if i%20==0:
                expired=Request(deadline=time.monotonic()-1)
                async def forbidden():raise AssertionError('Expired job executed')
                try:await mock.scheduler.submit(forbidden,expired)
                except RequestExpired:counts['expired_veto']+=1
            if backend is not None and elapsed>=next_gpu:
                # Mock producer is paused during GPU sample; no parallel stress.
                probe=SoakTransport();live=Runtime(settings,Borrowed(backend),probe,None,None,ledger_path=root/f'gpu-{len(gpu_rows)}.sqlite3')
                try:
                    await live.ingest(Event(base+10,2,3,4,'<@999> 8 더하기 7의 답을 숫자로만 말해 줘',datetime.now(timezone.utc),member_mentions=(999,)))
                    await settle(live,backend)
                    ok=len(probe.sent)==1 and probe.sent[0]['source']==base+10 and '15' in probe.sent[0]['text']
                    gpu_rows.append(dict(seconds=time.monotonic()-started,passed=ok,traces=live.traces))
                    if not ok:raise AssertionError('Sparse GPU probe failed')
                    counts['gpu_probe']+=1
                finally:await live.close()
                next_gpu=elapsed+gpu_interval
            if elapsed>=next_restart:
                traces.extend(runtime.traces);traces=traces[-2000:]
                await runtime.close();runtime=make_runtime()
                settings=Settings(1,key,root/'settings.json');runtime.settings=settings
                before=len(transport.sent);await runtime.ingest(event);await settle(runtime,mock)
                if len(transport.sent)!=before:raise AssertionError('Restart replay duplicated a completed reply')
                counts['restart']+=1;next_restart=elapsed+restart_interval
            if elapsed>=next_sample:
                gc.collect();s=memory_snapshot()
                if backend is not None:
                    import torch
                    s.update(gpu_allocated=torch.cuda.memory_allocated(),gpu_reserved=torch.cuda.memory_reserved())
                s.update(seconds=time.monotonic()-started,tasks=len(asyncio.all_tasks()),threads=threading.active_count(),flows=len(runtime.conversations.flows),states=len(runtime.states),message_index=len(runtime.conversations.message_flow),queue=mock.pending,choice_cache=len(getattr(backend,'_choice_cache',{})))
                samples.append(s);next_sample=elapsed+5
                atomic_private_json(root/'progress.json',dict(elapsed_seconds=s['seconds'],iterations=i,counts=dict(counts),sample=s))
            transport.sent.clear() # inspection fixture must not create a fake leak
            await asyncio.sleep(min(period,max(0,seconds-(time.monotonic()-started))))
    except BaseException as exc:
        errors.append(type(exc).__name__);raise
    finally:
        traces.extend(runtime.traces);await runtime.close();await mock.close()
        await asyncio.sleep(0);gc.collect()
        lingering=[t.get_name() for t in asyncio.all_tasks()-initial_tasks if not t.done()]
        result=dict(elapsed_seconds=time.monotonic()-started,iterations=i,counts=dict(counts),errors=errors,
            passed=not errors and not lingering and mock.pending==0 and time.monotonic()-started>=seconds,lingering_tasks=lingering,
            initial_threads=initial_threads,final_threads=threading.active_count(),samples=samples,gpu=gpu_rows,
            mock_pipeline=summarize(traces[-2000:]),real_discord=False,real_gpu=backend is not None,
            caution='Elapsed local mixed soak, not 24-hour use, semantic quality or cross-Windows certification')
        atomic_private_json(root/'summary-private.json',result)
    return {k:v for k,v in result.items() if k not in ('samples','gpu','mock_pipeline')}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--seconds',type=float,default=1200)
    a=p.parse_args();print(json.dumps(asyncio.run(run(a.output,a.seconds))))
