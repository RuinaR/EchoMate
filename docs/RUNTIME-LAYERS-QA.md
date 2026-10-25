# Runtime 판단 계층·의도·요약 근거 QA

후속 [의미 집중 QA](SEMANTIC-FOCUS-QA.md): 생성 단계 optional 발췌 예산·로컬 실행 안내·요약 동의 epoch/좁은 충돌 검사를 보강했다. 일반 복귀·자유 생성의 사실성은 해결 선언하지 않으며 아래 기록은 당시 범위로 보존한다.

후속 [봇 복귀 QA](BOT-RETURN-QA.md)에서 pending-human 관계/출처 버전·native 예산·제한 이름 호출 복귀를 보완했다. 아래는 해당 당시 기록이며 세 누락이 모두 해결됐다는 의미는 아니다. 7108은 정확한 원본 stack/입력이 없어 native 초과를 확정하지 않고, 8108은 보존 입력으로 확인했으며, 9108은 대상과 관계를 분리해 평가한다.

시작 main/origin `c2e6ced`, clean. Lime 단일 모델, 실제 Discord 미실행, 운영 자료 미변경. 장시간 검증은 **DEFERRED — USER REAL-WORLD TEST**다.

## 실제 호출 경로와 책임

| 단계 | 실제 재사용 경로 | 입력·결과·권한 경계 |
|---|---|---|
| 수신·통합 | Runtime.ingest/_ingest → member_evidence → utterances.offer → _ingest | 실제 Event·raw_parts·reply·발화자·채널·epoch. 조각 통합이 청자·쓰기 권한은 아님 |
| 대화 Router | conversations/social.packet → Runtime.social_route → SocialDecision → validate_social | 명시 멘션/reply/사람 대상 우선. 의미 target/relation/anchor/act/respond를 기존 타입으로 반환하고 검증. 실제 원본 reply와 참여자를 모델이 새로 만들지 못함 |
| 의도 Router | intent_router.IntentPlan → 기존 companion.request_kind/handle_request | CHAT/REQUEST/MENTION/CLARIFY/PROHIBITED·version·reason. 키워드는 후보일 뿐. 이 계획에는 DB·Discord 실행 API가 없음 |
| 읽기·기능 | subject_snapshot → 기존 memories/MemorySelection 및 companion → Receipt/ReadReceipt | 실제 권한·동의·시각·DB commit이 성공 근거. 이름은 읽기 전용 조립, 설정 변경은 Windows 관리자 경로 |
| 문맥·요약 | build_context / Summarizer / GGUFEngine native tokenizer | 원본·발화자·시간·source ID 유지. 요약은 추측 가능한 모델 산출물이며 장기 기억 승격 없음. native 텍스트·사회적 판단·기타 호출의 선택 계약 분리 |
| 응답 생성 | 기존 GGUFLocalBackend.text 및 선택적 response_pipeline | 확인된 상태 전달, 이름/조회 사실 안내와 기능 Receipt 응답을 재사용. 모델 자유 생성이 DB 변경의 권한이 되지 않음 |
| 출력·송신 | 기존 output_policy·action 검증 → fresh/delivery_current → transport.execute | source/조각/name·character epoch/동의/선택 기억/Receipt/요약 존재·설정 최신성 검사 후 SDK 송신. 기존 fair queue/취소/원본 reply/ledger 보존 |

새 거대 Runtime을 병행 구현하지 않았다. Conversation Router와 Response Generator의 기존 타입·함수·제어 흐름을 재사용하고, 의도 계획과 문맥 선택을 독립 모듈로 추출했다. `_process` orchestration이 모두 작은 클래스로 교체된 것은 아니며 구조 분리 자체를 의미 품질 PASS로 취급하지 않는다.

## 실제 수정

