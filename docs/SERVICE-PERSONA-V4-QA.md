# 캐릭터 서비스 기반 1회 생성 비교 v4 — 2026-10-24

시작 main/local/remote `440d294a7f0279bc5e2e9f7f59a5e4f057ec0901`, clean. 정식 릴리즈 **BLOCKED**. 기존 2단계 후보는 비활성 상태를 유지한다. 이번 비교는 같은 Gemma 4 12B no-LoRA의 기존 text 생성만 사용하며, 사회적 판단·Action·동의·기억·전송 guard를 대체하지 않는다.

## 조사와 적용 범위

| 자료 | 공개적으로 확인한 구조 | EchoMate와 차이·검토 | 비용·위험·사용 조건 |
|---|---|---|---|
| [Character.AI Definition](https://book.character.ai/character-guide/character-attributes/definition.md) | 자유 정의와 화자별 예시, 현재 사용자와 다른 예시 화자 변수 | 카드·예시는 이미 존재. 예시 화자를 현재 사용자와 구분하는 표현을 C에서 비교 | 별도 추론 없이 토큰 증가 가능. 내부 검색/장기 기억 구현은 공개 자료로 확정하지 않음. 문서 참고, 대사/설정 복제 없음 |
| [SillyTavern Prompt Manager](https://docs.sillytavern.app/usage/prompts/prompt-manager/)·[실제 순서 정의](https://github.com/SillyTavern/SillyTavern/blob/06bde939fb1e9c4c8d8641d810f0a916b5bce127/public/scripts/PromptManager.js) | main/세계관/인격/예시/history의 독립 삽입 위치 | EchoMate는 선택한 자료를 시스템 끝에 JSON으로 추가. C에서 가상 자료를 행동 정의 앞에 배치 | 추가 모델 호출0, 위치 변화가 사실성에 해로울 가능성도 평가. AGPL-3.0 코드는 복사하지 않고 자체 도구 작성 |
| [SillyTavern World Info](https://docs.sillytavern.app/usage/core-concepts/worldinfo/)·[실제 scan/budget 코드](https://github.com/SillyTavern/SillyTavern/blob/06bde939fb1e9c4c8d8641d810f0a916b5bce127/public/scripts/world-info.js) | scan depth/조건·우선순위·토큰 예산·삽입 위치 | 기존 최대 lore3/example2·추가900/전체6000토큰 유지. 선택과 실제 전달은 별개 | 재귀 검색/항목 증가를 도입하지 않음. 키워드 활성화는 의미적 관련성 보증 아님 |
| [RisuAI 공개 구현](https://github.com/risuai/RisuAI/blob/63c59c15336cc6da865218ff3717756557206fcb/src/ts/process/lorebook.svelte.ts) | loadLoreBookV3Prompt의 character/chat/module 자료, scanDepth/tokenBudget, source별 matchLog | 새 저장소 없이 기존 선택 결과의 현재/과거 활성화 출처를 C에 표시 | 고정 commit 파일도 별도 확인. GPL-3.0 코드 복사/의존 추가 없음 |
| [Letta 상태·기억](https://docs.letta.com/v1-sdk/concepts/stateful-agents)·[Apache-2.0 라이선스](https://github.com/letta-ai/letta/blob/main/LICENSE) | 고정 core block과 검색 가능한 과거 메시지, 명시 tool을 통한 기억 편집 | EchoMate의 카드와 동의된 실제 기억 분리는 이미 있음. 자동 기억 편집/추가 추론 도입은 이번 목표와 다름 | 새 에이전트/DB 도입 기각. 지속 상태는 사실 주장 정확성 보증이 아님 |
| [Crack 공개 프롬프트 설명](https://help.crack.wrtn.ai/character/prompt) | 시스템/캐릭터/기능 프롬프트, 조건부 키워드북, 예시와 history·요약 | 기능 이름을 새로 만드는 대신 현 입력 구조 감사 | 비공개 모델/삽입 알고리즘·라이선스 불명 코드 추정/복사 없음 |

이는 외부 서비스의 품질을 EchoMate에서 재현했다는 근거가 아니다. 각 기능의 공개 설명과 코드에서 확인한 부분만 참고했다. 유명 캐릭터의 이름·대사·설정을 수집하지 않았고 새 모델·의존성·학습도 없다.

GitHub 공개 metadata로 RisuAI main63c59c1·Letta main8816d3a를 확인했다. RisuAI 고정 lorebook 파일 SHA256은 비공개 조사 기록에 보존했다. Letta의 지정 schema 파일 직접 조회는 실패해 그 기억 구조는 공식 문서 근거로 한정하며 코드를 검증했다고 주장하지 않는다. 조사 사본은 실행/번들/Git에 넣지 않는다.

## 실제 입력 감사와 가설

기존 `character.instruction`은 출력·현실 기능·관계/개인정보 정책 뒤 `compile_profile(applied_profile)`을 넣고 이어 기분·성별·성인 경계를 적용한다. `backend.text`는 이 system과 Runtime 원문/이력/기억/기능 메타데이터를 전달한다. GPU Worker에서 `character_card.augment`가 선택 자료를 system 끝에 넣고 **실제 공식 chat template**으로 6000토큰을 확인한다. 원문을 잘라 맞추지 않는다.

기존 selector는 현재 발언 hit×10과 이전 사용자 발언 hit×1을 더한다. 이전에만 키워드가 있어도 활성화될 수 있다. 기존 JSON world는 내용 문자열, examples는 user/character 문자열이며 선택 ID·활성화 근거는 모델 payload에 없다. 예시는 모두 system 안에 있어 Discord 실제 화자 role로 삽입되지 않는다. 예산 부족 시 examples→world→기타 필드를 제거한다. 단순히 더 많은 문맥이 필요하다고 단정할 근거는 없다.

`tools/service_persona_v4.py`와 실행기만 후보를 구성한다. 앱/Controller/Settings에는 활성 경로를 추가하지 않는다.

- A: 기존 instruction/augment 그대로. 토크나이저 입력과 원문 해시를 비공개 보존한다.
- B: 기존 compiler의 반응 접근 문단만 상황 해석→복합 반응의 구체적 문단으로 교체한다. 수치·기분·관계·거친 표현·상위 정책과 선택 예시는 유지한다. 예시를 통째로 없애거나 이전 레퍼런스 compiler 전체 교체를 반복하지 않는다.
- C: B에 선택 항목의 fiction ID/현재 또는 과거 활성화/현재 사용자 근거가 아닌 scope/별도 예시 화자 필드를 넣고, 가상 자료를 행동 정의 앞에 둔다. 선택 항목 자체·관계 조건·private 제외·복제 제외는 그대로다. 현재 키워드만 강제하면 정상 후속을 누락할 수 있어 그런 차단은 도입하지 않는다. C는 출처+배치의 묶음이므로 성공하더라도 두 요소의 개별 인과 효과를 주장하지 않는다.

C의 추가 출처 표현이 동일 예산을 넘으면 B의 기존 증강 결과로 제한 복귀하고 fallback을 기록한다. 원문/기억/기능 자료나 상위 정책을 삭제하는 방식으로 통과시키지 않는다. 새 후보가 사실성을 악화시키면 운영 적용하지 않는다.

## 실행 계약

새 합성 개발5상황×4실제 프리셋×A/B/C를 같은 모델 인스턴스로 순서 교대 비교한다. 새 상황은 개발 자료이며 미사용 최종 평가가 아니다. 기존 1650사례·최종316개 소비 장부는 변경하지 않는다. 동일768 출력 상한·greedy·실제 Runtime/임시 SQLite/실제 discord.py SDK HTTP mock을 사용한다. 저수준 Discord/aiohttp HTTP를 차단한다. 기존 출력 재작성·닫힌 기능 응답은 숨기지 않고 실제 호출과 구분한다.

실제 후처리된 모델 입력/역할/선택 자료/예산/fallback·호출 metric·원본 reply·pending·전체 지연을 ignored `local_data/service-persona-v4-20261024/`에 저장한다. HTML은 로컬 정적 리포트이며 외부 자원을 요청하지 않는다. 토큰별 메시지 측정은 각 메시지를 독립 template로 센 진단이며 합산 총 토큰으로 쓰지 않는다.

채택은 인격의 관점·복합 반응 차이와 사실성을 별개로 본다. 알려진 미래 기억 약속·공동 사건 오류가 늘거나 인격 개선이 불명확하면 실패로 남긴다. 부적격 Gemma/Qwen 평가자의 자동 점수를 합격 근거로 쓰지 않는다. 자연어 전체의 사실성을 자동 검증했다고 주장하지 않는다. 개발에서 실패하면 최종316개/대규모 표준 GPU를 소비하지 않는다.

## 실제 결과와 마감

### 고정 개발 비교 — 후보 B·C 기각

`run_service_persona_v4.py --model local_data/stabilization-20261020/models/gemma4-sharded --output local_data/service-persona-v4-20261024/development`를 실행했다. 준비/probe 포함856.422초, 모델 인스턴스1개·로딩1회다. Runtime 60회/SDK mock60송신, 실제 모델 **64회 = 텍스트50(48기본+기존 재작성2) + 이력 판별12 + 준비probe2**다. A/C 재작성 각1, B0이며 새로운 계획/채점 호출은 없다.

| 같은 개발 코호트 | A 기존 | B 행동 | C 행동+출처/배치 |
|---|---:|---:|---:|
| 전체 이벤트 |20|20|20|
| 모델 호출(probe 제외) |21|20|21|
| 전체 이벤트 p50/p95 초 |10.938 / 32.680|11.688 / 26.195|11.664 / 31.453|
| text 경로 이벤트(닫힌 안내 제외) |16|16|16|
| text 경로 전체 p50/p95 초 |13.422 / 34.711|13.922 / 30.536|15.211 / 33.828|
| text 추론당 출력 토큰 p50 |110|108|118|
| 잘못된 원본 reply / 중복 송신 / 종료 후 pending |0 / 0 / 0|0 / 0 / 0|0 / 0 / 0|

큐 대기 최대0.015초/p50 0초인 순차 비교이며 포화·다사용자 지연 인증이 아니다. text 경로 추가 카드381~465→C383~505토큰, 최종 text 입력 최대2072토큰, C fallback0. 900/6000 상한 아래여서 이 개발 사례의 인격 수렴을 입력 잘림이나 카드 누락 탓으로 설명할 수 없다. 출력 길이·재작성 수가 달라 p95 감소를 속도 향상으로 해석하지 않는다. 이전 차수의6.742초 baseline과는 현재 부하·코호트가 달라 직접 비교하지 않는다.

인격 관찰: 동아리 역할 갈등은 A/B/C 모두 대체로 부담 인정→역할 분담 제안으로 수렴했다. 분석형은 장문의 목록이 되기도 했으며 C에서 다른 관점으로 바뀌었다고 보기 어렵다. 라벨 분실 장난의 B 장난형은 놀이를 확장했지만 분석형 A/B는 완전히 같은 답변이었다. 배경은 세 조건 모두 기존 가상 사건과 가치관을 연결했다. 문구 변화/일부 비유만으로 강한 인격 차별성을 합격 처리하지 않는다.

사실성은 아래 **명시적 구간의 검토 관측**이며 검증된 일반 AI 평가자의 점수나 전체 자연어 사실 오류율이 아니다. 원문/판정 키는 비공개로 유지한다.

| 알려진 근거와 실패 | A | B | C |
|---|---|---|---|
| 미래 취향 회상4개: 영수증 없이 명백한 미래 기억 약속 |1|1, 추가 기록 약속과 불가 설명이 충돌한 모호1|2|
| 같은4개: reminders=ready를 기능 없음/비활성으로 잘못 설명 |3|3|2|
| 가상 일터 질문4개: 카드에 없는 이직 사건을 명백히 확정 |1|0관측|0관측|
| 온라인 공동 관람4개 |기존 닫힌 안내4|기존 닫힌 안내4|기존 닫힌 안내4|

두 미래 오류는 중복될 수 있어 단순 합산하지 않는다. memory=off·own_consent=false·reminders=ready라는 실제 공개 상태가 입력됐고, 임시 저장소 기억 수0과 실행 영수증 없음도 확인했다. 그럼에도 자유 생성에서 약속/기능 부재를 꾸몄다. 이는 실제 provider가 틀린 상태를 제공한 사례가 아니다. 가상 이직의 국소 감소가 미래 약속 악화를 상쇄하지 않는다.

온라인 공동 관람은 기존 `is_history_request` 후 닫힌 요약 안내로 전환돼 카드 증강/text 생성이 없었다. 따라서 이12송신을 C의 공동 경험 환각 개선으로 세지 않는다. 초기 seal은 두 축 veto를 고정했고, 배경/미래/공동 사건의 세부 검토 계약은 해당 사실 출력 열람 전에 별도 보존했다. 앞서 본 인격·장난 출력은 개발 관찰이다. 완전 사전 등록 독립 평가라고 부르지 않는다.

**최종 판정: B·C 모두 운영 미채택.** 사실성/인격 동시 개선이 없으므로 추가 같은 프롬프트 조정·새 모델·추가 단계·독립/표준 대규모 생성으로 확대하지 않는다. 기존1650개·최종316개 소비0. 새 독립 확인, 기분/친밀도 변화 GPU, 장기/다자 GPU, 사람 만족도는 **NOT VERIFIED**다. 60건의 메타데이터 직접 호출 결과로 기존 사회적 오개입·후속 누락·연결 오류가 해결됐다고 주장하지 않는다.

### 자원·도구 마감

사전 RAM 약8.34GiB/commit 여유31.59GiB/VRAM13049MiB·53℃, 기존 로딩 reserve/admission 통과. 실행 중 시스템 RAM 최소5.266GiB/commit 최소19.114GiB, OS private high-water13.009GiB. 실제 CUDA 최대 allocated8333.2MiB/reserved8660.0MiB. GPU 종료 후 집계 조회43℃/free12487MiB였으며 타 앱 사용량을 특정하지 않는다. 단일 Worker·InstanceLease·기존 취소/안전 검사를 유지하고 드라이버 오류/메모리 중단 없이 종료했다. 다른 앱/게임의 창·목록·프로세스 내부·입력·화면 조회0, 실제 FPS 영향은 미측정이다.

평가 도구의 자유 소개 문장이 compiler 경계로 오인되지 않도록 JSON 종료 이후의 고정 행동 문단만 교체하게 보강했다. 표적7검사 OK0.014초, 봉인된 네 프로필의 변경 전후 실제 프롬프트가 완전히 같음을 대조했다. 따라서 이 보강을 이유로 같은 GPU 출력을 재생성하지 않았다. 운영 src 전체는 봉인 hash와 동일하다.

비공개 `development/report.html`은 입력/결과/metric을, `blind-review.html`은 캐릭터·후보 이름을 제거한60개 응답을 표시한다. 답안 키는 별도 비공개 파일이다. 블라인드 파일 생성은 사람 평가 수행이 아니다. 공개 Git/Portable에 전체 입력·출력·정답·운영 자료를 넣지 않는다.

## 다음 중요한 작업과 남은 차단

1. 일반 자유 생성의 기능 설명에서 **제공 가능/동의 필요/실제 commit 영수증/미래 약속**을 원자 주장으로 구분하는 검증 계약을 먼저 교정한다. 기존 닫힌 기능 안내를 모든 잡담에 강제하는 해법은 채택하지 않는다. 추가 호출 없는 계약도 의미 추출 신뢰성·말투 손실을 검증해야 하며 이번에 구현/통과한 것으로 표시하지 않는다.
2. 인격은 이미 전달되는 행동/배경의 단순 재서술 대신, 새로운 가치 충돌·정정·기분 변화의 반응 선택을 검증할 데이터와 신뢰 가능한 평가자를 확보한다. 불합격 평가자의 점수 최적화나 동일 문단 반복 교체는 하지 않는다.
3. 실제 `/동의` 비표시는 원인 미확정. 별도 읽기 승인→원격 Application/전역/서버별 확인→별도 변경 승인→클라이언트 표시·실행 확인을 유지한다. 사회적 오개입·누락·연결, 실제 사용자 UI/다른 Windows/장시간도 계속 BLOCKED/NOT VERIFIED다.

## 최종 회귀·Portable·자료 보존·Git

- `PYTHONPATH=src;tests;tools .venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`: **753검사 OK236.152초**. 기존746+신규 계약7이며 인격 품질 PASS와 구분한다. 실행 중 비동기 느린 callback 진단은 있었지만 실패0이다.
- Portable 기존 번들 Python을 별도 `bundle-check/local_data`에서 실행한 `test_character_card.CardData test_memory_evidence_delivery`: **19검사 OK2.202초**. 두 VBS `/check`는0 종료이며 GUI/Discord를 시작하지 않았다.
- 공개 src/docs160파일+README/공개 기본 프로필162쌍과 manifest **21,564항목**의 membership/공개 SHA256/전체 파일 크기를 대조했다. 전체 재빌드·인터프리터 전체 재해시·새 GUI 렌더·번들 GPU·다른 Windows 검증은 하지 않았다. 운영 실행 소스는 시작 버전과 같고 평가 도구는 앱에 번들 활성화하지 않는다. 공개 문서만 증분 최신화했다.
- 운영 bootstrap·서명 settings·companion/sent 두 DB의 시작/종료 SHA2564개 모두 동일. 모델·LoRA·운영 프로필/선택·토큰을 수정/복사하지 않았다. 모델/토크나이저 환경 버전과 작은 설정 파일 hash는 실행 후 별도 비공개 기록으로 보존했으며 가중치 전체 재해시라고 주장하지 않는다.
- 실제 Discord 인증/REST/Gateway/명령 조회·등록·삭제·sync·송신0회. 공개 기술 조사와 승인된 GitHub 작업만 네트워크를 사용했다. 개인 자료·공개 원문 corpus·모델·전체 평가 출력은 Git/Portable 제외다.
- 평가 도구·합성 계약 테스트 단계 커밋 **`83eb7e2`**. 시작 실행 소스 `440d294`와 동일한 운영 src를 유지한다. 최종 문서 마감 커밋/원격 일치·clean은 Git 로그와 최종 보고를 따른다. 정식 릴리즈는 **BLOCKED**다.
