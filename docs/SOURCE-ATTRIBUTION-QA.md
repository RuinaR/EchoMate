# 발화자·취향·인용 출처 경계 QA — 2026-10-27

## 2026-10-27 자연어 규칙 감사·일반화 경계

검증: 전체1,159개 OK326.343초·Portable263개 OK24.853초. GPU DIRECT는 짧은 health 중단으로 미실행, CPU mock6/4·자율0 유지.

16개 주요 모듈의 정규식 API169곳을 A안전/B프로토콜/C의미추정/D?과적합의심/E중복으로 감사했다. 40개 신규 원천 비교에서 장문 보류/의미 필터의 단순 제거는 부적격 개인 기억 저장을 늘려 기각했다. 정정 인용 처리만 기존 prose로 통합해8개 CPU 사례의 오정정2→0·직접 정정4/4를 유지했고, 정확한 source span 검증을 공통화했다. 연구용 reading 계약은 기존 추출기를 재사용하며 Runtime/저장 권한은 항상 비활성이다. 코드 총량 감소나 일반 의미 정확성 향상은 인증하지 않는다. 초기 자원 보류 뒤 실제 여유 증가로 GPU8사례24응답·능동5턴을 검증했다. 창작 대사 회상은 제한적으로 개선됐지만 긴 주체 정정 실패와 원인 미확정 backend health 중단이 남아 모든 정식 READY/RELEASE BLOCKED다. 실제 Discord 미실행·장시간 DEFERRED 유지. [전체 감사](SEMANTIC-RULE-AUDIT.md) · [비교·구현·한계](GENERALIZATION-QA.md).


시작 로컬/원격 main `08415bb` 일치·clean. 현재 Lime와 Context Compiler·명시적 기능 Receipt·모드별 게이트를 보존했다. **이번에 재현·수정한 것은 자동 저장과 요약의 근거 손실이며 새 실제 GPU 대화 품질 향상을 인증하지 않는다. RELEASE BLOCKED 유지.**

## 계획과 실제 실행 범위

1. 기존 실제 Lime 원문/현재 문맥/DB·읽기 상태를 대조했다.
2. 새 취향·직접/간접/중첩 인용·모델 추측·조건·정정·정상 수다12사례와 기준을 출력 전에 `protocol.json`에 고정했다.
3. 기존 생성 B / 주체 읽기 정책 C1 / 원문 보고 ledger C2 후보를 비공개 작성했다. **GPU 로딩이 기존 RAM 준비 기준에서 차단되어 세 조건 모두 실행되지 않았다.** 후보를 제품에 이식하지 않았다.
4. 독립적으로 재현된 저장·요약 무결성 결함을 CPU/합성 SQLite·실제 Summarizer fallback으로 수정·검증했다.
5. DIRECT는 Runtime→SDK HTTP mock으로 별도 검증하고 전체 회귀·Portable·보존 해시·공개 diff 감사를 수행한다. 마감 수치는 아래 기록/비공개 체크포인트를 따른다.

원문·후보·진단은 `local_data/attribution-20261027/`에만 있다. final316 소비0. 이번 신규 프로토콜은 GPU 출력 미실행 자료이며, CPU 개발에 사용한 예문을 미사용 독립 최종 평가로 부르지 않는다.

## 실제 실패와 원인 구분

기존 실제 GPU 대화26턴을 이번 새 대화로 집계하지 않는다. 이전 `context-compiler-20261026/gpu3/command-005-response.json`은 사용자가 **친구 농담을 전달**했지만 모델이 대사의 작성자를 자기로 말했다. 현실 모임 참석은 부정했으므로 현실 동행 긍정과 발화자 오류를 구분한다. 사용자 정정 후 화자 구분을 수용한 기록도 보존했다.

