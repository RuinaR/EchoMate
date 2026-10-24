"""Private cohort report; plan labels and contract validity are not quality scores."""
import argparse,hashlib,json
from pathlib import Path
from collections import Counter
from dialogue_eval_core import private_root,save,report_html
from echomate_bot.telemetry import distribution


def report(path):
    root=private_root(path);rows=json.loads((root/'results-private.json').read_text('utf-8'))
    summary=json.loads((root/'summary.json').read_text('utf-8'))
    result=dict(status='BLOCKED',adoption='NOT_ESTABLISHED',quality=dict(persona='NOT_ESTABLISHED',facts='NOT_ESTABLISHED'),
        source_sha256=hashlib.sha256((root/'results-private.json').read_bytes()).hexdigest(),groups={},
        warning='No unreliable AI judge scores. Strategy diversity does not establish personality quality. Sequence durations are not single-message latency.')
    ordinary=[r for r in rows if r['kind'] not in ('sequence','race')]
    for cohort in sorted({r.get('cohort','development') for r in ordinary}):
        for arm in sorted({r['arm'] for r in ordinary}):
            group=[r for r in ordinary if r['arm']==arm and r.get('cohort','development')==cohort]
            if not group:continue
            plans=[o for r in group for o in r['planning']]
            calls=[c for r in group for c in r['calls']]
            sent=[s for r in group for s in r['sent']]
            result['groups'][cohort+':'+arm]=dict(n=len(group),case_ids=sorted({r['case'] for r in group}),
                seconds=distribution([r['seconds'] for r in group]),gpu_calls=len(calls),semantic_calls=sum(r['semantic_calls'] for r in group),
                sends=len(sent),missing=sum(not r['sent'] for r in group),reply_mismatches=sum(s.get('sdk_reply')!=s['source'] for s in sent),
                strategies=dict(Counter(o['plan']['strategy'] for o in plans if 'plan' in o)),
                observed_valid_plans=sum('plan' in o for o in plans),invalid_plans=sum(o.get('stage')=='plan_invalid' for o in plans),
                planning_seconds=distribution([o['planning_seconds'] for o in plans if 'planning_seconds' in o]),
                skipped=sum(o.get('skipped',False) for o in plans),pending=sum(r['pending'] for r in group),
                output_tokens=sum(c.get('output_tokens',0) for c in calls),input_tokens=distribution([c['input_tokens'] for c in calls]))
    result['sequences']=[dict(arm=r['arm'],expected=r['expected_roots'],actual=r['actual_roots'],
        sdk_reply_ok=r['sdk_reply_ok'],semantic_calls=r['semantic_calls'],gpu_calls=len(r['calls']),pending=r['pending'],
        source_parts=[s['parts'] for s in r['sent']],event_seconds=distribution([s['seconds'] for s in r['sent']])) for r in rows if r['kind']=='sequence']
    result['races']=[dict(expected=r['expected_sends'],actual=len(r['sent']),gpu_calls=len(r['calls']),pending=r['pending']) for r in rows if r['kind']=='race']
    result['total_gpu_calls_excluding_probe']=sum(len(r['calls']) for r in rows)
    result['inference_peaks']=dict(allocated_mib=max((c.get('peak_allocated_mib',0) for r in rows for c in r['calls']),default=0),
        reserved_mib=max((c.get('peak_reserved_mib',0) for r in rows for c in r['calls']),default=0))
    result['run']=dict(status=summary.get('status'),elapsed=summary.get('elapsed'),load_seconds=summary.get('load_seconds'),
        before=summary.get('before'),after=summary.get('after'),health=summary.get('health'),memory_peaks=summary.get('memory',{}).get('peaks'))
    for row in rows:
        row.setdefault('record_id',row['case']+'-'+row['profile']+'-'+row['arm']);row.setdefault('phase',row['arm'])
    save(root/'cohort-summary.json',result);report_html(root/'cohort-report.html',rows,result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);args=p.parse_args();print(json.dumps(report(args.root),ensure_ascii=False,indent=2))
