# 릴리즈 요구사항 추적표

2026-10-25 최신 연구 `1813a17`/929회귀: 선택 원천·혼합참조와 새 SFT/DPO 학습·재개를 검증했으나 공동 품질 미달로 모두미채택. [실측·권리·제약](ADVANCED-CHARACTER-QA.md), [Phase 계획](ADVANCED-CHARACTER-ROADMAP.md). C1/F2/F3/S1은 계속 FAIL, 새 장기상태/5–100턴/adapter Runtime GPU 통합은 NOT VERIFIED, D1은 BLOCKED다.

2026-10-25 최신: 준비 backward의 eval/checkpoint 불일치를 수정하고 전체GPU64/16step 자원 검증을 완료했다. CPU I/O fresh/warm 품질 후보는 모두기각했다. 원래2GiB 여유·운영no-LoRA는 유지한다. [근거](QLORA-ADMISSION-QA.md). 필수 품질·실제Discord·장기/다른Windows 게이트는 그대로 BLOCKED/FAIL/NOT VERIFIED다.

초기2026-10-25 Admission 항목 감사와 tinyNF4 단계 계측은 [신규 QA](QLORA-ADMISSION-QA.md)에 기록했습니다. 당시 실제12B 추가학습/품질A/B는 자원 미달로 BLOCKED였으며 사전 문턱·2GiB 여유·앱기본값을 낮추지 않았습니다.

최신 실제재개: [QLoRA 재개 QA](QLORA-RESUME-QA.md). 전체264/399token/66step·재개·기존2GiB guard를통과했지만 조회/시점/화자오류로어댑터미채택이다. 계산전cache정리는연구용기본OFF이고앱모델은no-LoRA다. 독립56/최종316미소비·기존필수품질/실제Discord/장기/다른Windows게이트를유지한다.

2026-10-25 최신 근거: [공개 원천·조건부 정답 QA](PUBLIC-TRAINING-DATA-QA.md). 후보1,838개를 학습 승인으로 세지 않는다. 학습264/개발56/별도56의 새자료는 토큰·출처 계약만 확인했고 실제12B는14.195GiB 요구/12.937GiB 가용으로 로딩0회다. 새품질/학습/Runtime GPU PASS는 없으며 기존 필수 FAIL/BLOCKED/NOT VERIFIED를 유지한다.

기준 시작 main/local/remote `4587355590330f86c83f561121ac2f0a5db521c9` (2026-10-24). 현재 단계 **DEVELOPMENT / RELEASE BLOCKED**. 필수 FAIL/BLOCKED/NOT VERIFIED가 남으면 RC/PASS로 승격하지 않는다. 아래 PASS는 명시된 범위의 근거이며 제품 전체/다른 PC/실서버 보장이 아니다. 최신 자료v4/12B349token·3LR 미채택/장시간 진행은 [자료·QLoRA QA](DATASET-QLORA-QA.md), 이전 짧은 학습/장시간 안전 중단은 [학습 가능성v2](TRAINING-FEASIBILITY-V2-QA.md), 이전 진단 누수 수정72546e4·학습 사전 검증/소스·운용 근거는 [학습·안정화 QA](TRAINING-STABILITY-QA.md)를 우선한다. 이전 [릴리즈 준비 QA](RELEASE-READINESS-QA.md)는 당시 범위로 보존한다.

상태: PASS=필요 근거 확보, FAIL=재현 결함/기준 미달, BLOCKED=명시된 승인·환경·데이터 제약, NOT VERIFIED=미수행/근거 부족, NOT APPLICABLE=적용 제외 사유 확인. 테스트 개수나 문서 수는 독립적인 완료 기준이 아니다.

