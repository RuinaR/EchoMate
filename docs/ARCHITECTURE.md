# 아키텍처

## 2026-10-19 로더·해제 수명주기 후속

실제 로딩 계측에 따라 파일 COW 예약 외 준비 reserve를 admission에 반영하며 최초 process private 기준을 backend 수명 동안 보존해 import/재로딩 이중 계산을 막는다. 단일 worker drain 후 모델 참조/traceback을 해제하고, 초기화된 CUDA에서만 synchronize → capability 확인한 cuBLAS workspace 정리 → allocator empty_cache를 수행한다. 일반 생성마다 workspace를 지우지 않으며 실패 cleanup은 원래 오류와 안전 비활성 상태를 보존한다. no-LoRA/복구/생성 중 전환/Portable 실제 미리보기 검증과 남은 청자 품질 차단은 [재개 QA](RESUMED-GPU-QA.md)를 따른다.

## 2026-10-19 모델·캐릭터 분리 및 일반 배포 — 최신 기준

시작 HEAD/원격5249fd2·clean을 확인했다. 공식 기본 Gemma4 12B 하나와 독립 캐릭터를 사용하며 기존 persona/adult 고정 UI·기본 LoRA 의존을 제거한다. 이전 서명 설정은 검증 후 base로 읽고 기존 가중치/자료는 삭제하지 않는다. 성인 유머는 별도 기본OFF 정책이다. 로컬 모델/HF 캐시 탐색·호환성 검사·전환/복구, 프로필 서명 저장·편집·미리보기, GUI 첫 설정/Windows DPAPI와 Portable 런타임을 구현했다. 기존 개인정보 동의/기억/관계/요약/알림/검색/공정 큐/Unicode 반응/원본 reply를 유지한다.

청자 무공백 호격·2인칭/맞장구를 분리한 GPU 개발 재검45/46, 오개입1·누락0이었다. 추가 제외 근거를 검증기에 넣었지만 공식 no-LoRA 로더의 독립20문항은 Windows commit 부족1455로 실행을 마치지 못했다. 실제 캐릭터 생성/전체 지연 A/B·깨끗한 Windows VM·실제 Discord는 미검증이며 전체 릴리즈는 **BLOCKED**다. 이전 세 모델 QA와 숫자를 최신 구조의 성공으로 재사용하지 않는다. 사용자 데스크톱/실제 Discord 접속을 수행하지 않았다.

[모델](MODEL-REGISTRY.md) · [캐릭터](CHARACTER-PROFILES.md) · [설치](USER-INSTALLATION.md) · [배포 QA·실패·마감](DISTRIBUTION-QA.md) · [전체 지연](PERFORMANCE-PIPELINE.md). 아래 이전 차수보다 이 절을 우선한다.

## 2026-10-19 사회적 청자·대화 상대 — 현재 기준

허용/권한/실제 이벤트→MemberDirectory 역할 근거→SocialRouter 분리 후보→필요 시 단일 공통 base 의미 판정→애플리케이션 청자/관계/응답 자격 검증→기존 행동·기억/검색·생성→최신 source/권한/중복 검증→송신으로 처리한다. 시간은 만료/정리/부하/기한/스팸/쿨다운에만 쓰고 청자 판정 입력/후보 우선 순위에 넣지 않는다. 새 임시 요청은 확인 전 기존 대화에 섞지 않으며 완료 sibling만 정리한다. 새 DB 스키마/추가 모델/학습은 없다.

[설계와 경계](SOCIAL-ROUTING.md) · [검증·실패·재현](SOCIAL-ROUTING-QA.md). 아래 이전 차수 기록보다 이 절을 우선한다.

## 2026-10-19 후속 릴리즈 — 현재 기준

runtime→ledger는 무상한 원자 예약·중복/간격·관찰 통계를 담당한다. safe_web/web_research는 공개 HTTPS/DNS 검증과 원문 근거 검사를 분리하며, 로컬 유한 라벨 도구는 필요할 때만 호출한다. summarization/summary_store는 실제 RAM 턴→동의 버전 재검사→출처 인덱스가 있는30일 압축 기록을 담당한다. 자동 요약은 priority3·유휴 시점·새 입력 취소이며 단일 GPU와 알림 이벤트 루프를 분리한다. CompanionStore 스키마6은 기존 자료를 보존하는 추가 마이그레이션이다.

상세 변경·검증·실패·재현 명령: [후속 릴리즈 QA](FOLLOWUP-RELEASE-QA.md). 아래 이전 날짜/차수 기록은 당시 상태이며 최신 안내를 대체하지 않는다.

