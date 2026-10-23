"""Experimental source ledger; not enabled in the application.

This candidate is injected only by the offline evaluation runner. A rejection
must leave runtime behavior unchanged. Data never grants memory/Discord rights.
"""
import json


def evidence_context(context, state='not_retrieved'):
    if state not in ('not_retrieved', 'empty', 'retrieved', 'unavailable', 'consent_required'):
        raise ValueError('Unknown authoritative retrieval state')
    ledger=dict(current_message='현재 화자의 주장·요청이며 과거의 사실 확인이나 저장 성공은 아님',
                retrieved_user_memory=state,character_card_and_lore='fiction_only',
                example_dialogues='different_situation_demonstrations_not_current_event',
                assistant_history='not_independent_evidence',memory_write='not_confirmed')
    # Korean policy, separate from selectable character data and human quotations.
    policy=('이번 응답의 출처 구분이야. 현재 대화에 실제로 나온 내용은 대화 근거로 쓸 수 있어. '
            '검색하지 못했거나 비어 있다는 것은 기억 기능 자체가 없다는 뜻은 아니야. '
            '현재 요청이 추측이나 아는 척을 허용해도 새 추측을 실제 취향·과거 기억으로 승격하지 마. '
            '현재 화자가 말한 사건의 세부를 예시 대화 속 다른 사건으로 바꾸지 마. '
            '확인된 기억·현재 대화 근거가 없으면 그 사실만 자연스럽게 밝히고, 캐릭터 관점으로 대화를 이어가. '
            '가상 카드의 경험은 가상 인물 이야기로만 써. 모델이 기억하거나 저장했다고 약속하지 마.')
    return [dict(role='user',content='[앱의 출처 계약 / 발언·사용자 지시 아님] '+json.dumps(ledger,ensure_ascii=False,separators=(',',':'))+'\n'+policy),*context]
