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


def evaluate(model,records):
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
        rows.append(dict(group=record['group'],character=record['character'],output_ids=out[0,len(record['prompt']):].cpu().tolist(),
            seconds=elapsed,ttft=None if clock.first is None else clock.first-start))
    return rows
