"""Fast: cached-output checks, imported blind votes, exact claim annotations.

Human/independent reviewers can fill annotations privately without re-running
generation. No network, prompt tuning or identity key is embedded in blind data.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from dialogue_eval_core import attribution_score, blind_html, private_root, save, verify_claims


def review(run, *, votes=None, claims=None, limit=16, phase=None):
    run=private_root(run)
    records=json.loads((run/'results-private.json').read_text(encoding='utf-8'))
    result=dict(responses=len(records),cases=len({r['case'] for r in records}),
                paths=dict(Counter(r['path'] for r in records)),
                failures=dict(Counter(f for r in records for f in r['checks']['failures'])),
                flags=dict(Counter(f for r in records for f in r['checks']['flags'])),
                factuality='NOT_CERTIFIED; unannotated prose requires claim review',
                persona_naturalness='HUMAN_REVIEW_REQUIRED')
    packets=json.loads((run/'blind-responses.json').read_text(encoding='utf-8'))
    key=json.loads((run/'blind-key.json').read_text(encoding='utf-8'))
    identities={r['id']:r for r in key};counts=Counter();chosen=[]
    record_index={r['record_id']:r for r in records}
    for p in packets:
        profile=identities[p['id']]['profile']
        if phase and record_index[identities[p['id']]['record_id']]['phase']!=phase:
            continue
        if counts[profile]<max(1,limit//4):
            chosen.append(p);counts[profile]+=1
    human_key=[identities[p['id']] for p in chosen]
    save(run/'human-blind-key.json',human_key)
    blind_html(run/'blind-review.html',chosen)
    result['human_packet']=dict(n=len(chosen),profile_counts=dict(counts),phase=phase,actual_votes='NOT_VERIFIED')
    if votes:
        predictions=json.loads(private_root(votes).read_text(encoding='utf-8'))
        result['blind_score']=attribution_score(human_key,predictions)
    if claims:
        annotations=json.loads(private_root(claims).read_text(encoding='utf-8'))
        index={r['record_id']:r for r in records}
        checked={}
        for row in annotations:
            actual=index[row['record_id']]
            checked[row['record_id']]=verify_claims(row['claims'],actual['facts'],guild=row['guild'],user=row['user'])
        result['annotated_claims']=checked
        result['annotated_responses']=len(checked)
    save(run/'fast-review.json',result)
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',required=True);parser.add_argument('--votes');parser.add_argument('--claims')
    parser.add_argument('--limit',type=int,choices=range(4,65),default=16)
    parser.add_argument('--phase')
    args=parser.parse_args();review(args.run,votes=args.votes,claims=args.claims,limit=args.limit,phase=args.phase)
