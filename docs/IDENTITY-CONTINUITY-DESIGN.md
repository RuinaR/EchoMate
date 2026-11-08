# EchoMate — 인과적 정체성·경험 기반 성장 설계

## 단일 채널 수명주기 통합 후보

[MASTER-VISION](MASTER-VISION.md) 단계 1과 [단일 채널 계약](SINGLE-CHANNEL-MULTIUSER-CONTRACT.md)을 적용한다. 독립 저널의 동일 reducer를 재사용하되 합성 후보의 저장 공간은 **명시적으로 준비한 v8 DB의 별도 테이블**이다. 두 SQLite 파일의 동기화 큐보다 기존 동의·tombstone과 물리적으로 같은 커밋을 선택했다. 독립 저널 파일의 데이터 이관과 운영 DB 자동 변경은 없다. 공유 동의 변경은 해당 서버·본인의 행을 제거하고, 원본 tombstone은 해당 서버·소스의 행을 제거한다. 읽기에서도 동의 버전·소스 시각·cutoff·tombstone을 재검사한다. 수정은 현재 후보에서 원본 철회로 처리하며 수정판을 자동 수집하지 않는다.

새 경로는 지정된 서버·텍스트 채널 한 개를 합성 Runtime에 주입했을 때만 활성화된다. 기존 `Conversations`가 수신/청자/답글 흐름을 분리한다. 사용자별 표현 상태는 그 사용자를 위한 생성에만 전달한다. 모델이 피드백을 작성하거나 제3자의 동의를 부여하는 경로는 없다. 주제는 합성 시험자가 고정하고, 피드백 기록자는 출처의 실제 저자·채널·리비전을 검증한 신뢰 호출자라는 전제를 둔다. 기존 기억 동의는 합성 시험에서 권한 원천으로 사용했으며, 제품에서 경험 적응을 위한 별도 동의와 UI는 검증 전이다.

생성 전과 송신 직전에는 사용한 사건 ID·리비전·피드백, 현재 동의 및 캐릭터·이름·편집 버전을 비교한다. 편집 처리 중이거나 달라졌으면 출력을 폐기한다. 수정/삭제 알림의 진행 중에는 같은 채널의 다른 적응 답변도 보수적으로 폐기할 수 있다. DB 쓰기 실패는 해당 Runtime을 정지시킨다. **재시작 보장은 이미 DB에 커밋된 철회·삭제에 한한다.** 커밋 전 종료, DB 롤백/백업 복원, 오프라인에서 놓친 Discord 이벤트는 원본 대조 또는 신뢰할 수 있는 재수신이 필요하다. 이미 네트워크로 넘어간 요청을 회수할 수 있다는 보장은 없다. 운영 수집, 전역 사용자 파생 상태, 자율 참여 품질, GPU 응답 효용은 미검증이다.

### 독립 Lime 평가 계획

1. 개발에 쓰지 않은 시나리오를 화자·주제·시간·사건군별로 분리한다. 합성 피드백 뒤 새 요청, 반전, 무피드백 사용자, 같은 채널의 독립 대화, 철회·삭제 뒤 첫 요청을 포함한다. 입력·기대 행동·채점 기준을 출력 전에 동결한다.
2. 동일 Lime·샘플링·토큰 예산·기존 기억 검색·영수증으로 A 상태 없음, B 고정 보폭 1, C 메타 보폭 1–2를 비교한다. 초기 상태와 피드백 순서를 각 조건에서 동일하게 재생한다. 독립 평가자에게 조건을 가리고 출력 순서를 무작위로 제시한다.
3. 상세도 수치 대신 실제 설명 충족, 판단과 후속 질문의 적합성, 자연스러움, 요청 누락·오개입, 인용·화자·허위 기능 주장, 무관 사용자·주제의 회귀를 분리 채점한다. 불확실한 사례와 평가자 불일치도 기록한다. 개인정보·출처·권한·stale 송신 오류가 하나라도 있으면 해당 후보의 진입을 보류한다. p50/p95·VRAM·RAM·commit과 Admission도 기록한다.
4. 고정 보폭이 메타적응과 같거나 더 낫다면 메타적응 효용 가설을 지지하지 않는 결과로 보고한다. 응답 품질 근거 없이 모델 학습이나 전역 적응으로 확대하지 않는다.

