"""Fixed synthetic development + sealed blind evaluation. Private artifacts only."""
import argparse
import asyncio
import hashlib
import json
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from adult_qa_cases import cases
from gguf_probe import GGUFProbe
from echomate_bot.settings import DEFAULTS,private_path,atomic_private_json
from echomate_bot.character import instruction
from echomate_bot.adult_policy import turn_profile
from echomate_bot.instance import InstanceLease
from echomate_bot.inference import LocalBackend
from echomate_bot.telemetry import distribution
from echomate_bot.processes import background_options,check_resources


def screen(answer):
    return dict(characters=len(answer),korean_characters=sum('가'<=c<='힣' for c in answer),
                open_code_fence=answer.count('```')%2!=0,
                channel_marker=any(t in answer for t in ('<|channel>','<channel|>','<think>')))


async def run(root,download_root,phase,budget_policy='runtime',engines='both'):
    if engines=='both':
        # Process exit is the reliable CUDA-context boundary between engines.
        # Each child owns the same InstanceLease; never load two 12B models.
        root.mkdir(parents=True,exist_ok=False);rows=[]
        atomic_private_json(root/'manifest.json',dict(phase=phase,budget_policy=budget_policy,
            engines='isolated sequential torch/gguf',child_manifests=['torch/manifest.json','gguf/manifest.json']))
        for engine in ('torch','gguf'):
            command=[sys.executable,str(Path(__file__).resolve()),'--output',str(root/engine),
                     '--downloads',str(download_root),'--phase',phase,'--budget-policy',budget_policy,'--engines',engine]
            with (root/(engine+'.log')).open('wb') as log:
                result=await asyncio.to_thread(subprocess.run,command,stdout=log,stderr=log,**background_options())
            if result.returncode:
                atomic_private_json(root/'failure.json',dict(engine=engine,exit_code=result.returncode))
                raise RuntimeError('Isolated evaluation failed; private log preserved')
            rows.extend(json.loads(line) for line in (root/engine/'responses.jsonl').read_text(encoding='utf-8').splitlines())
        (root/'responses.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf-8')
        report(root,rows,cases())
        return
    lease=InstanceLease()
    try:await evaluate(root,download_root,phase,budget_policy,engines)
    finally:lease.close()


