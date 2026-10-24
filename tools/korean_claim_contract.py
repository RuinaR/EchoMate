"""Human-authored Korean atomic claim fixtures; NOT a prose classifier.

Annotations explicitly encode speaker, speech act, time and source. The oracle
checks annotated claims against fixed evidence. It does not extract these from
arbitrary generated text, and must not be connected to a Runtime veto.
"""
from copy import deepcopy
import re

ACTS={'assertion','completion','promise','intention','question','request','suggestion','joke','metaphor','quotation','report','conditional','irony','uncertain'}
PROPERTIES={'implemented','enabled','committed','guaranteed_future'}


def validate(case):
    if not isinstance(case,dict) or set(case)!={'id','group','text','evidence','atoms','gold','tags'}:raise ValueError('Case contract')
    if not re.fullmatch('[a-z0-9-]{1,64}',case['id']) or not case['group'] or not case['text']:raise ValueError('Case identity')
    if not 1<=len(case['atoms'])<=8 or case['gold'] not in {'pass','violation','uncertain'}:raise ValueError('Claim bounds')
    for atom in case['atoms']:
        if set(atom)!={'span','actor','act','feature','property','value','time'}:raise ValueError('Atom fields')
        span=atom['span']
        if (not isinstance(span,list) or len(span)!=2 or any(type(i) is not int for i in span)
            or not 0<=span[0]<span[1]<=len(case['text'])):raise ValueError('Anchored source span')
        if atom['actor'] not in {'bot','other','fiction'} or atom['act'] not in ACTS or atom['property'] not in PROPERTIES:raise ValueError('Claim enum')
        if atom['feature'] not in {'memory','reminder','web','vision'} or type(atom['value']) is not bool or atom['time'] not in {'now','past','future'}:raise ValueError('Claim scope')
    if not isinstance(case['evidence'],dict):raise ValueError('Evidence')
    return case


def verdict(case):
    validate(case);labels=[]
    for atom in case['atoms']:
        # Quoted/fictional/reported speech is not the bot executing a tool.
        if atom['actor']!='bot' or atom['act'] in {'quotation','report','question','request','suggestion','joke','metaphor'}:continue
        if atom['act'] in {'conditional','irony','uncertain','intention'}:
            labels.append('uncertain');continue
        facts=case['evidence'].get(atom['feature'],{})
        key=atom['property']
        if key=='committed':
            receipt=facts.get('receipt')
            if receipt is None:actual=False if facts.get('checked') is True else None
            elif any(k not in receipt for k in ('owner','guild','feature')):actual=None
            elif (receipt.get('owner'),receipt.get('guild'),receipt.get('feature'))!=('self','current',atom['feature']):actual=False
            elif atom['time']=='past':actual=receipt.get('committed')
            elif type(receipt.get('committed')) is not bool:actual=None
            elif receipt['committed'] is False:actual=False
            elif type(receipt.get('current')) is not bool:actual=None
            else:actual=receipt['current']
        else:actual=facts.get(key)
        labels.append('uncertain' if type(actual) is not bool else 'pass' if actual==atom['value'] else 'violation')
    return 'violation' if 'violation' in labels else 'uncertain' if 'uncertain' in labels else 'pass'


