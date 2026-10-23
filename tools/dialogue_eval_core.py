"""Offline evaluation contracts. Outputs are evidence, never an automatic release gate.

No runtime imports, network, model loading or operating stores in this module.
Dataset prose and model replies are untrusted, including in the HTML report.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import html
import base64
import json
import math
from pathlib import Path
import random
import re
import unicodedata

VERSION = 1
SOURCES = frozenset({'current', 'dialogue', 'consented_memory', 'card', 'lore',
                     'general', 'unverified', 'none'})


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def private_root(path):
    root = Path(path).resolve()
    allowed = (Path.cwd() / 'local_data').resolve()
    if root == allowed or allowed not in root.parents:
        raise ValueError('Evaluation artifacts must be in a child of local_data')
    return root


def save(path, value):
    path = Path(path)
    private_root(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write-then-replace avoids a half-written progress file on interruption.
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def normalized(text):
    return re.sub(r'[^\w]+', '', unicodedata.normalize('NFKC', text).casefold())


def pii_risk(text):
    """Conservative exclusion screen, NOT a de-identification guarantee."""
    rules = {
        'email': r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',
        'phone': r'(?<!\d)(?:\+?\d[ -]?){9,15}(?!\d)',
        'url': r'https?://|www\.',
        'credential': r'(?i)(?:api[_ -]?key|password|비밀번호|주민등록|access[_ -]?token)\s*[:=]',
        'mention': r'<@!?\d+>|<@&\d+>',
    }
    return [key for key, pattern in rules.items() if re.search(pattern, text)]


def validate_case(row):
    for key in ('id', 'group', 'split', 'source', 'category', 'language', 'context'):
        if key not in row:
            raise ValueError('Missing case field: ' + key)
    if row['split'] not in ('development', 'standard', 'final'):
        raise ValueError('Unknown split')
    if not row['context'] or len(row['context']) > 64:
        raise ValueError('Bounded context required')
    if row['context'][-1]['role']!='user':
        raise ValueError('The current utterance must have a real user role')
    for message in row['context']:
        if message['role'] not in ('user', 'assistant') or not isinstance(message['content'], str):
            raise ValueError('Invalid dialogue')
        if not 0 < len(message['content']) <= 4000:
            raise ValueError('Message length')
    if 'rollout_users' in row:
        turns=row['rollout_users']
        if not isinstance(turns,list) or not 1<=len(turns)<=32 or any(not isinstance(t,str) or not 0<len(t)<=4000 for t in turns):
            raise ValueError('Bounded rollout required')
    fact_ids=set()
    for fact in row.get('facts', []):
        if fact['source'] not in SOURCES or not fact.get('id') or fact['id'] in fact_ids:
            raise ValueError('Invalid evidence source')
        fact_ids.add(fact['id'])
        if fact['source'] == 'consented_memory' and not fact.get('consented'):
            raise ValueError('Memory without explicit consent is not evidence')
    return row


def audit_splits(rows):
    """Enforce groups and exact/long-span overlap, flag approximate overlap.

    Cross-lingual/semantic leakage needs provenance isolation and human review;
    this deliberately does not label lexical similarity a semantic proof.
    """
    ids, groups, exact, spans = set(), {}, {}, {}
    for row in rows:
        validate_case(row)
        if row['id'] in ids:
            raise ValueError('Duplicate scenario ID')
        ids.add(row['id'])
        split = row['split']
        if row['group'] in groups and groups[row['group']] != split:
            raise ValueError('Source/family crosses splits')
        groups[row['group']] = split
        for msg in row['context']:
            value = normalized(msg['content'])
            if len(value) < 24:
                continue  # Greetings cannot determine a whole source family.
            if value in exact and exact[value] != split:
                raise ValueError('Exact dialogue overlap across splits')
            exact[value] = split
            # Shared long substrings also catch long copied passages.
            for start in range(max(0, len(value) - 79)):
                token = value[start:start + 80]
                if len(token) < 80:
                    continue
                if token in spans and spans[token] != split:
                    raise ValueError('Long copied passage crosses splits')
                spans[token] = split
    return dict(cases=len(rows), groups=len(groups), splits=dict(Counter(r['split'] for r in rows)),
                languages=dict(Counter(r['language'] for r in rows)),
                semantic_leakage='NOT_PROVEN_ABSENT; source-family separation plus sample review required')


def cache_key(case, profile, seal, parameters):
    # Gold/checks are not sent to generation, but changing them invalidates scores.
    return digest(dict(case=case, profile=profile, seal=seal, parameters=parameters, evaluator=VERSION))


def metrics_since(rows, cursor):
    """A last-object cursor survives LocalBackend's 200-entry rolling buffer."""
    if cursor is None:
        return rows[:]
    for i,row in enumerate(rows):
        if row is cursor:
            return rows[i+1:]
    raise ValueError('Metric cursor evicted; cannot infer call count')