| ID / 필수 요구 | 상태 | 검증 방법·현재 근거와 코드 버전 | 남은 완료 조건 |
|---|---|---|---|
| C1 인격의 반응·가치관 구별 | FAIL | 기존3턴/기분·관계 비교와 [신규 Runtime48/공식sampling 기각](RELEASE-READINESS-QA.md), 실행src4587355/도구67f8823 | 새 원천의 열린 대화에서 일관된 반응 차이·사실성 동시 개선 |
| C2 가상 배경·습관 입력 보존 | PASS | dec2787의 카드 단위/실제 GPU 배경0/4→4/4, [범위](STABILITY-DIALOGUE-QA.md); 이후 해당 카드 경로 동일 | 예산 부족의 상세 선택·긴 카드 품질은C1/C4와 별도 |
| C3 기분·관계·여러 턴의 일관성 | NOT VERIFIED | 기분 평온/화남/피곤함·친밀도20/80의 실제 입력·3턴 reply는 [4587355 근거](CONSISTENCY-CLAIMS-QA.md) | 입력 값 전달과 독립적인 기분/관계 효과·장기 일관성 분리 검증 |
| C4 자연스러운 한국어·관점/인칭 | FAIL | 기본/CFG의 관점 혼동·인격 수렴, [실제 출력 검토](CONSISTENCY-CLAIMS-QA.md) | 다양성만 늘리지 않고 인칭·반응·완결성과 자연스러움 유지 |
| F1 실제 기억 근거·변경 최신성 | PASS | 701b947/4587355, 행·빈/상위3개 선택의 temp SQLite/실제 GPU→SDK GET 뒤 삽입1→0 | 새 변경 후 관련/전체 회귀; 장기 운용은L2 별도 |
| F2 공동 경험·취향·가상/현실 분리 | FAIL | [대규모 평가](DIALOGUE-EVALUATION-QA.md), [모델 분리](MODEL-SYSTEM-DIAGNOSIS-QA.md), 간접 허위 주장 잔존 | 새로운 핵심·원천 분리 확인에서 근거 위반0, 과잉 부정/거절 방지 |
| F3 미수행 저장·미래 약속·기능 상태 | FAIL | 이전 실패 보존·[이번 미래 부탁12개](RELEASE-READINESS-QA.md)의 명백 위반greedy2/4·sampling2/4와3/4, 실제 저장/예약0 | 실행 영수증/지원/활성/준비 상태를 정확히 설명, 무근거 약속0 |
| F4 한국어 원자 주장 검증 신뢰성 | FAIL | 기존68사례 oracle≠NLP, 초기27건 계약7/완전 주석 일치0, 규약 모호성 [기록](CONSISTENCY-CLAIMS-QA.md) | 형식/의미/주석 오류 분리·quote/부정/조건/복합 주장 적격성 입증; 미검증 veto 금지 |
| S1 다자 청자·후속·대화 연결 | FAIL | [사회적 통제의 오개입/누락](SOCIAL-ROUTING-QA.md), [최근 명세](MULTI-MESSAGE-UTTERANCES.md) | 원천 분리된 긴 이벤트 시퀀스에서 직접/후속/타인·독립 흐름 검증 |
| S2 원본 reply·분할·중복/편집·삭제 | PASS | 현재929 CPU 회귀와 최근 실제 Runtime→SDK mock의 source/reply/취소 보호 | 기능 통과와S1의 의미 정확도 분리, 실제 Discord는D1 |
| P1 사용자 동의·권한·격리·삭제 | PASS | 현재929 회귀/임시 DB/SDK mock, [실행/조회](OPERATION-EVIDENCE-QA.md)와 [최근 선택](CONSISTENCY-CLAIMS-QA.md) | 실제 Interaction 접근은D1, 운영 DB 무승인 변경 금지 |
| P2 운영 자료·공개 저장소 보호 | PASS | 이번 운영4파일+소비장부5hash 동일·코드diff/명시 staged 내용 감사, [마감](RELEASE-READINESS-QA.md) | 전송 대상 public 경계를 유지; 다른 시점 변경/전체 바이너리 비밀 부재 보장 아님 |
| A1 기억·관계·요약·예약 CRUD/복구 | PASS | 현재929 기능 회귀, [예약 기한](STABILITY-DIALOGUE-QA.md), [동의/DB](LIVE-SERVER-FIXES-QA.md) | 장시간/비정상 중단·실환경은L2/D1과 별도 |
| M1 분할 모델 로딩·단일 Worker | PASS | 같은 호스트의 기존 shard/NF4·no-LoRA 로딩 약13GiB private, [로더](RESUMED-MEMORY-UX-QA.md) | 변경시 자원 admission/실제 준비 재검; 다른 PC 미보장 |
| M2 원본 단일 파일 안전 로딩 | NOT VERIFIED | 운영 base의 선택은 자동 변경하지 않음, [모델 레지스트리](MODEL-REGISTRY.md) | 원본에 shard 측정 재사용 금지; 자원 여유가 허용할 때 별도 검증 |
| M3 취소·전환·종료·실패 복구 | PASS | 현재929 기능 회귀/기존 실제 모델 해제 기록 | 경쟁/장시간은L2, 실제 다른 환경은W2 |
| L1 지연·TTFT·큐·메모리 SLO | NOT VERIFIED | 이번같은8입력/조건 측정·전체TTFT/queue0, [GPU 표](RELEASE-READINESS-QA.md); 출력 길이/seed 효과 구분 | 이번2문장 workload8개/조건의 관측 p50/p95는10/20초 이내; 포화 부하/긴 운용·통계적 신뢰 범위 추가 확인 |
| L2 장시간 운용·누수·재시작 | NOT VERIFIED | 72546e4 진단 누수 수정·실경과1시간3108반복/59재시작·포인터23·퇴역0/오류0; private25.23→41.10MiB로소폭증가잔존 [범위](TRAINING-STABILITY-QA.md) | 이전2시간시도는quota fixtureFAIL·약70분자원중단; 최신39dab96의CPU/mock7200초ON/OFF·6204/6275반복/각118재시작PASS·오류/잔류Task/반환후참조0 [신규 QA](DATASET-QLORA-QA.md); 실경과8시간/주기적GPU·회수·재시작은별도확인 |
| U1 Windows UI 입력→저장→표시 | PASS | 이전420조합·격리 렌더66화면, 최근800 회귀는 기능 근거 [UI](RESUMED-MEMORY-UX-QA.md) | 현재 주요 화면 격리 렌더/이벤트 확인; 실제 사용자 만족도 별도 |
| U2 격리된 최신 화면/오류/DPI | PASS | setup/models/character/status와팝업, 100/125/150%·두 창 크기30행/55PNG, callback0·own Desktop 검증, [범위](RELEASE-READINESS-QA.md) | 대표4이미지 직접 확인; 나머지 심미성/모든 화면·실제 사용자 만족도 미검증 |
| W1 Portable 소스·파일·동작 | PASS | 앱src는f243675 그대로·기존번들83검사 근거 보존; 공개176쌍/manifest21,578파일 전체hash·금지 파일 경계 감사 [신규 QA](QLORA-ADMISSION-QA.md) | 같은 호스트의 파일 정합성 범위; 다른Windows/번들GPU별도 |
| W2 깨끗한 다른 Windows·설치/업데이트 | BLOCKED | 이 호스트/격리 데이터는 다른 OS·드라이버·새 사용자 환경이 아님 | 별도 Windows 환경 확보; 시스템 전역 설정/VM 임의 설치 금지 |
| D1 실제 Discord 통합·명령 접근 | BLOCKED | `/동의` 비표시 원인 미확정, [복구 경계](COMMAND-RECOVERY-QA.md) | 나머지 품질 준비 후 읽기 인증 조회→명령 변경→송신 별도 승인·클라이언트 확인 |
| D2 `/동의`·`/성격` 오프라인 계약 | PASS | 현재929 회귀의 실제 SDK payload/owner/ephemeral·승인 fingerprint | 실제 등록/표시/실행 PASS로 확대 금지 |
| X1 스티커·이미지 생성/통화·중앙호스팅 | NOT APPLICABLE | [제품 범위](PROJECT-DEFINITION.md)의 미지원 기능 | 기능 안내가 지원한다고 꾸미지 않아야 함(F3) |

