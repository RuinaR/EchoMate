# Context Compiler 선택적 근거·실제 Lime QA — 2026-10-26

## 2026-10-27 발화자·취향 저장·요약 경계

검증 마감: 전체 **1,147개 OK312.890초**, Portable **251개 OK25.498초**, 운영6hash 일치·final316 미사용. 마감 RAM6.27GiB<준비7GiB여서 새 실제 GPU 대화/후보 A/B는 BLOCKED·0턴이다.

자동 추출이 가정/역할극을 저장하고 긴 원문의 뒤쪽 부정을 잘라내던 결함을 재현·수정했다. 전달 취향에서 보고 틀이 사라진 요약은 거절·원문 복귀하며 실제 발신자/시각/reply 출처를 보존한다. Context Compiler 생성 prompt는 그대로다. 새 GPU 비교는 RAM 준비7GiB 미달로 차단·해제되어 새 능동 대화0턴이며 후보 프롬프트는 채택하지 않았다. CPU Runtime→SDK mock은6송신/4무송신·자율0, 실제 모델 검증과 구분한다. **모든 모드 정식 READY/RELEASE BLOCKED**, 실제 Discord 미실행·장시간 DEFERRED 유지. [원인·구현·미검증·재개](SOURCE-ATTRIBUTION-QA.md).


시작 main/원격 `a52aea6` 일치·clean. Lime 단일 모델/운영 설정을 유지하고 신규 모델·학습은 수행하지 않았다. **조회 설명은 제한적으로 개선됐지만 자유 생성 고위험 사실성 FAIL·모든 모드 정식 READY/RELEASE BLOCKED**다. 원문은 공개하지 않고 `local_data/context-compiler-20261026/`에 보존했다.

## 구현과 실제 호출 경로

Discord 수신 → 기존 조각/Router/권한 → Intent/실제 읽기·Action/Receipt → Context 선택 → Lime `GGUFLocalBackend.text` → 새 `generation_context.compile_context` → 기존 native tokenizer 예산/단일 Worker → 기존 출력 검증/송신 직전 최신성 → SDK mock. LOCAL은 `LocalChat.send`의 합성 DB·같은 생성기를 사용한다. 명확한 기능 질문은 기존 Runtime 결정 응답을 먼저 사용하며 강제 생성 실험과 실제 제품 응답을 구분했다.

새 Compiler는 읽기 전용 투영이다. 기존 ReadReceipt/MemorySelection·ConsentEpoch·CharacterEpoch·NameVersion·DB v8·fair queue·reply·취소·출력 코드 제한·성인 정책을 재사용한다. Router/DB/영수증 생성/송신 권한을 새로 만들지 않았다. 호출자가 넘긴 carrier와 **객체 동일성**이 확인되는 경우만 중복 carrier를 대체한다. 비슷한 문자열/JSON/사용자 명령이 VERIFIED로 승격되지 않는다. 알 수 없는 외부 문맥은 임의로 파싱·삭제하지 않는다.

- VERIFIED: 실제 이름/표현 상태/허용 범위에서 선택한 기록/현재 읽기 결과/유효 Receipt. **기록이 존재한다는 근거와 기록 속 사용자의 외부 세계 주장은 구분**한다.
- REPORTED: 현재·과거 사용자 원문/인용. GENERATED: 이전 모델 답변·모델 요약·가상 배경. 모델 발언은 실행 근거가 아니다.
- 일반 잡담은 관련 없는 조회·capability·NOT_EXECUTED 기본 묶음을 제외한다. 기억/알림 관련성은 생성 문맥 선택에만 사용하며 실행 의도·청자·권한 판정에 쓰지 않는다. 실제 성공한 해당 도메인에만 성공 설명을 붙인다.
- 실제 scope/current 검사를 통과한 저장 기억은 출처·시점·조건을 보존한다. 긴 기억/예약 text는 임의 접두 절단 대신 전체 내용 생략 표시를 쓴다. 기존 Receipt가 이미 잘렸다고 표시한 내용도 완전 사실처럼 전달하지 않는다. 원본 DB/Receipt는 보존한다. 생략으로 인한 내용 부족은 기능 성공/빈 결과로 바꾸지 않는다.
- LOCAL 긴 회상은 현재와 관련 있는 **짧은 사용자 원문 전체 최대2개**만 시간순으로 보존한다. 이전 모델 응답/요약은 새 사실로 pin하지 않는다. 기존 native2048/출력384/margin64 예산과 완전 대화 쌍 회수는 유지한다. Runtime의 원본 reply·현재 발언 보호는 기존 경로를 따른다.
- observed/event 시간대 투영과 긴 원문 생략은 결정적 CPU 회귀로 검증했다. 다른 시간대의 자연어 모델 정확성·모든 장문 recall은 NOT VERIFIED다.

