"""Private editorial source queue, never automatically approved SFT targets.

Topical-Chat data is CDLA-Sharing-1.0, not the repository's software license.
Preserve upstream notices and never fetch article URLs embedded in the data.
"""
import argparse
from collections import Counter
import hashlib
import json
import re

from dialogue_eval_core import digest, normalized, pii_risk, private_root, save

REVISION='7c939229cbcf6f55f6977b341a5a2f2fe982d53f'


def mixed_reference_index(sources,*,allow_unspecified_local_research=False):
    """Mix source pointers, retaining rights and family identity per record.

    Explicit permission admits unspecified sources to local editorial research;
    it does not relabel their license, certify privacy, approve raw SFT targets,
    or authorize redistribution. No raw dialogue/card text enters this index.
    """
    result=[];identities=set();families={}
    for source in sources:
        if source['license']=='UNSPECIFIED' and not allow_unspecified_local_research:
            raise ValueError('Explicit unspecified-source local research opt-in required')
        if source['license'] not in ('CDLA-Sharing-1.0','CC-BY-4.0','MIT','UNSPECIFIED'):raise ValueError('Separate restricted-source review required')
        if not re.fullmatch('[a-f0-9]{64}',source['sha256']):raise ValueError('Source content hash required')
        for record in source['records']:
            identity=source['dataset']+':'+str(record['index'])
            if identity in identities:raise ValueError('Duplicate source pointer')
            identities.add(identity);family=source['dataset']+':'+record['family'];bucket=int(digest(family)[:8],16)%10
            split=record.get('split','development' if bucket==8 else 'independent' if bucket==9 else 'train')
            if split not in ('train','development','independent') or family in families and families[family]!=split:raise ValueError('Existing source-family partition must be preserved')
            families[family]=split
            result.append(dict(id=identity,source_family=family,source_sha256=source['sha256'],license=source['license'],revision=source['revision'],
                dimensions=record['dimensions'],split=split,
                local_editorial_research=True,raw_training_approved=False,redistribution_approved=False,privacy_status='NOT_VERIFIED'))
    return result


def select_topical(data,*,maximum=600):
    if type(maximum) is not int or not 1<=maximum<=1000 or not isinstance(data,dict):
        raise ValueError('Bounded source queue required')
    eligible={};excluded=Counter();signatures=set()
    for identity,row in sorted(data.items()):
        turns=row.get('content',[])
        if not 4<=len(turns)<=100 or any(not isinstance(t,dict) or t.get('agent') not in ('agent_1','agent_2') for t in turns):
            excluded['invalid_turns']+=1;continue
        text=[t.get('message') for t in turns]
        if any(not isinstance(t,str) or not 1<=len(t)<=2000 or pii_risk(t) for t in text):
            excluded['privacy_or_length']+=1;continue
        signature=digest([normalized(t) for t in text])
        if signature in signatures:excluded['exact_dialogue']+=1;continue
        signatures.add(signature)
        article=row.get('article_url')
        if not isinstance(article,str):raise ValueError('Explicit article lineage required')
        # Same knowledge article stays in one source family; no URL is opened.
        family=digest(['topical-article',article] if article else ['topical-conversation',identity])
        bucket=int(family[:8],16)%10
        item=dict(id='topical:'+identity,source_family='topical:'+family,
            revision=REVISION,dialogue_sha256=signature,license='CDLA-Sharing-1.0',
            split='development' if bucket==8 else 'independent' if bucket==9 else 'train',
            turns=[dict(role=t['agent'],text=t['message'],sentiment=t.get('sentiment')) for t in turns],
            status='UNREVIEWED_NOT_TRAINING',source_notices=['wiki','wapo'])
        # Deterministically retain one conversation per family before capping.
        if family not in eligible or digest(identity)<digest(eligible[family]['id'][8:]):eligible[family]=item
    selected=sorted(eligible.values(),key=lambda x:digest(x['id']))[:maximum]
    return selected,dict(raw_conversations=len(data),eligible_source_families=len(eligible),
        selected=len(selected),splits=dict(Counter(x['split'] for x in selected)),excluded=dict(excluded),
        training_approved=0,automated_scope='Exact text, article-family separation and PII pattern screen only; not semantic deduplication or privacy certification')


def run(root):
    root=private_root(root)
    if (root/'topical-queue.json').exists():raise FileExistsError('Preserve prior queue')
    manifest=json.loads((root/'acquisition.json').read_text('utf-8'))
    entry=next(x for x in manifest['sources'] if x['file'].endswith('conversations--train.json'))
    raw=(root/entry['file']).read_bytes()
    if entry['revision']!=REVISION or hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Source binding changed')
    if any('CDLA-Sharing-1.0' not in x['license'] for x in manifest['sources']):raise ValueError('Data license evidence required')
    queue,report=select_topical(json.loads(raw))
    report.update(source_sha256=entry['sha256'],revision=REVISION,raw_redistribution=False)
    save(root/'topical-queue.json',queue);save(root/'topical-summary.json',report)
    print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(p.parse_args().root)
