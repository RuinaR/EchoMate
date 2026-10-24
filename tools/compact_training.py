"""Separate short conditioning experiment; not the full Runtime curriculum.

Preserves the existing 52/8 curriculum and final evaluation ledger. Original
MIT sources only. Reject over-budget records, never truncate their content.
"""
import json
import hashlib
from pathlib import Path


def compile_records(tokenizer,source):
    from prepare_conditioned_sft import supervised_pair,ids
    raw=Path(source).read_bytes();data=json.loads(raw)
    if data['schema']!=1 or data['source']!=dict(kind='original_synthetic',license='MIT',private_conversations=False,public_evaluation_corpus_reused=False):raise ValueError('Original source required')
    groups=set();responses=set();records=[]
    for case in data['cases']:
        if case['group'] in groups or case['split'] not in ('train','validation'):raise ValueError('Disjoint unique source groups required')
        groups.add(case['group'])
        if set(case['responses'])!=set(data['profiles']):raise ValueError('Balanced characters required')
        for key,profile in data['profiles'].items():
            target=case['responses'][key]
            if target in responses:raise ValueError('Duplicate target')
            responses.add(target)
            messages=[dict(role='system',content=profile+' 근거 없는 기억이나 실행을 꾸미지 마.'),dict(role='user',content=case['user'])]
            prompt,full,labels=supervised_pair(tokenizer,messages,target)
            if len(full)>128:raise ValueError('Whole compact example exceeds sealed 128-token budget: '+case['group']+'/'+key+'/'+str(len(full)))
            records.append(dict(group=case['group'],character=key,split=case['split'],input_ids=full,labels=labels,prompt=prompt,
                source_sha256=hashlib.sha256(raw).hexdigest()))
    if len(records)!=24 or sum(r['split']=='train' for r in records)!=16:raise ValueError('Sealed 16/8 experiment')
    return records


def evaluate(model,records,output=None,on_case=None):
    import time
    import torch
    rows=[];model.eval()
    class FirstToken:
        def __init__(self):self.calls=0;self.first=None
        def put(self,value):
            self.calls+=1
            if self.calls==2:self.first=time.monotonic()
        def end(self):pass
    for record in records:
        ids=torch.tensor([record['prompt']],device='cuda');clock=FirstToken();start=time.monotonic()
        with torch.no_grad():out=model.generate(input_ids=ids,max_new_tokens=96,do_sample=False,use_cache=True,streamer=clock)
        elapsed=time.monotonic()-start
        rows.append(dict(group=record['group'],character=record['character'],cohort=record.get('cohort','compact_development'),output_ids=out[0,len(record['prompt']):].cpu().tolist(),
            seconds=elapsed,ttft=None if clock.first is None else clock.first-start))
        if output:
            with Path(output).open('a',encoding='utf-8') as stream:stream.write(json.dumps(rows[-1])+'\n')
        if on_case:on_case('evaluation_'+str(len(rows)))
    return rows


def load_full_records(directory,source,model_root):
    """Read the previously audited full curriculum; verify byte provenance."""
    root=Path(directory);summary=json.loads((root/'summary.json').read_text('utf-8'))
    if summary.get('status')!='TOKENIZER_MASK_PASS_NOT_TRAINING' or summary.get('source_schema')!=2:raise ValueError('Audited schema2 required')
    if hashlib.sha256(Path(source).read_bytes()).hexdigest()!=summary['source_sha256']:raise ValueError('Source changed')
    data=json.loads(Path(source).read_bytes())
    from conditioned_curriculum import validate
    validate(data)
    expected_records={c['id']+'-'+k:(c['split'],c['source_group']) for c in data['scenarios'] for k in data['characters']}
    if set(summary['tokenizer_artifact_hashes'])!={'config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja'}:raise ValueError('Tokenizer provenance incomplete')
    for name,digest in summary['tokenizer_artifact_hashes'].items():
        if name not in ('config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja') or hashlib.sha256((Path(model_root)/name).read_bytes()).hexdigest()!=digest:raise ValueError('Tokenizer changed')
    records=[];groups={};seen=set()
    for split,expected in (('train',52),('validation',8)):
        raw=(root/(split+'.jsonl')).read_bytes()
        if len(raw)>4*1024**2 or hashlib.sha256(raw).hexdigest()!=summary[split+'_sha256']:raise ValueError('Export changed')
        items=[json.loads(line) for line in raw.splitlines()]
        if len(items)!=expected:raise ValueError('Sealed full curriculum size')
        for r in items:
            if r['id'] in seen or expected_records.get(r['id'])!=(split,r['group']):raise ValueError('Duplicate or wrong source binding')
            seen.add(r['id'])
            ids=r['input_ids'];labels=r['labels'];n=r['prompt_tokens']
            if (r['split']!=split or not 1<n<len(ids)<=1800 or len(labels)!=len(ids) or
                labels[:n]!=[-100]*n or labels[n:]!=ids[n:] or len(ids)-n>48 or
                not all(type(v) is int and v>=0 for v in ids)):raise ValueError('Untruncated supervised-boundary contract')
            group=r['group']
            if group in groups and groups[group]!=split:raise ValueError('Source group split overlap')
            groups[group]=split
            records.append(dict(r,prompt=ids[:n],character=r['id'].rsplit('-',1)[-1],source_sha256=summary['source_sha256']))
    if seen!=set(expected_records):raise ValueError('Missing source examples')
    return records
