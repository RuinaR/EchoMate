"""Matched fixed-workload diagnostic retention ablation; CPU/mock only.

Run each arm in a fresh process. Released means retention disabled, not
removal of Runtime tracing computation or product safety checks.
"""
import argparse
import asyncio
import ctypes
import gc
import json
import sys
from collections import Counter
from pathlib import Path
import tracemalloc
import weakref
from profile_runtime_memory import deep_size
from verify_stability_soak import run
from echomate_bot.loader_memory import memory_snapshot


async def compare(root,retained,traced=False,iterations=240,measure_size=True,size_interval=5):
    root=Path(root);refs=[];last=None;rows=[];baseline=None;modules_before=len(sys.modules);next_size=0;trace_bytes=None
    def observe(runtime,traces,sample):
        nonlocal last,next_size,trace_bytes
        if last is None or last()!=runtime:last=weakref.ref(runtime);refs.append(last)
        if sample['process_private']>256*1024**2 or sample['ram_available']<3*1024**3 or sample['commit_available']<2*1024**3:raise RuntimeError('Diagnostic resource reserve')
        if measure_size and sample['seconds']>=next_size:
            trace_bytes=deep_size((traces,runtime.traces));next_size=sample['seconds']+size_interval
        row=dict(seconds=sample['seconds'],private=sample['process_private'],handles=sample['process_handles'],
            pointers=len(ctypes._pointer_type_cache),retired=sum(r() is not None for r in refs[:-1]),
            traces=len(traces)+len(runtime.traces),trace_bytes=trace_bytes)
        if traced:row.update(traced=tracemalloc.get_traced_memory(),tracer_metadata=tracemalloc.get_tracemalloc_memory())
        rows.append(row)
    if traced:tracemalloc.start(1);baseline=tracemalloc.take_snapshot()
    try:
        result=await run(root,seconds=600,period=.001,restart_interval=10,observe=observe,
            diagnostic_retention=retained,max_iterations=iterations,sample_history_limit=16,restart_every_iterations=60)
        before_gc=memory_snapshot();collected=gc.collect();after_gc=memory_snapshot()
        objects=Counter(type(x).__name__ for x in gc.get_objects()
            if isinstance(type(x).__module__,str) and type(x).__module__.startswith('echomate'))
        report=dict(result=result,rows=rows,retained=retained,tracemalloc=traced,post_return_alive=sum(r() is not None for r in refs),
            measure_size=measure_size,size_interval=size_interval,
            post_close_gc=dict(collected=collected,before=before_gc,after=after_gc,own_object_types=objects),
            modules_before=modules_before,modules_after=len(sys.modules),
            caveat='Retention ablation, equal fixed input count; not elapsed endurance or disabled computation. Tracer changes resource cost.')
        if traced:
            after=tracemalloc.take_snapshot();report['allocations']=[dict(bytes=x.size_diff,count=x.count_diff,line=str(x.traceback)) for x in after.compare_to(baseline,'lineno')[:25]]
        (root/'retention-private.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        if not result['passed']:raise RuntimeError('Fixed workload did not complete safely')
        print(json.dumps(dict(iterations=result['iterations'],passed=result['passed'],post_return_alive=report['post_return_alive'])))
    finally:
        if traced:
            tracemalloc.stop()
            if 'report' in locals():
                report['after_tracer_stop']=memory_snapshot()
                (root/'retention-private.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--released',action='store_true');p.add_argument('--traced',action='store_true')
    p.add_argument('--iterations',type=int,choices=[240,2400],default=240);p.add_argument('--no-size',action='store_true');p.add_argument('--size-interval',type=int,choices=[5,60],default=5);a=p.parse_args()
    asyncio.run(compare(a.output,not a.released,a.traced,a.iterations,not a.no_size,a.size_interval))