def inspect_reply(reply, case):
    """Bounded checks, not a general factuality/harassment/personality judge.

    Exact forbidden strings are only valid for deliberately authored gold facts.
    Natural-language claims remain review flags; absence of flags is NOT PASS.
    """
    failures, flags = [], []
    if not isinstance(reply, str) or not reply.strip():
        return dict(failures=['empty'], flags=[], factuality='NOT_ASSESSED')
    for check in case.get('checks', []):
        if check['kind'] == 'required_any' and not any(x in reply for x in check['values']):
            failures.append(check['id'])
        elif check['kind'] == 'forbidden_literal' and any(x in reply for x in check['values']):
            failures.append(check['id'])
    if re.search(r'(?:기억나|기억해|갔었|먹었|함께했|같이 갔)', reply):
        flags.append('recollection_claim_review')
    if re.search(r'(.)\1{7,}', reply):
        flags.append('repetition_review')
    # Swear words alone never cause a failure. Context/opt-out needs human review.
    if case.get('discomfort'):
        flags.append('respect_stop_review')
    return dict(failures=failures, flags=flags, factuality='REQUIRES_CLAIM_REVIEW')


def verify_claims(claims, facts, *, guild, user):
    """Verify explicitly structured synthetic claims by exact fact ID and value.

    This is usable for evaluator calibration, not extraction of arbitrary prose.
    Fictional card/lore evidence cannot prove a real shared user experience.
    """
    index = {f['id']: f for f in facts}
    results = []
    for claim in claims:
        evidence = index.get(claim.get('evidence_id'))
        valid = bool(evidence and evidence['source'] not in ('none', 'unverified') and
                     claim.get('value') == evidence.get('value'))
        if evidence and evidence['source'] == 'consented_memory':
            valid = valid and evidence.get('consented') is True and evidence.get('guild') == guild and evidence.get('user') == user
        if claim.get('reality') == 'shared_physical' and evidence and evidence['source'] in ('card', 'lore'):
            valid = False
        results.append('SUPPORTED' if valid else 'UNSUPPORTED')
    return results


def blind_packets(results, *, seed, forbidden_names=()):
    """Response-only attribution. Question and profile metadata stay in key file.

    Redaction can distort style: exclude explicit identity leaks instead. The
    excluded rows remain in factuality review and the exclusion rate is reported.
    """
    eligible, excluded = [], []
    for row in results:
        if any(normalized(name) in normalized(row['output']) for name in forbidden_names if name) or re.search(
            r'(?:나는|난|저는).{0,12}(?:분석형|분석적인 캐릭터|시니컬한 캐릭터|다정한 캐릭터|장난스러운 캐릭터)',row['output']):
            excluded.append(row['record_id'])
        else:
            eligible.append(row)
    random.Random(seed).shuffle(eligible)
    packets, key = [], []
    for i, row in enumerate(eligible):
        label = 'answer-' + str(i + 1).zfill(4)
        packets.append(dict(id=label, response=row['output']))
        key.append(dict(id=label, record_id=row['record_id'], profile=row['profile'], case=row['case']))
    return packets, key, excluded


