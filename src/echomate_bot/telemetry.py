"""Bounded numeric diagnostics. Never accepts messages, IDs or exception text."""
from __future__ import annotations
from contextvars import ContextVar
from contextlib import contextmanager
from collections import Counter
import math
import time

active_trace = ContextVar('echomate_trace', default=None)
STAGES = frozenset({'assessment','continuity','visual','action','text','sending','memory_lookup','private_request','conversation_wait','research','output_check'})


def process_ram_mib():
    import os
    if os.name!='nt':return None
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in
            ('peak_working','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    kernel=ctypes.windll.kernel32;kernel.GetCurrentProcess.restype=wintypes.HANDLE
    fn=ctypes.windll.psapi.GetProcessMemoryInfo
    fn.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    if not fn(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):return None
    return round(counters.working/1048576,1)


class Trace:
    def __init__(self, started=None):
        self.started = time.monotonic() if started is None else started
        self.stage_name = None
        self.stage_at = time.monotonic()
        self.stages = {}
        self.calls = []
        self.outcome = 'silence'
        self.regenerations = 0
        self.codes = []

    def stage(self, name):
        if name not in STAGES:raise ValueError('Unknown stage')
        now = time.monotonic()
        key = self.stage_name or 'ingest_context'
        self.stages[key] = self.stages.get(key, 0.) + now-self.stage_at
        if self.stage_name is None:self.stages[key] += max(0.,self.stage_at-self.started)
        self.stage_name, self.stage_at = name, now

    def finish(self):
        now = time.monotonic()
        if self.stage_name:
            self.stages[self.stage_name] = self.stages.get(self.stage_name,0.)+now-self.stage_at
        return dict(seconds=now-self.started, outcome=self.outcome, stages=self.stages,
                    regenerations=self.regenerations, calls=self.calls,codes=self.codes,decision=getattr(self,'decision',None))


@contextmanager
def measure(name):
    """Subspans overlap stage totals and must not be added to them."""
    if name not in {'permissions','catalog','discord_send'}:raise ValueError('Unknown span')
    started=time.monotonic()
    try:yield
    finally:
        trace=active_trace.get()
        if trace:trace.stages[name]=trace.stages.get(name,0.)+time.monotonic()-started


def distribution(values):
    values=sorted(v for v in values if isinstance(v,(int,float)) and math.isfinite(v))
    def percentile(p):
        if not values:return None
        index=(len(values)-1)*p;lo=int(index);hi=min(lo+1,len(values)-1)
        return round(values[lo]+(values[hi]-values[lo])*(index-lo),4)
    return dict(n=len(values),p50=percentile(.5),p90=percentile(.9),p95=percentile(.95))


def summarize(records):
    """Only successful sends enter response percentiles; all outcomes are counted."""
    sent=[r for r in records if r['outcome']=='sent']
    calls=[c for r in records for c in r['calls']]
    return dict(samples=len(records),outcomes=dict(Counter(r['outcome'] for r in records)),
                response_seconds=distribution([r['seconds'] for r in sent]),
                queue_seconds=distribution([c.get('queue_seconds') for c in calls]),
                ttft_seconds=distribution([c.get('ttft_seconds') for c in calls]),
                tokens_per_second=distribution([c.get('tokens_per_second') for c in calls]),
                regenerations=sum(r['regenerations'] for r in records),
                stages={s:distribution([r['stages'][s] for r in sent if s in r['stages']])
                        for s in sorted({s for r in sent for s in r['stages']})})