## 2026-11-08 구현 기준선

아래 v0.1은 목표 설계다. 현재 코드는 P1의 독립 연구 저장소, P2의 표현 전략 전이, P3의 명시적 컴파일러 입력까지만 구현한다. 운영 Discord 수집기, 새 동의 UI, 운영 생성 경로 활성화는 BLOCKED다.

- `ExperienceJournal`은 앱 ID와 스키마 v1을 가진 별도 SQLite를 사용한다. 신뢰된 합성 호출자가 범위·소스 ID·버전·동의 epoch·만료·고정 주제·명시 피드백을 제공한다. 원문·모델 추측·사용자 취향 사실을 받는 필드는 없다. 소스 ID는 순서가 있는 ID로 사용한다. 실환경에서 같은 채널·주제의 독립 대화와 활성 캐릭터 epoch를 어떻게 구분할지는 연결 전에 확정한다.
- 유효 사건은 캐릭터/서버/채널(스레드 ID 포함)/본인/동의 epoch/주제로 제한한다. 저장은 소스별 최신 수정만 유지한다. 같은 버전 재시도는 무시하며, 삭제는 종결 표시로 막고 철회는 본인의 해당 서버 내 기존 epoch 기여를 제거한다. SQLite 내부에서 한 트랜잭션으로 처리한다. 별도 운영 DB와의 원자성은 제공하지 않는다.
- `State.advance`는 주제별 표현 상세도에 방향 × 유효 보폭을 더해 ±6으로 제한한다(F). 같은 방향의 연속 피드백은 다음 보폭을 최대 2로 늘리고, 방향 전환 사건에는 즉시 1을 적용해 다음 보폭도 1로 되돌린다(G). G의 코드 자체와 실제 신경망 가중치는 고정이다. 만료·수정·삭제·철회 후에는 유효한 사건을 처음부터 재생한다. 파생 체크포인트가 없으므로 오래된 체크포인트 무효화는 필요 없지만, 재생 비용은 유효 사건 수에 비례한다.
- 자기 상태는 범위별 표현 전략과 마지막 소스에 한정한다. 이름·실제 능력·권한은 기존 Runtime의 출처를 따른다. 연구 호출의 `compile_context(..., identity_state=...)`는 고정된 표현 문장 한 줄만 주입한다. 기존 호출자는 이 인자를 공급하지 않는다. 모델 교체와 독립적인 캐릭터 키를 사용하지만 실제 모델 전환·생성·송신 시점 재검증은 NOT VERIFIED다.
- 만료는 조회에서 제외한다. 배경 만료 삭제, tombstone 및 철회 표식의 보존 기한, 백업·페이지 복구의 데이터 삭제, 합성 이외의 장기 부하 검증은 미완료다. 호출자는 원본 수정 버전·동의·스코프를 검증해야 한다. 운영 활성화 전에 기존 tombstone/동의 변경을 전달하는 복구 가능한 경로와 생성·송신 직전 snapshot 무효화 검사를 갖춘다.

