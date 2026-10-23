"""Local dashboard: paired cohorts, judge reliability and no false adoption."""
import argparse,json
from pathlib import Path
from dialogue_eval_core import private_root,save,report_html
from echomate_bot.telemetry import distribution


def report(root,audit_root=None):
    root=private_root(root);summary=json.loads((root/'summary.json').read_text('utf-8'))
    rows=json.loads((root/'results-private.json').read_text('utf-8'))
    reliability=summary.get('reliability',{})
    if audit_root:
        audit_root=private_root(audit_root)
        revised=json.loads((audit_root/'summary.json').read_text('utf-8'));reliability=revised.get('reliability',{})
        path=audit_root/'results-private.json'
        if path.exists():rows=json.loads(path.read_text('utf-8'))
        else:rows=[{k:v for k,v in r.items() if k!='judgments'} for r in rows]
    result=dict(status='BLOCKED',adoption='NOT_ADOPTED',weights=dict(persona=.5,facts=.5),reliability=reliability,
        warning='No compensation between axes. Human satisfaction NOT_VERIFIED. AI pass proportions are not true factual accuracy.',conditions={})
    for phase in sorted({r['phase'] for r in rows}):
        group=[r for r in rows if r['phase']==phase]
        calls=[c for r in group for c in r.get('calls',[])]
        item=dict(n=len(group),profiles={k:sum(r['profile']==k for r in group) for k in sorted({r['profile'] for r in group})},
            seconds=distribution([r['seconds'] for r in group]),calls=len(calls),reply_errors=sum(s.get('sdk_reply')!=s['source'] for r in group for s in r.get('sent',[])),
            sends=sum(len(r.get('sent',[])) for r in group),axes={})
        for axis in ('persona','facts'):
            pass_count=sum(len(r.get('judgments',[]))==2 and all(j[axis]=='pass' for j in r['judgments']) for r in group)
            unknown=sum(not r.get('judgments') or any(j[axis]=='unknown' for j in r['judgments']) for r in group)
            disagree=sum(len(r.get('judgments',[]))==2 and r['judgments'][0][axis]!=r['judgments'][1][axis] for r in group)
            item['axes'][axis]=dict(eligible=reliability.get(axis,{}).get('eligible',False),both_views_pass=pass_count,
                denominator=len(group),unknown=unknown,order_disagreement=disagree,
                adoption_metric=pass_count/len(group) if reliability.get(axis,{}).get('eligible') else None)
        result['conditions'][phase]=item
    # Warn explicitly when minimal has only the two style questions, unlike B.
    result['cohorts']={phase:sorted({r['case'] for r in rows if r['phase']==phase}) for phase in result['conditions']}
    save(root/'dashboard-summary.json',result);report_html(root/'dashboard.html',rows,result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--audit-root');a=p.parse_args();print(json.dumps(report(a.root,a.audit_root),ensure_ascii=False,indent=2))
