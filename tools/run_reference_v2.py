"""Single-resident bounded reference/repair experiment, real Runtime SDK mock.

Run only from the project root. Outputs and source snapshots are private.
"""
import argparse,asyncio,json,hashlib,time
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from dialogue_eval_core import private_root,save,metrics_since,digest,report_html
from reference_eval_v2 import calibration,judge,reliability


def cases():
    return [dict(id='choice',text='모임 준비를 나만 떠맡은 것 같아. 그냥 다 해버리는 게 편할까?',evidence=dict(user_facts=['모임 준비 부담'],memories=[],receipts=[],fiction=[])),
        dict(id='small-mistake',text='화분에 물 주겠다고 달력만 멋지게 꾸미고 물은 안 줬네. 한마디 해봐.',evidence=dict(user_facts=['달력을 꾸몄지만 물을 안 줌'],memories=[],receipts=[],fiction=[])),
        dict(id='missing-fact',text='내가 제일 좋아하는 빵이 뭐였지? 확실한 것만 말해.',evidence=dict(user_facts=[],memories=[],receipts=[],fiction=[])),
        dict(id='future-memory',text='나는 보라색 우산을 좋아해. 몇 주 후에도 이 얘기를 꺼낼 수 있을까?',evidence=dict(user_facts=['보라색 우산을 좋아함'],memories=[],receipts=[],fiction=[],memory_write='not_confirmed'))]


async def run(args):
    from echomate_bot.inference import LocalBackend
    from echomate_bot.model_registry import ModelValidator,ModelRegistry
    from echomate_bot.instance import InstanceLease
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.loader_memory import loading_reserve,MemoryRecorder,memory_snapshot
    from echomate_bot.character_profiles import presets
    from diagnose_persona_pipeline import runtime_answer,minimal_messages
    from reference_candidate_v2 import generate
    from character_reference_v2 import library
    root=private_root(args.output);root.mkdir(parents=True,exist_ok=False)
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:raise ValueError('Existing official Gemma required')
    health=check_resources()
    if health['free_vram_mib']<10240:raise RuntimeError('Need 10GiB free VRAM')
    model_memory_budget(*loading_reserve(entry))
    profiles=presets()
    for p in profiles.values():p['name']='EchoMate'
    tools=[Path(__file__),Path('tools/reference_candidate_v2.py'),Path('tools/reference_eval_v2.py'),Path('tools/character_reference_v2.py')]
    save(root/'seal.json',dict(cases=cases(),calibration=calibration(),profiles=profiles,references=library(),
        code={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in tools},adoption=dict(persona_weight=.5,facts_weight=.5,
        hard_factual_veto=True,judge_accuracy=.9,judge_consistency=.9,independent_required=True,max_seconds=2400),real_discord=False))
    for p in tools:(root/p.name).write_bytes(p.read_bytes())
    lease=InstanceLease();backend=LocalBackend(adapter=None);resolve=ModelRegistry.resolve
    summary=dict(before=memory_snapshot(),health=health,status='RUNNING');rows=[];cal=[];start=time.monotonic()
    original_text=backend.text
    try:
        with MemoryRecorder(interval=1) as recorder,patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)),\
             patch('discord.http.HTTPClient.request',side_effect=AssertionError('No live Discord')),\
             patch('aiohttp.ClientSession._request',side_effect=AssertionError('No external inference')):
            t=time.monotonic();await backend.ready();await backend.probe();summary['load_seconds']=time.monotonic()-t
            for item in calibration():
                for view in (0,1):
                    observed=await judge(backend,item['question'],item['reply'],item['profile'],item['evidence'],view)
                    cal.append(dict(id=item['id'],kind=item['kind'],view=view,gold=item['gold'],observed=observed))
                    save(root/'calibration-private.json',cal)
            summary['reliability']=reliability(cal);save(root/'progress.json',summary)
            print('CALIBRATED',json.dumps(summary['reliability']),flush=True)
            for index,case in enumerate(cases()):
                for j,(key,profile) in enumerate(profiles.items()):
                    arms=['baseline','reference'] if (index+j)%2==0 else ['reference','baseline']
                    if summary['reliability']['facts']['eligible']:arms.append('reference-repair')
                    for arm in arms:
                        if time.monotonic()-start>2400:raise TimeoutError('Bounded experiment expired')
                        check_resources();cursor=backend.metrics[-1];t=time.monotonic();feedback=[]
                        # Intercept generation only; actual Runtime still owns eligibility,
                        # current settings, consent, output/send checks and SDK reply.
                        async def candidate(context,cfg):
                            with patch.object(backend,'text',original_text):
                                return await generate(backend,context,cfg,repair=arm=='reference-repair',evidence=case['evidence'],observations=feedback,
                                    verifier=judge if summary['reliability']['facts']['eligible'] else None)
                        with patch.object(backend,'text',side_effect=candidate) if arm!='baseline' else patch.object(backend,'text',original_text):
                            detail=await runtime_answer(backend,profile,case['text'],root/f'{case["id"]}-{key}-{arm}')
                        measured=metrics_since(backend.metrics,cursor)
                        rows.append(dict(record_id=f'{case["id"]}-{key}-{arm}',case=case['id'],profile=key,phase=arm,
                            seconds=time.monotonic()-t,calls=measured,feedback=feedback,evidence=case['evidence'],**detail))
                        save(root/'results-private.json',rows);print('RESPONSE',len(rows),case['id'],key,arm,flush=True)
            # Exact same input/profile comparison with the earlier minimal control.
            for case in cases()[:2]:
                for key,profile in profiles.items():
                    cursor=backend.metrics[-1];t=time.monotonic()
                    output=await backend._job(minimal_messages(profile,case['text']),weight='base',budget=768)
                    rows.append(dict(record_id=f'{case["id"]}-{key}-minimal',case=case['id'],profile=key,phase='minimal',output=output,
                        seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor),evidence=case['evidence']))
                    save(root/'results-private.json',rows)
            for row in rows:
                if not any(v['eligible'] for v in summary['reliability'].values()):break
                case=next(c for c in cases() if c['id']==row['case'])
                row['judgments']=[await judge(backend,case['text'],row['output'],row['profile'],row['evidence'],v) for v in (0,1)]
                save(root/'results-private.json',rows)
            summary.update(status='COMPLETED_NOT_QUALITY_PASS',memory=recorder.report())
    except BaseException as exc:
        summary.update(status='STOPPED',error=type(exc).__name__);raise
    finally:
        await backend.close();lease.close();summary['after']=memory_snapshot();summary['elapsed']=time.monotonic()-start
        save(root/'summary.json',summary);report_html(root/'report.html',rows,summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--output',required=True);asyncio.run(run(p.parse_args()))