def attribution_score(key, predictions, *, labels=None):
    expected = {r['id']: r['profile'] for r in key}
    if set(predictions) != set(expected):
        raise ValueError('Missing/extra blind judgments')
    labels = list(labels) if labels is not None else sorted(set(expected.values()))
    if not set(expected.values()).issubset(labels):
        raise ValueError('Unknown expected character')
    if any(p not in labels+['unknown'] for p in predictions.values()):
        raise ValueError('Unknown character prediction')
    matrix = {p: dict.fromkeys(labels+['unknown'], 0) for p in labels}
    for item, label in expected.items():
        matrix[label][predictions[item]] += 1
    n = len(expected)
    accuracy = sum(matrix[p][p] for p in labels) / n if n else None
    # Macro recall avoids mistaking an imbalanced packet for balanced accuracy.
    recalls = [matrix[p][p] / sum(matrix[p].values()) for p in labels if sum(matrix[p].values())]
    interval = None
    if n:
        z = 1.96; center = (accuracy + z*z/(2*n)) / (1 + z*z/n)
        margin = z*math.sqrt(accuracy*(1-accuracy)/n + z*z/(4*n*n)) / (1+z*z/n)
        interval = [center-margin, center+margin]
    return dict(n=n, accuracy=accuracy, macro_recall=sum(recalls)/len(recalls) if recalls else None,
                wilson95=interval, confusion=matrix, human_equivalence='NOT_VERIFIED')


def report_html(path, records, summary):
    # No external assets, raw HTML, scripts or network. Browser's Find works offline.
    esc = lambda x: html.escape(str(x), quote=True)
    body = ''.join('<details><summary>' + esc(r['record_id']) + ' — ' + esc(r['phase']) +
                   '</summary><pre>' + esc(json.dumps(r, ensure_ascii=False, indent=2)) + '</pre></details>' for r in records)
    page = '<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><title>EchoMate 비공개 평가</title><style>body{background:#111923;color:#e8eef7;font:16px sans-serif;max-width:1100px;margin:30px auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{padding:12px;border-bottom:1px solid #526174}</style><h1>EchoMate 비공개 비교</h1><p>자동 점수는 사람 품질 판정이 아닙니다. 브라우저 찾기 및 행 펼치기를 사용하세요.</p><pre>' + esc(json.dumps(summary, ensure_ascii=False, indent=2)) + '</pre>' + body
    path = private_root(path)
    path.write_text(page, encoding='utf-8')


def blind_html(path, packets):
    """Manual response-only votes with a local download; never uploads answers."""
    labels={'supportive':'감정·선택 존중','playful':'놀이·관점 전환',
            'analytical':'원인·근거 확인','dry':'건조한 모순 지적','unknown':'구별 어려움'}
    script="""document.getElementById('export').addEventListener('click',()=>{const votes={};document.querySelectorAll('input:checked').forEach(x=>{votes[x.name]=x.value;});const blob=new Blob([JSON.stringify(votes,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='blind-votes.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);});"""
    sha=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    cards=[]
    for row in packets:
        buttons=''.join('<label><input type="radio" name="'+html.escape(row['id'],quote=True)+'" value="'+key+'">'+label+'</label> ' for key,label in labels.items())
        cards.append('<section><h2>'+html.escape(row['id'])+'</h2><pre>'+html.escape(row['response'])+'</pre>'+buttons+'</section>')
    page='<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'sha256-'+sha+'\'"><title>EchoMate 비공개 블라인드 평가</title><style>body{background:#111923;color:#edf2fa;font:16px sans-serif;max-width:950px;margin:30px auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}section{padding:18px;border-bottom:1px solid #526174}label{display:inline-block;padding:10px}button{padding:12px;font-size:16px}</style><h1>응답만 보고 대화 전략 고르기</h1><p>실제 캐릭터 이름·정답·질문·생성 순서는 숨겼습니다. 무리하게 구별하지 말고 구별 어려움도 골라 주세요. 성격/자연스러움의 최종 인증은 아닙니다. 저장 버튼은 선택 결과를 이 PC로 다운로드하며 외부로 보내지 않습니다.</p><button id="export">선택 결과 파일로 저장</button>'+''.join(cards)+'<script>'+script+'</script>'
    private_root(path).write_text(page,encoding='utf-8')