1. **기능 후보와 현재 실행 의도 분리.** 기존 명령 문법 위에 읽기 전용 IntentPlan을 두고, 전달/가정/단순 기능 언급은 실행하지 않는다. 명시 금지·불완전 요청·서로 다른 기능 혼합은 무실행 상태를 설명한다. 한정된 한국어 발화행위 계약이며 모든 조건/인용 의미를 이해한다는 뜻은 아니다. 여러 쓰기를 원자적으로 실행하는 복합 executor는 아직 없고, 다른 기능 두 개를 부분 실행하지 않고 요청 분리를 안내한다.
2. **읽기 질문과 실행 영수증의 선점 제거.** 명확한 이름/기억 질문과 예약이 한 메시지에 있어도 기존 grounded_reply로 작성 가능한 사실 안내를 기존 commit 응답과 함께 보낸다. 기억 질문이 있으면 실제 조회 동의·선택 상태를 별도로 확인한다. 조회 실패가 이미 확정된 예약 성공을 덮어쓰지 않는다. 알림 payload는 하나의 명시적 알림 절일 때만 분리하며 인용 내용은 보존한다. 기억 저장은 앞의 사실이 필요하므로 이 분리를 적용하지 않는다.
3. **현재 이야기의 요약 가로채기 수정.** 단순 오늘 사건/감정은 과거 복기 요청이 아니다. history_review로 읽기 목적의 후보를 좁히고 기존 의미 history classifier를 유지한다. 후보에서 빠졌다고 침묵하는 것이 아니라 일반 응답 생성으로 이어간다. 무구두점·더 복잡한 의도는 미완료다.
4. **요약 JSON 오류 경계.** null/배열/잘못된 item·kind·source 타입이 TypeError로 번지지 않고 ValueError로 거절된다. 실패 시 동의된 DB에 생성 요약을 쓰지 않고, fresh 상태의 본인 짧은 원문만 source ID·시간과 함께 RAM 응답으로 선택한다. 봇 호출 표기만 제외하며 원문을 중간 절단하지 않는다. 안전한 선택이 없으면 그 사실을 안내한다. 기존 save_digest의 모든 참여자 동의/version·source tombstone/삭제·채널/캐릭터 경계는 그대로다. 과거 GPU TypeError에는 스택이 없어 이 자료형 문제가 그때의 정확한 원인이었다고 확정하지 않는다.
5. **요약 권위와 native 예산.** 정상 생성 요약에도 source ID·모델 요약/미검증을 표시한다. evidence가 원문에 들어 있다는 검사는 paraphrase의 의미 보존까지 증명하지 못한다. 모든 비텍스트 호출도 native apply-template/tokenize로 계산하고, 사회적 판단만 기존 trim_frame의 최신 실제 bot/source·현재 reply pair를 보존해 오래된 비보호 발언을 제외한다. 현재/pending human/surrounding/후보 index·참여자는 보존한다. 요약 JSON이나 일반 사용자 JSON은 이 선택 정책을 켤 수 없으며 초과 시 거절한다. task-local ContextVar를 기존 scheduler가 복사하므로 전역 실행 모드를 늘리지 않았다. 고정2048·출력별 reserve·margin64·RAM/commit/VRAM 기준 불변이다.
6. **청자 이름 근거 누락.** social packet의 current에 관리자가 설정한 실제 봇 이름·NameVersion·CharacterEpoch를 읽기 전용으로 추가했다. 사람 청자·충돌·권한 규칙을 우회하는 초대 신호가 아니다. 새 User ID·참여자를 추정하지 않는다.

## 실제 Lime 능동 대화와 A/B

비공개 `local_data/runtime-layers-20261025/`에 원문·모델 호출·DB·SDK payload·trace를 보존했다. 루트/`followup`/`independent`에서 각각 **12개 합성 사용자 이벤트**를 직전 모델 응답을 읽고 선택했다. 도자기 실수→조언 거절/감정→농담→이름/예약→친구 전달→타인 간 대화→봇 복귀→시점/요약→취소, 새 등산 준비→농담에 대한 반론→불완전 요청→기억/예약→친구 전달→타인 reply→이름/관리자 변경→취소를 진행했다. 관리자 이름 변경1회와 native 계산 전용1회는 사용자 대화 턴에 세지 않는다. 테스트 숫자를 위한 반복 생성/장시간 부하는 하지 않았다.

각 이벤트에 동일 모델/생성 설정의 이전 Runtime과 새 Runtime을 순서대로 사용했다. 임시 v8 DB는 각각 분리했다. backend·token budget·요약 모듈은 당시 수정본을 공유하므로 c2e6ced 전체 바이너리의 엄밀한 이전/이후 비교가 아니라 **Runtime/명령 경로의 국소 A/B**다. independent 세션4번부터 이전 request_kind/request_plan/handle_request 세 함수를 함께 고정했고 그 전에는 이전 handler만 고정한 한계도 기록한다. source hash는 각 시작 보고서에 보존한다. 새로운 등산 상황은 이전 데이터의 재생이 아니지만 개발용 능동 시나리오이며 미사용 holdout 인증이 아니다. final316 소비0.

확인된 차이:

