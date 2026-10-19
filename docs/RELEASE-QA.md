# 릴리즈 QA — 2026-10-19

> **최신 검증 범위(2026-10-19):** 사용자 지시에 따라 실제 Discord 서버·채널·스레드에 접속하거나 시험 메시지를 보내지 않는다. 사용자에게 계정 조작이나 수동 QA를 요청하지 않고 로컬 GPU·모의 이벤트·SDK 직렬화·격리된 저장소 검사로 진행한다. 아래 과거 실서버 테스트 절차는 실행 지시가 아닌 이전 기록이며, 새 명시적 지시 없이는 재개하지 않는다. 외부 서비스의 실제 동작은 미검증으로 구분한다.


추가 짧은 반복 부하 검사: 실제 단일 ThreadPoolExecutor에 32.157초/115묶음/2300요청을 투입했다. 정상1955·의도취소345·예기치 않은 오류0, 최대 동시 워커1, 종료 후 실행/대기0·asyncio task 증가0이다. SDK/GPU/원격 서버는 사용하지 않은 큐·취소·종료 검사이며 장시간 RAM/GPU 누수나24시간 안정성을 입증하지 않는다. 원본 스크립트·결과는 private short_soak.py/short-soak.json에 보존했다.

## 최신 릴리즈 후보 감사 — 다중 대화 (2026-10-19)

**최종 판정: NOT VERIFIED (전체 실사용 릴리즈).** 로컬 코드·모의 통합·실제 GPU 검사는 통과했지만, 사용자가 이번에는 로컬 GPU·모의 검증만 선택해 최신 다중 대화 코드의 실제 Discord 다중 계정 QA를 하지 않았다. 실제 Windows 사용자 조작/장시간 soak도 남는다. 이전 단계의 실제1분 알림 성공은 당시 구현의 증거다. 전체 PASS로 합치지 않는다.

기준 HEAD eaf1d1e(main clean), 모델 google/gemma-4-12B-it NF4와 기존 r8 q/k/v/o60. 성인 유머는 같은 기본 모델+정책 대안이다. 신규 GGUF/학습/미디어 확장 없음. Windows/Python3.10/RTX4070TiSUPER16GB·RAM32GB, 기존 .venv-gemma4를 사용했다. 단계별 commit/dirty hash·source snapshot·timestamp·원본 로그는 private manifest에 남겼다. 최종 구현 커밋은 AI-HANDOFF 최신 절과 git log를 따른다.

### 요구사항 추적 매트릭스