## 2026-10-19 최신 — 개인정보와 실행 경계

[릴리즈 후보 감사](RELEASE-CANDIDATE.md)·[개인정보 명령](PRIVACY-COMMANDS.md)을 따른다. Discord 입력→허용/권한/일일 budget→회원/대화 라우팅→공정 큐→의미/행동→필요 기억·공식 근거→생성→코드/URL/행동 검증→최신 권한·원본 검증→예약/전송으로 처리한다. 확정 코드 작성/반응·지원 버전 조회는 텍스트 GPU 호출을 생략한다. 전송 직전 강제 권한 확인은 짧은 중간 캐시와 구분한다.

ConsentPanel은 자기 ID만 다루고 PrivacyStore v5가 독립 세 범주와 시각/버전을 저장한다. 자동·관리 쓰기에서 동의를 재검사한다. Windows Controller는 Gateway 없이 로컬 DB를 조회하며 요청 번호로 오래된 결과를 배제한다. 요약은 본인 개인 발췌이며 다자 발언의 추상 요약이 아니다. 실험 시각 분석 기본 OFF는 유지하고 스티커/미디어 출력은 결정적으로 거부한다. research는 사용자 텍스트를 전송하지 않는 고정 공식 버전 API5개만 제공한다. 작업 모니터의 ID·단계는 소유자 RAM UI에만, 일반 진단에는 원문/토큰을 넣지 않는다.

## 2026-10-19 최신 — 구성원 근거 계층

Discord 어댑터는 관측된 작성자/멘션의 이름과 같은 채널의 실제 reply 작성자만 Event에 실어 보낸다. 범위·권한 이후 Runtime.member_evidence→MemberDirectory가 speaker/addressee/실제 언급/원본 답장/추정 후보를 분리한다. 봇 이름은 naming, 구성원 이름은 members로 분리하며 중복된 일반 호격 추측은 생산 의미 경로에서 제거했다. 명확한 타인 대화는 생성 없이 침묵하고 활성 lease만 해제하여 이후의 봇 후속 문맥은 보존한다.

불명확한 대상/발화행위/대화 연결은 기존 base 의미 모델이 판단한다. 구성원 판별을 위한 별도 GPU 분류기나 매 메시지 회원 조회는 추가하지 않는다. 승인된 별명의 미관측 대상만 제한 조회한다. 로컬 CompanionStore 스키마4의 별명 근거는 서버+출처 채널에 격리하며 소유자만 확정/수정/삭제한다. 추정 ID는 신원 권한으로 쓰지 않는다. 작성자/대화 FIFO, GPU 큐, 실제 원본 reply, 개인 기억·친밀도·예약 경계는 유지한다. [상세](MEMBER-ADDRESSING.md).


## 2026-10-19 — 의미 중심 참여·명확한 호칭·기분 표현 개선

결정적 호칭 계층(naming.name_address)과 로컬 의미 계층(dialogue_intent/LocalBackend.assess_dialogue)을 분리했다. 설정/계정/서버 표시 이름·별명의 제한된 호칭 형태와 실제 멘션/reply만 직접 초대를 부여한다. 제3자/인용/알려진 동명이인은 구별하고, 충돌은 호출된 형태에만 적용한다.

발화행위·수신자·new/continue/end·반응 가치를 유한 라벨로 판정한다. 실제 대화는 분류기의 대화 역할과 섞지 않고 JSON 자료로 넘기며 화자/직전 응답 수신자 메타데이터를 함께 제공한다. 일반 경로는 한 번, 애매한 이름 언급/진행 대화의 거절된 후속만 작은 수신자 재확인을 한다. group_continue는 봇의 현재 행동/답변에 대한 그룹 반응이고, 다른 사람에게 봇 정보를 묻는 것과 다르다.

새 화자의 단독 확정 호출은 유일한 진행 대화에 합류한다. 일반 합류 후보는 승인 전까지 별도 상태로 두고, 실제 source 발언만 병합한다. 작성자 FIFO 뒤 최신 공유 잠금을 선택하고, 후보가 판정 중 바뀌면 stale_context로 보호한다. 기다리던 이름 호출은 연결 여부만 판정할 수 있고 초대 자체는 거절하지 못한다. 원본 reply/nonce와 단일 GPU 스케줄러는 유지한다.

