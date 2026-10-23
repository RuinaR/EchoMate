"""Fast: cached-output checks, imported blind votes, exact claim annotations.

Human/independent reviewers can fill annotations privately without re-running
generation. No network, prompt tuning or identity key is embedded in blind data.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from dialogue_eval_core import attribution_score, inspect_reply, private_root, save, verify_claims


def review(run, *, votes=None, claims=None):
    run=private_root(run)
    records=json.loads((run/'results-private.json').read_text(encoding='utf-8'))
    result=dict(responses=len(records),cases=len({r['case'] for r in records}),
                paths=dict(Counter(r['path'] for r in records)),
                failures=dict(Counter(f for r in records for f in r['checks']['failures'])),
                flags=dict(Counter(f for r in records for f in r['checks']['flags'])),
                factuality='NOT_CERTIFIED; unannotated prose requires claim review',
                persona_naturalness='HUMAN_REVIEW_REQUIRED')
    if votes:
        key=json.loads((run/'blind-key.json').read_text(encoding='utf-8'))
        predictions=json.loads(private_root(votes).read_text(encoding='utf-8'))
        result['blind_score']=attribution_score(key,predictions)
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
    args=parser.parse_args();review(args.run,votes=args.votes,claims=args.claims)
