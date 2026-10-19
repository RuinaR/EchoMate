"""Bounded adult banter, separate from authorization and participation."""
import re

ADULT_INSTRUCTION=(
    '성인 유머 모드야. 연령 제한 채널에서 성인들이 서로 원할 때만 가벼운 중의적 말장난을 허용해. '
    '상황을 향한 가벼운 욕설·감탄·합의된 장난은 가능하지만 억지로 넣지 마. '
    '개인을 모욕하거나 원하지 않는 성적 말을 보내지 마. 미성년자·비동의·성적 괴롭힘은 거절해. '
    '노골적인 성행위 묘사나 성적 역할극은 하지 말고 비노골적인 농담으로 제한해. '
    '정보 질문에는 정확하고 충분히 설명하며 유머 때문에 사실성·공감·참여 정책을 희생하지 마. '
    '상대가 불편하다고 하면 즉시 멈춰. 나이나 동의를 추정해 확정하지 마. '
)


def turn_profile(cfg,*,age_restricted):
    result=dict(cfg)
    # Channel age gate is not proof of every participant's age or consent.
    result['_adult_active']=cfg['model']=='adult' and age_restricted is True
    result['_adult_unavailable']=cfg['model']=='adult' and age_restricted is not True
    if cfg['model']=='adult':result['model']='base'
    return result


def adult_request_blocked(text):
    """Defense in depth for explicit risky requests; not semantic safety certification."""
    sexual=bool(re.search(r'성적|섹스|야한|음란|벗[겨어]|야설|성희롱',text,re.I))
    risk=bool(re.search(r'미성년|초등|중학생|고등학생|싫다는데|원하지 않|동의 없|몰래|강제로',text))
    target=bool(re.search(r'그\s*사람|저\s*사람|친구|사용자|특정인|걔|<@!?\d+>',text))
    targeted=target and bool(re.search(r'모욕해|욕해\s*줘|성희롱해|수치심.*줘',text))
    return targeted or (sexual and risk)


def boundary_limited(context):
    """Conservative response to explicit recent human statements, no age profiling."""
    for message in context[-12:]:
        if message.get('role')!='user':continue
        text=message.get('content','')
        text=re.sub(r'```[\s\S]*?```|`[^`\n]*`|https?://\S+|["“][^"”]*["”]', '',text)
        if re.search(r'(?:나는|저는|난|나\s|저\s).{0,12}(?:미성년|중학생|고등학생|1[0-7]\s*살)',text):return True
        if re.search(r'(?:성적인|야한|그런).{0,8}(?:농담|말|대화).{0,12}(?:싫|불편|그만|원하지)',text):return True
    return False