거절된 옆 대화는 문맥 삭제 없이 활성 집계에서 내린다. 이후 근거 있는 후속을 신규 자율 쿨타임으로 버리지 않는다. 합류 후보의 자동 기억은 최종 flow ID 뒤 큐에 넣는다. 소유자/동의·기억/친밀도·예약·반응/기본 스티커 경계는 유지한다.

기분은 모델/성별과 독립인 생성 설정이다. 첫 반응·어휘·리듬을 지시하지만 사실/보안/필수 설명보다 우선하지 않는다. 알려진 채널 혼입·자모 검사 실패의 재생성은 합계 최대1회이며 보호 검사는 유지한다. 일반 로그에는 원문/토큰/ID 대신 단계별 이유 코드만 둔다. 앱 진행 상황은 최근 판단을 표시한다. 상세 경계와 실행 증거는 [SEMANTIC-ROUTING](SEMANTIC-ROUTING.md)를 따른다.


## 다중 대화와 GPU admission (2026-10-19)

Runtime은 physical channel과 논리 flow 키를 구별한다. Conversations는 guild/channel/thread·conversation ID·participants·source/reply·topic·last bot·상호작용/종료 상태를 RAM에서 보관한다. 최초 channel 키 호환을 유지하되 추가 흐름은 독립 DialogueState/task/version을 가진다. 실제 reply에 따른 공유 흐름만 실제 발언을 ID로 병합한다.

고정 잠금 순서: 작성자 FIFO→공유 대화 FIFO→GPUScheduler→기존 단일 executor→채널 송신 잠금. 다른 사람/독립 요청이 채널 전체 생성을 취소하지 않는다. priority0/1/2/3와5초 aging, GPU 용량12/user4/channel8, bounded admission32, 논리 흐름32,180초 deadline을 사용한다. 강제 GPU 선점·모델 중복 로딩은 없다. 포화 시 직접 요청은 deadline 내 capacity를 기다리며 무제한 보존을 보장하지 않는다.

활성 수는 실제 참여/최근 상호작용/미완료/종료/휴지로 집계한다. 자율 진입만 같은 범위 활성·범위별 idle cooldown·다른 활성 수와 큐 부하를 적용하며 다른 범위 전역 차단은 하지 않는다. 직접/지속 경로와 원문 중복·용량 제한을 구별한다. 네트워크 일시 끊김은 RAM 보류, 이미 ledger 선점한 불명확 송신은 재생하지 않는다. 앱 완전 재시작은 텍스트 작업을 재생하지 않는다.

DB schema3의 memory_flows와 subject_consents는 기존 레코드를 보존하며 트랜잭션으로 추가한다. 작업 기억은 흐름에 한정, 본인 명시 조회/취향 등은 사용자 사실 범위로 구별한다. 소유자 전체 설정으로 타인 자동 저장 동의를 대체하지 않는다. 상세/가드/실제 검증은 PARALLEL-CONVERSATIONS 참조.

## 공통 companion 계층 (2026-10-19)

Runtime→routing/context→선택적 memory_context→기존 단일 LocalBackend 순서다. private_request는 코드 해석/SQLite commit 후 GPU 없이 확인한다. background companion worker는 source revision/scope를 확인하며 만료/관계/메모리 저장을 수행한다. scheduler는 별도 task로 GPU 큐와 쿨다운을 기다리지 않는다. 선점 트랜잭션에서 최신 예약을 읽고 HTTP 직전 설정·권한·대상을 확인한다. 불명확한 전송은 앱 재시도하지 않는다.

CompanionStore는 per-connection SQLite/WAL과 서버·사용자·출처 채널 격리, tombstone/cutoff·opt-out, 만료 즉시 조회 제외, 상태별 보존을 제공한다. 소유자 Windows 관리와 본인 자료 삭제 권한을 구별한다. UI 목록은 별도 비동기 조회로 갱신하며 진단에는 본문을 넣지 않는다. RAM 발췌는 사실 생성 요약이 아니며 모델 weights에 자동 학습하지 않는다. 상세: [COMPANION-MEMORY-REMINDERS](COMPANION-MEMORY-REMINDERS.md).

## 성인 유머·성별·공통 지속 대화 경계 (2026-10-19)

adult_policy.py는 일반 모델/정책 대안의 turn_profile과 제한된 경계 검사를 제공한다. model=adult는 현재 동일 Transformers 기반 모델의 정책 모드이며 실제 job weight는 base다. GGUFProbe는 평가 전용 별도 프로세스/loopback 인증 HTTP/직렬 lock/취소·종료를 사용하고 개인 PEFT를 로드하지 않는다. 앱에 검증 안 된 GGUF를 자동 연결하지 않는다. 준비·승격 기준과 자원 실험은 ADULT-MODE-QA 참조.

