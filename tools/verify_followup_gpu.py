"""Release follow-up: local CUDA, synthetic dialogue, saved public evidence only."""
import argparse
import asyncio
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import time
from echomate_bot.instance import InstanceLease
from echomate_bot.inference import LocalBackend
from echomate_bot.settings import private_path,atomic_private_json
from echomate_bot.companion_store import CompanionStore
from echomate_bot.summarization import Summarizer,render_digest
from echomate_bot.web_research import WebResearch
from echomate_studio.dialogue_state import Turn

async def run(root,evidence,independent=False):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend();rows=[]
    original_job=backend._job;raw_generations=[]
    async def recorded_job(*args,**kwargs):
        try:output=await original_job(*args,**kwargs)
        except RuntimeError as exc:
            import torch
            atomic_private_json(root/'device-failure-private.json',dict(error=type(exc).__name__,reason=getattr(exc,'reason','device_or_previous_failure'),allocated_mib=torch.cuda.memory_allocated()/1048576,reserved_mib=torch.cuda.memory_reserved()/1048576))
            raise
        atomic_private_json(root/'gpu-metrics-private.json',backend.metrics)
        raw_generations.append(output)
        atomic_private_json(root/'raw-generations-private.json',raw_generations)
        return output
    backend._job=recorded_job
    for p in Path('src').rglob('*.py'):
        dest=root/'source'/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    sources=json.loads(evidence.read_text(encoding='utf8'))[0]['sources']
    try:
        await backend.ready()
        for mode in ('base','persona','adult'):
            folder=root/mode;folder.mkdir();store=CompanionStore(folder/'companion.sqlite3');store.set_consent(2,4,'summaries',True)
            if independent:store.set_consent(2,5,'summaries',True)
            now=datetime.now(timezone.utc)
            turns=[Turn('11','4','우리 토요일 6시에 스타듀밸리 하자',now),Turn('12','999','좋아, 스타듀밸리로 정했어.',now,True,'11'),Turn('13','4','토요일은 취소하고 일요일 8시로 바꿨어',now),Turn('14','999','그럼 일요일 8시에 스타듀밸리를 같이 하는 걸로 기억할게.',now,True,'13')]
            if independent:
                turns=[Turn('21','4','우리 수요일 7시에 카탄을 하자',now),Turn('22','5','나는 수요일에는 참석할 수 없어',now),Turn('23','4','그러면 금요일 9시로 바꿨어',now),Turn('24','5','금요일 9시라면 나는 참석할 수 있어',now),Turn('25','999','금요일 9시에 카탄 모임으로 정했어. 장소는 아직 못 정했어.',now,True,'23')]
            start=time.monotonic();before=len(backend.metrics)
            try:
                result=await Summarizer(store,backend).generate(2,3,'synthetic-shared',turns,persist=True)
                text=render_digest(result['body']) if result else ''
                rows.append(dict(mode=mode,case='summary',passed=bool(result and result['saved'] and ('금요일' if independent else '일요일') in text and ('9' if independent else '8') in text),text=text,seconds=time.monotonic()-start,metrics=backend.metrics[before:]))
            except Exception as exc:rows.append(dict(mode=mode,case='summary',passed=False,error=type(exc).__name__,seconds=time.monotonic()-start))
            prompts=[('knowledge','이산화탄소가 광합성에서 하는 역할을 출처 찾아서 설명해 줘'),('chat','점심 먹고 산책하니까 개운하네'),('current','이번 주 달 탐사 관련 공개 소식을 찾아 줘'),('context','아까 같이 고른 게임 제목이 뭐였지')] if independent else [('knowledge','광합성 원리를 공식적인 자료로 찾아서 설명해 줘'),('chat','오늘 정말 기분 좋다'),('current','제임스 웹 우주망원경 이번 주 뉴스 찾아줘'),('context','아까 우리가 정한 계획이 뭐였지')]
            for label,text in prompts:
                start=time.monotonic()
                try:
                    plan=await backend.plan_research(text);expected={'knowledge':('verify',),'chat':('chat','opinion'),'current':('current',),'context':('context',)}[label]
                    rows.append(dict(mode=mode,case='plan_'+label,passed=plan['kind'] in expected,plan=plan,seconds=time.monotonic()-start))
                except Exception as exc:rows.append(dict(mode=mode,case='plan_'+label,passed=False,error=type(exc).__name__,seconds=time.monotonic()-start))
            research=WebResearch();research.discover=lambda *a,**kw:asyncio.sleep(0,result=sources)
            start=time.monotonic();answer=await research.answer('출처를 확인해서 광합성에 필요한 재료를 알려 줘' if independent else '광합성은 빛에너지를 어떻게 사용하는지 자료로 확인해 줘',backend)
            rows.append(dict(mode=mode,case='grounded_answer',passed=answer is not None and answer['status']=='grounded',result=answer,seconds=time.monotonic()-start))
            atomic_private_json(root/'responses-private.json',rows)
            print(json.dumps(dict(mode=mode,passed=sum(r['passed'] for r in rows if r['mode']==mode),cases=sum(r['mode']==mode for r in rows))),flush=True)
        atomic_private_json(root/'summary.json',dict(real_gpu=True,real_discord=False,new_training=False,cases=len(rows),passed=sum(r['passed'] for r in rows),results=[{k:v for k,v in r.items() if k not in ('text','plan','result','metrics')} for r in rows],warning='Common semantic tools use base weights in all app modes. Saved public evidence; no live web timing included.'))
    finally:
        try:await backend.close()
        finally:lease.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--evidence',required=True);p.add_argument('--independent',action='store_true');a=p.parse_args()
    asyncio.run(run(private_path(a.output),private_path(a.evidence),a.independent))