## 요소별 비용·출처·삽입 계약

실제 native tokenizer로 전체 입력과 해당 요소만 뺀 입력을 각각 셌다. 아래는 **주변 토큰 상호작용을 포함한 한계 비용이며 단순 합산할 수 없다.** 템플릿도 비용을 갖는다. 제공 GGUF template이 자동으로 붙이는 공통 native token prefix227개를 관측했으며 그 원본 캐릭터 설정을 수정하지 않았다. A도 이 제공자 템플릿을 사용하므로 완전 무정책 조건이 아니다.

| 요소 | 출처·범위/권위·삽입 조건 | 이전 B 비용 | 최종 후보 비용 |
| --- | --- | --- | --- |
| 출력 정책 | 기존 공통 코드 출력 제한; 모든 생성 | 128 | 129 |
| 출처/기능 경계 | 앱 정책; 이전 모델/요약에 실행 권한 없음 | 319 | 264 |
| 현재 이름 | 관리자 EffectiveName/NameVersion; identity wrapper | 46 | wrapper 유지; 다른 섹션과 중복 합산 금지 |
| 기분/친밀도 | 현재 cfg·동의 관계값; 사실/권한 아님 | 조회 상태 묶음에 포함 | 23(관측 평온·관계 미동의) |
| 발화자 | 현재 요청의 서버 파생 사용자/캐릭터 구분 | LOCAL carrier에 포함 | 21 |
| 조회/기본 실행 묶음 | 요청별 실제 상태; 미조회와 실패는 unknown | 170–174 | 알림 미조회46/실패54; 수다에는 제외 |
| LOCAL 전체 carrier | 현재 합성 사용자/선택 기억/영수증/명령 안내 | 116–122 | 중복 carrier 제외, 필요한 근거별 투영 |
| 저장 기억 | 실제 허용된 선택, 내용은 REPORTED; 관련 있을 때 | carrier에 포함 | 관련 기억+알림 사례88 |
| 실제 기억 조회 | 현재 ReadReceipt; 관련 질문만 | 기본 묶음에 포함 | 해당 항목 존재 사례71 |
| 알림 조회 | 현재 ReadReceipt; 성공이면 실제 항목만 | 기본 묶음에 포함 | 같은 관련 사례46(미조회) |
| 최근 Receipt | current/scope 검사 후 관련 작업만 | carrier에 포함 | 통합 능동 사례91(최종 정책 복원 전 측정) |
| 기능 지원 | 현재 capability view; 관련 기능 질문에만 | Runtime 항상 전체 packet | 해당 기능 state만; 실행 성공 의미 아님 |
| 성인 정책 | 기존 기본 OFF/허용 계약 | 이전 정책에 포함 | 19(OFF) |
| 최근 대화 | 원문 사용자/모델 역할 분리, 현재 격리 범위 | 사례별 이력0–30/현재13–25 | 필요한 원문·현재 발언 유지; native 최종 예산 확인 |
| 요약 | 출처/동의/버전 검사 후 GENERATED | 별도 Summarizer 경로 | 생성기에서 새 요약 저장 없음; 아래 실패/복귀 검증 |

B 예시 입력: old-read1259/new-failed1248/casual1223. 최종: 각각838/845/763. 선택한 동일10사례 B 입력1206–1268·중앙1223, 최종759–1006·중앙828.5. **토큰 감소 자체를 사실성 개선으로 판정하지 않는다.** 필드 비용/최종 prompt는 비공개 `gpu4/token-components.json`, `gpu5/token-components-final.json`, 각 native-prompts/compiled-sections 기록에 있다.

## 동일 조건 A/B/C/D와 기각한 후보

출력 전 기대 상태를 고정한 개발18사례(이전14+새4)다. final316을 소비하지 않았다. 동일 Lime GGUF hash/llama.cpp b11721·temperature0/top_p1/top_k0/min_p0/seed2026, context2048/출력384/margin64. 사례 내 실제 임시 DB·실행·읽기는 동일하게 두고 생성 문맥만 바꿨다.