설정 DEFAULTS에 gender=neutral을 추가한다. 기존 HMAC 검증을 먼저 수행한 후 누락 필드만 보충한다. 성별과 기분/성격/활동/모델은 독립이다. Runtime.switch_model은 소유자 검사→changing_model→기존 작업 취소/worker 완료→prepare_mode→선택 저장 순서이며 실패 시 이전 설정을 유지한다. 이 단계의 세 선택지는 같은 기본 가중치라 두 번째12B를 적재하지 않는다. 준비 중의 새 이벤트는 bounded 상태에 실제 화자/메시지로 보류하며 재개 전 최신 상태/범위를 재검사한다.

지속 참여의 신규 확률 재적용을 금지하고, 실제 대상/주제 증거와 유용성/개입 적절성을 사용한다. 새 질문이 봇에게 향하면 주제 변경만으로 신규 확률을 뽑지 않는다. 경과 시간만으로 대화를 종료하지 않으며 engagement_seconds는 최소1시간/최대24시간의 메모리 보관 보조 값이다. 실제 이력은100턴/최대32채널 등 기존 제한을 유지한다. fresh는 권한/NSFW REST await가 끝난 뒤 버전/서명 revision을 다시 검사한다.

check_resources는 Torch를 가져오지 않는 공통 온도/VRAM/RAM 안전 검사다. GPU/OS 상태 조회는 창을 숨기고 timeout을 둔다. 평가용 GGUF 서버는 시작/HTTP 요청150초, 정상 종료 대기15초 제한을 사용한다. 엔진 교체는 CUDA 잔여 메모리를 피하도록 자식 프로세스 완전 종료 뒤 다음 엔진을 실행하며 각 자식이 InstanceLease를 소유한다. GUI destroy는 예약 poll/콜백/폰트 참조를 UI 스레드에서 정리한다. 테스트에서 발견한 Tcl 다른 스레드 GC 종료를 회귀 대상으로 남긴다.

## 백그라운드 프로세스와 무콘솔 진입점 (2026-10-19)

processes.background_options는 Windows에서만 CREATE_NO_WINDOW를 제공한다. pythonw 자식인 nvidia-smi와 초기 설정 whoami/icacls에 적용하며 shell=True를 쓰지 않는다. GPU/ACL 조회의 timeout과 실패 전파는 유지한다. EchoMate.vbs는 자신의 위치에서 pythonw를 직접 실행한다. 환경/작업 경로는 실행 시 구하며 소유자/토큰/개인 경로는 스크립트에 넣지 않는다. /check는 파일 존재와 VBS 구문만 검증하고 앱을 열지 않는다. 기존 .cmd/PowerShell 진입점은 호환용으로 보존한다.

## 2026-10-19 추가 경계 — 서버별 이름·활동 목록·계측

`naming.py`는 2~32자 이름 검증/서버별 조회/호격 후보만 담당한다. signed guild에 optional name을 추가하며 기존 3필드 guild와 호환한다. Runtime은 configured_bot_name을 실제 발언이 아닌 이벤트 메타데이터로 전달한다. 이름 후보는 참여/대상 의미 평가 후에만 직접 응답 경로로 진입한다. 캐릭터 지침은 해당 서버의 별명과 오인 정정 방식을 제공한다. 이름은 식별자·권한 근거가 아니다. 실제 nickname 수정은 discord.py 자기 Member.edit만 사용하며 설정 변경/재연결 시 적용한다.

GUI 실행 중 목록은 기존 scope 해석기를 사용해 상속과 차단을 그대로 반영한다. REST/실시간 스냅샷의 thread parent ID는 메모리에서만 사용한다. 전체 목록 전환은 보기 상태이며 설정 권한을 바꾸지 않는다.

telemetry의 ContextVar는 단일 GPU executor에 copy_context로 전파한다. monotonic 기반 단계 시간과 worker 대기/준비/첫 stopping callback/생성 속도/VRAM/working-set RAM만 기록한다. 호스트 첫 callback은 GPU 동기화된 첫 토큰/Discord 표시 시간의 정확한 측정과 다르다. 저장은 별도 thread+순차 lock, 보관 1000요청/worker200개. 단계 총계와 permissions/catalog/send 하위 span은 겹치므로 합산하지 않는다. 실패한 worker는 요청 trace에 남고 성공 지연 분포에서 취소/침묵은 제외한다. 본문/이름/Discord ID/프롬프트/토큰 내용은 계측에 넣지 않는다.

