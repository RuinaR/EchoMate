"""Editorial pair contracts, not an automatic natural-language quality judge.

Pairs inherit SFT source-family/split and rights. An independent/final case
cannot be converted to preference training by changing a row's split field.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from persona_dataset import audit,messages_for,compiler_hashes,normalized
from prepare_conditioned_sft import supervised_pair
from dialogue_eval_core import pii_risk


def pair_audit(source_raw,pairs):
    source=json.loads(source_raw);records,_=audit(source);lookup={r['id']:r for r in records}
    if pairs.get('schema')!=1 or pairs.get('source_sha256')!=hashlib.sha256(source_raw).hexdigest():raise ValueError('Pair source binding')
    if pairs.get('labeler')!='codex_editorial_not_human' or pairs.get('automatic_judge_approval') is not False:raise ValueError('Explicit limited editorial review')
    seen=set();accepted=[];excluded=0
    for row in pairs['rows']:
        identity=row['id'];record=lookup.get(identity)
        if identity in seen or record is None or record['split'] not in ('train','development'):raise ValueError('Unique training/development source only')
        seen.add(identity)
        if row['source_family']!=record['group'] or row['split']!=record['split']:raise ValueError('Pair cannot relabel source split')
        if type(row['eligible']) is not bool or len(row.get('justification',''))<12:raise ValueError('Explicit pair review required')
        if not row['eligible']:excluded+=1;continue
        reasons=row.get('reasons',[])
        if not reasons or not set(reasons).issubset({'factuality','function_state','speaker_time','current_intent','relationship_boundary','persona'}):raise ValueError('Known preference reasons required')
        text=row['rejected'];chosen=record['response']['text']
        if not 8<=len(text)<=600 or pii_risk(text) or normalized(text)==normalized(chosen):raise ValueError('Distinct bounded response contrast')
        start,end=row['rejected_issue_span']
        if not 0<=start<end<=len(text) or text[start:end]!=row['rejected_issue']:raise ValueError('Rejected issue must quote the actual response')
        if not set(row.get('evidence_ids',[])).issubset({f['id'] for f in record['case']['evidence']}):raise ValueError('Unknown contrast evidence')
        if set(reasons)&{'factuality','function_state','speaker_time'} and not row.get('evidence_ids'):raise ValueError('Factual preference needs evidence annotation')
        accepted.append((record,row))
    return source,accepted,dict(candidates=len(seen),eligible=len(accepted),excluded_ambiguous=excluded,
        splits=dict(Counter(r['split'] for r,_ in accepted)),human_validation='NOT_VERIFIED',
        scope='Source/split/span/reason annotation contracts only, NOT semantic correctness or preference reliability certification')


def export(source,pairs,model,output):
    from transformers import AutoTokenizer
    from dialogue_eval_core import private_root,save
    out=private_root(output)
    if out.exists():raise FileExistsError('Fresh private export only')
    out.mkdir(parents=True)
    raw=Path(source).read_bytes();pair_raw=Path(pairs).read_bytes();data,accepted,summary=pair_audit(raw,json.loads(pair_raw))
    tokenizer=AutoTokenizer.from_pretrained(model,local_files_only=True,trust_remote_code=False)
    exported=[]
    for record,row in accepted:
        messages=messages_for(record,data)
        prompt,chosen,chosen_labels=supervised_pair(tokenizer,messages,record['response']['text'])
        other,rejected,rejected_labels=supervised_pair(tokenizer,messages,row['rejected'])
        if prompt!=other or max(len(chosen),len(rejected))>512:raise ValueError('Same complete bounded prompt; never truncate')
        exported.append(dict(id=record['id'],group=record['group'],split=record['split'],prompt=prompt,
            chosen=dict(input_ids=chosen,labels=chosen_labels),rejected=dict(input_ids=rejected,labels=rejected_labels)))
    summary.update(source_sha256=hashlib.sha256(raw).hexdigest(),pairs_sha256=hashlib.sha256(pair_raw).hexdigest(),
        compiler_hashes=compiler_hashes(),pair_compiler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        tokenizer_hashes={n:hashlib.sha256((Path(model)/n).read_bytes()).hexdigest() for n in ('config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja')},
        lengths={s:sorted(max(len(r['chosen']['input_ids']),len(r['rejected']['input_ids'])) for r in exported if r['split']==s) for s in ('train','development')},loss='Sum of completion causal log probabilities; both prompts masked; no padding/packing/truncation')
    for split in ('train','development'):
        content=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in exported if r['split']==split).encode('utf-8')
        (out/(split+'.jsonl')).write_bytes(content);summary[split+'_sha256']=hashlib.sha256(content).hexdigest()
    save(out/'summary.json',summary);print(json.dumps(summary))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('source','pairs','model','output'):p.add_argument('--'+n,required=True)
    a=p.parse_args();export(a.source,a.pairs,a.model,a.output)
