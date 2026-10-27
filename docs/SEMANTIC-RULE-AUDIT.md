# 자연어 규칙 감사 — 2026-10-27

기준 main `f0d199f`. **A=필수 안전, B=프로토콜, C=의미 휴리스틱, D?=평가 표현 과적합 의심, E=중복/충돌**이다. 한 규칙이 여러 범주에 속할 수 있다. 안전 목적(A)과 그 구현의 한국어 추정(C)을 구분한다. D?는 과적합 확정이 아니다. 문항 ID/새 평가 문장 전체를 운영 분기로 쓰는 증거는 찾지 못했지만, 그 사실이 일반화를 입증하지 않는다.

대상 메시지 처리/호출 경로: 수신→조각/실제 ID·reply→사회적 판단→Intent/읽기·Action→MemorySelection/Receipt→Context Compiler→생성→출력 검사→송신 직전 guard. 자동 기억은 Runtime memory_queue→서비스의 `to_thread(companion.extract,...)`; 명시 저장도 companion→extract로 수렴한다. 요약은 Summarizer→validated_digest→fidelity→동의/source/삭제 검사→저장·재사용·fallback이다. LOCAL은 같은 저장·읽기 계약과 생성기를 재사용한다.

## 규칙 가족별 감사·결정

| ID·유형 | 실제 역할·도입 근거 | 정상 입력 손실/충돌 가능성 | 회귀 근거·제거 위험·현재 결정 |
| --- | --- | --- | --- |
| R01 B/C/E | routing.prose의 인용/코드/URL 분리. 구형 grounded 후속 helper는 이전 구두점/어휘 경로 흔적 | 한국어 의미·중첩 인용을 증명하지 못함. correction의 별도 인용 정규식과 처리 범위 달랐음 | test_parallel_runtime/test_bot_return. prose 재사용으로 중복1개 통합. 구형 helper는 유지; 아래 호출 조사 |
| R02 B/C | intent_router의 요청/언급/금지/불완전·복합 grammar. 미실행 기능 완료/복합 요청 사고 방지 | 보고 어미·가정 어휘/절 분리가 새로운 한국어를 놓칠 수 있음. 시간 부족은 NLP 판정 아님 | test_intent_layers/test_read_correction/test_operation_grounding. 권한/Receipt는 유지; 검증 없이 LLM 대체 금지 |
| R03 B/C | identity_contract의 현재/기본 이름 질문 및 관리자 설정 안내 | 160/320자·최대4절과 알려진 이름 표현 밖에는 미처리. 일반 제안/인용 혼합은 생성기로 감 | test_identity_contract. 이름 변경 권한은 문자열이 아니라 관리자 ID/설정 성공. 문장 grammar만으로 설정 변경하지 않음 |
| R04 C/D? | lookup_inquiries의 제한 상태 질문·과거 기억 문의. 허위 조회/조회 실패 안내 문제에서 도입 | 정해진 질문형과 다른 동의어는 누락·일부 혼합 질문은 안내가 가로챌 수 있음 | test_lookup_inquiries/test_factual_context. 결정적 응답 내용은 실제 조회 상태(B); 질문 감지는 C. 범용 사실 판정기로 사용 금지 |
| R05 A/B/C/D? | ReadEvidence9상태/current와 read_question이 한 모듈에 공존 | 특정 대비 질문에 가까운 fullmatch 및 친인용/라면 단어 배제는 의미 일반화 한계 | test_read_correction. ReadReceipt/current는 필수(A/B), query grammar만 C/D?; 둘을 함께 제거하지 않음 |
| R06 C/E | correction_requested와 correction_view. 이전 모델 추측을 최신 사용자 정정 뒤 근거에서 낮춤 | 라면 같은 문자열이 실제 정정을 가릴 수 있고, 인용문만으로 과거 모델 문맥을 지울 수 있었음 | test_semantic_sources/test_generation_context/test_read_correction. 별도 quote 제거를 기존 prose로 통합. 의미 조건 검사는 미검증이므로 유지 |
| R07 B/C | companion request_kind/plan/단일·복합 실행·시간 해석 연결 | 기능 단어의 언급과 요청이 겹침; 자유 문장의 매개변수 추정 위험 | test_operation_grounding/test_intent_layers. 실제 대상/권한/시각·Receipt와 별도; 모르는 시각을 생성하지 않음 |
| R08 A/B/C | safe_subject_text·개인정보/동의·500자 안전 형식·300자 추출 및 자기 보고/종류/보고·가정 필터 | 친구/농담/따옴표 등이 정상 자기 취향도 보류. 부정·간접 전달 누락은 여전히 가능 | test_source_attribution/test_companion_store/test_character_store. 장문 확대/의미 필터 제거 비교는 부적격 저장 증가로 기각. 300자 보류 유지 |
| R09 B/C/D? | summary_fidelity의 원문 범위·부정/조건/전달·시점 변형 차단. 실제 요약 의미 손실에서 도입 | 어휘가 유지돼도 주체가 바뀔 수 있고 올바른 바꿔말하기도 거절 가능 | test_source_attribution/test_generation_context/test_semantic_focus. source 위치 계산은 공유 exact helper로 통합; 의미 검사는 일반 정확성 인증 아님 |
| R10 A/B/C | Summarizer의 source ID/증거·참여자 동의/최신성·요약 요청/원문 fallback | 인용 기호/길이·민감어에 따라 원문 fallback도 보류될 수 있음 | test_followup_release/test_source_attribution. source/권한/삭제는 A/B; 의미 동등성은 별도 검증. 원문을 새 기억/권한으로 만들지 않음 |
| R11 B/C | Context Compiler의 관련성 어휘, old_reports 선택, caller 소유 carrier/9상태·실제 영수증 투영 | 어휘 관련성이 실제 의미 연관성과 다를 수 있음. 160/220/120자 정책은 문맥 누락 비용 | test_generation_context/test_runtime_context_budget. 영향은 생성 문맥 선택뿐; 실행·권한·청자 판단으로 승격 금지. 기존 GPU 범위만 유지 |
| R12 A/B/C | capability_view는 실제 구현/설정/동의·권한(B), question/_describe는 자연어 문의(C) | 친밀도/기억 단어가 잡담에 있어도 기능 안내로 가로챌 수 있음 | test_factual_context/test_semantic_focus. 기능 지원과 현재 수행 성공을 구분. 실제 state 계산은 유지 |
| R13 A/B/C | Discord 코드/URL/빈 출력 경계·explicit_code_request 감지 | 코드 유사 텍스트/개념 설명과 충돌 가능. 코드 울타리만 지우는 우회 위험 | 기존 전체 출력/프로토콜 회귀. 제품 코드 출력 금지(A)는 유지, 요청 감지 휴리스틱(C)과 구분 |
| R14 B/C | social frame·실제 참여자/reply 기반 구조와 명칭·인용 처리 | 이름 언급과 실제 호출, pending-human 복귀 의미는 여전히 어려움 | test_social_routing/test_bot_return. 실제 ID/reply 우선 유지; 자율 청자 미완료는 별도 BLOCKED |
| R15 A/B/C | Runtime scope/epoch/송신·큐·중복/실제 멘션 + 의미 분기 연결 | 실패 원인을 모두 NLP 실패로 묶으면 권한·경합 오류를 숨길 수 있음 | test_operation_grounding/test_memory_selection_delivery/test_mode_gates. DIRECT는 의미 판별0회 원칙; 저장·송신 보호 제거 금지 |
| R16 B/C | DialogueIntent의 네 축/엄격 enum parser와 기존 공통 모델 프롬프트 | valid 형식은 올바른 청자 증명이 아님; 낮은 모델 정확도를 정규식으로 보완하려는 압력 | test_semantic_dialogue. 기존 모델 재사용, 두 번째 상주 GPU 모델 없음. LLM 확신도는 정확도가 아님 |
| R17 B/C | tools/korean_claim_extraction·contract의 실험용 원자 주장/명시 근거·행위/시점 구분 | 과거 신뢰성 미달, 정확한 근거도 틀린 의미를 가질 수 있음 | test_korean_claim_extraction/contract/test_semantic_sources. Runtime 최종 판정자로 연결하지 않음; 읽기 전용 reading 제안 계약으로 확장 |
| R18 A/B | source_span/source_spans의 정확한 code-point 위치/형식/동일 원문 확인 | 정확한 구간≠참된 주장. 중첩 출현을 단순 str.count로 유일하다고 오인 가능 | test_semantic_sources. 언어 독립 검증 공유; 불확실성/영수증/저장 권한을 생성하지 않음 |
| R19 A/B | slash commands/실제 UserID·DB namespace/동의 epoch·수정·삭제/실행 Receipt | 단순한 대화 품질 문제로 격하하면 실제 유출·오송신 위험 | test_character_store/test_operation_grounding/test_reminder_freshness. 유지. 분석기의 subject/quote만으로 권한 변경 금지 |

