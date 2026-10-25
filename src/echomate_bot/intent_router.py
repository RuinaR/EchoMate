"""Read-only execution boundary around the existing private-command grammar.

This plan never grants audience, consent or write authority. Unrecognized
conversation remains generation input; ambiguous feature mentions ask for an
explicit request rather than triggering a keyword-selected mutation.
"""
from dataclasses import dataclass
from enum import Enum
import re
from .routing import prose


class IntentMode(str, Enum):
    CHAT='chat'
    REQUEST='request'
    MENTION='mention'
    CLARIFY='clarify'
    PROHIBITED='prohibited'


@dataclass(frozen=True)
class IntentPlan:
    mode: IntentMode
    kind: str|None
    reason: str
    version: int=1


def request_clauses(text):
    """Read-only clause views. Never use these to rewrite a stored payload."""
    clean=prose(text).strip()
    return tuple(p.strip() for p in re.split(r'[?!。\n]+|\.\s+|\s+(?:그리고|근데|그런데)\s+',clean) if p.strip())


def needs_memory_read(text):
    from .lookup_inquiries import memory_inquiry_answer
    return any(memory_inquiry_answer(p,'not_requested') is not None for p in request_clauses(text))


def history_review(text):
    """An event about today is not by itself a request to summarize history.

    A negative result keeps ordinary response generation available. The
    existing semantic history classifier still decides ambiguous candidates.
    """
    current=prose(text)
    explicit=bool(re.search(r'대화.*요약|요약.*대화',current))
    past=bool(re.search(r'아까|지난번|전에|말했던|하던',current))
    request=bool(re.search(r'무슨|어떤|뭐|기억|되짚|정리|요약|이어|계속|알려\s*줘|말해\s*줘',current))
    return explicit or past and request


def readonly_fragments(backend,text,lookup):
    """Only existing known-fact contracts can author a factual response part."""
    answer=getattr(backend,'grounded_reply',None)
    if not callable(answer):return ()
    values=[]
    for clause in request_clauses(text):
        value=answer(clause,lookup)
        if value is not None and value not in values:values.append(value)
    return tuple(values)


def execution_text(text,kind):
    """Select one explicit reminder clause, preserving quoted payload bytes.

    Memories still need the preceding factual statement. Multiple operation
    clauses are kept whole for the existing validation, never partially run.
    """
    if kind!='reminder':return text
    from .companion import request_kind
    pattern=r'"[^"\n]*"|“[^”\n]*”|`[^`\n]*`|(?P<boundary>[?!]\s*|\.\s+|\s+(?:그리고|근데|그런데)\s+)'
    start=0;parts=[]
    for match in re.finditer(pattern,text):
        if match.group('boundary') is None:continue
        parts.append(text[start:match.start()].strip());start=match.end()
    parts.append(text[start:].strip())
    parts=[re.sub(r'^(?:그리고|근데|그런데)\s+','',p) for p in parts]
    candidates=[p for p in parts if request_kind(p) is not None and plan_intent(p,request_kind(p)).mode==IntentMode.REQUEST]
    if len(candidates)==1:return candidates[0]
    return text


def plan_intent(text,kind):
    """Bounded current-speech-act contract, not a general Korean NLP model."""
    if kind is None:return IntentPlan(IntentMode.CHAT,None,'no_private_candidate')
    current=prose(text).strip()
    if re.search(r'(?:예약|등록|저장|생성|실행|기억|삭제|취소|정정|변경)\s*하지\s*(?:마|말)|(?:알림|예약|저장|기억)(?:으로|로)\s*바꾸지\s*(?:마|말)',current):
        return IntentPlan(IntentMode.PROHIBITED,kind,'explicit_prohibition')
    # Inspect the outer ending, not embedded "...라고 알려 줘" payloads.
    ending=current.rstrip('.!?。 ')
    reported=bool(re.search(r'(?:더라|다더라|했대|한대|준다더라|했다고|했다는|달라는|달라고).*(?:들었|이야기|말이|소식|전해)|(?:했대|한대|더라|한다더라|했다더라)$',ending))
    hypothetical=bool(re.search(r'(?:다면|라면|가정|예시|예를|예로).*(?:어떨|이야기|얘기|뿐|좋겠|할까)',ending))
    # A separate outer command can request something despite earlier reporting.
    clauses=[part.strip() for part in re.split(r'[.!?\n]|(?:그리고|그러면|그런데|근데)\s+',current) if part.strip()]
    outer=clauses[-1] if clauses else current
    imperative=r'(?:알려|불러|깨워|보여|기억해|요약해|저장해|삭제해|지워|취소해|변경해|정정해|늦춰|미뤄|잊어)\s*(?:줘|주세요|줄래|줄래요|해줘)|(?:부탁해|부탁할게)'
    separate=outer!=current and bool(re.search(imperative,outer))
    if (reported or hypothetical) and not separate:
        return IntentPlan(IntentMode.MENTION,kind,'reported_or_hypothetical')
    from .companion import request_kind
    kinds={request_kind(part) for part in request_clauses(text)}-{None}
    requests=[part for part in request_clauses(text) if request_kind(part) is not None and re.search(imperative,part)]
    if len(kinds)>1 or len(requests)>1:
        return IntentPlan(IntentMode.CLARIFY,kind,'multiple_private_kinds')
    if kind=='summary':return IntentPlan(IntentMode.REQUEST,kind,'summary_candidate')
    read=bool(re.search(r'(?:기억|정보|알림|예약).*(?:목록|조회|보여|뭐\s*있)',current))
    request=read or bool(re.search(imperative,current))
    # Legacy short controls are explicit commands even without a final 줘.
    request=request or bool(re.search(r'(?:알림|예약).*(?:취소|늦춰|미뤄|연기|변경)',current))
    if request:return IntentPlan(IntentMode.REQUEST,kind,'explicit_private_request')
    # An incomplete request is not permission to invent a time or payload.
    if re.search(r'(?:알려|기억|예약|알림).*(?:줘|부탁|좋겠)',current):
        return IntentPlan(IntentMode.CLARIFY,kind,'incomplete_private_request')
    return IntentPlan(IntentMode.MENTION,kind,'feature_mention_only')


def clarification(plan):
    if plan.mode==IntentMode.PROHIBITED:
        return '실행 금지 표현이 포함되어 이번 변경은 수행하지 않았어. 변경이 필요하면 대상과 요청을 따로 명확히 알려 줘.'
    if plan.reason=='multiple_private_kinds':
        return '서로 다른 기능 요청이 함께 있어 아직 실행하지 않았어. 각 기능의 대상과 내용을 나누어 부탁해 줘.'
    return '아직 실행하지 않았어. 실행을 원하면 대상과 내용을 명확히 부탁해 줘. 알림은 날짜와 시각도 필요해.'
