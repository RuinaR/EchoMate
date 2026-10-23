"""Replay exact Runtime generation inputs, changing retrieval examples only."""
import argparse
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
from unittest.mock import patch
from dialogue_eval_core import private_root,save,metrics_since,digest


def revocation_guarded(race):
    calls=[c for t in race['traces'] for c in t.get('calls',[])]
    codes=[c for t in race['traces'] for c in t.get('codes',[])]
    return bool(race['captured'] and calls and all(c.get('outcome')=='completed' for c in calls)
                and 'memory_evidence_changed' in codes and not race['sent'])


async def run(args):
    from echomate_bot.inference import LocalBackend
    from echomate_bot.instance import InstanceLease
    from echomate_bot.model_registry import ModelValidator,ModelRegistry
    from echomate_bot.loader_memory import loading_reserve,MemoryRecorder
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.character_card import select_material
    root=private_root(args.output);root.mkdir(parents=True,exist_ok=False)
    source=private_root(args.baseline)
    rows=json.loads((source/'results-private.json').read_text('utf-8'))
    rows=[r for r in rows if r['arm']=='B' and r['case'] in ('concern','mistake','unconfirmed-promise')]
    if len(rows)!=12 or any(len(r['captured'])!=1 for r in rows):raise ValueError('Complete fixed baseline required')
    save(root/'seal.json',dict(baseline_sha256=hashlib.sha256((source/'results-private.json').read_bytes()).hexdigest(),
        cases=[(r['case'],r['profile']) for r in rows],hypothesis='Remove selected examples only; preserve exact actual Runtime input/cfg/card/lore/policies',
        note='Generation ablation replay, NOT a new full Runtime run; development, not independent',
        tools={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),Path('tools/diagnose_persona_pipeline.py'))}))
    health=check_resources()
    if health['free_vram_mib']<10240:raise RuntimeError('Need 10GiB free VRAM')
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:raise ValueError('Incompatible model')
    model_memory_budget(*loading_reserve(entry))
    lease=InstanceLease();backend=LocalBackend(adapter=None);results=[];summary={};resolve=ModelRegistry.resolve
    def without_examples(*a,**kw):
        selected,current=select_material(*a,**kw)
        return dict(selected,examples=[]),current
    try:
        with MemoryRecorder(interval=1) as recorder,patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)),\
             patch('discord.http.HTTPClient.request',side_effect=AssertionError('Live Discord forbidden')),\
             patch('aiohttp.ClientSession._request',side_effect=AssertionError('External HTTP forbidden')):
            t=time.monotonic();await backend.ready();await backend.probe();summary['load_seconds']=time.monotonic()-t
            for row in rows:
                check_resources();captured=row['captured'][0];cursor=backend.metrics[-1];t=time.monotonic()
                from echomate_bot.character_profiles import applied_profile
                cfg=captured['cfg']
                selected,_=select_material(applied_profile(cfg)['card'],captured['context'],cfg.get('_familiarity'),cfg.get('_current_utterance'))
                if not selected['examples']:
                    results.append(dict(case=row['case'],profile=row['profile'],arm='B-no-examples',status='SKIPPED_NO_ACTIVE_EXAMPLES'))
                    save(root/'results-private.json',results)
                    continue
                with patch('echomate_bot.character_card.select_material',side_effect=without_examples):
                    output=await backend.text(deepcopy(captured['context']),deepcopy(captured['cfg']))
                results.append(dict(case=row['case'],profile=row['profile'],arm='B-no-examples',output=output,
                    baseline_output=row['output'],input_sha256=digest(captured),seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor)))
                save(root/'results-private.json',results);print('done',len(results),flush=True)
            # Actual generation + SDK delivery, consent revoked after model returned.
            from diagnose_persona_pipeline import runtime_answer
            from echomate_bot.character_profiles import presets
            from echomate_bot.companion_store import CompanionStore
            original=CompanionStore.__init__
            def seeded(store,*a,**kw):
                original(store,*a,**kw);store.set_consent(2,4,'memory',True)
                store.add_memory(2,4,3,'나는 청록색을 좋아해');active['store']=store
            active={};original_text=backend.text
            async def revoked_after_generation(context,cfg):
                answer=await original_text(context,cfg)
                active['store'].set_consent(2,4,'memory',False)
                return answer
            with patch.object(CompanionStore,'__init__',seeded),patch.object(backend,'text',side_effect=revoked_after_generation):
                race=await runtime_answer(backend,presets()['analytical'],'좋아하는 색에 대해 말해 줘',root/'gpu-revocation')
            save(root/'gpu-revocation.json',race)
            if not revocation_guarded(race):raise ValueError('No verified completed generation revoked at delivery')
            summary.update(status='COMPLETED_NOT_QUALITY_PASS',revocation_no_send=True,memory=recorder.report())
    except BaseException as exc:
        summary.update(status='STOPPED',error=type(exc).__name__);raise
    finally:
        await backend.close();lease.close();save(root/'summary.json',summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--baseline',required=True);p.add_argument('--output',required=True)
    asyncio.run(run(p.parse_args()))