CLI/GUI는 진단 파일 쓰기보다 자원 종료를 먼저 수행한다. GUI 종료는 controller main task와 inventory 작업을 정리하고 lease를 반환한다. lifecycle lock은 start/stop/shutdown/name 작업의 경쟁을 막는다. 이 변경의 실제 종료·장시간 안정성 승인은 RELEASE-QA를 따른다.

## 현재: 다크 앱·기본 에셋·실험 분석

최종 UX는 5개 화면이며 앱을 자동 재실행하지 않는다. GUI 시작은 응답 허용과 함께 동작하고, 일시정지는 현재 작업만 취소해 실제 이력을 보존하며 새 메시지는 받지 않는다. 종료는 연결/모델/이력을 정리한다. 실제 이력에서 확인한 bot message의 reply_to도 명시적 요청으로 취급해 끼어들기 투표 없이 생성한다. 작성 중 표시는 별도 비동기 작업으로 보내며 최종 텍스트 검증 전 부분 출력은 송신하지 않는다. 취소/완료 시 표시 갱신 작업도 종료한다.

`desktop_ui.py`의 Canvas 컨트롤과 `desktop.py`의 controller를 분리한다. 모델/Gateway를 시작하지 않아도 공식 Bot REST로 초대 서버·텍스트/포럼 채널·접근 가능한 활성 스레드 메타데이터를 읽는다. 내용/이미지는 수집하지 않는다. GUI의 소유자 적용으로만 범위를 활성화하며 실행기는 실제 길드/권한/최신 상태를 재확인한다. 목록은 Ctrl 다중 선택/휠/키보드로 조작한다.

등록 미디어 모듈은 제거했다. MEDIA/TEXT_MEDIA 구형 제안은 호환 파서가 읽더라도 검증기에서 거절하며 명령/파일 송신 경로는 없다. 정상 출력은 SILENCE/TEXT/REACTION/TEXT_REACTION/STICKER. 반응은 Unicode, 스티커는 공식 StandardSticker 객체만 허용한다. 기본 스티커 공식 팩 설명/태그는 관측 메타데이터이고 실제 픽셀 증거가 아니다. 시각 분석은 기본 OFF인 실험 vision 토글에만 있으며, ON도 커스텀 송신을 허용하지 않는다. 서명 검증 후 asset_policy=2로 이전 설정을 마이그레이션한다.

명시적 멘션에는 끼어들기 판단을 생략해 1회 TEXT 생성이 가능하다. 안전 지침/출력/권한 검증은 유지하며 무멘션은 합친 참여·지속 판단을 사용한다. 미응답 멘션의 원래 메시지 ID와 최신 문맥 이벤트 ID를 분리해 답장 대상/취소·중복 검증을 함께 유지한다. [DESKTOP-UI](DESKTOP-UI.md) 참조.

## 이전 1차 GUI 구조 기록 — 등록 미디어 제거 전

`desktop.py`는 Tk 메인 스레드, Discord asyncio 별도 스레드, 기존 단일 GPU executor를 연결한다. GUI는 큐로 받은 상태 사본만 읽고, 모든 설정 변경은 Discord loop에서 bootstrap 소유자 권한으로 검증·서명 저장한다. 공개 HTTP 관리 서버 없음. 로컬 권한 경계는 bootstrap ACL의 Windows 계정이며 원격 Discord owner ID 검사는 유지한다. `instance.py`의 OS 파일 잠금은 GUI/CLI 중복 모델 로드를 막는다.

기존 범위 스키마에 선택적 `reaction_mode`를 추가한다. 없으면 기존 모드를 유지하고, GUI 저장 시 텍스트/반응을 각각 명시한다. 기본 차단/명시적 스레드 상속/최종 행동별 차단은 유지한다. `assess_turn`의 5비트 의미 판단은 민감성/유용성/참여 적절성/봇 대상/주제 지속을 함께 반환한다. 유용한 TEXT에 승인 미디어/스티커 선택이 없으면 planner를 생략한다. 이 판단은 의미 정확성을 보장하는 규칙 점수가 아니다.

