"""Private paired pilot evidence; no model judge or automatic quality approval."""
import argparse
from collections import Counter
import html
import json
import math
from pathlib import Path


def distribution(values):
    values=sorted(float(v) for v in values if v is not None)
    if not values or not all(math.isfinite(v) for v in values):raise ValueError('Finite measurements required')
    def percentile(q):
        index=(len(values)-1)*q;lo=math.floor(index);hi=math.ceil(index)
        return values[lo]+(values[hi]-values[lo])*(index-lo)
    return dict(n=len(values),p50=percentile(.5),p95=percentile(.95),maximum=max(values))


def operation_coverage(source):
    """Count annotated situations, not four responses as four source cases."""
    result={}
    for split in ('train','development','independent'):
        counts=Counter()
        for case in source['cases']:
            if case['split']!=split:continue
            for key in case.get('relevant_features',[]):
                feature=case['features'][key]
                counts[(key,feature['operation'],feature['status'])]+=1
        result[split]=[dict(feature=k[0],operation=k[1],status=k[2],situations=n) for k,n in sorted(counts.items())]
    return result


def comparison_arms(report):
    arms=[('baseline',report['baseline'])]
    if 'previous' in report:arms.append(('previous',report['previous']))
    return arms+[(str(t['lr']),t['generation']) for t in report['trials']]


def summarize(report):
    if report['status']!='PILOT_COMPLETE_REQUIRES_QUALITY_REVIEW':raise ValueError('Completed pilot required; never promote partial runs')
    expected=report['development_generation_ids']
    if len(expected)!=len(set(expected)) or not expected:raise ValueError('Unique frozen comparison IDs required')
    arms=comparison_arms(report)
    if len({a for a,_ in arms})!=len(arms):raise ValueError('Duplicate candidate arm')
    result={}
    for name,rows in arms:
        if [r['id'] for r in rows]!=expected:raise ValueError('Unpaired or reordered comparison')
        result[name]=dict(formats=dict(Counter(r['format_status'] for r in rows)),
            seconds=distribution(r['seconds'] for r in rows),ttft=distribution(r['ttft'] for r in rows),
            output_tokens=distribution(r['output_tokens'] for r in rows))
    return dict(arms=result,curriculum=report.get('curriculum'),baseline_development_loss=report.get('baseline_development_loss'),
        trials=[dict(lr=t['lr'],optimizer_steps=t['optimizer_steps'],development_loss=t['development_loss'],
                     resume_metrics_match=t['resume_metrics_match'],resume_weights_match=t['resume_weights_match'],
                     base_sentinels_versions_unchanged=t['base_sentinels_versions_unchanged']) for t in report['trials']],
        automated_quality='NOT_VERIFIED; paired timing/format and replay are not persona/factuality scores',
        latency_caution='Output lengths and completion rates differ; do not claim throughput or Runtime latency improvement')


def render(report,extra=None):
    summary=summarize(report);esc=lambda value:html.escape(str(value),quote=True)
    summary.update(extra or {})
    arms=comparison_arms(report)
    parts=['<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><title>Private paired pilot</title>',
        '<style>body{font:16px sans-serif;background:#17191e;color:#ddd;margin:2em}table{border-collapse:collapse;width:100%}td,th{border:1px solid #555;padding:12px;vertical-align:top;white-space:pre-wrap}</style>',
        '<h1>Private paired development evidence</h1><p>NOT VERIFIED: persona, factuality and human quality. Raw/incomplete channels are not displayed.</p>',
        '<pre>'+esc(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre><table><tr><th>Scenario / card</th>']
    parts.extend('<th>'+esc(name)+'</th>' for name,_ in arms);parts.append('</tr>')
    for i,identity in enumerate(report['development_generation_ids']):
        parts.append('<tr><td>'+esc(identity)+'</td>')
        for _,rows in arms:
            row=rows[i];text=row['text'] if row['format_status']=='visible' else '['+row['format_status']+']'
            parts.append('<td>'+esc(text)+'</td>')
        parts.append('</tr>')
    parts.append('</table>');return ''.join(parts)


def main(run,output,source=None):
    from dialogue_eval_core import private_root
    root=private_root(run);out=private_root(output)
    if out.exists():raise FileExistsError('Fresh private report required')
    report=json.loads((root/'report.json').read_text('utf-8'));summary=summarize(report);extra={}
    if source:
        import hashlib
        raw=private_root(source).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=report['data_hash']:raise ValueError('Coverage source differs from trained source')
        extra['operation_coverage']=operation_coverage(json.loads(raw));summary.update(extra)
    out.mkdir(parents=True);(out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'comparison.html').write_text(render(report,extra),encoding='utf-8');print(json.dumps(summary))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--output',required=True);p.add_argument('--source');a=p.parse_args();main(a.run,a.output,a.source)