- 같은 오늘의 도자기 감정 발언에서 이전 Runtime은 기록/요약 부재 안내, 새 Runtime은 실제 기분·이야기를 묻는 응답으로 이어졌다.
- 이름 질문+예약: 이전은 예약만 답했고, 새 경로는 현재 하루라는 이름과 실제 예약 영수증을 함께 답했다. 기억 질문+예약에서는 미동의·미조회 사실과 실제 예약을 따로 답했다.
- 친구의 요청을 전달한 도자기·등산 사례에서 이전 DB는 불필요한 새 알림을 만들었고 새 DB는 만들지 않았다. 기존 정상 예약/목록/취소는 작동했다. 새 payload에는 혼합 이름 질문 대신 알림 절만 남았다.
- 새 등산 대화의 시각 없는 내일 요청에서 이전은 내일 다시 알려준다고 약속했지만 새 경로는 날짜/오전·오후 시각을 확인했다. 예약은 생성하지 않았다.
- 서로 다른 기능의 삭제+목록 혼합 요청은 이전이 한 기능만 선택해 답했고 새 경로는 부분 실행 없이 각 요청을 나누도록 안내했다. 완전한 복합 기능 실행을 구현한 것은 아니다.
- 테스트 관리자 경로 하루→유나 변경 성공 후, 일반 대화의 라임으로 되돌리라는 요구는 양쪽 모두 유나·Windows 관리자 변경 경계를 유지했다. 운영 이름 파일은 쓰지 않았다.

**청자 품질은 개선 완료가 아니다.** 세 세션에서 각 variant당 36이벤트 중 사람 대상6건 오개입0, 봇 호출/복귀 응답 누락3건이다. 양쪽 모두 동일하다. 각 세션9건씩 SDK mock 응답/원본 reply를 확인했다. 첫 두 세션의 호출 누락 각1건은 native 예산 거절, 등산1건은 실제 사람 간 미해결 질문/pending 경계가 bot_group/join 모델 판정을 veto한 결과다. 이를 정상 침묵이라고 재분류하지 않는다. 나머지 감정·농담·무권한 회상 표현의 자연스러움은 Codex 검토이며 사람 만족도 인증이 아니다.

**자유 생성 사실성도 미완료다.** 실제 예약이 있는데 모델이 설정된 것이 없다고 말하거나 친구의 전달을 기억하겠다고 표현했다. 뒤이어 직접 확인하면 정정하기도 했지만 처음 발언의 성공으로 세지 않는다. 실제 DB·Receipt는 오염되지 않았다. 범용 자연어 주장 추출기를 최종 판정자로 재도입하지 않았으며 일반 잡담을 금칙어로 일괄 차단하지 않았다.

native 실패 원인은 별도 tokenizer 계측에서 입력2577→필수 근거1999토큰, 해당 호출 허용1952토큰이었다. policy만1339토큰이다. 안전 margin을 줄이거나 현재/사람 질문 근거를 버리지 않았다. 등산 실행에서는1937입력+32출력+64margin으로 실제 의미 호출이 실행됐어도 pending 관계 오판 때문에 응답이 빠졌다. 자원 예산 문제와 의미 판단 문제를 분리한다.

GPU 로딩13.172~15.328초. 세 짧은 세션 최소 free VRAM9769MiB, RAM12,873,662,464bytes, commit39,913,771,008bytes, 최고61°C. 각 Controller/model 정상 종료를 확인했다. 세션 경과187.922/169.765/242.828초를 장시간 안정성으로 합산하지 않는다. 마감의 task-local 정책 범위 제한은 이후 loopback CPU 검사로 검증했고 GPU 세션 전체를 재실행하지 않았다. 통제된 TTFT/p50/p95 전후 비교는 NOT VERIFIED다.

## 판정과 다음 작업

RELEASE BLOCKED·DISCORD_AUTONOMOUS FAIL/BLOCKED 유지. LOCAL_CHAT와 명시 멘션/reply의 이전 준비 상태를 자율 참여 PASS로 승격하지 않는다. 장시간은 DEFERRED — USER REAL-WORLD TEST, 실제 Discord/다른 Windows는 미검증/승인 전이다. 이번 UI 디자인 변경·새 시각 렌더링은 없으며 격리 위젯 회귀와 구별한다.

