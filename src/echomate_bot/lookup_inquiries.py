"""Explicit historical-memory questions, answered from the actual lookup state.

Bounded input intent grammar, not a generated-claim detector. Suggestions,
quotations, hypotheticals, memory-write requests and ordinary chat stay intact.
Found evidence still uses the existing source-grounded generation path.
"""
import re
from .routing import prose


def lookup_state_answer(text,state):
    """An explicit read-only status query; never intercept mixed conversation.

    Only a complete query in this bounded grammar gets a deterministic answer.
    Found results are scoped existence, not unrestricted memory contents.
    """
    from .factual_context import lookup_evidence
    lookup_evidence(state)
    text=re.sub(r'^<@!?\d+>\s*','',prose(text).strip()).rstrip('?!。.! ')
    if not text or len(text)>200:return None
    query=(r'(?:(?:지금|현재|이번)\s*)?(?:저장된\s*)?기억\s*(?:조회|검색)(?:의|한)?\s*'
           r'(?:상태|결과)(?:는|가|를|을|이)?\s*(?:뭐야|어떻게\s*됐어|알려\s*줘|확인해\s*줘|말해\s*줘)')
    if re.fullmatch(query,text):
        return {
            'not_requested':'이번에는 기억을 조회하지 않았어. 기록이 있는지 없는지 확인한 결과가 아니야.',
            'not_authorized':'기억 조회 동의·권한이 없어 조회하지 않았어. 기록 부재나 조회 실패와는 달라.',
            'failed':'기억 조회를 시도했지만 실패했어. 결과는 확인할 수 없고, 기록이 없다는 뜻은 아니야.',
            'empty':'기억 조회는 성공했지만 이번 허용 범위의 결과가 비어 있어. 실제 사건이 없었다는 뜻은 아니야.',
            'found':'이번 허용 범위의 기억 조회에서 항목을 찾았어. 제공된 항목만 확인한 것이고 전체 기억이나 다른 사용자의 기억을 확인한 것은 아니야.',
            'invalidated':'조회 뒤 근거가 바뀌어 현재 결과를 사용할 수 없어. 다시 확인하기 전에는 확정할 수 없어.',
        }[state]
    meaning=(r'(?:기억\s*)?(?:조회|검색)\s*실패(?:가|는)?\s*(?:기록|기억|결과)(?:이|가)?\s*'
             r'(?:없다는|없단|없음을|없음이라는)\s*(?:뜻|말)(?:이야|인가요|이지|맞아)')
    if re.fullmatch(meaning,text):
        return '아니. 조회 실패는 시도했지만 결과를 확인하지 못했다는 뜻이야. 조회 성공 뒤 빈 결과를 받은 것과는 달라.'
    return None


def memory_inquiry_answer(text, state):
    text=prose(text).strip()
    if (not text or len(text)>500 or re.search(r'만약|라면|다면|라고|냐고|다고|가상|상상|소설|역할극|세계관|기억해\s*줘',text)):
        return None
    historical=bool(re.search(r'우리|나랑|나와|내가|지난|전에|예전',text))
    query=bool(re.search(r'(?:기억(?:나|해|하니)|기억(?:은|이)?\s*있(?:니|어)|기록(?:은|이)?\s*있(?:니|어))[?!.\s]*$',text))
    if not historical or not query:return None
    return {
        'not_requested':'이번에는 저장된 기억을 조회하지 않았어. 그래서 그 일을 기억한다고 확인할 수는 없어.',
        'not_authorized':'저장된 기억을 조회할 동의가 없어 확인하지 않았어. 그 일이 없었다는 뜻은 아니야.',
        'failed':'기억 조회에 실패했어. 기록이 없는 것과는 달라. 지금은 그 일을 확인할 수 없어.',
        'empty':'이번에 허용된 범위로 조회했지만 결과가 비어 있어. 실제로 그 일이 없었다고 단정할 수는 없어.',
        'invalidated':'조회한 뒤 근거가 바뀌어 현재는 그 일을 확인할 수 없어.',
    }.get(state)