이전 `command-017-response.json`은 실제 기억 조회 SUCCESS_EMPTY/count0·저장 성공 영수증 없음인데, 모델이 사용자가 말하지 않은 장르 취향을 추가했다. 원문에는 헌책방의 조용한 시간을 이야기하고 싶다는 말만 있었다. **모델이 문맥 주제를 개인 취향으로 확장한 오류**이며, 실제 DB가 그 취향을 반환한 것은 아니다. 앞선 같은 입력/이력 비교에서 기존 생성기와 Compiler는 서로 다른 허위 주장을 보여 어느 쪽도 이 오류를 해결했다고 할 수 없다. 이번 CPU 추적으로 외부 세계의 사실/새 한국어 의미 성능을 인증하지 않는다.

자동 저장·요약에는 별도 재현 가능한 결함이 있었다.

| 경계 | 수정 전 합성 재현 | 실제 수정 | 수정 후 확인 |
| --- | --- | --- | --- |
| 자동 기억 추출 | 첫인칭 취향 뒤 가정/역할극 설명이 있어도 저장 | 기존 추출 eligibility에서 명시 가정·역할극·반어 문맥 보류 | 해당 원문 저장0; 직접 자기 취향은 정상 저장 |
| 작은따옴표·축약 전달 | 고유명사 화자가 전한 인용 속 난/좋아해를 현재 사용자 취향으로 저장한2사례 | 자동 추출에서 인용 구획·축약 전달 보류 | 두 전달문 저장0; 원래 문장은 새 사용자 사실로 승격하지 않음 |
| 원문 길이 | 최대500자 원문이 검사 후300자로 잘려 뒤쪽 부정·귀속이 사라질 수 있음 | 자동 추출은300자 초과 전체 원문 보류; 접두를 사실로 저장하지 않음 | 긴 원문 저장0·원본 유지; UI 명시 편집/기존 DB를 자동 수정하지 않음 |
| 전달 취향 요약 | 친구가 전한 취향을 주체 없는 확정 취향으로 바꿔 기존 validator 통과 | 취향 절의 명시 전달/인용 경계가 빠지는 좁은 변형을 거절 | 새 요약 저장0·출처 원문 fallback |
| 요약 표시 출처 | source ID/역할은 있었지만 발신자·시각·reply가 body에 명시되지 않음 | 모델 출력이 아닌 실제 Turn에서 reporter/observed_at/reply_to 투영 | 원래 발신자/시각/reply와 일치; 기존 요약은 LEGACY_UNKNOWN |

수정 검토 중 가정 어휘가 음식명 라면·가정식을 오차단할 가능성도 발견했다. 조건 표시를 좁히고 실제 음식 취향의 정상 저장을 함께 검증했다.

새 guard는 한국어 전체 의미 분석기나 취향 추출기가 아니다. 자동 저장을 보수적으로 보류할 뿐 반어를 정확히 해석했다고 주장하지 않는다. 직접 인용/간접 전달의 원래 화자·대상은 원문에 남고, 추정 닉네임을 실제 User ID로 만들지 않는다. 같은 보고 어미를 유지하면서 대상을 잘못 바꾸는 요약 등 일반 의미 오류는 **NOT VERIFIED/잔여 위험**이다. 기존 동의/권한/원본 수정·삭제/요약 fingerprint·source tombstone·생성/송신 최신성 계약을 재사용한다. 운영 DB migration·초기화는 없다.

## 문맥·토큰·정상 대화 영향

`generation_context.py`, `gguf_backend.py`, LOCAL/Runtime 생성 입력 구성은 이번에 변경하지 않았다. 기존 VERIFIED/REPORTED/GENERATED 선택·현재 이름·Native2048/출력384/margin64·reply/최근 발언 보호를 유지한다. 작성한 C1/C2는 미검증 비공개 후보로만 남겼다. **새 native 토큰 비용·응답 지연·허위 취향 전후 개선율은 측정하지 못했다.** 이전10사례의 토큰 감소를 신규 사례에 일반화하지 않는다.

요약 body에는 실제 이벤트 전달자/관측 시각/reply 메타데이터만 추가하며 인용 화자를 추론하지 않는다. 렌더링은 전달자/시각과 모델 요약임을 함께 표시한다. 이 정보의 실제 native 예산·모델 품질 영향은 GPU 재개 후 확인해야 한다. 기존 stored 요약은 schema 변경 없이 읽고 없는 출처를 새로 추정하지 않는다.