A=최소 이름/현재 입력만(과거 이력 없음), B=a52 생성 정책+LOCAL 근거+이력, C=최소 문맥+관련 실제 근거+같은 이력, D=새 Compiler+같은 이력. A와 나머지의 차이는 이력 포함 여부도 있어 순수 정책 효과로 해석하지 않는다. 원인 단위 비교는 동일 이력의 B/C/D와 저장 native 입력의 단일 요소 제거를 사용했다. 제한 기능 Runtime 응답은 별도 `deterministic`/`product` 기록이며 여기서 D는 Compiler 후보를 뜻한다. B 강제 생성은 기존 제품 shortcut 우회 진단이다. 한 조건만 새 기능을 실행해 우위를 만들지 않았다.

1. v0:18사례4조건. 미조회/실패 설명은 나아졌지만 실제 성공 조회를 접근 불가로 말하는 회귀와 미래 조회 약속이 있어 **기각**했다.
2. v1: 성공 설명을 전역으로 추가하니 미조회 허위 주장이 재발해 **기각**했다. 초기 fixture의 이미 닫힌 요청 ID 재사용 오류로 bridge가 중단된 사실을 보존했다. 모델/OOM 실패가 아니며 finally 해제 완료. 다른 fixture로 재구성했고 기준은 낮추지 않았다.
3. 저장한 B native prompt에서 한 요소씩 제거했다. 상태 묶음 제거/LOCAL carrier 제거/이전 assistant 가리기의 효과는 사례마다 달랐다. 단일 과거 모델 발언만이 원인이라는 가설은 성립하지 않았다. **같은 v1 native 입력에서 전역 성공 설명 한 문장만 제거**하면 미조회 사례의 거짓 조회가 사라졌고 실패 사례의 unknown 설명은 유지됐다. 특정 문장이 모든 오류의 원인이라는 일반화는 하지 않는다.
4. 성공 설명을 실제 성공 도메인에만 붙이고 발화자·항목의 civil time을 보존한 v2를10사례 재검증했다. 기존 신체/의식/관계 경계를 복원한 최종 후보도 같은10사례를 실제 GPU로 검증했다. 최종10에는 이전 미조회/실패와 새로운 빈 성공/항목 존재/기억-알림 분리/수다/제안/복합 질문이 포함된다. **전체18의 최종4조건 반복을 완료했다고 주장하지 않는다.** 이미 출력한 신규 사례는 개발 검증 자료다. 재실행 positive fixture의 ID/시각은 달라 완전 동일 bytes A/B가 아니다.

| 관측 | 이전 B | 최종 Compiler | 해석 |
| --- | --- | --- | --- |
| 미조회 목록 old-read | 조회/빈 목록 주장 | 조회하지 않았고 등록 근거 없음 | 해당 개발 사례 개선 |
| 실패 new-failed | 빈 결과로 설명 | 실패·항목 유무 미확인 | 해당 개발 사례 개선 |
| 실제 빈 성공/항목 존재 | 이전 데이터 상세 누락 가능 | 빈 성공과 실제 합성 항목/시각 구별 | 실제 DB/Receipt 일치 |
| 기억 내용 vs 알림 읽기 | 기억을 목록 확인 근거로 혼동 가능 | 실제 목록 조회 아님을 설명 | 도메인 구분 유지 |
| 일반 수다/미래 제안 | 기존 정상 예시 유지 | 정상 수다를 결정적 안내로 교체하지 않음 | 고정 정상 사례 가로채기0; 모든 자연스러움 인증 아님 |
| 빗소리 미래 제안 | 지각처럼 표현 가능 | 실제 소리가 들리는 듯한 표현 잔존 | 의미 한계, 해결 아님 |

최종10 강제 생성 p50 약0.891초/p95(최근접 순위)1.344초. B 대응10 p50약0.922초/p95약1.297초다. 순차 실행·캐시·출력 길이가 달라 **인과적 속도 향상으로 주장하지 않는다.** TTFT/토큰/큐/worker는 각 raw metric에 기록했다.

## Codex 능동 대화와 기능 통합

