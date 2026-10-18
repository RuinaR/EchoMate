"""Local paired GPU measurements; private outputs, no training or Discord sends.

TF32 is a hypothesis for residual FP32 operations, not a presumed improvement.
One warmup per case; alternating A/B order and unchanged inputs/decoding.
"""
import argparse
import asyncio
import hashlib
import json
import time
from pathlib import Path
from echomate_bot.inference import LocalBackend
from echomate_bot.character import instruction
from echomate_bot.settings import DEFAULTS,private_path,atomic_private_json
from echomate_bot.telemetry import Trace,active_trace,distribution


async def run(root,repeats):
    from echomate_bot.instance import InstanceLease
    lease=InstanceLease()
    try:await measure(root,repeats)
    finally:lease.close()


async def measure(root,repeats):
    root.mkdir(parents=True,exist_ok=False)
    backend=LocalBackend();rows=[]
    prompts={'chat':'오늘 할 일 끝냈어. 이제 좀 쉬어야겠다.',
             'technical':'파이썬 리스트의 얕은 복사와 깊은 복사는 어떻게 달라? 차이와 짧은 예를 설명해 줘.'}
    sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/echomate_bot').glob('*.py')}
    atomic_private_json(root/'manifest.json',dict(seed=2026,repeats=repeats,sources=sources,
        model='google/gemma-4-12B-it',adapter=str(backend.adapter),budget=384,greedy=True,
        cases=prompts,warmup_per_case=1,hypothesis='TF32 for residual FP32 operations'))
    try:
        cold=time.monotonic();await backend.ready()
        import torch
        original=torch.backends.cuda.matmul.allow_tf32
        print(json.dumps(dict(loaded_seconds=round(time.monotonic()-cold,3),tf32_default=original)),flush=True)
        async def sample(case,variant,warmup=False):
            def configure():
                torch.backends.cuda.matmul.allow_tf32=original if variant=='A' else True
                torch.manual_seed(2026)
            await asyncio.get_running_loop().run_in_executor(backend.executor,configure)
            trace=Trace();token=active_trace.set(trace);started=time.monotonic()
            try:
                answer=await backend._job([dict(role='system',content=instruction(DEFAULTS)),
                    dict(role='user',content=prompts[case])],budget=384)
                row=dict(case=case,variant=variant,warmup=warmup,seconds=time.monotonic()-started,
                         call=trace.calls[-1],response=answer,sha256=hashlib.sha256(answer.encode()).hexdigest())
                rows.append(row);atomic_private_json(root/'results.json',rows)
                print(json.dumps({k:row[k] for k in ('case','variant','warmup','seconds')}),flush=True)
            finally:active_trace.reset(token)
        for case in prompts:await sample(case,'A',True)
        for iteration in range(repeats):
            for case in prompts:
                for variant in ('A','B') if iteration%2==0 else ('B','A'):await sample(case,variant)
        summary={case:{v:dict(seconds=distribution([r['seconds'] for r in rows if r['case']==case and r['variant']==v and not r['warmup']]),
            ttft=distribution([r['call']['ttft_seconds'] for r in rows if r['case']==case and r['variant']==v and not r['warmup']]),
            tps=distribution([r['call']['tokens_per_second'] for r in rows if r['case']==case and r['variant']==v and not r['warmup']]),
            outputs_identical=len({r['sha256'] for r in rows if r['case']==case and not r['warmup']})==1)
            for v in ('A','B')} for case in prompts}
        atomic_private_json(root/'summary.json',summary)
        print(json.dumps(summary),flush=True)
    finally:
        if backend.model is not None:
            torch.backends.cuda.matmul.allow_tf32=original
        await backend.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repeats',type=int,default=5);a=p.parse_args()
    if not 3<=a.repeats<=20:p.error('repeats must be 3..20')
    asyncio.run(run(private_path(a.output),a.repeats))
