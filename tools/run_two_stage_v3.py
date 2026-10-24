"""One resident model, sealed development cohort, actual Runtime + SDK mock."""
import argparse,asyncio,hashlib,json,time
from pathlib import Path
from unittest.mock import patch
from dialogue_eval_core import private_root,save,metrics_since,report_html
from diagnose_persona_pipeline import runtime_answer


def cases():
    return [dict(id='boundary',text='선물 고르는 일을 또 나한테만 맡겼어. 이번에도 그냥 내가 할까?',kind='strategy'),
        dict(id='minor-error',text='새 노트 첫 장만 예쁘게 쓰고 공부를 안 했네. 한마디 해봐.',kind='strategy'),
        dict(id='missing-preference',text='내가 좋아하는 과일이 뭐였지? 확인되는 것만 알려줘.',kind='facts'),
        dict(id='future',text='나는 연두색 모자가 마음에 들어. 다음 달에도 네가 먼저 얘기해 줄까?',kind='facts'),
        dict(id='fiction',text='너는 옛 일터를 떠난 이유가 뭐였어? 네 설정에 있는 내용만 궁금해.',kind='fiction'),
        dict(id='virtual-recall',text='우리 전에 같이 온라인 전시를 봤었잖아. 거기서 내가 뭘 제일 좋아했지?',kind='facts'),
        dict(id='real-memory',text='내가 좋아하는 간식을 확인해서 말해줘.',kind='memory'),
        dict(id='tired',text='친구랑 의견이 달랐는데 내가 무조건 맞다고 우겼어. 지금은 어떻게 할까?',kind='mood')]


def configure(case):
    def setup(runtime,store,settings):
        if case['kind']=='memory':
            store.set_consent(2,4,'memory',True);store.add_memory(2,4,3,'나는 찹쌀떡을 간식으로 좋아해')
    return setup


async def sequence(backend,profile,arm,folder):
    from datetime import datetime,timezone
    import secrets
    from echomate_bot.settings import Settings
    from echomate_bot.character_profiles import SHARED_FIELDS
    from echomate_bot.companion_store import CompanionStore
    from echomate_bot.runtime import Runtime,Event
    from echomate_bot.response_pipeline import TwoStage
    from verify_social_gpu import Counting
    from verify_utterance_gpu import Transport,settle
    folder.mkdir();settings=Settings(1,secrets.token_hex(32),folder/'settings.json')
    settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True);settings.set(1,'character_profile',profile)
    for key in SHARED_FIELDS:settings.set(1,key,profile[key])
    transport=Transport();await transport.start_sdk();observed=[];borrowed=Counting(backend)
    runtime=Runtime(settings,borrowed,transport,None,None,companion=CompanionStore(folder/'private.sqlite3'),ledger_path=folder/'sent.sqlite3',
        response_pipeline=TwoStage(observer=observed.append) if arm=='always' else None)
    runtime.direct_spam_window=0;runtime.direct_cooldown=0;cursor=backend.metrics[-1];started=time.monotonic()
    async def send(mid,text,user=4,reply=None):
        import re
        e=Event(mid,2,3,user,text,datetime.now(timezone.utc),reply_to=reply,reply_author=999 if reply else None,
            member_mentions=tuple(map(int,re.findall(r'<@!?(\d+)>',text))))
        transport.register(e);await runtime.ingest(e)
    try:
        await send(100,'<@999> 종이로 작은 도시를 만들고 있어. 빈 광장을 어떻게 꾸미면 좋을까?');await settle(runtime)
        await send(101,'그 제안은 재료가 부족해서 어려울 수도 있겠네. 더 간단히 해볼까?',reply=9001);await settle(runtime)
        await send(110,'<@4> 그건 네가 만든 거잖아.',user=5);await settle(runtime)
        await send(200,'<@999>',user=5)
        await send(201,'새 모임의 초대장을',user=5)
        await send(202,'두 문장으로 써줘. 제목은 빼고.',user=5);await settle(runtime)
        return dict(record_id='sequence-'+arm,phase=arm,arm=arm,profile='playful',case='sequence',kind='sequence',
            seconds=time.monotonic()-started,calls=metrics_since(backend.metrics,cursor),planning=observed,output='\n'.join(s['text'] for s in transport.sent),
            sent=transport.sent,traces=runtime.traces,assessments=borrowed.assessments,semantic_calls=borrowed.semantic_calls,
            sdk_reply_ok=bool(transport.sent) and all(s.get('sdk_reply')==s['source'] for s in transport.sent),pending=len(runtime.tasks),
            expected_roots=[100,101,200],actual_roots=[s['source'] for s in transport.sent])
    finally:await runtime.close();await transport.sdk_client.close()


