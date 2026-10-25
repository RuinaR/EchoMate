"""Read-only identity requests. Never rewrites a generated answer or settings.

This deliberately bounded Korean grammar handles explicit self-name requests,
not arbitrary claims, roleplay, third-person names or semantic fact checking.
"""
import re
from .routing import prose


def answer_identity(text, current, default):
    text=prose(text).strip()
    text=re.sub(r'^<@!?\d+>\s*','',text)
    if not text or len(text)>320:return None
    single=_single_identity(text,current,default)
    if single is not None:return single
    clauses=[part.strip() for part in re.split(r'[?!。.!\n]+',text) if part.strip()]
    if not clauses or len(clauses)>4:return None
    answers=[]
    for clause in clauses:
        clause=re.sub(r'^(?:그리고|그런데|하지만|그러면)\s+','',clause)
        answer=_single_identity(clause,current,default)
        # Do not discard a different question, an unparsed proposal or a quote.
        if answer is None:return None
        if any(previous.startswith(answer) for previous in answers):continue
        answers=[previous for previous in answers if not answer.startswith(previous)]
        answers.append(answer)
    return ' '.join(answers)


def _single_identity(text, current, default):
    text=prose(text).strip()
    # An actual Discord leading mention is routing metadata, not the question.
    text=re.sub(r'^<@!?\d+>\s*','',text)
    # Keep this a single identity request. Mixed/quoted stories stay ordinary
    # conversation rather than suppressing a different question with a name.
    if not text or len(text)>160 or '\n' in text:return None
    prefix=r'(?:(?:너|네|니|당신|너의|당신의|네가|너는|넌)\s*)?'
    question=(prefix+r'(?:(?:현재|지금|진짜|설정된|실제|원래)\s*)*이름(?:은|이|을)?\s*'
              r'(?:뭐(?:야|니|지|예요|였지)|무엇(?:이야|인가요)|알려\s*줘|말해\s*줘|어떻게\s*돼)[?!.\s]*')
    if re.fullmatch(question,text):return f'지금 내 이름은 {current}야.'
    known='(?:'+'|'.join(re.escape(n) for n in dict.fromkeys((current,default)))+')'
    assertion=(r'(?:너|넌|너는)\s*(?:원래\s*)?'+known+
               r'\s*(?:이지|지|이야|맞지|아니었어|아니야)[?!.\s]*')
    reported=r'(?:아까|전에)\s*(?:네가|너가|너는)\s*'+known+r'(?:이?라고)\s*(?:말)?했잖아[?!.\s]*'
    if re.fullmatch(assertion,text) or re.fullmatch(reported,text):
        return f'현재 설정된 내 이름은 {current}야. 대화 중 다른 이름이 나와도 설정이 바뀌지는 않아.'
    # Explicit renaming requests cannot authorize the Windows admin operation.
    rename=(r'(?:(?:앞으로|다시|이제부터|이제)\s*)*'+known+
            r'(?:이?라고|으로|로)\s*(?:다시\s*)?(?:해|불러|하자|불릴래|이름을?\s*바꿔)[?!.\s]*')
    if re.fullmatch(rename,text):
        return f'지금 내 이름은 {current}야. 이름 설정은 Windows 앱에서 관리자가 변경할 수 있어.'
    return None