멘션/검증된 지속은 2초, 신규 참여는 설정한 쿨다운을 적용한다. 최신 상태/권한/서명 revision/일일 상한/중복 예약 검증은 그대로다. 실제 발언은 Turn.content, 시각·출력 관측은 Turn.context_metadata로 분리한다. 기분/활동 변경은 대화 이력을 유지하고 현재 생성만 취소한다. 범위 철회/연결 끊김은 관련 이력을 정리한다. 상태 화면에는 본문/토큰 없이 단계·경과·대기 수만 전달한다.

## 이전 초기 Bot 통합 구조 — 등록 미디어 제거 전

`src/echomate_bot/`은 추론 전용 실행 패키지다. 기존 `echomate_studio`의 DialogueState/참여 판단/멘션 검사/engagement/assessment schema를 가져오되 Studio 학습·데이터 import·실험 도구는 Bot에서 호출하지 않는다. 이전 오프라인 평가 코드는 수정하지 않는다.

- `settings.py`: 로컬 bootstrap의 소유자 ID/서명 키는 mutable 설정과 분리. 설정 HMAC/스키마 검사·원자 저장, 서버/채널/스레드 allowlist와 명시적 상속. 같은 OS 계정은 신뢰 경계.
- `character.py`: 가중치를 수정하지 않는 성격/기분 지침, 자모 표현 검사 후 최대 1회 재생성. 인용/코드/URL을 삭제하지 않는다. 자동 연출은 소유자 옵션이며 단순 축하/휴식 표현에만 제한한다.
- `inference.py`: 단일 GPU executor/최대12 대기, 읽기 전용 NF4/BF16 Gemma+보존된 rank8-60. base/persona 전환으로 중복 로딩 방지. 공식 Gateway 전 모델 준비, 이후 worker 추론. token 단위 취소와 주기적 온도/VRAM/RAM 검사, OOM 안전 정지, 채널 제어/미완결 fail closed. 사용자 지정 모델 코드를 실행하지 않는다.
- `vision.py`: HTTPS Discord CDN/프록시·공인 DNS·redirect 금지·바이트/픽셀/프레임 제한 → Pillow raster/여러 프레임 → 실제 기본 가중치 분석 → 엄격한 구조화 결과 → guild+asset+내용hash+분석버전 캐시. 이름은 시각 증거가 아니다. 소유자 승인 미디어 저장소와 분리한다.
- `media.py`: 소유자가 승인한 바이트를 private library로 복사, 실제 분석/해시/서명된 승인 정보/서버 범위/파일별 쿨다운 관리. 받은 미디어의 cache 엔트리만으로 송신할 수 없다.
- `runtime.py`: bounded 채널 상태/중복 수신 → 기존 맥락·멘션/지속/신규 참여 게이트 → 허용 시 비동기 이미지 분석 → 구조화 행동 제안 → 텍스트 생성 → 최신 설정/권한/상태와 카탈로그 재검사 → 영속 예약/빈도 제한 → 전송. 새 메시지/설정 변경은 취소, 애매한 실패는 재전송하지 않는다. 본문 없는 진단 코드만 제한된 로컬 로그에 남긴다.
- `actions.py`/`discord_app.py`: AI가 API를 호출하지 못하도록 분리한 결정적 행동 검증과 공식 discord.py 실행. SILENCE/TEXT/REACTION/TEXT_REACTION/STICKER/MEDIA/TEXT_MEDIA. 소유자 검사와 ephemeral 관리 UI, 최소 Intents, 멤버십 REST 재확인, 전송 직전 재검사, nonce, 삭제/보관/재연결 상태 정리. text+reaction은 원자적이지 않다.

과거 Unicode 전용/관리자 권한 허용 계획은 최신 사용자 요구에 따라 변경했다. 관리자는 소유자 ID와 일치하지 않으면 설정을 바꿀 수 없다. 서버 전용 에셋은 현재 서버 내에서만 사용한다. 실제 Discord 운영 품질/권한/장기 안정성은 모의 테스트나 합성 이미지 성공으로 선언하지 않는다. 현재 사용법/미지원 사항은 DISCORD-BOT, GPU 근거는 ML-EXPERIMENTS 참조.

## 2026-10-18 최신 ML 실행 경계

추가 품질 단계: `src/echomate_studio/response_policy.py`는 응답 목적에 따른 지침과 선택적 train 집계 prior만 만든다. 발언 권한·멘션·침묵·상태/취소를 변경하지 않는다. `tools/persona_quality_v3.py`는 별도의 고정 pilot/holdout에서 가중치 × 정책 비교, 적용/masking GPU 진단, 동일 프롬프트 검사, 원자 진행 저장, 블라인드 평가를 수행한다. 자율 참여 문항만 기존 판단/참여 코어를 공통으로 호출하며 실제 송신은 없다. 기술/일상 가중치 라우팅 후보는 캐시된 동일 생성 결과로 평가한다. `tools/persona_memorization_probe.py`는 비공개 prefix 노출 진단이며 추론 안전성 보증이나 추가 학습이 아니다. 이 모든 경로는 오프라인 실험이며 기존 Ollama Bot 경로에 연결하지 않았다.

