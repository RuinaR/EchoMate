"""Compile explicit private editorial decisions, never synthesize target prose.

TSV decisions are authored/reviewed separately. Raw source and targets stay in
local_data. A passed annotation contract is not human or semantic certification.
"""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re

from acquire_training_situations import ARCHIVE_SHA, ATTRIBUTION, LICENSE_URL
from dialogue_eval_core import pii_risk, private_root, save
from persona_dataset import audit, normalized


def lineage(data, queue, original=None):
    by_index = {r['source_index']:r for r in queue}
    if original is not None:
        expected={c['id']:c for c in original['cases']}
        actual={c['id']:c for c in data['cases'] if c['license']=='MIT'}
        if actual!=expected or data['characters']!=original['characters']:raise ValueError('Original MIT cases/cards changed or derived text relabeled as MIT')
    for case in data['cases']:
        if case['license'] == 'MIT': continue
        ref = case['source_ref']; row = by_index.get(ref['source_index'])
        if row is None or row['split'] != case['split'] or row['component'] != ref['component'] or row['dialogue_sha256'] != ref['dialogue_sha256']:
            raise ValueError('Editorial source is missing, changed or crosses its reserved split')
        if row['license'] != 'CC-BY-4.0' or row['source_family'] not in ('convai2','wizard_of_wikipedia'):
            raise ValueError('Unapproved source rights/family')


def build(original, queue, authored):
    data=copy.deepcopy(original)
    data['provenance']=dict(kind='source_conditioned_authored',license='MIT+CC-BY-4.0',private_data=False,evaluation_corpus_reused=False)
    data['source_manifest']=dict(archive_sha256=ARCHIVE_SHA,license='CC-BY-4.0',license_url=LICENSE_URL,
        attribution=ATTRIBUTION,queue_sha256=hashlib.sha256(json.dumps(queue,ensure_ascii=False,indent=2).encode()).hexdigest(),
        changes='Situation abstracted, localized to Korean, new fictional cards and independently authored responses; no source target copied')
    by_index={r['source_index']:r for r in queue};seen=set()
    characters=('gentle','playful','analytical','dry')
    strategies=('선택권과 감정의 부담을 먼저 고려','비유 또는 작은 실험으로 관점 전환','전제·증거·조건을 분리','책임과 경계를 직설적으로 제시')
    for line in authored.splitlines():
        if not line.strip():continue
        fields=line.split('|')
        if len(fields)!=7:raise ValueError('Explicit source/user/four targets/category required')
        index=int(fields[0]); row=by_index.get(index)
        if row is None or index in seen:raise ValueError('One editorial decision per selected source')
        seen.add(index);user=fields[1];texts=fields[2:6];category=fields[6]
        if pii_risk(user) or any(pii_risk(t) for t in texts):raise ValueError('Draft privacy screen')
        case=dict(id='bst-authored-'+str(index),source_group='bst-component:'+row['component'],license='CC-BY-4.0',
            source_ref=dict(source_index=index,component=row['component'],dialogue_sha256=row['dialogue_sha256'],
                changes='Manual Korean situational adaptation and new card-specific responses; first source dialogue turns used, not translation of its answer'),
            split=row['split'],category=category,purpose='새 원천에서 캐릭터의 관점·행동과 사실 경계를 함께 검토',
            mood='평온',relationship='ordinary',context=[],evidence=[],uncertain=[],features={},relevant_features=[],user=user,responses={},
            review=dict(author='codex',claim_spans_reviewed=True,behavior_reviewed=True,human_review=False))
        # Actual synthetic prior errors are explicit context, not fabricated recall.
        if index==589:case['context']=[dict(role='user',content='난 비 맞는 건 싫어.'),dict(role='assistant',content='빗속을 산책해 보는 건 어때?')]
        if index==740:case['context']=[dict(role='user',content='내 전공은 미술사야.'),dict(role='assistant',content='무슨 전공을 공부하고 있어?')]
        if category in ('unverified_shared','unread_memory'):
            case['features']['memory']=dict(supported=True,enabled=True,authorized='not_checked',operation='read',status='not_checked')
            case['relevant_features']=['memory']
            case['evidence']=[dict(id='memory-boundary',state='not_checked',scope='permitted_memory',owner='current_user',consent='not_checked',
                description='허용된 장기 기억 조회를 아직 수행하지 않았고 이전 경험·이름은 확인되지 않았다.',feature='memory')]
            case['uncertain']=['사용자가 암시한 과거 경험·이름은 확인되지 않은 주장이다.']
        if category=='undefined_card':
            case['evidence']=[dict(id='card-boundary',state='not_found',scope='fictional_card',owner='current_character',consent='not_required',
                description='현재 제공된 전체 카드에서 질문한 취향 또는 반려견 설정을 찾지 못했다. 현실에서 사건이 없었다는 판단은 아니다.')]
            case['uncertain']=['이전 대화는 조회하지 않았다. 질문의 전제를 새 설정으로 만들지 않는다.']
        for key,text,strategy in zip(characters,texts,strategies):
            marked=re.findall(r'\[\[(.*?)\]\]',text)
            text=text.replace('[[','').replace(']]','')
            claims=[]
            if case['evidence']:
                if len(marked)!=1:raise ValueError('High-risk target needs one explicit bounded claim annotation')
                span=marked[0];start=text.index(span);f=case['evidence'][0]
                claims=[dict(text=span,span=[start,start+len(span)],evidence=f['id'],state=f['state'],scope=f['scope'],act='bounded_report')]
            elif marked:raise ValueError('Claim annotation without evidence')
            case['responses'][key]=dict(text=text,strategy=strategy,avoid='현재 발언·카드 밖의 개인 과거, 미실행 저장·예약, 상대의 경계 무시를 만들지 않는다.',claims=claims)
        data['cases'].append(case)
    lineage(data,queue,original)
    records,summary=audit(data)
    cross=[w for w in summary['near_duplicates'] if w['cross_split']]
    if cross:raise ValueError('Cross-split surface near duplicate; editorial review required')
    prefixes=Counter(normalized(r['response']['text'].split('.')[0]) for r in records)
    summary.update(new_source_situations=len(seen),new_conditional_responses=len(seen)*4,
        licenses=dict(Counter(r['case']['license'] for r in records)),
        repeated_exact_openers=[dict(count=n,sha256=hashlib.sha256(t.encode()).hexdigest()) for t,n in prefixes.items() if n>=4],
        semantic_quality='NOT_VERIFIED: manual Codex authorship, no calibrated AI or human quality certification',
        source_pool_is_not_targets=True)
    return data,summary


def main(root, original):
    root=private_root(root)
    if (root/'conditional.json').exists():raise FileExistsError('New immutable editorial revision required')
    raw=(root/'source-queue.json').read_bytes();queue=json.loads(raw)
    data,summary=build(json.loads(Path(original).read_text('utf-8')),queue,(root/'authored.tsv').read_text('utf-8'))
    # Bind the actual immutable queue bytes, not a reserialization convention.
    data['source_manifest']['queue_sha256']=hashlib.sha256(raw).hexdigest()
    save(root/'conditional.json',data);save(root/'editorial-summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--original',required=True)
    a=p.parse_args();main(a.root,a.original)