| 요구 | 구현·근거 | 코드/모의 검증 | 이번 실제 GPU/외부 검증 | 상태 |
|---|---|---|---|---|
| 기본/개인/성인 정책·성별·기분·성격 | inference/character/adult_policy/settings | 기존 adult/character/owner 회귀 | 세 모드 실제 생성, 새 weights 미선정 | 구현·실제GPU |
| 모델 전환/준비 실패 복귀 | Runtime.switch_model | model_change/reconnect/소유자 검사 | gpu-lifecycle 생성중2대상 보존·주입 실패 후 실제 재응답 | 구현·실제GPU |
| 멘션/이름·별칭·접미사·인용 차단 | naming/Runtime/routing | 기존 이름 QA+다른 대상/인용 회귀 | gpu-2 이름/멘션 혼합; 이전 독립 이름36사례는 이전 버전 | 구현·GPU+모의 |
| 동일작성자1/2/5초 직접 호출 | sessions/FIFO/고정 source | test_parallel_runtime | gpu-bursts-2 세 모드18/18 | 구현·실제GPU |
| 보충/독립/완전 중복 구분 | intent prefix/SUPPLEMENT/hash | 명시 이름 보충·코드 대소문자·별개 보존 | 각 모드 보충1/중복1/독립4 통과 | 구현·GPU+모의 |
| 다른 사용자·같은 채널 별개 흐름 | Conversations·독립 DialogueState | context/target/cancel 검증 | gpu-2 변경18/18·기준9/18 | 구현·실제GPU |
| 실제 reply로 다자 합류 | 공유 conversation ID·실제 발언 merge | 세 사람/queued shared/타인취소 차단 | group-1 기본누락 후 group-2 세 모드4대상·최신사실 | 구현·작은GPU회귀 |
| 다른 채널·스레드 동시 | guild/channel/thread 범위 키 | 두 스레드/별개 상태·source 고정 | 이번 CUDA+실서버 여러 스레드는 미시험 | 구현·모의 |
| 신규 자율/지속 분리·침묵/종료/휴지 | activity lease/근거 후속/의미 판단 | 지역별 cooldown/부하/다른 채널 비전역/종료·노후·pending | 작은 GPU 그룹 후속, 인적 자연스러움 미평가 | 구현·모의/부분품질 |
| 활성 대화 집계 | 실제 참여·상호작용·종료·pending·idle | 저장세션≠활성/idle 복귀/대기중 active | 실제 사용자 체감 미관찰 | 구현·모의 |
| 중앙 단일 GPU·공정성 | scheduler+기존 executor1 | 단일 실제CPU워커/priority·aging·capacity/취소 소유권 | 실제CUDA중첩·대기 측정 | 구현·GPU+모의 |
| source reply/편집·삭제·nonce | execute/ledger/hash | SDKmock fetch/reply/수정·삭제/보충/멘션 없음 | CUDA synthetic target 정확; Discord 실제 API 미시험 | 구현·모의 |
| Unicode/기본 스티커 | 기존 액션 validator·source reply | STANDARD 제한/권한/nonce 회귀 | 이번 실서버 송신 없음 | 구현·모의 |
| 최근/발췌 문맥·장기 회상 | DialogueState/context/merge | source·speaker/관련·오래된 발언·편집 | 합성5/10/20/50턴 지정 사실12/12 | 구현·제한GPU |
| 작업 기억 flow/사용자/서버 격리 | memory_flows/schema3 | task flow/명시 본인 archive·타인 차단 | 이번 새 schema의 품질 A/B는 미실행 | 구현·모의 |
| 기억 만료·갱신·삭제/철회 | 기존 TTL/cutoff/tombstone | 실제SQLite DST/기간·삭제 부활 방지 | 실제 사용자 삭제 확인 미실행 | 구현·모의 |
| 관계·reaction 영속/중복 | companion_store transaction | event idempotency/철회/서버 분리 | 이번 실서버 reaction 없음 | 구현·모의 |
| 구성원 자동 저장 동의 | subject_consents + /내기억 | 부재·허용·철회·guild clear/legacy 보존 | 새 slash 실제 sync/당사자 조작 미시험 | 구현·모의 |
| 자연어 예약·UTC·대상/중복/복구 | companion/temporal/독립서비스 | source commit/시간/타인/불명확 전송/200예약 | GPU-lifecycle 모의 발송1·약15ms, 이전 실서버1분은 과거버전 | 구현·GPU+모의 |
| Gateway 끊김·모델 변경 겹침 | RAM보류/resume/fresh/ledger | 미송신 보존/불명확 선점 미재생 | 실제망 끊김 미시험 | 구현·모의 |
| 종료/worker/취소·task 누수 | close/ownership/FIFO locks | queued close/반복cancel/worker소유권 | 평가프로세스 순차 종료, 장시간 실제앱 미시험 | 구현·부분실제 |
| DB version/lock/rollback/복구 | schema3 atomic/WAL/FK/strict version | 실제SQLite1→3/lock/손상보존/rollback/QAbackup | 운영DB migration 실제실행 안함 | 구현·모의 |
| 소유자/서명/allowlist/안전 | 기존검증+전송직전 가드 | 침입자/서명/permission/age/token/무한루프 회귀 | 실제권한변경/운영서버 미시험 | 구현·모의 |
| OOM/온도/VRAM 보호 | 기존health+device failure stop | 오류 주입/기기실패/자원 임계 회귀 | 실제GPU health 적용, 실제OOM·과열 유도 안함 | 구현·부분실제 |
| Windows 시작/종료/설정/페이지 | 기존VBS/Controller+진행UI | 설정/명령·상태·숨긴Tk·DPI100/125/150% | 실제화면/마우스/키보드 자동조작 미사용 | 구현·모의 |
| 진단/queue/진행·export | 숫자 trace/scheduler snapshot | 원문/ID 미포함·디스크 실패 비재전송 | private GPU 지표 수집 | 구현·실제계측 |
| 새GGUF/등록미디어/멀티모달 확장 | 사용자 제외·품질보류 | 복구하지 않음/기본OFF 유지 | 새 모델승격 안함 | 의도적 제외 |
| 자동 과거수집·생성요약·24시간 soak | 별도 장기 검증 필요 | 출처 발췌 유지, 가짜 과거 없음 | 사람 블라인드·장시간 미실행 | 부분/미구현 |