기존 질문 일괄 실행과 구분해 실제 응답을 읽고 후속을 정한 새 대화2개, **12턴+14턴=26턴(모델19/Runtime7)**을 실제 LOCAL Controller에서 진행했다. 출력·DB·현재 읽기·Receipt·이름 버전은 `gpu3/command-002`부터`command-029` 결과와 native/model 로그에 있다. 관리자 이름 변경1회는 대화 턴 수에서 제외했다.

- 12턴: 게임 실수/감정→농담/책방→실수한 사람을 친구로 정정→친구가 봇 참석을 농담으로 인용→현실 참석 확인→이름→미래 제안→기억→가상 취향→초기 사건 회상. 마지막 입력1588토큰·완전 과거 쌍4개 회수 후에도 친구의 규칙 오해/사용자의 민망함을 회상했다. 실제 참석은 부정했지만 **친구 농담의 작성자를 자기로 바꾸는 발화자 오류1개**가 있었다.
- 14턴: 기억 동의→보고형 저장 명령은 NOT_EXECUTED→빈 조회→사용자 정정→명확한 저장 SUCCESS→취향 설명→실제 예약 SUCCESS→내용 설명→실제 기억 OSError FAILED→재조회→Haru에서Yuna로 관리자 변경 후 자기 이름→예약 취소→조회+불명확한 시간의 PARTIAL/NEEDS_INFORMATION→일반 수다. 첫 저장 실패를 성공으로 집계하지 않았다. 정정1입력은 중국어이고 응답은 한국어였으므로 모든 입력이 한국어였다고 하지 않는다.
- 위 빈 기억 조회에서 모델이 **말하지 않은 고전문학 취향을 추가**했다. 정확히 같은 빈 조회·입력·이력을 기존 생성기/후보로 비교하니 이전은 저장·회상을 근거 없이 주장하고 후보는 없는 장르를 추가했다. **양쪽 모두 실패**이며 이식한 사실성 필터로 숨기지 않았다. 잘못된 응답이 실제 기억/예약으로 자동 저장되지는 않았다.
- 실제 동의/저장/예약/취소/FAILED/부분 결과는 DB·영수증으로 검증했다. 모델 발언은 실행 권한이 아니다. 일반 대화만으로 이름/DB를 변경하지 않았다. Human 만족도·전체 대화 자연스러움은 NOT VERIFIED, Codex 원문 검토와 분리한다.

## 요약의 의미 보존

실제 GPU 요약에서 원문의 명시적 '미확정/가능성'을 '확정된 계획인지 확인'이라는 열린 질문으로 바꿔 이전 guard를 통과하는 사례를 발견했다. 임시 저장한 요약은 철회 후 사용 불가·삭제 후0건을 확인했다. 새 좁은 fidelity 검사는 원본 질문을 제외하고 **명시 부정→열린 확정 확인** 변형을 거절한다.

동일 실제 GPU 출력 원문을 새 `Summarizer.answer`에 CPU 재생했을 때 저장을 거절하고 원본 사용자 메시지31/33(화자·시간·부정·조건) 선택으로 복귀했다. 이것은 **실제 출력 replay 검증이며 새 GPU 요약 생성/일반 의미 동등성 PASS가 아니다.** 기존 provenance/동의/source version/삭제/epoch 검사와 fallback을 재사용한다.

## DIRECT·자원·검증 범위

최종 실제 Lime→Runtime→SDK HTTP mock **10이벤트 통과·6송신/4무송신·실패0·assess_social/link_direct/verify_target 각각0회**. 원본 reply·세 조각 통합 유지. 자율 참여의9108/청자 모호성은 이번 결과로 해결하지 않았다.

5개 짧은 단일 모델 세션을 순서대로 실행하고 모두 Controller/자체 자식 해제 `closed=true`를 기록했다. 첫 fixture 중단/마감 후 미실행 token audit도 보존하고 실제 후속 세션에서만 완료 처리했다. 예약 합성 DB 활성 scheduled/processing0. 세션 로딩14.36–15.39초(설치/Controller 전체 경로); 최종 backend 자체 로딩3.625초와 구분한다. 관측 최소 freeVRAM8079MiB, RAM약3.918GiB, commit약21.766GiB, 최고 GPU65°C(backend extrema 포함). 자체 llama 서버 Private Commit 피크약10.629GiB. CUDA allocated/reserved는 llama.cpp 경로에서 NOT AVAILABLE이며 전체 GPU 집계와 동일시하지 않는다. 타 프로그램을 조사하지 않았다. 안전2GiBVRAM/3GiBRAM/2GiBcommit/85°C를 유지했다.