## 고정된 수용 조건과 증거 운용

- 품질: 단어·길이·욕설만 다른 것을 개성으로 세지 않는다. 인격/사실성은 별개 축이며 한쪽 악화로 다른 쪽을 상쇄하지 않는다. 핵심 권한/동의/기억 무결성과 명백한 무근거 실행·공동 기억 위반은 고정 핵심 세트0건을 목표로 한다. 작은0건을 전 환경 무오류로 일반화하지 않는다.
- 성능: 초기 SLO는 상주 모델·직접 호출·short 잡담(요청2문장, 실제 출력 길이도 함께 기록)·한 활성 요청에서 p50≤10초/p95≤20초, 기본 대비 큰 악화 없음이다. 장문 기술 설명/포화 큐는 따로 집계한다. 이 기준은 이번 새 workload 전에 정하며 과거 다른 코호트를 소급 PASS/FAIL시키지 않는다. 다중 사용자 공정성·취소 기한은 scheduler 계약과 실제 대기 분포로 추가 확인한다.
- 장시간: 이번 허용 시간 안의 bounded mock soak는 정확한 실경과/반복수/재시작/작업 잔류를 기록한다. 20분을8시간이나 실서버/GPU 장기 인증으로 부르지 않는다.
- 승인 경계: D1의 읽기 인증 API, 명령 등록/정리, 실제 메시지 송신은 서로 다른 승인이다. 지금은 어떤 것도 요청/실행하지 않는다. BLOCKED 하나가 있어도 독립 개발을 계속하되 필수 FAIL/NOT VERIFIED를 숨기지 않는다.
- 버전: 오래된 증거는 그 source의 근거로 보존한다. 최종 QA/HEAD·manifest와 이번 실제 실행 여부를 연결하고, 미사용316개는 소비 승인·장부 없이 열지 않는다.