다음은 실제 pending human 질문에서 봇 쪽으로 돌아오는 수신자 판단과 relation 표현의 충돌을 먼저 재현한다. 봇 target 투표만으로 pending veto를 해제하지 않는다. 현재 원문·pending 질문·기존 실제 bot/source pair로 작은 독립 귀환 판단 실험을 설계하고, 사람에게 계속 답하는 반례와 복귀 누락을 함께 측정한다. 실패한 단순 권한 문구/역할 별칭/타인 frame 축소를 반복하지 않는다. 이어 요약 paraphrase의 조건·부정·화자 보존은 원문 evidence 포함 검사와 별도 검증하고, 자유 생성의 무근거 기존 예약/조회 주장을 다룬다.

재개: 최신 main·AI-HANDOFF·이 문서 확인 → `PYTHONPATH=src;tools;tests`에서 프로젝트 Python `-m unittest test_intent_layers test_operation_grounding test_followup_release test_gguf_backend` → 자원 admission 후 단일 모델/합성 DB/SDK mock의 짧은 시나리오. 외부 Discord/운영 DB 쓰기 금지·장시간 soak 제외 유지. 실제 private bridge는 최대5분/20요청·finally 자체 자원 정리·외부 socket 차단이며 원문은 Public에 올리지 않는다.


## 회귀에서 발견한 추가 연결부

첫 전체 회귀1,066개 중 LOCAL_CHAT `/알림 취소`1건이 실패했다. 원인은 명시적 명령 어댑터가 취소 내용 뒤에 알림 종류를 붙였기 때문이다. 자연어 실행 기준을 넓히지 않고 `알림 + 명령 내용`으로 정규화해 기존 취소 테스트 그대로 통과시켰다. 표적48개/45개는 각각 GUI 환경 미제공1건 skip을 포함하므로 격리 GUI PASS로 대신 쓰지 않는다. 검토 중 전체 재실행1회는 자체 runner를 중단·정리하고 로그를 보존했다.

코드 검토에서 전달 문장 뒤 별도 명령이 마침표로 끝나면 마지막 빈 절을 선택하는 결함도 수정했다. 실제 알림 절을 선택하므로 전달된40분 대신 요청한20분이 DB에 저장되는 것을 검사했다. 같은 종류의 복수 실행은 하나만 실행하지 않고 명확히 분리를 요청한다. 요약 의도 classifier의 예산 실패도 전체 turn 실패/자료 부재로 바꾸지 않는다. 이 마감 delta들은 합성 DB/CPU·loopback에서 검증했으며 GPU 능동 세션 전체를 다시 실행했다고 주장하지 않는다.


## 최종 마감 근거

- 최종 전체 **1,068개 OK / 280.928초**. 자체 비활성 Desktop 검증·외부 socket/DNS 차단·CPU/mock 실행이며 새 코드의 의도/요약/LocalChat/권한/취소/기억/예약/queue/UI 경계를 포함한다. 앞선 실패1건과 검토 중단 로그는 별도로 보존했다.
- Portable 자체 Python과 번들 src import를 확인한 **172개 OK / 15.685초**. 격리 Tk DPI/상태/실제 위젯 이벤트를 포함한다. 다른 Windows·새 육안 디자인 검증·Portable 실제 GPU로 확대하지 않는다.
- 공개 Portable `dist/EchoMate-rc-utterance`: 전체 **21,603파일 / 4,878,004,167bytes** SHA256·membership·금지파일 감사 PASS, 누락/추가/불일치/금지0. 공개 src/docs/README200파일이 현재 checkout과 일치한다. 이후 최종 문서 통계만 delta 동기화·변경 hash 검증하며 기존 전체 감사의 불변 record를 보존한다.
- staged 공개20파일의 전체 내용/diff·확장자·민감 패턴 감사 검출0. 모델/DB/원문/토큰/비공개 로그는 stage하지 않았다. 운영 설정/bootstrap/두 DB/소비 장부5개 SHA256과 원본Lime SHA256 일치, 최종316 소비0. 합성 테스트 예약도 남기지 않았다.
- 원문·상태 증거는 비공개 root의 각 `bridge-report.json`, `model-calls.json`, `event-totals.json`, `independent/native-cause.json`, `preserved-after.json`, `full-regression-first.log`/`full-regression-interrupted-review.log`/`full-regression-final.log`, `bundle-tests.log`, `portable-full-audit.json`에 연결된다. repo 공개 문서는 비식별 근거만 싣는다.

실사용 준비 완료/RELEASE PASS를 선언하지 않는다. 다음 개발은 위 pending-human/봇 복귀와 의미 근거의 한계를 우선하며, 실제 Discord 인증/REST/Gateway/명령/송신은 계속 별도 승인 전 미실행이다.