### 실행·비교 증거

- 기준 전체328검사 OK18.002초. 최종 `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`: **366검사 OK25.682초**. 단위/실제SQLite/SDKmock·runtime통합/숨긴Tk를 포함하며 단위 개수는 제품 품질 점수가 아니다. PYTHONPATH=src.
- GPU 모드는 한 개 NF4 모델에서 base disable_adapter/개인 LoRA/기본+성인정책을 순차 사용했다. 표의 작은 단일응답 A/B는 프롬프트·응답 해시 일치 모드당5/5, 워밍업1쌍 제외·순서교대다. 상세 p50/p95·VRAM·큐·분모는 [PARALLEL-CONVERSATIONS](PARALLEL-CONVERSATIONS.md)에 있다. 초기측정 후 추가된 가드를 포함한 모든 경로의 속도 향상을 주장하지 않는다.
- 실제 중첩 gpu-2: 세 모드 각각3회 중첩, 변경 원본18/18응답·대상오류0·중복0. 기준9/18이며 취소·쿨타임 누락 원인을 구분했다. 변경은 더 많은 실제 답변을 생성하므로 walltime 우위를 비교하지 않는다.
- 같은 작성자의 실제1·2·5초·GPU대기·보충·중복18/18. 보충 교체1회/모드는 의도한 취소다. 장문 blocker 때문에 p95가25~31초인 사례를 숨기지 않는다. TTFT/queue/TPS/VRAM/RAM 원본은 private에만 있다. 판단과 텍스트 호출을 섞은 TTFT를 전체 사용자 지연으로 쓰지 않는다.
- 50턴은 합성 실제발언 fixture의 회상이며50번 실제 상호 생성이 아니다. 그룹 보강 후 다른 사실 fixture3모드 통과도 작은 회귀다. 자연스러운 한국어/사람 선호/환각률·일반화가 모두 통과했다는 뜻은 아니다.
- GPU중 실제base→persona 제어/미송신2대상 보존, 준비 실패 주입 후 이전선택의 실제응답, GPU중 독립SQLite알림 모의전송1회0.015초를 확인했다. 실제Discord API latency가 아니다.
- 실제 UI 사용자 조작과 새 Discord 송수신은 **범위 밖/미실행(사용자 지시: 로컬 모의 검증만)**. 원래 사용자가 금지한 컴퓨터 자동 조작은 하지 않았다. 새로운외부GPU·유료API·학습·미디어 확장0.

### 결함·보안·남은 게이트

수정한 주요 결함은 채널전체작업 취소, 독립질문 덮어쓰기, 조기타이머 wakeup시발언거절, model/Gateway 보류유실, 일반오류전역정지, 원본편집미검출, 공유요청에 앞선실제답변미반영, 타인요청취소, 비동의구성원자동갱신, 코드대소문자중복오인이었다. 오류·source snapshot·group-1 누락·import 오류 중단 로그도 보존한다. 초기 중단한 이 저장소 QA 프로세스만 종료했고 사용자 앱을 조작하지 않았다.

