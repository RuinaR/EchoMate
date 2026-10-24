"""Allocation provenance of the existing synthetic soak, never other processes.

Diagnostic acceleration changes event rate: not elapsed production endurance.
No GPU/Discord/operating stores. Snapshots and raw filenames stay private.
"""
import argparse
import asyncio
from collections import Counter
import ctypes
import gc
import json
from pathlib import Path
import sys
import tracemalloc
import weakref
from verify_stability_soak import run


def deep_size(value,seen=None):
    seen=set() if seen is None else seen
    if id(value) in seen:return 0
    seen.add(id(value));size=sys.getsizeof(value)
    if isinstance(value,dict):return size+sum(deep_size(k,seen)+deep_size(v,seen) for k,v in value.items())
    if isinstance(value,(list,tuple,set)):return size+sum(deep_size(x,seen) for x in value)
    return size


async def profile(root,seconds=120):
    if not 15<=seconds<=300:raise ValueError('Bounded allocation probe')
    root=Path(root);rows=[];refs=[];last=None;baseline=None;latest=None
    def observe(runtime,traces,sample):
        nonlocal last,baseline,latest
        if last is None or last()!=runtime:last=weakref.ref(runtime);refs.append(last)
        objects=Counter(type(x).__name__ for x in gc.get_objects()
            if isinstance(type(x).__module__,str) and type(x).__module__.startswith('echomate'))
        row=dict(seconds=sample['seconds'],pointer_types=len(ctypes._pointer_type_cache),runtime_objects=objects,
            retired_runtimes_alive=sum(r() is not None for r in refs[:-1]),trace_count=len(traces)+len(runtime.traces),
            retained_trace_bytes=deep_size((traces,runtime.traces)),traced=tracemalloc.get_traced_memory(),
            tracer_metadata=tracemalloc.get_tracemalloc_memory(),private=sample['process_private'])
        rows.append(row);latest=tracemalloc.take_snapshot()
        if baseline is None:baseline=latest
    tracemalloc.start(5)
    try:
        result=await run(root,seconds=seconds,period=.001,restart_interval=10,observe=observe)
        gc.collect();after=tracemalloc.take_snapshot()
        def top(snapshot):return [dict(bytes=x.size_diff,count=x.count_diff,traceback=str(x.traceback)) for x in snapshot.compare_to(baseline,'lineno')[:25]]
        report=dict(result=result,rows=rows,top_live=top(latest),after_return=top(after),
            runtime_refs_alive_after_return=sum(r() is not None for r in refs),
            caveat='tracemalloc and accelerated fixture retention affect private memory; not a 20min/8h GPU run')
        (root/'allocation-private.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(dict(passed=result['passed'],samples=len(rows),runtime_refs_alive_after_return=report['runtime_refs_alive_after_return'])))
    finally:tracemalloc.stop()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--seconds',type=float,default=120);a=p.parse_args()
    asyncio.run(profile(a.output,a.seconds))
