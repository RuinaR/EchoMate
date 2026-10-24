"""Existing elapsed CPU/mock soak plus bounded, own-process retention counts.

No tracemalloc/GPU, operating stores, live Discord or other process inspection.
Not a long GPU or cross-Windows certificate; duration is real elapsed time.
"""
import argparse
import asyncio
import ctypes
import gc
import json
from pathlib import Path
import weakref
from profile_runtime_memory import deep_size
from verify_stability_soak import run


async def verify(root,seconds,released=False):
    if not 60<=seconds<=7200:raise ValueError('Bounded elapsed run required')
    refs=[];last=None;next_measure=0;trace_bytes=0
    def observe(runtime,traces,sample):
        nonlocal last,next_measure,trace_bytes
        if last is None or last()!=runtime:last=weakref.ref(runtime);refs.append(last)
        if sample['seconds']>=next_measure:
            trace_bytes=deep_size((traces,runtime.traces));next_measure=sample['seconds']+60
        sample.update(pointer_types=len(ctypes._pointer_type_cache),retired_runtimes_alive=sum(r() is not None for r in refs[:-1]),
            retained_trace_count=len(traces)+len(runtime.traces),last_measured_trace_bytes=trace_bytes)
        if sample['process_private']>256*1024**2 or sample['ram_available']<3*1024**3 or sample['commit_available']<2*1024**3:
            raise RuntimeError('Own soak/system aggregate safety reserve reached')
    result=await run(root,seconds=seconds,observe=observe,diagnostic_retention=not released)
    gc.collect();result['runtime_refs_alive_after_return']=sum(r() is not None for r in refs)
    assert result['runtime_refs_alive_after_return']==0
    (Path(root)/'retention-summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=1200);p.add_argument('--output',required=True);p.add_argument('--released',action='store_true');a=p.parse_args()
    asyncio.run(verify(a.output,a.seconds,a.released))
