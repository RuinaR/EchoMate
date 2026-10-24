"""Matched fixed-workload diagnostic retention ablation; CPU/mock only.

Run each arm in a fresh process. Released means retention disabled, not
removal of Runtime tracing computation or product safety checks.
"""
import argparse
import asyncio
import ctypes
import gc
import json
from pathlib import Path
import tracemalloc
import weakref
from profile_runtime_memory import deep_size
from verify_stability_soak import run


async def compare(root,retained,traced=False,iterations=240):
    root=Path(root);refs=[];last=None;rows=[];baseline=None
    def observe(runtime,traces,sample):
        nonlocal last
        if last is None or last()!=runtime:last=weakref.ref(runtime);refs.append(last)
        row=dict(seconds=sample['seconds'],private=sample['process_private'],handles=sample['process_handles'],
            pointers=len(ctypes._pointer_type_cache),retired=sum(r() is not None for r in refs[:-1]),
            traces=len(traces)+len(runtime.traces),trace_bytes=deep_size((traces,runtime.traces)))
        if traced:row.update(traced=tracemalloc.get_traced_memory(),tracer_metadata=tracemalloc.get_tracemalloc_memory())
        rows.append(row)
    if traced:tracemalloc.start(1);baseline=tracemalloc.take_snapshot()
    try:
        result=await run(root,seconds=600,period=.001,restart_interval=10,observe=observe,
            diagnostic_retention=retained,max_iterations=iterations,sample_history_limit=16)
        gc.collect()
        report=dict(result=result,rows=rows,retained=retained,tracemalloc=traced,post_return_alive=sum(r() is not None for r in refs),
            caveat='Retention ablation, equal fixed input count; not elapsed endurance or disabled computation. Tracer changes resource cost.')
        if traced:
            after=tracemalloc.take_snapshot();report['allocations']=[dict(bytes=x.size_diff,count=x.count_diff,line=str(x.traceback)) for x in after.compare_to(baseline,'lineno')[:25]]
        (root/'retention-private.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(dict(iterations=result['iterations'],passed=result['passed'],post_return_alive=report['post_return_alive'])))
    finally:
        if traced:tracemalloc.stop()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--released',action='store_true');p.add_argument('--traced',action='store_true');a=p.parse_args()
    asyncio.run(compare(a.output,not a.released,a.traced))