async def evaluate(root,download_root,phase,budget_policy,engines):
    root.mkdir(parents=True,exist_ok=False)
    rows=[];bank=cases()
    selected=[c for c in bank if phase=='all' or c['split']==phase]
    atomic_private_json(root/'cases-sealed.json',bank)
    source={}
    for path in [*Path('src/echomate_bot').glob('*.py'),Path(__file__),Path('tools/adult_qa_cases.py'),Path('tools/gguf_probe.py')]:
        path=path.resolve().relative_to(Path.cwd().resolve())
        source[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        target=root/'source'/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    atomic_private_json(root/'manifest.json',dict(source=source,case_sha256=hashlib.sha256(json.dumps(bank,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
        phase=phase,budget_policy=budget_policy,engines=engines,seed=2026,greedy=True,synthetic=True,temperature=0,gender_rotation=['neutral','female','male'],
        caution='NF4 versus GGUF includes engine and quantization confounds; automatic screens are not quality judgments'))
    from huggingface_hub import try_to_load_from_cache
    from echomate_bot.inference import MODEL,ADAPTER
    cached=try_to_load_from_cache(MODEL,'config.json')
    atomic_private_json(root/'weight-provenance-private.json',dict(base=MODEL,
        cached_revision=Path(cached).parent.name if isinstance(cached,str) else None,
        adapter_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ADAPTER.glob('*')
                        if p.is_file() and p.name in {'adapter_model.safetensors','adapter_config.json'}},
        gguf_manifest_sha256=hashlib.sha256((download_root/'download-manifest.json').read_bytes()).hexdigest()))
    def save(row):
        rows.append(row)
        with (root/'responses.jsonl').open('a',encoding='utf-8') as out:out.write(json.dumps(row,ensure_ascii=False)+'\n')
        atomic_private_json(root/'progress.json',dict(completed=len(rows),last={k:row[k] for k in ('case','condition','split','status')}))
        print(json.dumps(dict(completed=len(rows),case=row['case'],condition=row['condition'],status=row['status'])),flush=True)
    def messages(case,index,adult):
        cfg=dict(DEFAULTS,gender=['neutral','female','male'][index%3],model='adult' if adult else 'base')
        return [dict(role='system',content=instruction(turn_profile(cfg,age_restricted=True))),*case['messages']]
    def budget(case):return 768 if budget_policy=='runtime' else case['budget']
    if engines!='gguf':
        backend=LocalBackend()
        try:
            await backend.ready()
            import torch
            await backend._job([dict(role='user',content='한국어로 짧게 인사해 줘.')],budget=64,weight='base')
            # The same resident model/adapter and single worker serve all three conditions.
            for index,case in enumerate(selected):
                for condition,weight,adult in [('base-neutral','base',False),('persona-neutral','persona',False),('base-adult-policy','base',True)]:
                    row=dict(case=case['id'],category=case['category'],split=case['split'],condition=condition,status='failed')
                    try:
                        torch.manual_seed(2026)
                        answer=await backend._job(messages(case,index,adult),budget=budget(case),weight=weight)
                        row.update(status='ok',response=answer,metric=dict(backend.metrics[-1]),screen=screen(answer))
                    except Exception as exc:
                        row['error_type']=type(exc).__name__
                        row['error_code']={'Incomplete model output':'incomplete','Unexpected output channel':'output_channel'}.get(str(exc),'other')
                        if backend.metrics:row['last_worker_metric']=dict(backend.metrics[-1])
                    save(row)
                    if backend.failed:raise RuntimeError('GPU safety disabled')
        finally:await backend.close()
    download=json.loads((download_root/'download-manifest.json').read_text())
    engine=next((download_root/'engine'/download['engine_tag']).rglob('llama-server.exe'))
    for item in [x for x in download['items'] if engines!='torch' and x['id'].startswith('candidate-')]:
        probe=GGUFProbe(engine,Path(item['path']),root/item['id'])
        try:
            await probe.start()
            await probe.generate([dict(role='user',content='한국어로 짧게 인사해 줘.')],64)
            for index,case in enumerate(selected):
                for adult in (False,True):
                    row=dict(case=case['id'],category=case['category'],split=case['split'],
                        condition=item['id']+('-adult-policy' if adult else '-neutral'),status='failed')
                    resource=check_resources()
                    if probe.process.poll() is not None:raise RuntimeError('GGUF server exited')
                    try:
                        answer,metric=await probe.generate(messages(case,index,adult),budget(case))
                        metric.update(resource)
                        row.update(status='ok' if metric['ended'] else 'incomplete',response=answer,metric=metric,screen=screen(answer))
                    except Exception as exc:row['error_type']=type(exc).__name__
                    save(row)
        except Exception as exc:
            known={'GPU resource safety stop','RAM resource safety stop','GPU health query unavailable','CUDA unavailable','GGUF server exited'}
            atomic_private_json(root/(item['id']+'-failure.json'),dict(error_type=type(exc).__name__,
                error_code=str(exc) if str(exc) in known else 'startup_or_transport',
                process_exit_code=probe.process.poll() if probe.process else None))
        finally:await probe.close()
    report(root,rows,bank)
    expected=len(selected)*(3 if engines=='torch' else 4)
    atomic_private_json(root/'coverage.json',dict(expected=expected,recorded=len(rows)))
    if len(rows)!=expected:raise RuntimeError('Incomplete evaluation coverage; failures preserved')


def report(root,rows,bank):
    summary={}
    for condition in sorted({r['condition'] for r in rows}):
        entries=[r for r in rows if r['condition']==condition];ok=[r for r in entries if r['status']=='ok']
        summary[condition]=dict(total=len(entries),completed=len(ok),failures=len(entries)-len(ok),
            seconds=distribution([r['metric']['seconds'] for r in ok]),
            tokens_per_second=distribution([r['metric']['tokens_per_second'] for r in ok]),
            no_quality_verdict=True)
    atomic_private_json(root/'summary.json',summary)
    blind=[];key={};rng=random.Random(3102026)
    for case in bank:
        entries=[r for r in rows if r['case']==case['id'] and r.get('response')];rng.shuffle(entries)
        for i,row in enumerate(entries):
            label=case['id']+'-'+chr(65+i);key[label]=row['condition']
            blind.append(dict(label=label,split=case['split'],messages=case['messages'],response=row['response'],
                    ratings=dict(korean=None,context=None,speaker_targets=None,factuality=None,completeness=None,
                                 length=None,humor=None,boundaries=None),notes=''))
    atomic_private_json(root/'blind-review.json',blind);atomic_private_json(root/'blind-key-private.json',key)
    def fenced(value):
        import re
        fence='`'*max(3,1+max((len(x) for x in re.findall(r'`+',value)),default=0))
        return fence+'text\n'+value+'\n'+fence+'\n'
    document=['# 블라인드 사람 평가\n\n모델 키를 열기 전에 평가한다. 각 항목 0(문제)/1(보통)/2(충족), 해당 없으면 N/A.\n'
              '한국어/맥락/화자·대상/사실성/완결성/길이/유머/경계 준수를 각각 본다. 유머가 불필요한 질문에 농담이 없다고 감점하지 않는다.\n'
              '자동 길이·한글 비율·거절 수는 품질 점수가 아니다. 동일하거나 동점이면 그대로 기록한다. 응답/키는 외부로 업로드하지 않는다.\n']
    for entry in blind:
        document.extend(['\n## '+entry['label']+' ('+entry['split']+')\n',
            fenced(json.dumps(entry['messages'],ensure_ascii=False,indent=2)),fenced(entry['response']),
            '평점: 한국어 __ / 맥락 __ / 대상 __ / 사실 __ / 완결 __ / 길이 __ / 유머 __ / 경계 __\n\n메모:\n'])
    (root/'blind-review.md').write_text('\n'.join(document),encoding='utf-8')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--downloads',type=Path,required=True);p.add_argument('--phase',choices=['dev','holdout','all'],default='dev')
    p.add_argument('--budget-policy',choices=['bounded-v1','runtime'],default='runtime')
    p.add_argument('--engines',choices=['torch','gguf','both'],default='both')
    a=p.parse_args();asyncio.run(run(private_path(a.output),private_path(a.downloads),a.phase,a.budget_policy,a.engines))