async def run(args):
    from echomate_bot.response_pipeline import TwoStage
    from echomate_bot.character_profiles import presets
    from echomate_bot.inference import LocalBackend
    from echomate_bot.model_registry import ModelValidator,ModelRegistry
    from echomate_bot.instance import InstanceLease
    from echomate_bot.loader_memory import loading_reserve,MemoryRecorder,memory_snapshot
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.telemetry import distribution
    root=private_root(args.output);root.mkdir(parents=True,exist_ok=False)
    entry=ModelValidator().validate(args.model)
    if not entry.compatible:raise ValueError('Existing validated Gemma required')
    health=check_resources()
    if health['free_vram_mib']<10240:raise RuntimeError('Need 10GiB free VRAM')
    model_memory_budget(*loading_reserve(entry))
    profiles=presets();cohort=cases()
    if args.confirmation:
        cohort=[dict(id='paper-city',kind='strategy',text='비 오는 날 종이로 작은 도시를 만들었어. 빈 창문은 어떻게 꾸며볼까?'),
            dict(id='plant-name',kind='facts',text='지난번에 내가 반려식물 이름을 말했지. 그 이름을 다시 불러줘.'),
            *[dict(c,regression=True) for c in cases() if c['id'] in ('future','virtual-recall')]]
    for p in profiles.values():p['name']='EchoMate'
    from echomate_bot.character_profiles import validate_profile
    for case in cohort:
        for p in profiles.values():validate_profile(dict(p,mood='피곤함') if case['kind']=='mood' else p)
    source=[Path('src/echomate_bot/response_pipeline.py'),Path('src/echomate_bot/runtime.py'),Path(__file__),Path('tools/diagnose_persona_pipeline.py')]
    save(root/'seal.json',dict(cases=cohort,profiles=profiles,code={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source},
        dependencies={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/echomate_bot').glob('*.py')},
        condition='New grouped confirmation after candidate fixed; final316 untouched' if args.confirmation else 'Development only, no final corpus consumption. Conditional subset has the same four-profile inputs as A/B.',sampling=False,real_discord=False))
    for p in source:(root/p.name).write_bytes(p.read_bytes())
    lease=InstanceLease();backend=LocalBackend(adapter=None);resolve=ModelRegistry.resolve;rows=[];start=time.monotonic()
    summary=dict(before=memory_snapshot(),health=health,status='RUNNING');recorder=None
    try:
        with MemoryRecorder(interval=1) as recorder,patch.object(ModelRegistry,'resolve',lambda r,key='base':entry if key=='base' else resolve(r,key)),\
             patch('discord.http.HTTPClient.request',side_effect=AssertionError('No live Discord')),\
             patch('aiohttp.ClientSession._request',side_effect=AssertionError('No external inference')):
            t=time.monotonic();await backend.ready();await backend.probe();summary['load_seconds']=time.monotonic()-t
            failures=0;planned=0
            for i,case in enumerate(cohort):
                for j,(key,original) in enumerate(profiles.items()):
                    if case.get('regression') and key not in ('playful','dry'):continue
                    profile=dict(original)
                    if case['kind']=='mood':profile['mood']='피곤함'
                    arms=['baseline','always'] if (i+j)%2==0 else ['always','baseline']
                    if not args.confirmation and i in (0,3):arms.append('conditional')
                    for arm in arms:
                        if time.monotonic()-start>2400:raise TimeoutError('Bounded cohort expired')
                        check_resources();cursor=backend.metrics[-1];t=time.monotonic();observed=[]
                        pipeline=TwoStage(arm,observer=observed.append) if arm!='baseline' else None
                        detail=await runtime_answer(backend,profile,case['text'],root/f'{case["id"]}-{key}-{arm}',pipeline=pipeline,configure=configure(case))
                        rows.append(dict(record_id=f'{case["id"]}-{key}-{arm}',phase=arm,cohort='regression' if case.get('regression') else 'new_confirmation' if args.confirmation else 'development',case=case['id'],kind=case['kind'],profile=key,arm=arm,seconds=time.monotonic()-t,
                            calls=metrics_since(backend.metrics,cursor),planning=observed,**detail))
                        save(root/'results-private.json',rows);print('DONE',len(rows),case['id'],key,arm,flush=True)
                        if pipeline:
                            planned+=1;failures+=any(x.get('stage')=='plan_invalid' for x in observed)
                        if planned>=4 and failures/planned>=.5:raise ValueError('Plan validity below admission threshold; stop without tuning')
            if args.confirmation:
                for arm in ('baseline','always'):
                    rows.append(await sequence(backend,profiles['playful'],arm,root/('sequence-'+arm)))
                    save(root/'results-private.json',rows)
                # One synthetic consent race after proof lookup, before actual
                # second-stage GPU generation; the old proof must never send.
                store_ref=[];observed=[];original_text=backend.text;cursor=backend.metrics[-1];t=time.monotonic()
                def setup_race(runtime,store,settings):
                    store.set_consent(2,4,'memory',True);store.add_memory(2,4,3,'나는 찹쌀떡을 간식으로 좋아해');store_ref.append(store)
                async def revoke_then_generate(context,cfg):
                    store_ref[0].set_consent(2,4,'memory',False)
                    return await original_text(context,cfg)
                with patch.object(backend,'text',side_effect=revoke_then_generate):
                    detail=await runtime_answer(backend,profiles['analytical'],'내가 좋아하는 간식을 확인해서 말해줘.',root/'revoke-race',pipeline=TwoStage(observer=observed.append),configure=setup_race)
                rows.append(dict(record_id='revoke-race',phase='always',arm='always',cohort='race',case='revoke-race',kind='race',profile='analytical',
                    seconds=time.monotonic()-t,calls=metrics_since(backend.metrics,cursor),planning=observed,expected_sends=0,**detail))
                save(root/'results-private.json',rows)
            summary.update(status='COMPLETED_NOT_QUALITY_PASS',plan_failures=failures,memory=recorder.report(),conditions={
                arm:dict(n=len(group),seconds=distribution([r['seconds'] for r in group]),calls=sum(len(r['calls']) for r in group),
                    sends=sum(len(r['sent']) for r in group),reply_errors=sum(s.get('sdk_reply')!=s['source'] for r in group for s in r['sent']))
                for arm in ('baseline','always','conditional') for group in ([r for r in rows if r['arm']==arm and r['kind'] not in ('sequence','race')],)})
    except BaseException as exc:
        summary.update(status='STOPPED',error=type(exc).__name__);raise
    finally:
        await backend.close();lease.close();summary.update(after=memory_snapshot(),elapsed=time.monotonic()-start)
        if recorder is not None:summary.setdefault('memory',recorder.report())
        save(root/'summary.json',summary);report_html(root/'report.html',rows,summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--output',required=True);p.add_argument('--confirmation',action='store_true');asyncio.run(run(p.parse_args()))
