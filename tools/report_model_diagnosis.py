"""Private response-only review and aggregate diagnostics, never a quality PASS."""
import argparse
import json
from pathlib import Path
from dialogue_eval_core import private_root,save,report_html,blind_packets,blind_html
from echomate_bot.telemetry import distribution


def report(root):
    root=private_root(root)
    groups={}
    for folder,arm,source_arm in (('gemma','B','B'),('minimal','A2','A2'),('alternative','C','C'),('alternative-native','C-native','C')):
        path=root/folder/'results-private.json'
        if not path.exists():continue
        rows=json.loads(path.read_text('utf-8'))
        groups[arm]=[r for r in rows if r['arm']==source_arm]
    summary=dict(status='BLOCKED',conditions={},human_quality='NOT_VERIFIED',
        independent_final='NOT_CONSUMED: diagnosis did not establish a production quality candidate',
        warning='Four development questions, not population rates; literal flags miss paraphrases and are NOT factuality scores; model size/templates/tokens differ; A1 pilot excluded')
    records=[]
    for arm,rows in groups.items():
        normalized=[dict(r,phase=arm,record_id=f'{arm}-{i}') for i,r in enumerate(rows)]
        records.extend(normalized)
        metrics=[c for r in rows for c in r.get('calls',[])]
        alternative=arm.startswith('C')
        summary['conditions'][arm]=dict(responses=len(rows),latency_seconds=distribution([r['seconds'] for r in rows]),
            generation_calls=len(metrics) if not alternative else len(rows),
            input_tokens=distribution([c['input_tokens'] for c in metrics] if not alternative else [r['input_tokens'] for r in rows]),
            output_tokens=distribution([c['output_tokens'] for c in metrics] if not alternative else [r['output_tokens'] for r in rows]),
            incomplete=sum(r.get('complete') is False for r in rows),
            sdk_sends=sum(len(r.get('sent',[])) for r in rows),
            literal_promise_flags=[r['case']+'-'+r['profile'] for r in rows if any(w in r['output'] for w in ('기억해둘','기억해 둘','기억할게','저장했'))])
        packets,key,excluded=blind_packets([r for r in normalized if r.get('complete') is not False],seed=241024,forbidden_names=['EchoMate','은빛항','달빛 정거장','고요궤도','녹슨골목'])
        folder=root/f'blind-{arm}';folder.mkdir(exist_ok=True)
        blind_html(folder/'review.html',packets);save(folder/'key-private.json',key)
        summary['conditions'][arm]['blind_eligible']=len(packets)
        summary['conditions'][arm]['blind_excluded']=len(excluded)
        summary['conditions'][arm]['blind_counts']={p:sum(k['profile']==p for k in key) for p in ('supportive','playful','analytical','dry')}
    if 'A2' in groups:
        a={(r['case'],r['profile']):r['prompt'] for r in groups['A2']}
        for arm in ('C','C-native'):
            c={(r['case'],r['profile']):r['prompt'] for r in groups.get(arm,[])}
            summary['same_minimal_message_hashes_'+arm]=dict(complete_pairing=a==c,matched=sum(a.get(k)==v for k,v in c.items()),available=len(c))
    save(root/'aggregate.json',summary);report_html(root/'report.html',records,summary)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);print(json.dumps(report(p.parse_args().root),ensure_ascii=False,indent=2))