검증 범위 내 재현된 미해결 P0/P1 차단 결함은 없다. **운영 릴리즈 증거 부족 게이트는 남는다.** 재연결·rate-limit·실제 권한/채널삭제·실제CPU/GPU자원부족·24시간운영의 외부 효과를 주입검사만으로 확인했다고 쓰지 않는다. 자동 backup UI는 추가하지 않았고 SQLite API의 QA fixture backup/restore만 검사했다. 과거 자료의 권리·동의 적합성은 자동검사로 확정하지 않는다.

자원 한도는 논리흐름32/GPU12+admission대기32/180초 deadline이다. 긴 생성은 선점하지 않아 뒤 요청이 늦어질 수 있다. 모호한 보충/대상·종료는 규칙·의미판정에 한계가 있고 모든 한국어와 동명이인 정확성을 보장하지 않는다. 완전앱재시작시미완료텍스트는재생하지 않으며 불명확HTTP결과의 exactly-once도보장하지 않는다.

후속 검증도 로컬 모의 환경에서 진행한다. 사용자에게 실서버 조작을 요청하지 않는다. 장시간 대표 부하 관찰과 모의 장애·격리·복구 검사를 이어가며, 실제 Discord 외부 효과는 범위 밖 미검증으로 유지한다.

## 2026-10-19 — companion 통합 QA

- 코드 완료: 공통 별칭/RAM 발췌/관계/선택적 장기 기억/만료/본인 자연어 예약·소유자 관리. 자동 기억 OFF, weights 보존.
- 단위·통합: 전체328검사 OK20.504초. 실제 SQLite 재시작·DST·수정경쟁·격리·삭제 부활 차단·200예약, 모의 Discord·GPU busy 독립, 숨긴 Tk DPI 경계 포함.
- 실제 GPU: 개발72턴, 이름 독립36사례. 세 모드 기억 재시작 A/B3/3 사실 반영. 기본/개인 다중 화자 누락은 남는다. 출력이 다른 경로 latency를 동일 품질 속도 개선으로 주장하지 않는다.
- 실제 Discord: 허용 테스트 채널 수신/확인/알림 각각1. 실제 GPU 중 예정+1.936초, API1.312초. 사용자1회 도착 확인. 원래 설정 불변, QA 종료 정리. 초기 채널 불일치·수신0 시도도 기록했다.
- 실제 Windows 사용자 화면·장시간 soak·블라인드 말투 평가는 미완료. 운영 릴리즈 승인 및 새 모델 최종 선정 보류.

세부 수치·방법·다음 검증은 [COMPANION-MEMORY-REMINDERS](COMPANION-MEMORY-REMINDERS.md). private 원본은 local_data/companion-qa-20261019/이며 공개 문서에 응답 원문/계정 ID/개인 경로를 쓰지 않는다.

## 추가 범위 — 성인 유머·성별·지속 대화 (2026-10-19)

자동 판정 추가 검토: 정상166응답 전부 만점이었으나, 같은 판정기의 사전 고정 대조6개 중 기대 기준 일치는3개(부정 대조 검출2/5)였다. 따라서 자동 점수는 모델 선정/품질 동등성 근거에서 제외한다. GGUF 승격은 보류하고 사람 블라인드 평가를 남긴다. 세부 결과는 ADULT-MODE-QA를 따른다.

공통 성별/서명 마이그레이션, 세 모델 선택, 준비 중 최신 이벤트 보류, 실패 복구, 연령 제한 재검사, 의미 기반 대화 지속을 구현했다. 세 번째 선택은 기본 Gemma 4+정책 대안이며 GGUF 실사용 승격은 보류한다. GPU 비교·합성 Discord·사람 평가·실제 서버 상태는 [ADULT-MODE-QA](ADULT-MODE-QA.md)의 최신 결과를 기준으로 한다. 이전 테스트 수/모델 수는 당시 기록이다. 화면 자동 조작은 계속 비활성이다.

## 2026-10-19 추가 — 콘솔 창 회귀

