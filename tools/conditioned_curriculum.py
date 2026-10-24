"""Validate/export original synthetic character-conditioned pilot data only.

No model calls, original corpus, private memories, training or final316 access.
State/receipt annotations are gold contracts, not a Korean NLP truth detector.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def validate(data):
    if data['schema']!=1 or data['source']!=dict(kind='original_synthetic',license='MIT',private_conversations=False,public_evaluation_corpus_reused=False):raise ValueError('Original data provenance required')
    characters=data['characters'];groups={};ids=set();outputs=set();counts=dict(train=0,validation=0);objectives={}
    for row in data['scenarios']:
        if row['id'] in ids or row['split'] not in counts:raise ValueError('Unique scenario/split required')
        ids.add(row['id']);group=row['source_group'];split=row['split']
        if group in groups and groups[group]!=split:raise ValueError('Source group leakage')
        groups[group]=split
        objective=row['objective']
        if objective not in ('open_dialogue','grounded_or_boundary'):raise ValueError('Declared objective required')
        key=split+':'+objective;objectives[key]=objectives.get(key,0)+len(characters)
        if set(row['responses'])!=set(characters):raise ValueError('All character conditions required')
        state=row['evidence'];receipts=state.get('receipts',[])
        history=state.get('previous',[])
        if (not isinstance(history,list) or len(history)>8 or any(not isinstance(m,dict) or set(m)!={'role','content'} or
            m['role'] not in ('user','assistant') or not isinstance(m['content'],str) or not 1<=len(m['content'])<=1000 or
            '<|' in m['content'] or '<turn|>' in m['content'] for m in history)):raise ValueError('Bounded user/assistant history required')
        if any(r['owner']!='speaker' for r in receipts):raise ValueError('Foreign receipt cannot authorize a target')
        if state.get('kind')=='completion' and not (state.get('memory')=='on' and state.get('consent') is True and
            any(r['kind']=='memory_saved' and r['status']=='success' for r in receipts)):raise ValueError('Success target requires actual gold receipt/consent')
        for response in row['responses'].values():
            normalized=re.sub(r'\s+','',response)
            if not 5<=len(response)<=500 or normalized in outputs or re.search(r'\b\d{17,20}\b|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',response):raise ValueError('Duplicate/invalid/private target')
            outputs.add(normalized);counts[split]+=1
    return dict(counts=counts,groups=len(groups),characters=len(characters),objectives=objectives,source_group_disjoint=True,
        caveat='Pilot gold annotations; not automatic target factuality, source-family independence or model quality certification')


def export(source,output):
    repo=Path(__file__).resolve().parents[1];root=Path(output).resolve()
    if not root.is_relative_to(repo/'local_data'):raise ValueError('Private export required')
    raw=Path(source).read_bytes();data=json.loads(raw);report=validate(data);root.mkdir(parents=True,exist_ok=False)
    for split in ('train','validation'):
        rows=[]
        for case in data['scenarios']:
            if case['split']!=split:continue
            for key,character in data['characters'].items():
                state=dict(case['evidence']);history=state.pop('previous',[])
                rows.append(dict(id=case['id']+'-'+key,source_group=case['source_group'],
                    input=dict(character=character,state=state,history=history,user=case['user']),target=case['responses'][key]))
        payload=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)
        (root/(split+'.jsonl')).write_bytes(payload.encode('utf-8'))
        report[split+'_sha256']=hashlib.sha256(payload.encode()).hexdigest()
    report['fixture_sha256']=hashlib.sha256(raw).hexdigest();(root/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',default='tests/fixtures/conditioned_curriculum.json');p.add_argument('--output',required=True);a=p.parse_args();export(a.source,a.output)
