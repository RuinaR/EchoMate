"""Explicit historical-memory questions, answered from the actual lookup state.

Bounded input intent grammar, not a generated-claim detector. Suggestions,
quotations, hypotheticals, memory-write requests and ordinary chat stay intact.
Found evidence still uses the existing source-grounded generation path.
"""
import re
from .routing import prose


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