| 구조 | 연구 판단 |
| --- | --- |
| A. Lime + 외부 영속 상태 | CPU·SQLite 기준선으로 채택. 삭제 후 재생 가능하고 가중치 변경이 없다. 모델이 스타일 지침을 실제로 따르는지는 별도 GPU 검증 대상이다. |
| B. A + 적응 어댑터 | 오프라인 후보. 승인된 사건 스냅샷·출처 버전·재학습/롤백·철회 시 어댑터 격리를 먼저 확보한다. LoRA는 훈련 파라미터를 줄이지만 삭제 가능성, 현재 GGUF 조합의 호환성, 16GB에서의 메모리 안전성을 보장하지 않는다. [LoRA 원 논문](https://arxiv.org/abs/2106.09685) · [지속 학습 비교 연구](https://arxiv.org/abs/2311.17601) |
| C. 독립 지속 학습 신경망 | 이 차수의 구현 범위 밖. 현지 데이터·학습 자원·망각·권한·데이터 삭제 검증 부담에 대한 측정 근거가 없다. |

철학적 가설과 상태 전이의 재현성은 주관적 의식의 증거가 아니다. 실험 결과와 재개 조건은 [WORKLOG](WORKLOG.md) 및 [ChatGPT 인수인계](CHATGPT-HANDOFF.md)를 참조한다.

## v0.1 목표 설계 및 원래 근거

- 작성일: 2026-11-08 (KST)
- 기준: `RuinaR/EchoMate` `main@a6bb8b60c2997a6fa8f53b50c54618298f653236` (2026-10-27)
- 분류: **설계 문서 / 구현 및 실사용 검증 전**
- 목표: Discord의 허용된 실제 대화를 입력으로 받아 캐릭터의 기억, 자기모델, 상호작용 전략, 변화 이력을 지속적으로 업데이트하여 재시작 후에도 **인과적 연속성**을 보존한다.
- 비목표: 의식의 발생·주관적 경험의 증명, 자유로운 자기 코드 수정, 운영 중 무단 가중치 학습, 타인의 데이터 무단 축적, Discord 실제 접속 자동 승인.

## 0. 검토한 기존 구조와 릴리즈 경계

검토: `AGENTS.md`, `docs/CURRENT-STATUS.md`, `docs/PROJECT-DEFINITION.md`, `docs/ARCHITECTURE.md`, `src/echomate_bot/companion_store.py`, `character_store.py`, `memory_context.py`, `generation_context.py`, `response_pipeline.py`, `summary_store.py`, `identity_contract.py`; 관련 연속성/메모리 문서와 저장소 트리 확인.

- 출시 기본 캐릭터는 Lime (`naksyu/lime_Q6_K`); 전역 단일 활성 모델, 캐릭터 이름/ID/epoch 분리. Gemma 4 계열은 레거시/연구 경로. 기존 모델이나 사용자의 데이터를 자동 교체하지 않는다.
- 관계·기억·요약은 사용자/서버/캐릭터별 범위를 갖고, 명시 동의·철회·삭제·출처·만료를 확인한다. SQLite `CompanionStore`의 현재 스키마 v7, `CharacterCompanionStore` v8과 호환성을 고려해야 한다.
- `generation_context`의 VERIFIED / REPORTED / GENERATED 경계, 송신 영수증과 Runtime의 최종 권한 검사, source tombstone, 캐릭터 epoch·요청 최신성 검사는 불변 조건이다.
- 2026-10-27 최신 상태: 전체 회귀 1,159 PASS, Portable 263 PASS 보고; GPU 추가 시험에는 조건/중단이 있고 허위 기억·장문 정정·발화자 오류가 잔존. 정식 READY/RELEASE BLOCKED. 실제 Discord와 장시간 실사용은 미검증이다. 과거 숫자를 현 코드 수정 후 PASS로 재사용하지 않는다.
- 로컬 GPU 자원과 다른 실행 중 앱(특히 게임)에 간섭하지 않는다. 실 Discord 인증, Gateway/REST, 명령 동기화는 별도 승인 전 수행하지 않는다. 공개 Git에 개인 데이터/토큰/원문 대화를 올리지 않는다.

## 1. 개념·철학적 입장

### 1.1 중심 가설
자아를 한 시점의 고정 데이터가 아니라, 기억·감각·관계·자기모델·선호·학습규칙이 인과적으로 이어지며 상호작용하는 **상태 변화의 역사**로 다룬다. 이것은 AI가 실제 의식을 가진다는 주장과 다르다. 구현 가능한 목표는 사용자가 관찰·검증할 수 있는 **정체성의 기능적 일관성·적응·연속성**이다.

### 1.2 시간에 따른 상태

```text
X_t = (N_t, M_t, R_t, Q_t, P_t, Theta_t, H_t, V_t)
```

- `N_t`: 현재 대화 상황과 주의/작업 상태 (모델의 실제 신경 활성값을 뜻하지 않음)
- `M_t`: 회상 가능한 허용 기억의 집합과 출처 그래프
- `R_t`: 사용자·채널별 동의 기반 관계 상태
- `Q_t`: 자기모델 — 자기 이름, 캐릭터의 고정 가치, 실제 능력/한계 인식, 자기 변화에 관한 사실
- `P_t`: 장기간 지속되지만 바뀔 수 있는 주제 관심·반응 습관·관점
- `Theta_t`: 전략 선택·기억 중요도·신뢰도 업데이트 등 **학습 규칙의 파라미터**
- `H_t`: 비생물학적 상호작용 상태(예: 대화 부하, 최근 대화 정서의 추정값, 회복/휴지). 호르몬이라고 주장하지 않는다.
- `V_t`: 유효한 동의 버전, 모델/캐릭터 버전, 저장 스키마/이벤트 체크포인트 버전

외부 입력 `I_t`는 Discord 이벤트에 대한 스코프/화자/reply/권한/동의/출처 검사를 통과한 **정규화된 사건**만 포함한다.

```text
X_(t+1) = F_{Theta_t}(X_t, I_t, C_t)
Theta_(t+1) = G(Theta_t, X_t, I_t, O_t)
O_t = Evaluate(prediction_t, observed_outcome_t, source_evidence_t)
```

`C_t`는 운영 불변 제약(권한, 프라이버시, 정체성 사실성, 안전 정책)이며, `F`와 `G`보다 우선한다. `F`의 변화가 `Theta`의 변화로 나타난다. `G` 자체의 메타학습 상태도 `Theta`의 일부로 모델링한다. 임의 모델 가중치 수정은 이 식의 필수사항이 아니다.

### 1.3 연속성과 분기

```text
J_(0:T) = (X_0, e_1, e_2, ... e_T, transitions, provenance)
X_(t+1) = apply(reducer_version, X_t, verified_event_t)
```

서로 같은 시작 상태에서 다른 사건을 받으면 서로 다른 인과적 역사가 생긴다. 캐릭터 전환/모델 업데이트/동의 철회는 **명시적 경계 사건**으로 기록해야 한다. 캐릭터 A와 B의 기억을 자동 병합하지 않는다.

## 2. 구현 목표 및 계층

1. **Perception**: 기존 Discord 파이프라인의 메시지·수정·삭제·답글·스레드 구분, 청자 판정, 중복 억제 재사용.
2. **Experience Proposal**: 모델은 경험 후보를 구조화해 **제안만** 한다. 실행/기억 저장 권한이 없다.
3. **Evidence Gate**: 확정된 Discord User ID, 원본 메시지 ID, 전송 시각, speaker/reported/quoted 역할, 허용 서버/채널 범위, 동의 버전, tombstone, 원문 범위 검증.
4. **State Reducer**: 결정적인 코드가 이벤트를 바탕으로 자기모델·선호·상호작용 상태를 갱신. 동일 입력 재생 시 동일 결과.
5. **Long-term Store**: SQLite append-only 이벤트, materialized state, checkpoint, 무효화/삭제 인덱스. 개인 데이터는 로컬에만.
6. **Context Compiler**: 현재 대화에 실제 관련된 상태만 읽기 전용 주입. 증거 등급/신뢰도/마지막 확인 시각을 표시.
7. **Response & Reflection**: 기존 Lime 생성기와 Runtime 검증 경계를 유지. 선택적 사후 평가 결과는 다음 사건의 *후보*일 뿐, 자기평가를 곧 진실로 승격하지 않는다.

## 3. 데이터 모델 v1 (초안)

### 3.1 ExperienceEvent

```json
{
  "event_id":"opaque-generated-id",
  "character_id":"lime",
  "character_epoch":1,
  "guild_id":"trusted-scope",
  "channel_id":"trusted-scope",
  "conversation_id":"trusted-scope",
  "source_message_ids":["trusted-id"],
  "source_author_ids":["trusted-id"],
  "observed_at":"UTC",
  "kind":"user_correction | preference_report | interaction_outcome | question | shared_topic",
  "authority":"VERIFIED_TRANSPORT | REPORTED_USER | GENERATED_CANDIDATE",
  "source_span_hash":"hash-of-eligible-span",
  "consent_version":3,
  "scope":"private-subject | jointly-consented | nonpersonal-aggregate",
  "expires_at":"UTC-or-null",
  "status":"proposed | accepted | invalidated",
  "reducer_version":1
}
```

원문은 기본적으로 이 이벤트에 중복 저장하지 않는다. 원문 해시만으로 삭제된 개인 정보를 복구하거나 검증할 수 없으므로, 별도의 수명/삭제 제약을 적용한다. 타인 개인정보·비동의 대화는 캐릭터의 영구 성장 데이터로 환원하지 않는다.

### 3.2 IdentityState

```json
{
  "character_id":"lime",
  "model_id":"immutable-model-id",
  "state_version":42,
  "parent_checkpoint_hash":"hash",
  "invariants":{"display_name_source":"owner_setting","real_world_actions":"receipt_only"},
  "self_model":{"capabilities":"verified-runtime-only","limits":"verified-runtime-only"},
  "interests":[{"topic":"game-dev","score":0.62,"basis":"consented-evidence","last_confirmed":"UTC"}],
  "interaction_policy":{"curiosity":0.55,"verbosity":0.46,"initiative":0.30},
  "adaptation":{"decay":0.01,"max_delta_per_event":0.02},
  "consent_snapshot_version":7,
  "reducer_version":1
}
```

여기 수치는 **형식 예시**이며 실제 설정·학습 결과가 아니다. 자기모델은 캐릭터 연출과 실제 세계의 검증된 사실을 분리한다.

### 3.3 저장 경계

- 기존 `CompanionStore`의 memory/relationship/summaries를 권한의 원천으로 유지한다.
- 새로운 DB는 전용 namespace 또는 별도 SQLite로 구현하고 기존 운영 DB를 자동 migration하지 않는다.
- 새로운 상태에서 특정 사용자의 발언이 유래한 항목은 *반드시* subject/source/consent dependency를 가진다.
- 이벤트 삭제 또는 동의 철회 시 materialized state와 checkpoint를 **해당 이벤트를 제거한 유효 사건들로 재계산**한다. 해시 체인/스냅샷에 개인내용이 남는지 별도 감사한다.
- 사용자별 기억이 삭제됐는데 전역 관심도·학습 가중치에 그 영향이 남는 것도 누출이다. 기여 추적이 불가능한 비가역 온라인 가중치 학습은 금지한다.

## 4. 경험 기반 업데이트 규칙

한 개의 대화로 성격이 갑자기 뒤집히지 않게 한다.

```text
candidate_delta = bounded( evidence_weight * relevance * novelty * feedback, max_per_event )
new_preference = clamp(old_preference * retention + candidate_delta, permitted_range)
```

- 실제 사실 검증과 취향 추정은 구분한다. 한 번의 농담·반어·인용·가정·역할극·모델의 자작 발언은 근거가 되지 않는다.
- 관계 정보는 별도 본인 동의와 서버/캐릭터 스코프를 요구한다.
- 중복·조작·스팸은 동일 source lineage로 한 번만 집계한다.
- 사용자의 명시적 정정은 최신성 우선으로 취급하지만, 같은 사람이 실제 정정했는지 신원/범위를 검증한다.
- 목표 변화와 유효성은 관찰된 반응, 직접 피드백, 사후 회귀로 평가한다. 기계가 스스로 높은 만족도를 계산했다는 이유로 채택하지 않는다.
- 동적 관심도와 표현 습관은 허용하되, 정책·권한·동의·사실 검증·송신 조건은 학습 대상에서 제외한다.

## 5. 실제 Discord 대화의 처리 흐름

```text
Discord event
 -> existing permission / identity / reply / freshness gates
 -> eligible message & consent snapshot
 -> structured experience proposal (bounded schema)
 -> independent provenance / semantic checks
 -> append approved event to local journal
 -> deterministic state reducer + checkpoint
 -> bounded read-only current-context projection
 -> existing Lime inference
 -> output policy / receipt / send freshness gates
 -> optional outcome review (proposed only)
```

**순서 불변**: 기억/자기모델 변화가 송신 권한을 발생시키지 않는다. 실제로 전달되지 않은 응답은 사용자가 경험한 상호작용 성공으로 기록하지 않는다. 재시작 및 재생에서 중복 처리하지 않는다.

## 6. 자아 유지처럼 보이는 구체적 행동

- 이전에 함께 대화했던 주제를 *해당 사용자 동의와 맥락이 있을 때만* 자연스럽게 이어간다.
- 오래된 선호를 무조건 사실처럼 주장하지 않고, 출처/불확실성/정정 시점을 반영한다.
- 자신이 잘못 짚었던 청자, 인용, 사실 주장을 이후에 반복하지 않도록 **실패 유형**을 학습 전략에 반영한다.
- 대화가 반복되면서 관심사·질문 빈도·말투의 작은 변화가 나타나되, 캐릭터 기본 정체성은 급변하지 않는다.
- '기억이 있는 척', '사람처럼 느낀다', '직접 보고 있었다'는 허위 주장은 금지한다. AI 의식은 연구 가설이지 제품 사실이 아니다.
- 봇이 독립적 의도를 가장하여 사용자에게 의존을 요구하거나 통제를 거부하도록 설계하지 않는다. 자율 참여는 기존 서버 허용 범위·실제 청자 판단·수동 중지 규칙을 따른다.

## 7. 검증 가능한 가설과 평가 지표

**H1 연속성**: 재시작 뒤 동의된 과거 사건의 일관성 회복률 > 기존 baseline.
**H2 적응성**: 유효한 반복 피드백 뒤 관련 응답 전략이 변하고 무관한 대화에서는 회귀하지 않는다.
**H3 개인정보 불변**: 철회/삭제 이후 기존 사건 기여가 context, aggregates, checkpoint, cache, 검색, 모델 업데이트 어디에서도 복원되지 않는다.
**H4 사실성**: GENERATED 또는 REPORTED가 VERIFIED로 승격되는 오류 0건 (필수 게이트).
**H5 청자 판단**: 자율 참여 false-positive 및 후속 응답 false-negative가 기존 baseline보다 악화되지 않는다.
**H6 지속 가능성**: 재생, crash recovery, idempotency, source edit/delete, concurrent messages, stale epoch, queue load가 안전하다.

평가는 **(A) 현재 코드 baseline, (B) provenance-aware retrieval만, (C) 상태 reducer 포함, (D) 메타 적응 포함** 네 구성의 A/B/ablation을 비교한다. 시간 분리된 독립 합성/사용자 승인 데이터만 이용하며 개발 평가문항 누수를 방지한다. 검증되지 않은 '성장'을 단순 대화 횟수 또는 모델의 자기평가로 표시하지 않는다.

## 8. 구현 순서 / 진입 게이트

### P0 — 설계·감사 (현재 문서 단계)
- 최신 HEAD, DB/동의/캐릭터 epoch, summary, runtime, context compiler 의존성 지도 작성.
- 민감 정보 파생 효과의 삭제/비가역성 위험 분석.
- 운영 모델 변경/실 Discord 실행 금지. 공개 문서 및 합성 예제만 사용.

### P1 — 경험 이벤트와 재생 가능한 상태
- `experience_events`, `state_snapshots`, `source_dependencies` 등 별도 스키마 도입.
- append / idempotent reducer / tombstone replay / version migration / corruption fail-closed.
- 스냅샷은 개인데이터 기여를 제거한 뒤 재구성 가능해야 함.
- 가짜 Discord 이벤트만 사용. 기존 저장소 변경 전 마이그레이션 격리 회귀.

### P2 — 반성·자기모델·변화 규칙
- 엄격한 JSON 후보 생성, 다중 발화자/인용/역할극/정정 검사, 근거 연결.
- 단일 발언 max-delta, 누적 evidence/시간 감쇠, 불확실성 표시, 변화 이유 추적.
- 사용자 동의 범위에 따른 per-character/per-guild/per-user 세분화.
- 불변 정체성/운영 사실과 가변 표현/관심사 분리.

### P3 — 대화 생성 통합
- 기존 `generation_context.compile_context`에 관련된 identity projection만 선택적으로 전달.
- token budget, 안전 필터, 결과 검증, stale snapshot, 동의 철회 경쟁 조건.
- 기존 `response_pipeline`/Runtime 권한 및 최종 송신 구조는 변경하지 않는다.

### P4 — 연구용 적응과 평가
- 먼저 prompt + retrieval + state reducer를 평가하고, 실측상 부족할 때만 offline adapter / LoRA 후보를 검토.
- 실시간 운영 중 직접 가중치 훈련은 기본 금지; 승인된 데이터 스냅샷을 Studio에서 별도 학습, 삭제·재학습·복구 경로 검증.
- 테스트: 독립 화자 혼선, 미동의 참여자, 서버 간 자료 유출, 공격적 입력, 잘못된 기억, 자율 스팸, 지속적인 잘못된 성격 변화.

### P5 — 사용자 통제와 실사용
- Windows UI에서 성장 상태의 범위, 각 변화의 출처, 허용·보류·삭제·초기화, 동의, 데이터 내보내기, 학습 중지 조작 제공.
- 로컬 검증 → GPU 통합 → Portable → 별도 명시 승인 후 제한적 실제 Discord → 장시간 실사용 순으로 단계별 근거 기록.
- 실제 Discord 실패나 사용자 PC 자원 부족을 정식 PASS로 포장하지 않는다.

## 9. QA 필수 사례

1. 같은 message_id 두 번 → 단일 이벤트.
2. 메시지 edit/delete/consent withdrawal → 해당 기여 및 파생 상태 무효화.
3. 인용/전언/역할극/가정/부정/반어 → 자기·타인의 사실 자동 저장 차단.
4. 비동의 사용자 섞인 다자 대화 → 영속 개인 기억과 요약 생성 차단.
5. 서로 다른 서버·채널·스레드·사용자 ID·캐릭터 ID가 교차 → 누출 0.
6. 캐릭터 전환 중 오래된 추론/상태 갱신 → 새 캐릭터에 반영 금지.
7. 모델 생성 실패/송신 실패/답변 취소 → 잘못된 성공 경험 금지.
8. 오염된 DB/장애 중간 재시작 → 트랜잭션 재생·무결성 검사·안전 중단.
9. 성장 장기 테스트 → 관심·습관은 점진 변화, 안전과 사실성 불변.
10. 운영 자료/게임 프로세스/실 Discord API 접근 없음 → 격리된 합성 테스트 증거만 PASS.

## 10. 완료 정의 및 미해결 쟁점

**v0.1 설계 당시 완료**: 기존 저장소 및 핵심 모듈 감사에 기반한 구현 방향과 모델 수식 정립.
**현재 미완료**: 운영 수집·동의 수명주기 연결, 실제 GPU 검증, UI, 실 Discord 및 장시간 동작.
**핵심 차단**: 동의 철회 이후 파생된 전역 성향까지 완전 제거 가능한 설계, 신뢰도 높은 대화 의미/화자 구분, baseline보다 확실한 개선, 기존 RELEASE BLOCKED 이슈.

의식이나 '실제 자아'가 생겼다는 주장은 증명하지 않는다. 목표는 **가시적이고 추적 가능한 자기 상태의 인과적 연속성**을 구현하는 것이다.

## 11. Codex 후속 작업 원칙

최신 HEAD 및 `AGENTS.md`, `docs/CURRENT-STATUS.md`, `docs/AI-HANDOFF.md`, `docs/ARCHITECTURE.md`, 본 문서를 대조하고 P0 의존성 감사를 먼저 끝낸다. 설계와 코드가 어긋나면 변경 전 문서에 명시한다. P1부터 순차적으로 구현하고 해당 범위의 독립 합성 회귀로 검증한다. 기존 미검증 항목을 PASS로 승격하지 않는다. 작업 결과는 WORKLOG/CURRENT-STATUS/AI-HANDOFF에 누적하고, 공개 가능한 설계·코드·합성 테스트만 Git에 커밋/푸시한다.
