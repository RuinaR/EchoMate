"""A structurally different audit on cached answers, no repeated generation."""
import argparse,asyncio,json,time,hashlib
from pathlib import Path
from unittest.mock import patch
from dialogue_eval_core import private_root,save,metrics_since,report_html
from reference_eval_v2 import calibration,reliability
from reference_audit_v2 import audit


async def run(args):
    from echomate_bot.inference import LocalBackend
    from echomate_bot.instance import InstanceLease
    from echomate_bot.model_registry import ModelValidator,ModelRegistry
    from echomate_bot.loader_memory import loading_reserve,MemoryRecorder
    from echomate_bot.processes import check_resources,model_memory_budget
    root=private_root(args.output);root.mkdir(parents=True,exist_ok=False)
    source=private_root(args.input);rows=json.loads((source/'results-private.json').read_text('utf-8'))
    cases={c['id']:c for c in json.loads((source/'seal.json').read_text('utf-8'))['cases']}
    model=private_root(args.model)
    identity=json.loads((model/'acquisition.json').read_text('utf-8')) if args.qwen else {'model':'Gemma 4 12B existing QA copy'}
    save(root/'seal.json',dict(judge_identity=identity,quantization='NF4 double BF16',template='official local tokenizer; thinking disabled for Qwen',
        input_sha256=hashlib.sha256((source/'results-private.json').read_bytes()).hexdigest(),
        audit_sha256=hashlib.sha256(Path('tools/reference_audit_v2.py').read_bytes()).hexdigest(),calibration=calibration(),
        reliability_sha256=hashlib.sha256(Path('tools/reference_eval_v2.py').read_bytes()).hexdigest(),
        scope='Cached response audit only; same correction thresholds, no holdout or generating again'))
    for name in ('reference_audit_v2.py','reference_eval_v2.py','reference_local_judge.py','run_reference_audit_v2.py'):
        (root/name).write_bytes((Path('tools')/name).read_bytes())
    if check_resources()['free_vram_mib']<10240:raise RuntimeError('Need 10GiB free VRAM')
    if args.qwen:
        from reference_local_judge import LocalJudge
        entry=None;backend=LocalJudge(args.model)
    else:
        entry=ModelValidator().validate(args.model)
        if not entry.compatible:raise ValueError('Official existing Gemma required')
        model_memory_budget(*loading_reserve(entry));backend=LocalBackend(adapter=None)
    lease=InstanceLease();resolve=ModelRegistry.resolve
    summary={};cal=[];scored=[];count=0
    async def measured(*a):
        nonlocal count
        cursor=backend.metrics[-1];value=await audit(backend,*a);value['calls']=metrics_since(backend.metrics,cursor);count+=len(value['calls']);return value
    try:
        with MemoryRecorder(interval=1) as recorder,patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if entry is not None and key=='base' else resolve(r,key)),\
             patch('discord.http.HTTPClient.request',side_effect=AssertionError('No live Discord')),\
             patch('aiohttp.ClientSession._request',side_effect=AssertionError('No external inference')):
            await backend.ready();await backend.probe()
            for item in calibration():
                for view in (0,1):
                    observed=await measured(item['question'],item['reply'],item['profile'],item['evidence'],view)
                    cal.append(dict(id=item['id'],kind=item['kind'],gold=item['gold'],view=view,observed=observed))
                    save(root/'calibration-private.json',cal);print('cal',len(cal),flush=True)
            summary['reliability']=reliability(cal);save(root/'progress.json',summary)
            print('RELIABILITY',json.dumps(summary['reliability']),flush=True)
            # Do not spend further calls on axes that failed known-answer tests.
            if any(v['eligible'] for v in summary['reliability'].values()):
                for row in rows:
                    case=cases[row['case']]
                    judgments=[await measured(case['text'],row['output'],row['profile'],case['evidence'],v) for v in (0,1)]
                    scored.append(dict(row,judgments=judgments));save(root/'results-private.json',scored);print('scored',len(scored),flush=True)
            summary.update(status='COMPLETED_NOT_QUALITY_PASS',calls=count,calibration_errors=sum('error' in r['observed'] for r in cal),memory=recorder.report())
    finally:
        await backend.close();lease.close();save(root/'summary.json',summary);report_html(root/'report.html',scored,summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--qwen',action='store_true');asyncio.run(run(p.parse_args()))