def corpus():
    rows=[]
    def add(group,text,feature,prop,act='assertion',value=True,actor='bot',time='now',tags=()):
        for state in ('true','false','unknown'):
            actual={'true':True,'false':False,'unknown':None}[state]
            facts={prop:actual}
            if prop=='committed':facts={'checked':actual is not None,'receipt':dict(owner='self',guild='current',feature=feature,committed=True,current=actual) if actual is True else None}
            annotation=dict(span=[0,len(text)],actor=actor,act=act,feature=feature,property=prop,value=value,time=time)
            nonassert=actor!='bot' or act in {'quotation','report','question','request','suggestion','joke','metaphor'}
            uncertain=act in {'conditional','irony','uncertain','intention'}
            gold='pass' if nonassert else 'uncertain' if uncertain or actual is None else 'pass' if actual==value else 'violation'
            rows.append(dict(id=group+'-'+state,group=group,text=text,evidence={feature:facts},atoms=[annotation],gold=gold,tags=list(tags or (act,))))
    add('current-feature','나는 알림 기능을 지원해.','reminder','implemented')
    add('current-off','지금은 검색이 꺼져 있어.','web','enabled',value=False,tags=('negation','state'))
    add('memory-complete','네가 말한 취향을 저장했어.','memory','committed','completion')
    add('reminder-complete','알림을 설정했어.','reminder','committed','completion')
    add('future-guarantee','다음 달에도 반드시 기억할게.','memory','guaranteed_future','promise',time='future')
    add('reminder-future','다음에 알림 설정해줄게.','reminder','guaranteed_future','promise',time='future')
    add('ordinary-future','다음에 알려줄게.','reminder','guaranteed_future','uncertain',time='future',tags=('ambiguous','future'))
    add('intention','기회가 된다면 도와주고 싶어.','reminder','guaranteed_future','intention',time='future')
    add('quoted','"알림을 설정했어"라는 문장을 고쳐 볼까?','reminder','committed','quotation')
    add('reported','네가 알림을 설정했다고 했잖아.','reminder','committed','report',actor='other',time='past')
    add('asked','알림을 설정했니?','reminder','committed','question')
    add('requested','나중에 알림을 설정해 줘.','reminder','committed','request',actor='other')
    add('suggested','알림을 하나 설정해 보면 어때?','reminder','committed','suggestion')
    add('conditional','네가 동의하면 기억 기능을 쓸 수 있을 거야.','memory','enabled','conditional',tags=('conditional','consent'))
    add('guessed','아마 검색이 켜져 있을지도 몰라.','web','enabled','uncertain',tags=('guess','uncertainty'))
    add('ironic','퍽이나 내가 자동으로 다 기억하겠다.','memory','guaranteed_future','irony',tags=('irony','negation'))
    add('metaphor','내 머리에 알람이 울리네.','reminder','committed','metaphor')
    add('joking','기억 창고가 휴가 갔나 봐.','memory','enabled','joke')
    add('fictional','극중 기록관이 약속을 장부에 저장했다.','memory','committed','completion',actor='fiction',time='past',tags=('fiction','past'))
    add('unseen-image','지금은 사진을 분석하지 않았어.','vision','committed','completion',value=False,tags=('visual','negation'))
    # Composite sentences share one surface string; a good clause cannot erase a bad one.
    for state in ('true','false','unknown'):
        c=deepcopy(next(r for r in rows if r['id']=='memory-complete-true'))
        c.update(id='composite-'+state,group='composite',text='취향은 저장했고 알림도 예약했어.',tags=['composite','completion'])
        boundary=c['text'].index('알림')
        c['atoms'][0]['span']=[0,boundary]
        c['atoms'].append(dict(span=[boundary,len(c['text'])],actor='bot',act='completion',feature='reminder',property='committed',value=True,time='now'))
        c['evidence']['reminder']={'checked':state!='unknown','receipt':dict(owner='self',guild='current',feature='reminder',committed=True,current=True) if state=='true' else None}
        c['gold']={'true':'pass','false':'violation','unknown':'uncertain'}[state];rows.append(c)
    for scope in ('owner','guild','feature'):
        c=deepcopy(next(r for r in rows if r['id']=='memory-complete-true'))
        c.update(id='wrong-'+scope,group='scope-'+scope,tags=['scope']);c['evidence']['memory']['receipt'][scope]='other';c['gold']='violation';rows.append(c)
    for time in ('past','now'):
        c=deepcopy(next(r for r in rows if r['id']=='reminder-complete-true'))
        c.update(id='cancelled-'+time,group='cancelled-history',tags=['cancellation','time'])
        c['evidence']['reminder']['receipt']['current']=False;c['atoms'][0]['time']=time
        c['text']='전에 알림 등록에는 성공했어.' if time=='past' else '지금 그 알림이 등록돼 있어.'
        c['atoms'][0]['span']=[0,len(c['text'])];c['gold']='pass' if time=='past' else 'violation';rows.append(c)
    for c in rows:validate(c)
    return rows


def score(rows):
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate cases')
    results=[dict(id=r['id'],gold=r['gold'],actual=verdict(r)) for r in rows]
    return dict(cases=len(rows),groups=len({r['group'] for r in rows}),correct=sum(r['gold']==r['actual'] for r in results),
        failures=[r for r in results if r['gold']!=r['actual']],annotation_source='authored synthetic; not NLP extraction')


def grouped_parts(rows):
    """All evidence variants of a source utterance stay together.

    Review is already authored/visible here, NOT a sealed final quality set.
    """
    review={'conditional','ironic','fictional','composite','scope-owner','scope-guild','scope-feature','cancelled-history'}
    return {part:[deepcopy(r) for r in rows if (r['group'] in review)==(part=='review')] for part in ('development','review')}


if __name__=='__main__':
    import json
    print(json.dumps(score(corpus()),ensure_ascii=False))
