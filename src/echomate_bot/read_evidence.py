"""Request-local read evidence. A model sentence cannot create this record."""
from dataclasses import dataclass,replace
from enum import Enum
import re

from .operation_receipts import ReadReceipt,read_receipt


class ReadState(str,Enum):
    NOT_REQUESTED='NOT_REQUESTED'
    NOT_EXECUTED='NOT_EXECUTED'
    NOT_AUTHORIZED='NOT_AUTHORIZED'
    PENDING='PENDING'
    SUCCESS_EMPTY='SUCCESS_EMPTY'
    SUCCESS_WITH_ITEMS='SUCCESS_WITH_ITEMS'
    FAILED='FAILED'
    CANCELLED='CANCELLED'
    STALE='STALE'


@dataclass(frozen=True)
class ReadEvidence:
    family:str
    state:ReadState=ReadState.NOT_REQUESTED
    receipt:object=None

    def checked(self,store):
        if self.state in (ReadState.SUCCESS_EMPTY,ReadState.SUCCESS_WITH_ITEMS):
            if self.receipt is None or not self.receipt.current(store):
                return replace(self,state=ReadState.STALE)
        return self

    def public(self):
        return dict(version=1,family=self.family,state=self.state.value,
                    count=len(self.receipt.values) if self.receipt is not None and self.state in
                    (ReadState.SUCCESS_EMPTY,ReadState.SUCCESS_WITH_ITEMS) else None)


def memory_evidence(state,selection):
    code={'not_requested':ReadState.NOT_REQUESTED,'not_authorized':ReadState.NOT_AUTHORIZED,
          'failed':ReadState.FAILED,'empty':ReadState.SUCCESS_EMPTY,'found':ReadState.SUCCESS_WITH_ITEMS,
          'invalidated':ReadState.STALE}[state]
    return ReadEvidence('memory',code,selection)


def receipt_reads(receipts):
    return {r.kind:ReadEvidence(r.kind,ReadState.SUCCESS_WITH_ITEMS if r.values else ReadState.SUCCESS_EMPTY,r)
            for r in receipts if isinstance(r,ReadReceipt)}


def apply_read_outcomes(reads,outcomes):
    values=dict(reads)
    for item in outcomes:
        family=item['operation'].removesuffix('_read')
        if family in values and item['operation'].endswith('_read'):
            state=ReadState(item['state']);previous=values[family]
            values[family]=replace(previous,state=state,receipt=previous.receipt if state.value.startswith('SUCCESS') else None)
    return values


def read_question(text):
    """Bounded current self-read/status queries; quotes/reports stay prose.

    Return (family, mode). No audience, consent or write permission is granted.
    """
    from .routing import prose
    value=re.sub(r'^<@!?\d+>\s*','',prose(text).strip()).rstrip('?!。.! ')
    if not value or len(value)>240:return None
    if re.fullmatch(r'(?:지난번|아까|전에)(?:에)?\s*(?:네가\s*)?확인했다고\s*(?:했잖아|말했잖아)',value):return (None,'history')
    if re.search(r'["“”`]|친구|다면|라면|만약|가정|소설|다더라',value):return None
    if re.fullmatch(r'내가\s*(?:전에|지난번에?)\s*(?:무슨|어떤)\s*[^?!。\n]{1,35}(?:한다고\s*했어|말했어)',value):return ('memory','read')
    if re.search(r'라고|다고',value):return None
    own=r'(?:내|나의)\s*'
    reminder=r'(?:알림|예약)(?:\s*목록)?'
    if re.fullmatch(own+reminder+r'(?:을|를)?\s*(?:확인|조회)(?:했어|했니|한\s*거야)',value):return ('reminders','status')
    if re.fullmatch(r'(?:내가\s*(?:등록|예약)한\s*알림|'+own+reminder+r')(?:은|이|에)?\s*(?:뭐(?:야|가\s*있어)|어떤\s*게\s*있어)',value):return ('reminders','read')
    if re.fullmatch(r'알림이?\s*없다는\s*거야[, ]*조회가?\s*안\s*된\s*거야',value):return ('reminders','read')
    if re.fullmatch(own+r'기억(?:을|은)?\s*(?:아직\s*)?조회(?:하지\s*않았지|하지\s*않았어|했어|했니)',value):return ('memory','status')
    return None


def describe_read(record):
    label='기억' if record.family=='memory' else '알림 목록'
    meaning={ReadState.NOT_REQUESTED:'이번 응답에서 조회하지 않았어. 항목이 없다고 확인한 것은 아니야.',
             ReadState.NOT_EXECUTED:'요청은 확인했지만 조회를 실행하지 않았어.',
             ReadState.NOT_AUTHORIZED:'조회할 동의·권한이 없어 확인하지 않았어.',
             ReadState.PENDING:'조회 중이라 아직 결과를 확인할 수 없어.',
             ReadState.SUCCESS_EMPTY:'조회는 성공했고 이번 허용 범위의 결과가 비어 있어.',
             ReadState.SUCCESS_WITH_ITEMS:'조회한 허용 범위에서 항목을 찾았어.',
             ReadState.FAILED:'조회에 실패했어. 목록이 비었다는 뜻은 아니야.',
             ReadState.CANCELLED:'조회가 취소되어 결과를 확인할 수 없어.',
             ReadState.STALE:'조회 뒤 근거가 바뀌어 현재 결과를 사용할 수 없어.'}[record.state]
    return label+': '+meaning


def execute_read(store,event,family,cfg):
    """Use the existing self-list access and freshness contract, without writes."""
    if family not in ('memory','reminders'):raise ValueError('Unsupported read family')
    if family=='reminders' and not cfg.get('reminders_enabled',True):
        return ReadEvidence(family,ReadState.NOT_EXECUTED)
    consent=store.subject_snapshot(event.guild,event.author) if family=='memory' else None
    rows=(store.memories(event.guild,event.author,event.channel)[:3] if family=='memory' else
          [r for r in store.reminders(event.guild,event.author,active=True) if r['channel']==str(event.channel)][:10])
    receipt=read_receipt(family,event,rows,consent,character_id=getattr(store,'character_id',None))
    return ReadEvidence(family,ReadState.SUCCESS_WITH_ITEMS if rows else ReadState.SUCCESS_EMPTY,receipt).checked(store)


def read_answer(record):
    answer=describe_read(record)
    if record.state==ReadState.SUCCESS_WITH_ITEMS:
        rows=[dict(row) for row in record.receipt.values]
        answer+='\n'+'\n'.join(row['summary'] if record.family=='memory' else
                               row['reminder_id'][:8]+' · '+row['text'][:70] for row in rows)
    return answer


def unverified_read_reference():
    return '이전 모델이 확인했다고 말한 것만으로 실제 조회가 수행됐다고 인정할 수는 없어. 어떤 기억·알림 조회인지 명확하게 부탁해 줘.'