## 호출·과적합·중복 조사

`grounded_followup`은 저장소 src/tools/tests 검색에서 정의 외 호출이 없었고 `grounded_group_followup`은 회귀용 직접 호출이 있다. 운영 미사용 관측만으로 전체 안전성을 보장하지 않아 둘 다 유지했다. 함수 삭제는 관리 도구의 자동 승인 검토에서도 청자 보호 약화 위험으로 거절되어 수행하지 않았다. 우회 삭제·전부 침묵/참여·임계값 완화는 없다.

특정 실패에 가까운 어휘가 들어간 C/D?를 확정 과적합으로 부르지 않는다. 그러나 전체 한국어 의미 이해로 인증할 근거도 없다. 새40개 저장 경계 비교에서 기존에도 정상 기억 누락/부적격 저장이 함께 관측됐으므로 단순 테스트 통과 개수로 일반성을 주장하지 않는다. 상세 지표는 [일반화 QA](GENERALIZATION-QA.md).

현재의 자동 저장(기억 원문을 대상으로 한 휴리스틱)과 연구용 의미 제안(실제 원문 구간이 있는 미검증 해석)을 구분한다. 모델 제안은 storage_eligible=false/runtime_enabled=false이며 기존 consent/ReadReceipt/송신 guard를 대체하지 않는다. 긴 원문은 현재300자 규칙을 무조건 풀지 않았고, 연구 제안에는 근거 국소 구간뿐 아니라 전체 원문/hash/version을 보존한다.

