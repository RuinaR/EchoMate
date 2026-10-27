"""Known action/commitment conflicts, not a semantic equivalence judge.

Ambiguous evidence and recognized predicate contrasts reject the digest. The
caller can select complete original turns instead; this never grants an action.
"""
import re

ACTION=r'(?:등록|저장|조회|검색|실행|예약|참석|선택|확정|결정)'
NEGATIVE=ACTION+r'.{0,10}(?:않|못|실패|취소|아니)|미(?:등록|조회|실행|확정)|(?:안|못)\s*'+ACTION
COMMIT=ACTION+r'.{0,4}(?:완료|성공|했다|했음|해뒀)|(?:하|가|오)기로|확정(?:했|되)|결정(?:했|되)'
TENTATIVE=r'만약|경우|수\s*도|된다면|시간이\s*되면|원하면|싶|희망|제안|하자|부탁|요청|가정'
REPORTED=r'라고|라며|전해|들었|인용|전달|말했|말하'
PREFERENCE_REPORT=r'라고|다고|라\s*했|다며|전했|전해|들었|인용|전달'


def check_fidelity(text,evidence,source):
    # Expand to the source sentence, so quoting only the object cannot hide
    # a negation/condition just outside the model-selected substring.
    spans=[]
    for match in re.finditer(re.escape(evidence),source):
        left=max(source.rfind(c,0,match.start()) for c in '.!?\n')+1
        ends=[source.find(c,match.end()) for c in '.!?\n']
        right=match.end() if evidence[-1] in '.!?\n' else min((n for n in ends if n>=0),default=len(source))
        spans.append(source[left:right].strip())
    if not spans or len(set(spans))!=1:raise ValueError('Ambiguous summary evidence')
    clause=spans[0]
    # Do not strip the reporting frame from a preference paraphrase. No
    # inferred subject is manufactured here; ambiguous cases use raw sources.
    if (re.search(r'좋아|싫|선호|취향',clause) and
        re.search(PREFERENCE_REPORT+r"|[\"“”‘’']",clause) and
        not re.search(PREFERENCE_REPORT,text)):
        raise ValueError('Summary removed reported preference attribution')
    # "하기로 제안했다" describes a proposal, not an executed commitment.
    projected=re.search(r'(?:기로|완료|성공|확정|결정).{0,6}(?:제안|희망|요청|부탁|검토)',text)
    affirmative=bool(re.search(COMMIT,text) and not re.search(NEGATIVE,text) and not projected)
    if affirmative and re.search(NEGATIVE,clause):raise ValueError('Summary reversed explicit action failure/negation')
    if affirmative and re.search(TENTATIVE,clause) and not re.search(COMMIT,clause):
        raise ValueError('Summary promoted a proposal/condition to commitment')
    if affirmative and re.search(REPORTED,clause) and not re.search(REPORTED,text):
        raise ValueError('Summary promoted reported execution to a fact')
    # An explicit negative assertion must not become an unresolved check.
    # Questions/uncertain source clauses are excluded from this narrow guard;
    # it is not a general Korean speech-act or semantic-equivalence classifier.
    open_check=re.search(r'(?:확정|결정|완료|성공).{0,12}(?:인지|여부)',text)
    source_question='?' in source or re.search(r'인지|여부|묻|물었|인가|나요',clause)
    if open_check and not source_question and re.search(NEGATIVE,clause) and not re.search(NEGATIVE,text):
        raise ValueError('Summary changed explicit negation into an open question')
    distinction=bool(re.search(r'다른|다르|구별|구분|뜻.{0,6}아니|의미.{0,6}아니',text))
    if re.search(r'(?:조회|검색).{0,12}(?:실패|못했|불가)',clause) and re.search(r'(?:기록|기억|항목).{0,8}없',text) and not distinction:
        raise ValueError('Lookup failure is not an empty result')
    for earlier,later in (('어제','오늘'),('과거','현재'),('이전 이름','현재 이름')):
        if earlier in clause and later not in clause and later in text:
            raise ValueError('Summary changed temporal scope')