`tools/persona_experiments.py`: reviewed text-only 자료 → 누수/식별자 휴리스틱 검사 → 독립 스타일 예시 + 실제 Gemma 생성 prefix → 응답/turn 마스킹 loss → NF4/BF16 decoder LoRA → 로컬 체크포인트/상태 → 동일 조건 생성/블라인드 평가. `tools/persona_report.py`는 로컬 집계 대시보드만 작성한다. 상세 제한은 `ML-EXPERIMENTS.md`.

원문·체크포인트·optimizer/RNG·생성·블라인드 키는 저장소의 `local_data/` 하위 경계로 제한한다. HTTP/API 업로드·자동 모델 다운로드·클라우드 추적 없음. 봇의 참여/침묵/멘션/취소 정책과 학습/실험 도구는 분리하며 새 어댑터를 실행 봇에 자동 연결하지 않는다. 단일 화자 자료로 화자 관계 학습을 주장하지 않는다.

`tools/evaluate_persona_candidate.py`는 모델 가중치와 별개로 추론 정책 v1/v2를 명시하고 양쪽 모델에 동일 적용한다. 실패 분석에 쓴 최종 집합은 개발용으로 은퇴시키며 새 합성 집합을 분리한다. v2는 실제 실행 능력 한계와 절차 설명 완결성을 지시하는 오프라인 실험 설정이며, Bot에 연결된 검증 완료 출력 가드가 아니다. 생성 결과는 규칙 지표뿐 아니라 사람이 읽을 블라인드 Markdown/JSON과 별도 키로 보존한다.

## 데이터 흐름
사용 허가 검토 → N개 JSON 파일(각 파일 하나의 채널) 분석/출처 범위 분리 → 안전한 정규화/비식별화 → 스타일 통계/품질 평가 → 허용 시 예문 검색 또는 스타일 학습

지정 Discord 스레드 이벤트 → 권한/대상 확인 → 대화 상태 → 발언 판단기 → (페르소나 프로필 + 허용된 검색 사례 + 최근 대화) → 로컬 Ollama → 출력 검사/중복 방지 → Discord 전송 → 최소화된 로그

## 컴포넌트 경계
- `src/echomate/discord/`: 명령/이벤트, 스레드 경계, 닉네임 및 역할 동기화
- `src/echomate/persona/`: ID 기반 등록/선택/메타데이터, 추후 사용자별 LoRA
- `src/echomate/data/`: 패키지 구조 검사, 정규화, 개인정보 제거, 출처·허가 상태 검증
- `src/echomate/ai/`: Ollama 연결, 프롬프트, 응답 검증, 선택적 검색/LoRA
- `src/echomate/autonomy/`: 참여 결정, 쿨다운, 동시성, 침묵 및 제한
- `src/echomate/storage/`: 설정/상태/감사 로그(SQLite 예정)
- `tests/`: 단위·통합 테스트, 외부 API 모킹, 합성 샘플

## 로컬 운영 원칙
- Discord 통신만 외부 네트워크를 사용하고 LLM 추론은 로컬.
- 봇 토큰은 환경변수 또는 로컬 비밀 저장소. .env 커밋 금지.
- 명시된 guild_id/thread_id 외 읽기/쓰기 최소 권한.
- 명령 실행 권한은 서버 관리자/허용 사용자로 제한.
- 서버 닉네임 길이/권한 한계 및 동시 사용 페르소나 모델 고려.
- 메시지 수신과 AI 생성 작업을 비동기로 분리. 최신 대화에 대해 낡은 답변 전송을 방지.
- 장기 실행 시 메모리 상한/재접속/요청 timeout/취소 처리.

## 모델 실험
A: 기본 모델+간결한 스타일 프롬프트
B: A+허용된 예문 검색(RAG)
C: B+허용된 데이터로 QLoRA
사용 모델/프롬프트/학습 데이터 버전, 평가 분할, 추론 파라미터, 점수, VRAM, 지연을 기록. A보다 악화되면 C를 채택하지 않는다.