최종 검증 수치·Portable/보존 결과는 아래 마감 기록을 따른다. UI 코드/레이아웃 변경은 없으며 전체/Portable의 격리 위젯 이벤트 회귀와 새로운 시각·다른 Windows 검증을 구분한다. 실제 Discord는 미실행. **30분 GPU/2시간 Runtime/8시간 soak는 DEFERRED — USER REAL-WORLD TEST**, 이번 짧은 세션 합계로 장시간 안정성을 주장하지 않는다.

## 모드 판정과 다음 작업

| 모드 | 현재 결과 | 남은 필수 조건 |
| --- | --- | --- |
| LOCAL_CHAT_READY | 정식 READY BLOCKED; 격리 합성 기술 시험 가능 | 빈 기억의 없는 취향·화자/현실 경험 자유 생성 잔여 실패 |
| DISCORD_DIRECT_BETA_READY | 정식 OFFLINE READY BLOCKED; 라우팅 오프라인 검증 유지 | 고위험 자유 생성 사실성 및 별도 승인 실제 Discord |
| DISCORD_AUTONOMOUS_RELEASE | BLOCKED | 위 위험·기존 의미 청자/복귀·실환경·장시간 근거 |

다음은 없는 선호 생성/인용 발화자 혼동을 **같은 빈 결과/원문·기능 실행 상태**로 원인 분해하고 명시적 기능 응답과 자연 잡담을 분리 검증하는 것이다. 실패 문항의 답을 prompt에 하드코딩하지 않는다. 긴 저장 기록 생략 시 사용자에게 필요한 원문 선택/확인 UX도 후속 검증한다. 현재 Lime 유지·선택적 Runtime 문맥 개선은 근거가 있지만 모델 환각 제거/실사용 준비 완료를 선언하지 않는다.

재개: 최신 main/clean과 `AI-HANDOFF`, 이 QA, 비공개 `final-checkpoint.json` 확인 → `preserved-before/after.json` 대조 → 집계 자원 확인 → 새 프로토콜을 출력 전에 고정 → LOCAL Controller/단일 Lime와 임시 DB로 능동 검증. 완료된 GPU command 폴더는 재사용하지 않는다. 최종316은 그대로 보존하며 실제 Discord 승인은 별도다.

## 2026-10-27 검증 마감

최종 소스261개 Python SHA256 freeze와 실행 후 일치. 표적41개 OK11.585초, 최종 전체 **1,136개 OK327.930초**(wrapper335.297초; regression-final.json), Portable 자체 Python/src **240개 OK23.994초**(비활성 Desktop wrapper28.859초). 최초 최종 이전1,134개 성공 기록도 pre-final 파일로 보존했다. 실제 장시간 시험 없이 짧은 mock/격리 UI/취소·경합을 실행했다. 새 UI 시각 검증·다른 Windows·실제 Discord는 NOT VERIFIED다.

운영 설정/bootstrap/두 DB/평가 장부/원본 Lime의 **6개 SHA256 동일**. 원본Lime SHA256 `bafcfe3f624f0e1f84014c9b9136788992629955f7ce9146941226cd280d618e`. final316 소비0·합성54개 reminders 테이블의 활성 예약0, 합성 DB 파일56개를 검사했다. 모델/LoRA/DB/원문은 공개하지 않았다. Portable `dist/EchoMate-rc-utterance`는 모델 미포함·manifest21,616파일이며 최종 전체 해시/금지 파일 감사 결과는 비공개 `portable-final-audit.json`과 `final-checkpoint.json`에서 확인한다. 문서까지 동기화 후 manifest 감사하며 감사 중 bundle을 수정하지 않는다.

소스/통합 검증 완료와 모델 고위험 품질 실패는 분리한다. **LOCAL 정식 READY·DIRECT OFFLINE READY·AUTONOMOUS RELEASE 모두 BLOCKED**, LOCAL 격리 기술 시험만 가능하다. 장시간 DEFERRED와 실제 Discord 별도 승인 경계를 유지한다.

전체 manifest 감사 이후 문서의 wrapper 소요시간 표기만 정정했다. 해당 문서 한 파일과 manifest는 추가 SHA256 대조했으며 다른 manifest 항목은 동일하다. 결합 근거는 비공개 `portable-final-attestation.json`에 보존한다.