일반 자유 대화를 차단하거나 같은 거절문으로 교체하는 로직은 추가하지 않았다. 정상 직접 취향의 저장·요약은 CPU 검사에서 보존된다. 과도한 불확실 응답/일상 자연스러움은 새 실제 모델 대화가 없어 **NOT VERIFIED**다. 저장 후보 보류가 저장 성공으로 보고되지 않는 기존 Receipt 계약을 유지한다.

## GPU 안전 차단과 미실행 목록

최초 집계 freeVRAM11624MiB·RAM약6.26GiB·commit약24.36GiB·39°C. 설치 후 실제 로딩 직전 RAM 약5.08GiB로 **기존 준비 요구량7GiB(준비4+유지3)에 미달**, `ram_preparation`으로 차단됐다. `bridge-report.json`은 FAILED_OR_SAFETY_STOP/closed=true, 실제 GPU 비교·새 능동 대화0턴이다. 단순히 실행 중 RAM3GiB 여유만 있으면 시작 가능하다고 해석하지 않았다. 이후 CPU 표적 검증 뒤 집계도 약5.08GiB로 동일해 무조건 재시도하지 않았다. VRAM/commit/온도 기준도 완화하지 않았다. 다른 프로그램 조사·종료·설정 변경은 없다.

B/C1/C2 응답/토큰/지연, 새로운10–30턴 능동 대화, 실제 Lime→SDK 통합은 **BLOCKED — RESOURCE ADMISSION**다. 이전 차수 GPU 검증은 당시 결과로 보존하고 이번 소스의 새 GPU PASS로 재사용하지 않는다. 30분/2시간/8시간은 **DEFERRED — USER REAL-WORLD TEST**이며 이번에 실행하지 않는다.

## DIRECT·기능·회귀 범위

동일 기존10이벤트를 실제 Runtime→SDK HTTP mock에서 재생했다. **6송신/4무송신·10기대 일치·실패0·assess_social/link_direct/verify_target 모두0회**다. 정확한 원본 reply·삭제 후 늦은 응답 폐기·세 조각 통합을 기존 경로로 검증했다. **생성은 AsyncMock이며 GPU가 아니다.** 초기 CPU fixture가 GGUF 전용 인터페이스 없는 backend를 실제 캐릭터 backend처럼 등록해 실패한 기록을 보존하고, CPU backend를 실제 모델로 표시하지 않도록 fixture를 고쳤다. 제품 Router/판정 기준을 바꾸지 않았다.

11개 신규 회귀는 가정·긴 원문·타인 전달·동의 없는 저장 차단, 정상 자기 취향·사용자 격리, 요약 보고 틀·실제 메타데이터·레거시/모델 출처·원문 복귀를 다룬다. 최초 관련80개 실행에서 신규 fallback fixture에 conversation_id/요약 동의가 빠져1오류였고 이를 보완한 신규11개는 OK0.263초다. 최초 전체1,147개에서도 기존 최소 source 입력에 author_id가 없던 호환성1오류를 확인했다. 모델이 주는 값을 대체 근거로 쓰지 않고, 없는 reporter/시각은 추가하지 않아 LEGACY_UNKNOWN으로 렌더링하도록 수정했다. 이후 표적23개 OK1.016초이며 이전 전체 실패 로그는 before-compat-fix로 보존했다. 호환성 수정 뒤 전체 검증 중 별도로 위 인용 저장 오염과 음식명 오차단 위험을 발견해 경계를 추가 보완했으므로 이전 전체/Portable 결과를 최종 소스 PASS로 재사용하지 않았다. 마지막 신규11개는 OK0.315초다. 최종 전체 결과가 최종 소스 기준이다.

## 현재 모드와 재개

| 모드 | 현재 판정 | 다음 검증 |
| --- | --- | --- |
| LOCAL_CHAT | 격리 기술 시험 경로 유지; 정식 READY BLOCKED | 자원 충족 후 새 실제 능동 대화·허위 취향/인용 오류·정상 잡담 |
| DISCORD_DIRECT | OFFLINE ONLY·mock6/4 유지; 정식 READY BLOCKED | 새 소스 실제 Lime 통합·고위험 사실성·별도 승인 Discord |
| DISCORD_AUTONOMOUS | BLOCKED | 기존 의미 청자/복귀 및 위 사실성·실환경 근거 |

