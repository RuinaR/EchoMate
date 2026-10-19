"""Bounded, aging GPU admission queue; only its consumer enters the GPU worker."""
from __future__ import annotations
import asyncio
from collections import Counter,deque
from contextvars import ContextVar,copy_context
from dataclasses import dataclass,field
import secrets
import threading
import time

request_context=ContextVar('echomate_request',default=None)

class QueueRejected(RuntimeError):pass
class RequestExpired(RuntimeError):pass

@dataclass
class Request:
    conversation_id:str='offline'
    guild_id:int|None=None
    channel_id:int|None=None
    thread_id:int|None=None
    requester_user_id:int|None=None
    target_message_id:int|None=None
    request_type:str='background'
    priority:int=3
    context_version:int=0
    deadline:float=field(default_factory=lambda:time.monotonic()+180)
    request_id:str=field(default_factory=lambda:secrets.token_hex(12))
    created_at:float=field(default_factory=time.monotonic)
    cancellation_token:threading.Event=field(default_factory=threading.Event,repr=False)
    status:str='created'

class GPUScheduler:
    def __init__(self,limit=12,per_user=4,per_channel=8,aging_seconds=5.,clock=time.monotonic):
        self.limit=limit;self.per_user=per_user;self.per_channel=per_channel
        self.aging_seconds=aging_seconds;self.clock=clock;self.waiting=[];self.active=None
        self.consumer=None;self.closed=False;self.counts=Counter();self.recent=deque(maxlen=100)
        self.admissions=[];self.capacity_changed=asyncio.Event()

    @property
    def pending(self):return len(self.waiting)+int(self.active is not None)+len(self.admissions)

    def _has_capacity(self,r):
        entries=self.waiting+([self.active] if self.active else [])
        return not (len(entries)>=self.limit or
            r.requester_user_id is not None and sum(e[0].requester_user_id==r.requester_user_id and e[0].guild_id==r.guild_id for e in entries)>=self.per_user or
            r.channel_id is not None and sum(e[0].channel_id==r.channel_id and e[0].guild_id==r.guild_id for e in entries)>=self.per_channel)

    async def submit(self,operation,request=None,*,wait_for_capacity=False):
        if self.closed:raise QueueRejected('GPU scheduler closed')
        r=request or Request()
        if self.admissions or not self._has_capacity(r):
            if not wait_for_capacity or len(self.admissions)>=32:
                self.counts['rejected']+=1;raise QueueRejected('GPU queue capacity reached')
            self.admissions.append(r);r.status='admission'
            try:
                while True:
                    if self.closed:raise QueueRejected('GPU scheduler closed')
                    remaining=r.deadline-self.clock()
                    if remaining<=0:self.counts['expired']+=1;raise RequestExpired('Admission deadline reached')
                    eligible=[a for a in self.admissions if self._has_capacity(a)]
                    chosen=min(eligible,key=lambda a:(a.priority-(self.clock()-a.created_at)/self.aging_seconds,a.created_at)) if eligible else None
                    if chosen is r:break
                    self.capacity_changed.clear()
                    await asyncio.wait_for(self.capacity_changed.wait(),remaining)
            except asyncio.CancelledError:
                r.cancellation_token.set();self.counts['cancelled']+=1;raise
            except asyncio.TimeoutError:
                self.counts['expired']+=1;raise RequestExpired('Admission deadline reached') from None
            finally:
                self.admissions.remove(r);self.capacity_changed.set()
        if r.deadline<=self.clock():self.counts['expired']+=1;raise RequestExpired('GPU request expired')
        future=asyncio.get_running_loop().create_future();r.status='queued'
        entry=(r,future,operation,copy_context());self.waiting.append(entry);self.counts['accepted']+=1
        if self.consumer is None or self.consumer.done():self.consumer=asyncio.create_task(self._drain(),name='echomate-gpu-scheduler')
        try:return await asyncio.shield(future)
        except asyncio.CancelledError:
            r.cancellation_token.set()
            if entry in self.waiting:
                self.waiting.remove(entry);self._finish(entry,'cancelled');future.cancel()
            elif self.active is entry and getattr(self,'running',None):
                self.running.cancel()
                try:await asyncio.shield(future)
                except (asyncio.CancelledError,Exception):pass
            # Consume eventual exceptions without cancelling the GPU ownership barrier.
            future.add_done_callback(lambda f:f.exception() if not f.cancelled() else None)
            raise

    def _finish(self,entry,status):
        r=entry[0];r.status=status;self.counts[status]+=1
        self.recent.append(dict(status=status,wait_seconds=max(0,getattr(r,'started_at',self.clock())-r.created_at),
                                seconds=max(0,self.clock()-r.created_at),request_type=r.request_type))

    async def _drain(self):
        while self.waiting and not self.closed:
            now=self.clock()
            # Aging eventually outranks fresh priority-0 jobs, no random lottery.
            entry=min(self.waiting,key=lambda e:(e[0].priority-(now-e[0].created_at)/self.aging_seconds,e[0].created_at))
            self.waiting.remove(entry);r,future,operation,context=entry
            if r.deadline<=now or r.cancellation_token.is_set():
                status='expired' if r.deadline<=now else 'cancelled';self._finish(entry,status)
                if not future.done():future.set_exception(RequestExpired('Queued request no longer valid'))
                continue
            self.active=entry;r.status='running';r.started_at=self.clock()
            self.running=context.run(asyncio.create_task,operation())
            timer=asyncio.get_running_loop().call_later(max(0,r.deadline-self.clock()),self.running.cancel)
            try:
                value=await self.running
                if r.cancellation_token.is_set():raise asyncio.CancelledError()
                self._finish(entry,'completed')
                if not future.done():future.set_result(value)
            except asyncio.CancelledError:
                r.cancellation_token.set();self._finish(entry,'cancelled')
                if not future.done():future.cancel()
            except Exception as exc:
                self._finish(entry,'failed')
                if not future.done():future.set_exception(exc)
            finally:timer.cancel();self.active=None;self.running=None;self.capacity_changed.set()

    def snapshot(self):
        return dict(waiting=len(self.waiting)+len(self.admissions),admission_waiting=len(self.admissions),running=int(self.active is not None),
                    oldest_seconds=round(max([self.clock()-e[0].created_at for e in self.waiting]+[self.clock()-r.created_at for r in self.admissions],default=0),1),
                    active_type=self.active[0].request_type if self.active else None,
                    counts=dict(self.counts),recent=list(self.recent)[-5:])

    async def close(self):
        self.closed=True
        self.capacity_changed.set()
        for entry in self.waiting:
            entry[0].cancellation_token.set();self._finish(entry,'cancelled');entry[1].cancel()
        self.waiting.clear()
        if self.active:
            self.active[0].cancellation_token.set()
            if self.running:self.running.cancel()
        if self.consumer:await asyncio.shield(self.consumer)