## 조건부 학습 연구 게이트 — 필수12영역의 대체 근거가 아님

|연구 항목|상태|근거·남은 조건|
|---|---|---|
|헤더/라이브러리 기반 계획|PASS|675f517,677텐서·명시텍스트88대상·자원예산; 수치는계획reserve이며activation상한아님|
|작은Unified CPU/NF4 저장·재개|PASS|64차원896trainable·정렬커널·기본텐서불변/Adam step2; 실제12B/품질검증아님|
|실제12B 짧은 준비·학습|PASS|별도frozenBF1664/128token backward/저장·재개·16자료32step; [새근거](TRAINING-FEASIBILITY-V2-QA.md). 앱기본경로나전체길이학습인증아님|
|전체Runtime1800token 학습|BLOCKED|frozenBF16/선택logits 계획도21.808GiB; 실제실행없음·별도host/activation근거필요|
|조건부합성pilot자료|PASS|직접작성MIT schema2 train52/개발validation8·15scenario그룹분리/byte hash/최신동의receipt계약; 실제CPU토크나이저60개/최대1800tokens·정답경계PASS, 학습아님; 최종316개소비0|
|실제어댑터 인격·사실성A/B|FAIL|compact16train/8개발질문·32step, raw/visible평가를구분해교정; 후보유효형식의예약4개중확정위반3·인격개선근거미달로기각. 기존316개보존·운영적용없음|

상세근거/실행조건/완료1시간·잔여8시간/GPU운용은 [이번QA](TRAINING-STABILITY-QA.md)를따른다. 진단타입누수를고친것과모든Runtime누수·대화품질해결은구분한다.