다음 재개: 최신 main/clean·이 QA·비공개 `final-checkpoint.json` → 운영6hash 대조 → 집계 RAM7GiB 이상/VRAM·commit·온도 기존 admission 확인 → 새 GPU 폴더에서 instrument/compare 프로토콜 실행 → 원문을 읽고 C1/C2 채택/기각 → 실제 LOCAL10–30턴 여러 대화·확인된 상태/Receipt 대조 → DIRECT 실제 GPU6/4/자율0 → 필요 변경에만 회귀. 기존 실패 폴더/command를 덮어쓰거나 이미 실행한 원천을 미사용 최종 평가로 부르지 않는다. GPU 근거가 없는 프롬프트를 운영에 반영하지 않는다. 실제 Discord는 별도 명시 승인 전 금지다.

정확한 비공개 재개 준비 명령: `PYTHONPATH=src;tools;tests` 환경에서 `.venv-gemma4/Scripts/python.exe local_data/attribution-20261027/prepare_gpu_resume.py`. 이 helper는 집계 RAM을 검사하고 통과 시 새 고유 GPU 폴더/명령을 준비할 뿐 모델을 실행하지 않는다. 출력한 bridge 명령을 다음 개발 단계에서 실행하면 기존 모든 backend admission을 다시 확인한다. 현재의 실패 폴더에는 재실행하지 않는다.

재개 PowerShell 환경 예시:

```powershell
$env:PYTHONPATH='src;tools;tests'
$env:PYTHONIOENCODING='utf-8'
.venv-gemma4/Scripts/python.exe local_data/attribution-20261027/prepare_gpu_resume.py
```

미실행 비교 helper는 각 사례의 임시 캐릭터 DB에서 동의 후 실제 `execute_read`/ReadReceipt/current를 확인하고 같은 빈 결과를 각 생성 조건에 제공하도록 준비했다. 실행 시 DB 전후도 기록하며, 이 강제 생성 비교와 후속 실제 LOCAL 능동 대화는 별도다. 이번에 해당 helper의 GPU 실행을 검증했다고 주장하지 않는다.

## 최종 마감 근거

최종 전체 **1,147개 OK312.890초**, Portable 자체 Python/src **251개 OK25.498초**. 소스262개 Python SHA256 freeze 일치. 초기 전체 호환성 실패와 경계 보완 전 성공 기록도 별도 파일로 보존했다. 최종 DIRECT CPU Runtime→SDK mock10건은6송신/4무송신·자율0이며 GPU 생성으로 확대하지 않는다. 운영 설정/bootstrap/두 DB/평가 장부/원본 Lime **6개 SHA256 일치**, final316 소비0·합성 reminders 테이블2개 활성 예약0.

마감 집계 RAM 약6.27GiB로 여전히 준비7GiB 미달이므로 조건이 충족되지 않은 GPU 재시도를 하지 않았다. 새 GPU 능동 대화0턴·새 B/C1/C2 출력/토큰/지연0건이며 이 한계는 해소되지 않았다. 모드별 정식 READY/RELEASE BLOCKED와 실제 Discord 미실행·장시간 DEFERRED를 유지한다.

Windows 산출물은 `dist/EchoMate-rc-utterance/EchoMate.vbs`다. 신규 UI 디자인/시각 검증은 없으며 Portable 격리 위젯 이벤트/Controller·회귀와 구분한다. 다른 Windows 검증도 NOT VERIFIED다. 모델/토큰/운영 DB/원문 미포함·manifest21,617파일 전체 해시/금지 파일 감사 결과 및 공개 staged diff는 비공개 `portable-final-audit.json`, `public-audit.json`, `final-checkpoint.json`으로 연결한다. 최종 실행 소스 이후에는 검증 수치/문서만 갱신하고 manifest를 동기화한 상태로 감사한다.