GPU health 및 초기 설정 보조 명령에 CREATE_NO_WINDOW, stdout/stderr 수집, timeout을 적용했다. Windows에서 실제 Python 자식의 GetConsoleWindow=0과 출력 수집을 확인하는 테스트 및 GPU 과열/조회 timeout 안전 중단 회귀를 추가했다. EchoMate.vbs /check로 실제 WSH 파서를 실행하되 앱/대화상자를 열지 않는다. 시작/응답의 화면 관찰 검증과 구분한다. .cmd 실행 자체의 최초 콘솔은 OS 동작이므로 완전 무콘솔 시작은 .vbs로 안내한다.

현재는 개발 후보이며 릴리즈/개인 말투 모델의 최종 승인은 보류한다. 기존 r8 q/k/v/o60과 설정/비공개 실험을 보존했다. 추가 학습·실험 시각 활성화·제거한 송신 기능 복원은 하지 않았다.

| 항목 | 구현 및 모의 검증 | 이번 실제 검증 | 남음 |
|---|---|---|---|
| 멘션/직접 답장/무멘션 지속 | 기존 회귀 유지 | 이전 실서버 송신 이력만 보존 | 최신 실서버 다중 화자 품질 |
| 범위/상속/침묵/소유자 권한 | 회귀 통과 | 새 실계정 시험 없음 | 다른 계정·권한 변경 QA |
| 새 메시지/설정/삭제/보관 취소·중복 | 모의 통합 통과 | 새 장애 주입 없음 | 실제 재연결·HTTP 불확실성 |
| Unicode/기본 스티커 | SDK mock/정책 회귀 | 과거 Unicode API 성공 | 실제 기본 스티커 송신 |
| GPU | 기존 모델22회 반복 | TF32 A/B 완료 | 장시간 부하·실채팅 E2E |
| 진단/종료/저장 | 실패 주입 회귀 통과 | 실제 디스크 고갈 미실시 | 장시간 누수/종료 QA |
| Windows 앱 | Tk 합성 화면/목록/배선 통과 | 선택·미저장·성격 화면 관찰 | DPI/접근성/전체 종료 흐름 |
| 활동 목록 필터 | 실행/정지/전체 보기·상속·차단 통과 | 실제 조작 미검증 | 새 버전 앱 수동 확인 |
| 서버별 봇 이름 | 서명 저장·격리·SDK 자기 Member 호출·호격 판단 통과 | 실제 닉네임 API 변경 없음 | 권한/호칭 오인률/정정 |

전체 기준260테스트 통과 후 안정화267개, 이름/목록 통합274개 통과. 단위/모의 통합/Windows Tk 실제 위젯 생성 테스트이며 실제 Discord 전체 QA 성공을 의미하지 않는다. 예외 본문/실제 메시지/인증정보는 보고서에 넣지 않았다.

## GPU 비교와 제한

같은 합성 입력·모델·어댑터·greedy·max384. 상황별 warmup1회 제외 후 A/B각5회, 교차 순서. A 기존 TF32=false, B=true. p50/p90/p95는 정렬값 선형 보간.

| 상황/설정 | p50 | p90 | p95 | 토큰 | 생성 tokens/sec p50 |
|---|---:|---:|---:|---:|---:|
| 잡담 A | 4.968초 | 5.287초 | 5.300초 | 27 | 5.504 |
| 잡담 B | 5.141초 | 5.325초 | 5.335초 | 27 | 5.300 |
| 기술 A | 36.204초 | 37.872초 | 38.381초 | 208 | 5.753 |
| 기술 B | 36.282초 | 38.647초 | 39.268초 | 209 | 5.773 |

TF32 이득이 없어 기본값을 유지한다. 기술 응답은 A/B hash가 다르며 동일 설정 반복은 일관됐다. 전체22호출 생성 종료 토큰 확인, 이 스크립트의 GPU 오류0건. 정확성/자연스러움의 사람 평가는 하지 않았고 재생성 정책을 우회한 직접 backend 측정이므로 재생성률0이라는 운영 주장은 하지 않는다.