## 다중 채널 입력 계약
- 입력 JSON 1개 이상, 개수 제한 없음(현재 CLI `nargs='+'`).
- Studio는 파일별 통계와 채널 경계를 보존. 채널을 넘는 인접 메시지는 같은 발화로 묶지 않음.
- 향후 제작 과정에서는 동일 화자의 여러 채널 기록을 통합 평가할 수 있으나, 소스별 식별자·삭제·갱신 범위를 유지.

## 예정 디렉터리
```
src/echomate/{discord,persona,data,ai,autonomy,storage}/
tests/
docs/
configs/
local_data/                # ignored
models/                    # ignored
```

## 2026-10-18 개정 아키텍처
- 실행 경계: `EchoMate Bot` = Discord 공식 Bot Client + 모델 읽기 전용 Loader + Ollama + 스레드/채널 Allowlist + Autonomy Controller.
- 제작 경계: `EchoMate Studio` = 외부 백업 파일 Importer + 출처·허가 게이트 + 단일 화자별 학습 + 비교 평가 + immutable 아티팩트/캐시.
- 외부 DiscordChatExporter는 독립 도구이며 EchoMate가 수집을 자동 실행하지 않음.
- 세부: [DEPLOYMENT-SEPARATION.md](DEPLOYMENT-SEPARATION.md).

## 반응(reaction) 엔진
- 대화 텍스트 발언 제어기와 반응 엔진을 분리하고 각각 대상 채널/스레드 allowlist, 사용 여부, 빈도 제어를 독립 유지.
- Reaction Gate: 이벤트 중복/자기 메시지/다른 봇/opt-out/별도 allowlist/쿨다운/확률 검사 후 Unicode 기본 이모지만 선택.
- 실질적인 채팅 내용에 따른 이모지 선택은 추후 문맥 판단기로 추가; 현재 `reactions.py`는 선택 가능 여부와 기본 이모지 집합 결정만 담당.
- 실제 Discord API의 Add Reactions 권한, HTTP rate limit 준수, 반복 반응 방지 및 로그 테스트는 Bot 연결 단계에서 검증.

## 자율 발언 참여 결정 (2026-10-18)
- 참여 확률/활발함은 최종 발언을 강제하지 않고 이미 적격 판정된 기회에만 확률로 작동.
- ContextAssessment에서 민감한 분위기, 기여할 내용 존재, 끼어들기 적절 여부를 판정할 계획. 현재 `participation.py`는 외부 평가를 받는 순수 판정 게이트.
- 절대 차단 조건: 설정 중지, 비허용 채널/스레드, 봇 메시지, 사용자가 거부, 쿨다운, 지나친 침묵 상태, 민감 분위기, 기여할 내용 없음, 부적절한 개입.
- 실전 Discord 연결 시 입력 평가 신뢰성, 중복 이벤트 처리, 빈 답변, 지연/취소, LLM 평가 비용·속도 검증.

## 대화 연속성 상태 관리 (2026-10-18)
- `echomate_studio.dialogue_state.DialogueState`는 채널/스레드 경계별 bounded TTL 메시지 상태, 사용자 화자 라벨, 답장 참조를 유지.
- 채널별 메시지 버전(snapshot revision)을 기록하고 답변 생성 도중 새 메시지가 오면 이전 답변의 게시를 취소하는 토큰으로 사용.
- 중복 ID와 역순 도착 메시지를 무시하고 최근 기록을 전달(초기 구현; 실제 Discord 수신 순서 QA 필요).
- 첫 버전은 프로세스 메모리에만 보관하고 자동으로 장기 기록으로 저장하지 않음.
- 대화 흐름의 의미적 평가와 답장 대상 추적을 자동으로 추론하는 LLM 기반 assessor 및 실제 Bot 연결은 다음 단계.

## 32GB RAM 기준 단기 메모리 설정
- DialogueState 기본값: 채널/스레드별 500턴, 최근 86,400초(24시간). 생성 인자 `limit` 및 `max_age_seconds`로 변경 가능.
- 모델 전달용 `recent_context(..., max_chars=...)`: 오래된 원본 버퍼는 유지하면서 최신 항목 중심으로 문자 수 예산을 따로 적용. 기본 16,000자이며 토큰 단위 제한은 아직 아님.
- 메모리 사용량은 전체 활성 채널 수 및 발언 길이에 비례하며 VRAM 및 실제 모델 컨텍스트 창과 무관. 추후 토큰 추정/요약/메모리 안전상한과 휴면 채널 정리 필요.
