"""Character-only editors; atomic existing profile application, no user DB."""
from copy import deepcopy
import secrets
from .character_profiles import applied_profile,validate_profile
from .character_card import FIELDS,EDGES
from .ui_controls import choice_field,range_field


def apply(app,original,updated):
    return app.controller.submit('settings',values={'character_profile':updated},expected_profile=original)

def edit_card(app):
    profile=applied_profile(app.snapshot['cfg'])
    labels={'인격·기준':['priorities','relationships','fears','conflict','change','contradictions'],
            '배경·정체성':['age','appearance','background','dislikes'],
            '대화 습관':['humor','questions','closeness','vocabulary','opening']}
    def choose(v):
        if v['part']=='세계관 항목':return entries(app,profile,'lore')
        if v['part']=='예시 대화':return entries(app,profile,'examples')
        keys=labels[v['part']];card=deepcopy(profile['card'])
        def build(values):
            p=deepcopy(profile)
            for k in keys:p['card'][k]=values[k]
            if 'edge' in values:p['card']['edge']={v:k for k,v in EDGES.items()}[values['edge']]
            return validate_profile(p)
        fields=[(k,FIELDS[k],card[k]) for k in keys]
        controls={k:dict(kind='multiline',max_chars=800 if k=='background' else 240) for k in keys}
        if v['part']=='대화 습관':fields.append(('edge','거친 표현 · 기본은 보수적',EDGES[card['edge']]));controls['edge']=choice_field(list(EDGES.values()))
        app.form(v['part'],fields,lambda values:apply(app,profile,build(values)),
                 '가상 설정이에요. 적용 전에는 저장되지 않아요. 실제 사용자 기억·권한과는 달라요. 다른 카드 편집은 이 창을 닫고 다시 열어 주세요.',controls=controls,
                 preview=lambda values:app.character_preview(profile=build(values)))
    app.form('캐릭터 카드 · 배경과 세계관',[('part','편집할 영역',next(iter(labels)))],choose,
             '세계관과 예시는 별도 항목으로 관리해요. 비공개 항목은 모델 입력에서 제외하지만 내보낸 JSON에는 들어 있어요.',
             controls={'part':choice_field([*labels,'세계관 항목','예시 대화'])})


def entries(app,profile,kind):
    rows=deepcopy(profile['card'][kind]);names={r['id']:r for r in rows}
    def choose(v):
        row=None if v['op']=='추가' else names.get(v['item'])
        if v['op']!='추가' and row is None:raise ValueError('항목을 다시 선택해 주세요')
        if v['op']=='삭제':
            if row is None:raise ValueError('삭제할 항목을 선택해 주세요')
            def remove(confirm):
                if confirm['confirm']!='삭제':raise ValueError('삭제라고 입력해 주세요')
                p=deepcopy(profile);p['card'][kind]=[r for r in rows if r['id']!=row['id']];return apply(app,profile,p)
            return app.form('항목 삭제 확인',[('confirm','삭제 라고 입력','')],remove,'현재 적용 프로필의 항목만 지워요. 실제 기억·원본 파일은 지우지 않아요.')
        initial=row or (dict(id='item-'+secrets.token_hex(4),keys=['관련 단어'],priority=50,enabled=True,private=False,match='any',content='') if kind=='lore' else dict(id='example-'+secrets.token_hex(4),keys=['관련 단어'],priority=50,enabled=True,user='',assistant='',relation='any'))
        fields=[('keys','관련 키워드 · 쉼표로 구분',','.join(initial['keys'])),('priority','중요도',initial['priority']),('enabled','사용 여부','사용' if initial['enabled'] else '끄기')]
        controls={'priority':range_field('관련성이 같을 때의 우선순위예요.'),'enabled':choice_field(['사용','끄기'])}
        if kind=='lore':
            fields += [('content','가상 설정 내용',initial['content']),('private','모델에 제공','제외' if initial['private'] else '허용'),('match','키워드 조건','모두' if initial['match']=='all' else '하나 이상')]
            controls.update(content=dict(kind='multiline',max_chars=600),private=choice_field(['허용','제외']),match=choice_field(['하나 이상','모두']))
        else:
            fields += [('user','가상 상대의 발언',initial['user']),('assistant','캐릭터의 예시 답변',initial['assistant']),('relation','관계 조건',{'any':'항상','new':'낯선 상대','familiar':'동의된 친숙함'}[initial['relation']])]
            controls.update(user=dict(kind='multiline',max_chars=240),assistant=dict(kind='multiline',max_chars=400),relation=choice_field(['항상','낯선 상대','동의된 친숙함']))
        def save(values):
            updated=dict(initial,keys=[x.strip() for x in values['keys'].split(',') if x.strip()],priority=int(values['priority']),enabled=values['enabled']=='사용')
            if kind=='lore':updated.update(content=values['content'],private=values['private']=='제외',match='all' if values['match']=='모두' else 'any')
            else:updated.update(user=values['user'],assistant=values['assistant'],relation={'항상':'any','낯선 상대':'new','동의된 친숙함':'familiar'}[values['relation']])
            p=deepcopy(profile);p['card'][kind]=[updated if r['id']==updated['id'] else r for r in rows]+([] if row else [updated]);validate_profile(p)
            return apply(app,profile,p)
        return app.form('세계관 편집' if kind=='lore' else '예시 대화 편집',fields,save,'예시와 설정은 실제 대화 기록이 아니에요. 닫으면 변경을 취소해요.',controls=controls)
    app.form('세계관 항목' if kind=='lore' else '예시 대화',[('op','작업','추가'),('item','항목 ID',next(iter(names),'새 항목'))],choose,
             '추가/수정은 다음 창에서 적용해야 저장돼요. ID는 저장 후에도 유지돼요.',controls={'op':choice_field(['추가','수정','삭제']),'item':choice_field(list(names) or ['새 항목'])})
