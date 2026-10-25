"""Read-only provenance for generation, never a receipt or a memory writer."""

LOOKUPS={
    'not_requested':(False,None,'unknown'),
    'not_authorized':(False,False,'unknown'),
    'failed':(True,None,'unknown'),
    'empty':(True,True,'empty'),
    'found':(True,True,'provided_items'),
    'invalidated':(True,None,'invalidated'),
}


def lookup_evidence(state):
    if state not in LOOKUPS:raise ValueError('Invalid Runtime memory lookup state')
    attempted,authorized,result=LOOKUPS[state]
    return dict(version=1,state=state,attempted=attempted,authorized=authorized,
                result=result,scope='current_permitted_selection')


SOURCE_CONTRACT=(
    '출처를 구분해 답한다. 사용자 발언은 사용자가 전한 내용이며 너의 현실 참여 증거가 아니다. '
    '이전 assistant 답변·요약·캐릭터의 가상 과거도 실제 사용자 기억이나 실행 영수증이 아니다. '
    '확인된 기억은 제공된 사용자 사실 범위에서만 쓰며 너와의 현실 공동 경험으로 확장하지 않는다. '
    '직접 장소에 가거나 외부 활동에 참여했다는 전제에 동의하거나 기억한다고 회상하지 않는다. '
    '이 대화에서 실제로 나눈 말은 제공된 원문에 따라 회상할 수 있다. '
    '사용자가 겪은 일에는 자연스럽게 반응하고, 명시적 소설·농담·가정은 그 범위에서 이어 간다. '
    '미조회=확인 안 함, 접근 미허용=동의/권한 때문에 조회 안 함, 조회 실패=시도했으나 결과 불명, '
    '빈 성공=이번 허용 범위에서 결과 없음, 항목 발견=제공된 항목만 확인, 근거 변경=현재 사용 불가다. '
    '조회 실패를 빈 결과로 설명하지 않는다. 빈 결과도 현실 사건 부재의 증거는 아니다. '
    '조회 상태는 저장·예약·삭제·동의·이름 변경의 실행 증거가 아니다. 완료 안내는 현재 Runtime 영수증만 따른다. '
    '일반적인 미래 제안·조건·인용은 실제 예약/저장/능동 실행 약속으로 바꾸지 않는다. '
    '정상 잡담에 매번 근거 안내나 거절을 붙이지 않는다. '
)