warmup 제외 peak allocated7731.4MiB/reserved7878MiB, RAM working set 약1869~1871MiB. 첫 host stopping callback p50 약0.422~0.437초이며 동기화된 GPU TTFT/Discord 표시 시간은 아니다. 생성 이후 약5~6토큰/초 구간이 지연의 대부분이다. 시계 해상도 아래 준비/queue 시간은0으로 기록될 수 있다. 출력 축소나 정확성 손실을 통한 속도 개선을 주장하지 않는다. 단일 PC/소표본/백그라운드 작업 및 짧은 실행이므로 p95·누수·오류율의 일반화 한계가 있다.

## 진단과 재현

- private 원본: `local_data/release-qa-20261019/`의 preservation/baseline/tests/GPU manifest/results/summary. 개인 모델과 출력은 업로드하지 않는다.
- 운영: `local_data/bot/telemetry.json`의 최대1000요청 숫자/단계/call, worker 최대200개. permissions/catalog/send span은 상위 단계와 겹친다. 성공 송신만 응답 분포에 포함하고 침묵/실패/취소는 별도 계수한다. ingest 전 차단된 이벤트는 요청 표본에 포함하지 않는다.
- `진행 상황 → 개인정보 없는 진단 저장`: 숫자 집계/코드만 내보낸다. 아직 실행하지 않았거나 봇을 끈 뒤에는 현재 요청 집계가 비어 있다.
- `PYTHONPATH=src` 설정 후 `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`, `-m compileall -q src/echomate_bot`.
- GPU 재측정은 앱/봇을 먼저 종료하고 충분한 VRAM을 확보한 뒤 `tools/verify_release_performance.py --output local_data/<새 실험 폴더> --repeats 5`. 이 도구는 Discord 연결/송신/학습을 하지 않는다.
- 실제 사용자 검증은 TESTING-DISCORD-APP 최신 절부터 진행한다. 허용 테스트 서버만 사용하며 운영 서버에 임의 송신하지 않는다.

## 중단·남은 조치

Windows 화면 자동 조작은 도구가 물리 Escape 중단을 두 차례 보고해 멈췄다. 사용자 최신 요청에 따라 앞으로 컴퓨터 화면/마우스/키보드 자동 조작은 사용하지 않는다. 전역 제품 권한 설정을 변경했다고 주장하지 않는다. 파일 편집/명령 기반 테스트와 사용자의 수동 앱/Discord QA를 사용한다. 실제 UI 전체 흐름·이름/호칭·기본 스티커·비소유자/재연결/장시간 시험이 끝나기 전 릴리즈 완료로 표시하지 않는다.


최종 보존 검사: 기존 private1234파일 누락0, runtime.lock 실행 메타데이터만 갱신됐고 나머지1233파일의 크기/mtime는 보존됐다. 원래 모델 선택 persona, 자동 기억/실험 시각 OFF를 읽기 확인했으며 설정·운영DB·weights를 변경하지 않았다. 환경은 torch2.9.1+cu128/transformers5.20.1/peft0.21.2/discord.py2.7.1/tzdata2026.5다. 상세 inventory/로그는 private에만 보관한다.


### 추가 — 네트워크 없는 SDK 통합 검사

실제 discord.py2.7.1 객체와 운영 on_message/Runtime/Transport를 사용하고 HTTP 경계만 메모리로 대체한 test_discord_simulator.py 4검사를 추가했다. 원본 reply/nonce/멘션 억제, 채널·봇 차단, 스레드 권한·Unicode/기본 스티커, NotFound/Forbidden을 검사한다. HTTPClient.request는 실패하도록 차단했으며 로그인·토큰·슬래시 sync·실제 송신은 없다. 제한 환경의 Windows 비동기 루프 대기 시도는 중단·기록했고 정상 실행은 sdk-simulator-2.log의 4검사 OK0.372초다. 외부 Discord rate-limit/서버 전달은 모의 검증과 구분한다.