## 정적 위치 색인

아래는 요청된 경로16개 모듈의 모든 `re.*` 호출 위치 색인이다. **정규식 API 호출 수이며 독립 의미 규칙 수/실행 횟수가 아니다.** 부울·ID·상태/길이 계약과 모델 프롬프트의 비정규식 정책은 위 가족 표/설계에서 별도로 감사했다. 원문/평가 문장은 포함하지 않았다. family의 도입 원인·검증/제거 위험이 각 위치에 적용되며 같은 함수 안의 A/B/C는 구체 소스를 함께 대조해야 한다.

기준 호출 169개 → 현재 166개. D?를 삭제해 수를 줄이지 않았다. 변경 파일의 마지막 기존 커밋과 최종 실제 source hash/복잡도는 비공개 `audit-index.json`에 있다.

| 위치 | 함수·호출 | 유형·가족·행 변경 근거 |
| --- | --- | --- |
| [src/echomate_bot/capabilities.py:12](../src/echomate_bot/capabilities.py#L12) | `module` / `re.compile` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:13](../src/echomate_bot/capabilities.py#L13) | `module` / `re.compile` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:20](../src/echomate_bot/capabilities.py#L20) | `visual_question` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:24](../src/echomate_bot/capabilities.py#L24) | `question` / `re.findall` | A/B/C · R12 · `c2e6cedc` |
| [src/echomate_bot/capabilities.py:25](../src/echomate_bot/capabilities.py#L25) | `question` / `re.search` | A/B/C · R12 · `c2e6cedc` |
| [src/echomate_bot/capabilities.py:30](../src/echomate_bot/capabilities.py#L30) | `question` / `re.search` | A/B/C · R12 · `c2e6cedc` |
| [src/echomate_bot/capabilities.py:31](../src/echomate_bot/capabilities.py#L31) | `question` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:66](../src/echomate_bot/capabilities.py#L66) | `_describe` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:67](../src/echomate_bot/capabilities.py#L67) | `_describe` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:67](../src/echomate_bot/capabilities.py#L67) | `_describe` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:69](../src/echomate_bot/capabilities.py#L69) | `_describe` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:72](../src/echomate_bot/capabilities.py#L72) | `_describe` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:73](../src/echomate_bot/capabilities.py#L73) | `_describe` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:78](../src/echomate_bot/capabilities.py#L78) | `_describe` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:79](../src/echomate_bot/capabilities.py#L79) | `_describe` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:81](../src/echomate_bot/capabilities.py#L81) | `_describe` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:82](../src/echomate_bot/capabilities.py#L82) | `_describe` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:87](../src/echomate_bot/capabilities.py#L87) | `_describe` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/capabilities.py:93](../src/echomate_bot/capabilities.py#L93) | `_describe` / `re.search` | A/B/C · R12 · `d6bd50e1` |
| [src/echomate_bot/companion.py:13](../src/echomate_bot/companion.py#L13) | `request_kind` / `re.search` | B/C · R07 · `99761cce` |
| [src/echomate_bot/companion.py:14](../src/echomate_bot/companion.py#L14) | `request_kind` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:16](../src/echomate_bot/companion.py#L16) | `request_kind` / `re.fullmatch` | B/C · R07 · `11bc0aaa` |
| [src/echomate_bot/companion.py:18](../src/echomate_bot/companion.py#L18) | `request_kind` / `re.search` | B/C · R07 · `4169a81d` |
| [src/echomate_bot/companion.py:19](../src/echomate_bot/companion.py#L19) | `request_kind` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:19](../src/echomate_bot/companion.py#L19) | `request_kind` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:20](../src/echomate_bot/companion.py#L20) | `request_kind` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:36](../src/echomate_bot/companion.py#L36) | `request_plan` / `re.search` | B/C · R07 · `ff3de52c` |
| [src/echomate_bot/companion.py:36](../src/echomate_bot/companion.py#L36) | `request_plan` / `re.search` | B/C · R07 · `ff3de52c` |
| [src/echomate_bot/companion.py:38](../src/echomate_bot/companion.py#L38) | `request_plan` / `re.search` | B/C · R07 · `ff3de52c` |
| [src/echomate_bot/companion.py:106](../src/echomate_bot/companion.py#L106) | `_handle_single` / `re.sub` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:116](../src/echomate_bot/companion.py#L116) | `_handle_single` / `re.findall` | B/C · R07 · `99761cce` |
| [src/echomate_bot/companion.py:119](../src/echomate_bot/companion.py#L119) | `_handle_single` / `re.search` | B/C · R07 · `99761cce` |
| [src/echomate_bot/companion.py:132](../src/echomate_bot/companion.py#L132) | `_handle_single` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:135](../src/echomate_bot/companion.py#L135) | `_handle_single` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:147](../src/echomate_bot/companion.py#L147) | `_handle_single` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:147](../src/echomate_bot/companion.py#L147) | `_handle_single` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:149](../src/echomate_bot/companion.py#L149) | `_handle_single` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:154](../src/echomate_bot/companion.py#L154) | `_handle_single` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:154](../src/echomate_bot/companion.py#L154) | `_handle_single` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:156](../src/echomate_bot/companion.py#L156) | `_handle_single` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:163](../src/echomate_bot/companion.py#L163) | `_handle_single` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion.py:169](../src/echomate_bot/companion.py#L169) | `_handle_single` / `re.search` | B/C · R07 · `61dc4580` |
| [src/echomate_bot/companion_store.py:20](../src/echomate_bot/companion_store.py#L20) | `module` / `re.compile` | A/B/C · R08 · `61dc4580` |
| [src/echomate_bot/companion_store.py:25](../src/echomate_bot/companion_store.py#L25) | `safe_subject_text` / `re.search` | A/B/C · R08 · `61dc4580` |
| [src/echomate_bot/companion_store.py:209](../src/echomate_bot/companion_store.py#L209) | `extract` / `re.search` | A/B/C · R08 · `f0d199f5` |
| [src/echomate_bot/companion_store.py:210](../src/echomate_bot/companion_store.py#L210) | `extract` / `re.search` | A/B/C · R08 · `f0d199f5` |
| [src/echomate_bot/companion_store.py:211](../src/echomate_bot/companion_store.py#L211) | `extract` / `re.search` | A/B/C · R08 · `f0d199f5` |
| [src/echomate_bot/companion_store.py:212](../src/echomate_bot/companion_store.py#L212) | `extract` / `re.search` | A/B/C · R08 · `61dc4580` |
| [src/echomate_bot/companion_store.py:212](../src/echomate_bot/companion_store.py#L212) | `extract` / `re.search` | A/B/C · R08 · `61dc4580` |
| [src/echomate_bot/companion_store.py:212](../src/echomate_bot/companion_store.py#L212) | `extract` / `re.search` | A/B/C · R08 · `61dc4580` |
| [src/echomate_bot/companion_store.py:212](../src/echomate_bot/companion_store.py#L212) | `extract` / `re.search` | A/B/C · R08 · `61dc4580` |
| [src/echomate_bot/companion_store.py:212](../src/echomate_bot/companion_store.py#L212) | `extract` / `re.search` | A/B/C · R08 · `61dc4580` |
| [src/echomate_bot/companion_store.py:212](../src/echomate_bot/companion_store.py#L212) | `extract` / `re.search` | A/B/C · R08 · `61dc4580` |
| [src/echomate_bot/companion_store.py:214](../src/echomate_bot/companion_store.py#L214) | `extract` / `re.search` | A/B/C · R08 · `61dc4580` |
| [src/echomate_bot/companion_store.py:218](../src/echomate_bot/companion_store.py#L218) | `extract` / `re.search` | A/B/C · R08 · `99761cce` |
| [src/echomate_bot/companion_store.py:253](../src/echomate_bot/companion_store.py#L253) | `memories` / `re.search` | A/B/C · R08 · `61dc4580` |
| [src/echomate_bot/correction_context.py:9](../src/echomate_bot/correction_context.py#L9) | `correction_requested` / `re.search` | C/E · R06 · `11bc0aaa` |
| [src/echomate_bot/correction_context.py:10](../src/echomate_bot/correction_context.py#L10) | `correction_requested` / `re.search` | C/E · R06 · `11bc0aaa` |
| [src/echomate_bot/dialogue_intent.py:20](../src/echomate_bot/dialogue_intent.py#L20) | `parse_intent` / `re.fullmatch` | B/C · R16 · `a854d0a4` |
| [src/echomate_bot/generation_context.py:58](../src/echomate_bot/generation_context.py#L58) | `domains` / `re.search` | B/C · R11 · `08415bbd` |
| [src/echomate_bot/generation_context.py:59](../src/echomate_bot/generation_context.py#L59) | `domains` / `re.search` | B/C · R11 · `08415bbd` |
| [src/echomate_bot/generation_context.py:97](../src/echomate_bot/generation_context.py#L97) | `evidence_sections` / `re.search` | B/C · R11 · `08415bbd` |
| [src/echomate_bot/generation_context.py:101](../src/echomate_bot/generation_context.py#L101) | `evidence_sections` / `re.search` | B/C · R11 · `08415bbd` |
| [src/echomate_bot/generation_context.py:114](../src/echomate_bot/generation_context.py#L114) | `evidence_sections` / `re.search` | B/C · R11 · `08415bbd` |
| [src/echomate_bot/generation_context.py:149](../src/echomate_bot/generation_context.py#L149) | `old_reports` / `re.search` | B/C · R11 · `08415bbd` |
| [src/echomate_bot/identity_contract.py:12](../src/echomate_bot/identity_contract.py#L12) | `answer_identity` / `re.sub` | B/C · R03 · `c2e6cedc` |
| [src/echomate_bot/identity_contract.py:16](../src/echomate_bot/identity_contract.py#L16) | `answer_identity` / `re.split` | B/C · R03 · `c2e6cedc` |
| [src/echomate_bot/identity_contract.py:20](../src/echomate_bot/identity_contract.py#L20) | `answer_identity` / `re.sub` | B/C · R03 · `c2e6cedc` |
| [src/echomate_bot/identity_contract.py:33](../src/echomate_bot/identity_contract.py#L33) | `_single_identity` / `re.sub` | B/C · R03 · `7ba8d288` |
| [src/echomate_bot/identity_contract.py:40](../src/echomate_bot/identity_contract.py#L40) | `_single_identity` / `re.fullmatch` | B/C · R03 · `7ba8d288` |
| [src/echomate_bot/identity_contract.py:41](../src/echomate_bot/identity_contract.py#L41) | `_single_identity` / `re.escape` | B/C · R03 · `7ba8d288` |
| [src/echomate_bot/identity_contract.py:45](../src/echomate_bot/identity_contract.py#L45) | `_single_identity` / `re.fullmatch` | B/C · R03 · `7ba8d288` |
| [src/echomate_bot/identity_contract.py:45](../src/echomate_bot/identity_contract.py#L45) | `_single_identity` / `re.fullmatch` | B/C · R03 · `7ba8d288` |
| [src/echomate_bot/identity_contract.py:50](../src/echomate_bot/identity_contract.py#L50) | `_single_identity` / `re.fullmatch` | B/C · R03 · `7ba8d288` |
| [src/echomate_bot/intent_router.py:32](../src/echomate_bot/intent_router.py#L32) | `request_clauses` / `re.split` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:47](../src/echomate_bot/intent_router.py#L47) | `history_review` / `re.search` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:48](../src/echomate_bot/intent_router.py#L48) | `history_review` / `re.search` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:49](../src/echomate_bot/intent_router.py#L49) | `history_review` / `re.search` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:68](../src/echomate_bot/intent_router.py#L68) | `execution_clauses` / `re.finditer` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:72](../src/echomate_bot/intent_router.py#L72) | `execution_clauses` / `re.sub` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:117](../src/echomate_bot/intent_router.py#L117) | `plan_intent` / `re.search` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:121](../src/echomate_bot/intent_router.py#L121) | `plan_intent` / `re.search` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:122](../src/echomate_bot/intent_router.py#L122) | `plan_intent` / `re.search` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:124](../src/echomate_bot/intent_router.py#L124) | `plan_intent` / `re.split` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:127](../src/echomate_bot/intent_router.py#L127) | `plan_intent` / `re.search` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:130](../src/echomate_bot/intent_router.py#L130) | `plan_intent` / `re.search` | B/C · R02 · `898aa178` |
| [src/echomate_bot/intent_router.py:131](../src/echomate_bot/intent_router.py#L131) | `plan_intent` / `re.search` | B/C · R02 · `898aa178` |
| [src/echomate_bot/intent_router.py:139](../src/echomate_bot/intent_router.py#L139) | `plan_intent` / `re.search` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:145](../src/echomate_bot/intent_router.py#L145) | `plan_intent` / `re.search` | B/C · R02 · `898aa178` |
| [src/echomate_bot/intent_router.py:146](../src/echomate_bot/intent_router.py#L146) | `plan_intent` / `re.search` | B/C · R02 · `898aa178` |
| [src/echomate_bot/intent_router.py:148](../src/echomate_bot/intent_router.py#L148) | `plan_intent` / `re.search` | B/C · R02 · `4169a81d` |
| [src/echomate_bot/intent_router.py:150](../src/echomate_bot/intent_router.py#L150) | `plan_intent` / `re.search` | B/C · R02 · `11bc0aaa` |
| [src/echomate_bot/intent_router.py:154](../src/echomate_bot/intent_router.py#L154) | `plan_intent` / `re.search` | B/C · R02 · `11bc0aaa` |
| [src/echomate_bot/lookup_inquiries.py:19](../src/echomate_bot/lookup_inquiries.py#L19) | `lookup_state_answer` / `re.sub` | C/D? · R04 · `898aa178` |
| [src/echomate_bot/lookup_inquiries.py:23](../src/echomate_bot/lookup_inquiries.py#L23) | `lookup_state_answer` / `re.fullmatch` | C/D? · R04 · `898aa178` |
| [src/echomate_bot/lookup_inquiries.py:34](../src/echomate_bot/lookup_inquiries.py#L34) | `lookup_state_answer` / `re.fullmatch` | C/D? · R04 · `898aa178` |
| [src/echomate_bot/lookup_inquiries.py:41](../src/echomate_bot/lookup_inquiries.py#L41) | `memory_inquiry_answer` / `re.search` | C/D? · R04 · `7ba8d288` |
| [src/echomate_bot/lookup_inquiries.py:43](../src/echomate_bot/lookup_inquiries.py#L43) | `memory_inquiry_answer` / `re.search` | C/D? · R04 · `7ba8d288` |
| [src/echomate_bot/lookup_inquiries.py:44](../src/echomate_bot/lookup_inquiries.py#L44) | `memory_inquiry_answer` / `re.search` | C/D? · R04 · `7ba8d288` |
| [src/echomate_bot/output_policy.py:10](../src/echomate_bot/output_policy.py#L10) | `explicit_code_request` / `re.search` | A/B/C · R13 · `99761cce` |
| [src/echomate_bot/output_policy.py:11](../src/echomate_bot/output_policy.py#L11) | `explicit_code_request` / `re.search` | A/B/C · R13 · `99761cce` |
| [src/echomate_bot/output_policy.py:12](../src/echomate_bot/output_policy.py#L12) | `explicit_code_request` / `re.search` | A/B/C · R13 · `99761cce` |
| [src/echomate_bot/output_policy.py:13](../src/echomate_bot/output_policy.py#L13) | `explicit_code_request` / `re.search` | A/B/C · R13 · `99761cce` |
| [src/echomate_bot/output_policy.py:16](../src/echomate_bot/output_policy.py#L16) | `contains_code` / `re.search` | A/B/C · R13 · `99761cce` |
| [src/echomate_bot/output_policy.py:18](../src/echomate_bot/output_policy.py#L18) | `contains_code` / `re.search` | A/B/C · R13 · `99761cce` |
| [src/echomate_bot/output_policy.py:20](../src/echomate_bot/output_policy.py#L20) | `contains_code` / `re.search` | A/B/C · R13 · `99761cce` |
| [src/echomate_bot/output_policy.py:21](../src/echomate_bot/output_policy.py#L21) | `contains_code` / `re.search` | A/B/C · R13 · `ab22ec3e` |
| [src/echomate_bot/output_policy.py:22](../src/echomate_bot/output_policy.py#L22) | `contains_code` / `re.search` | A/B/C · R13 · `ab22ec3e` |
| [src/echomate_bot/output_policy.py:25](../src/echomate_bot/output_policy.py#L25) | `contains_code` / `re.fullmatch` | A/B/C · R13 · `99761cce` |
| [src/echomate_bot/output_policy.py:28](../src/echomate_bot/output_policy.py#L28) | `invalid_urls` / `re.findall` | A/B/C · R13 · `99761cce` |
| [src/echomate_bot/read_evidence.py:67](../src/echomate_bot/read_evidence.py#L67) | `read_question` / `re.sub` | C/D? · R05 · `11bc0aaa` |
| [src/echomate_bot/read_evidence.py:69](../src/echomate_bot/read_evidence.py#L69) | `read_question` / `re.fullmatch` | C/D? · R05 · `11bc0aaa` |
| [src/echomate_bot/read_evidence.py:70](../src/echomate_bot/read_evidence.py#L70) | `read_question` / `re.search` | C/D? · R05 · `11bc0aaa` |
| [src/echomate_bot/read_evidence.py:71](../src/echomate_bot/read_evidence.py#L71) | `read_question` / `re.fullmatch` | C/D? · R05 · `11bc0aaa` |
| [src/echomate_bot/read_evidence.py:72](../src/echomate_bot/read_evidence.py#L72) | `read_question` / `re.search` | C/D? · R05 · `11bc0aaa` |
| [src/echomate_bot/read_evidence.py:75](../src/echomate_bot/read_evidence.py#L75) | `read_question` / `re.fullmatch` | C/D? · R05 · `11bc0aaa` |
| [src/echomate_bot/read_evidence.py:76](../src/echomate_bot/read_evidence.py#L76) | `read_question` / `re.fullmatch` | C/D? · R05 · `11bc0aaa` |
| [src/echomate_bot/read_evidence.py:77](../src/echomate_bot/read_evidence.py#L77) | `read_question` / `re.fullmatch` | C/D? · R05 · `11bc0aaa` |
| [src/echomate_bot/read_evidence.py:78](../src/echomate_bot/read_evidence.py#L78) | `read_question` / `re.fullmatch` | C/D? · R05 · `11bc0aaa` |
| [src/echomate_bot/routing.py:10](../src/echomate_bot/routing.py#L10) | `prose` / `re.sub` | B/C · R01 · `61dc4580` |
| [src/echomate_bot/routing.py:22](../src/echomate_bot/routing.py#L22) | `grounded_followup` / `re.search` | B/C · R01 · `61dc4580` |
| [src/echomate_bot/routing.py:23](../src/echomate_bot/routing.py#L23) | `grounded_followup` / `re.search` | B/C · R01 · `61dc4580` |
| [src/echomate_bot/routing.py:24](../src/echomate_bot/routing.py#L24) | `grounded_followup` / `re.search` | B/C · R01 · `61dc4580` |
| [src/echomate_bot/routing.py:25](../src/echomate_bot/routing.py#L25) | `grounded_followup` / `re.search` | B/C · R01 · `61dc4580` |
| [src/echomate_bot/routing.py:26](../src/echomate_bot/routing.py#L26) | `grounded_followup` / `re.search` | B/C · R01 · `61dc4580` |
| [src/echomate_bot/routing.py:38](../src/echomate_bot/routing.py#L38) | `grounded_group_followup` / `re.search` | B/C · R01 · `6b369e68` |
| [src/echomate_bot/routing.py:39](../src/echomate_bot/routing.py#L39) | `grounded_group_followup` / `re.search` | B/C · R01 · `6b369e68` |
| [src/echomate_bot/runtime.py:458](../src/echomate_bot/runtime.py#L458) | `switch_model` / `re.fullmatch` | A/B/C · R15 · `826a816f` |
| [src/echomate_bot/runtime.py:727](../src/echomate_bot/runtime.py#L727) | `_ingest` / `re.sub` | A/B/C · R15 · `6b369e68` |
| [src/echomate_bot/runtime.py:729](../src/echomate_bot/runtime.py#L729) | `_ingest` / `re.escape` | A/B/C · R15 · `6b369e68` |
| [src/echomate_bot/runtime.py:729](../src/echomate_bot/runtime.py#L729) | `_ingest` / `re.escape` | A/B/C · R15 · `6b369e68` |
| [src/echomate_bot/runtime.py:774](../src/echomate_bot/runtime.py#L774) | `_ingest` / `re.fullmatch` | A/B/C · R15 · `a854d0a4` |
| [src/echomate_bot/runtime.py:815](../src/echomate_bot/runtime.py#L815) | `_ingest` / `re.search` | A/B/C · R15 · `e5cf00f0` |
| [src/echomate_bot/runtime.py:1430](../src/echomate_bot/runtime.py#L1430) | `_process` / `re.search` | A/B/C · R15 · `701b9470` |
| [src/echomate_bot/runtime.py:1520](../src/echomate_bot/runtime.py#L1520) | `_process` / `re.sub` | A/B/C · R15 · `ab22ec3e` |
| [src/echomate_bot/runtime.py:1665](../src/echomate_bot/runtime.py#L1665) | `_process` / `re.findall` | A/B/C · R15 · `99761cce` |
| [src/echomate_bot/runtime.py:1717](../src/echomate_bot/runtime.py#L1717) | `delivery_current` / `re.search` | A/B/C · R15 · `d6bd50e1` |
| [src/echomate_bot/social.py:140](../src/echomate_bot/social.py#L140) | `direct_signal` / `re.match` | B/C · R14 · `6dd3ba21` |
| [src/echomate_bot/social.py:240](../src/echomate_bot/social.py#L240) | `packet` / `re.search` | B/C · R14 · `6dd3ba21` |
| [src/echomate_bot/social.py:241](../src/echomate_bot/social.py#L241) | `packet` / `re.sub` | B/C · R14 · `6dd3ba21` |
| [src/echomate_bot/social.py:259](../src/echomate_bot/social.py#L259) | `validate_social` / `re.search` | B/C · R14 · `826a816f` |
| [src/echomate_bot/summarization.py:9](../src/echomate_bot/summarization.py#L9) | `history_candidate` / `re.search` | A/B/C · R10 · `ab22ec3e` |
| [src/echomate_bot/summarization.py:65](../src/echomate_bot/summarization.py#L65) | `suitable` / `re.sub` | A/B/C · R10 · `ab22ec3e` |
| [src/echomate_bot/summarization.py:66](../src/echomate_bot/summarization.py#L66) | `suitable` / `re.sub` | A/B/C · R10 · `ab22ec3e` |
| [src/echomate_bot/summarization.py:67](../src/echomate_bot/summarization.py#L67) | `suitable` / `re.search` | A/B/C · R10 · `ab22ec3e` |
| [src/echomate_bot/summarization.py:81](../src/echomate_bot/summarization.py#L81) | `answer` / `re.findall` | A/B/C · R10 · `ab22ec3e` |
| [src/echomate_bot/summarization.py:89](../src/echomate_bot/summarization.py#L89) | `answer` / `re.search` | A/B/C · R10 · `ab22ec3e` |
| [src/echomate_bot/summarization.py:104](../src/echomate_bot/summarization.py#L104) | `answer` / `re.sub` | A/B/C · R10 · `4169a81d` |
| [src/echomate_bot/summary_fidelity.py:30](../src/echomate_bot/summary_fidelity.py#L30) | `check_fidelity` / `re.search` | B/C/D? · R09 · `f0d199f5` |
| [src/echomate_bot/summary_fidelity.py:31](../src/echomate_bot/summary_fidelity.py#L31) | `check_fidelity` / `re.search` | B/C/D? · R09 · `f0d199f5` |
| [src/echomate_bot/summary_fidelity.py:32](../src/echomate_bot/summary_fidelity.py#L32) | `check_fidelity` / `re.search` | B/C/D? · R09 · `f0d199f5` |
| [src/echomate_bot/summary_fidelity.py:35](../src/echomate_bot/summary_fidelity.py#L35) | `check_fidelity` / `re.search` | B/C/D? · R09 · `1c64c86f` |
| [src/echomate_bot/summary_fidelity.py:36](../src/echomate_bot/summary_fidelity.py#L36) | `check_fidelity` / `re.search` | B/C/D? · R09 · `1c64c86f` |
| [src/echomate_bot/summary_fidelity.py:36](../src/echomate_bot/summary_fidelity.py#L36) | `check_fidelity` / `re.search` | B/C/D? · R09 · `1c64c86f` |
| [src/echomate_bot/summary_fidelity.py:37](../src/echomate_bot/summary_fidelity.py#L37) | `check_fidelity` / `re.search` | B/C/D? · R09 · `1c64c86f` |
| [src/echomate_bot/summary_fidelity.py:38](../src/echomate_bot/summary_fidelity.py#L38) | `check_fidelity` / `re.search` | B/C/D? · R09 · `1c64c86f` |
| [src/echomate_bot/summary_fidelity.py:38](../src/echomate_bot/summary_fidelity.py#L38) | `check_fidelity` / `re.search` | B/C/D? · R09 · `1c64c86f` |
| [src/echomate_bot/summary_fidelity.py:40](../src/echomate_bot/summary_fidelity.py#L40) | `check_fidelity` / `re.search` | B/C/D? · R09 · `1c64c86f` |
| [src/echomate_bot/summary_fidelity.py:40](../src/echomate_bot/summary_fidelity.py#L40) | `check_fidelity` / `re.search` | B/C/D? · R09 · `1c64c86f` |
| [src/echomate_bot/summary_fidelity.py:45](../src/echomate_bot/summary_fidelity.py#L45) | `check_fidelity` / `re.search` | B/C/D? · R09 · `08415bbd` |
| [src/echomate_bot/summary_fidelity.py:46](../src/echomate_bot/summary_fidelity.py#L46) | `check_fidelity` / `re.search` | B/C/D? · R09 · `08415bbd` |
| [src/echomate_bot/summary_fidelity.py:47](../src/echomate_bot/summary_fidelity.py#L47) | `check_fidelity` / `re.search` | B/C/D? · R09 · `08415bbd` |
| [src/echomate_bot/summary_fidelity.py:47](../src/echomate_bot/summary_fidelity.py#L47) | `check_fidelity` / `re.search` | B/C/D? · R09 · `08415bbd` |
| [src/echomate_bot/summary_fidelity.py:49](../src/echomate_bot/summary_fidelity.py#L49) | `check_fidelity` / `re.search` | B/C/D? · R09 · `1c64c86f` |
| [src/echomate_bot/summary_fidelity.py:50](../src/echomate_bot/summary_fidelity.py#L50) | `check_fidelity` / `re.search` | B/C/D? · R09 · `1c64c86f` |
| [src/echomate_bot/summary_fidelity.py:50](../src/echomate_bot/summary_fidelity.py#L50) | `check_fidelity` / `re.search` | B/C/D? · R09 · `1c64c86f` |

색인의 commit은 현재 행의 마지막 변경(blame) 근거이며, 그 자체를 최초 설계 원인/정확성 증명으로 보지 않는다. 원래 사고·도입 의도는 가족별 기존 QA·회귀와 함께 추적한다. 최신 작업 행의 값이0이면 미커밋 상태의 행을 뜻한다.
