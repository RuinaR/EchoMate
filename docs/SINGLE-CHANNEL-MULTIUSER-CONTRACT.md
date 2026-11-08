# EchoMate — 단일 Discord 채널·다중 사용자 사회적 환경 계약 (v1.0)

> 2026-11-08 KST / 최초 기준 `main@8abea5b`
> [MASTER-VISION](MASTER-VISION.md)의 운영 범위를 구체화한다. **최종 운영 범위는 사용자가 지정한 한 개의 Discord 텍스트 채널**이다. 기존 다른 채널 지원 코드는 폐기하지 않지만, 신규 정체성·경험 학습을 다른 채널/스레드/DM으로 확장하지 않는다. 테스트 및 관리자 설정에서 채널 변경은 명시적인 별도 작업이다.

## 1. 최종 운영 범위

- Windows 로컬 앱에서 서버 ID와 텍스트 채널 ID를 명시적으로 하나 지정한다. 채널 이름이나 사용자 닉네임은 권한·신원의 근거가 아니다.
- 대상 채널에서 접근 가능한 메시지·수정·삭제·원본 reply·멘션·Unicode Reaction을 공식 Discord Bot 권한 내에서 처리한다. 필요 없는 의도적 전 서버 히스토리 크롤링, DM 접근, 다른 채널/스레드의 대화 수집, 전역 사용자 추적은 하지 않는다.
- 스레드는 독립된 channel ID로 취급하므로 **초기 운영 범위에서 제외**한다. 동일 채널 내 reply 연결은 포함한다. 향후 스레드 상속은 명시적인 설계 변경과 별도 동의를 요구한다.
- 메시지 수신, 대화 참여, 장기 기억/학습 기록은 서로 다른 권한이다. '볼 수 있음'이 '기억해도 됨'을 뜻하지 않는다.
- 한 채널 내 여러 사람이 동시에 말할 수 있다. 채널 하나가 대화 하나라는 가정은 금지한다.
- 봇 자체의 새 메시지로 무한 응답하지 않으며 다른 봇/웹후크 콘텐츠는 기본적으로 비신뢰 입력으로 취급한다.

## 2. 세 층의 상태와 인과적 소유권

```text
GlobalAgentState [한 개의 EchoMate 캐릭터 인스턴스]
   ├─ verified self / actual capabilities / operating policy
   ├─ nonpersonal strategy / adapter candidate (개인기여 분리 가능할 때만)
   └─ immutable safety, consent, channel and send constraints

ConversationState[channel_id, conversation_id]
   ├─ active topic, participants, directed replies, uncertainty
   └─ short-lived turn graph, dedup and freshness

ParticipantState[guild_id, user_id, character_id]
   ├─ per-user consent/version and source-provenanced memories
   ├─ relationship style and corrections
   └─ reversible contributions to any global adaptive feature
```

참여자 A가 '자세히 설명해줘'라고 했다고 그 특성을 채널 내 B에 적용하지 않는다. 공유된 사회적 맥락은 실제 공통 대화로 확인된 경우에만 제한적으로 사용한다. 개인의 취향, 민감한 추론, 관계정보를 전역 에이전트 성향에 무단 혼합하지 않는다. 다른 사용자의 학습 기여를 나중에 제거할 수 없다면 전역 변경을 발생시키지 않는다.

## 3. 다중 화자 인과적 대화 그래프

각 사건은 `guild_id, channel_id, message_id, author_id, timestamp, edited_at, reply_to_message_id, mention_user_ids, bot_message_id, conversation_id?, source_text_span, consent_version, character_epoch, source_revision` 등을 보존하는 정규화된 관측으로 표현한다. `conversation_id`는 **추론 결과**이지 Discord가 인증하는 identity가 아니다.

엣지는 서로 다른 의미다:
- `authored_by`: 누가 작성했는가(Discord ID).
- `replies_to`: 실제 Discord reply target.
- `mentions`: 명시적 멘션(직접 청자 판단의 강한 근거지만 인용 여부를 확인).
- `addresses`: 누구에게 말했는가(모델 추정, confidence와 근거 필요).
- `quotes`: 누군가의 발언을 인용/전달했는가.
- `corrects`: 누가 어떤 자기 발언 또는 봇 발언을 정정했는가.
- `belongs_to`: 어느 임시 대화 흐름에 속하는가(항상 불확실성 관리).

**화자(author) ≠ 청자(addressee) ≠ 언급 대상(mentioned subject) ≠ 인용 원저자(quoted speaker)**. 같은 채널, 시간상 인접, 동일 화자, 유사 주제라는 이유만으로 대화를 합치지 않는다.

## 4. 디스코드의 대표적 경계 사례

| 상황 | 기대 동작 |
|---|---|
| A→B에게 질문, EchoMate 미호출 | 불필요한 개입 없이 관찰 또는 침묵 |
| A가 봇을 멘션 | 허용 상태에서 직접 응답 |
| A가 봇의 직전 답변에 멘션 없이 reply | 대화 연속성과 수신 대상 확인 후 응답 |
| A와 B가 교차해 별도 주제로 이야기 | 독립 conversation 그래프 유지; 맥락 오염 0 |
| C가 “A가 게임 싫어한대”라고 전언 | A의 취향으로 확정 저장 금지 |
| B가 A의 말을 인용하며 반박 | 인용 구간과 현재 B의 주장 분리 |
| A가 봇에게 “B를 기억해” | B의 동의를 대신 부여하지 못함 |
| A가 방금 보낸 말을 편집·삭제 | 구버전 기여를 취소·재생; 늦은 이벤트로 부활 금지 |
| A와 B가 봇을 연달아 호출 | 단일 GPU 공정 큐 + 원본 reply 보존 + 송신 전 최신성 확인 |
| 모델이 사용자 아닌 자기 판단으로 새 사실 작성 | GENERATED로 유지, VERIFIED 기억으로 승격 금지 |
| 상대가 정정을 함 | 실제 당사자 여부와 출처·시간 범위를 확인해 관련 상태만 갱신 |
| 사용자가 동의 철회 | 개인 기억·요약·파생 글로벌 변화까지 회수하거나 안전 정지 |
| 채널이 삭제/권한 상실/허용 설정 변경 | 새 수집·저장·송신 모두 즉시 중단 |
| Discord 연결 재시작/이벤트 재수신 | message_id+revision idempotency, 중복 응답/중복 학습 금지 |

## 5. 자율 참여와 자연스러운 사회적 행동

EchoMate는 '채널에 글이 올라왔으니 무조건 끼어드는 봇'도, '멘션만 응답하는 챗봇'도 목표가 아니다.

1. 실제 언급/reply/명확한 사용자 요청과 일반 잡담을 분리한다.
2. 기존 진행 중인 대화의 이어 말하기와 새 자율 참여를 구별한다.
3. 발화 대상·대화 흐름이 불명확하면 침묵하거나 신중히 확인한다. 일괄 침묵으로 QA 점수만 높이는 방식도 금지.
4. 독립 conversation별로 상태를 저장하되 하나의 EchoMate 자기모델·단일 GPU 공정 큐를 유지한다.
5. 인간의 발화를 기다릴 수 있는 여유, 짧은 응답, 가벼운 Reaction 같은 자연스러운 사회성은 허용한다. 반복 호출·자동 스팸·권한 우회를 성장으로 취급하지 않는다.
6. 사용자별 친숙함과 경험은 그 사람과의 대화에만 적용하며, 봇의 일반 성향 변화는 소유권을 추적할 수 있는 허용된 비개인 기여만 반영한다.

## 6. 수학 모델의 운영 범위 제한

```text
E_t = (guild, allowed_channel, message, author, reply, mentions, revision, time)
I_t = VerifyAndPerceive(E_t, Consents_t, Scope_t, Provenance_t)
X_t = (Q_global,t, C_conversation,t, M_user,t, R_user,t, Theta_reversible,t, V_t)
X_(t+1) = F_(Theta_t)(X_t, I_t, Outcome_t | SafetyConstraints)
Theta_(t+1) = G(Theta_t, X_t, I_t, VerifiedOutcome_t)
```

단일 채널은 외부 관측 범위를 의미할 뿐 단일 인간이나 단일 대화를 뜻하지 않는다. `Q_global`이 여러 사람의 영향을 받아 변화할 때는 **각 유효 기여의 출처·동의·기여량을 재생 가능**해야 한다. 사람별 상태 갱신은 그 사람에게 적법하게 귀속되는 근거만 사용한다.

## 7. 최소 검증 기준

- 두 명 이상이 동일 시각대에 다른 대화를 진행하는 재현 테스트, reply 체인 분리·재접속·중간 편집/삭제.
- bot mention/reply/자율 시작/침묵의 각 경로: false positive(끼어들기) / false negative(후속 응답 누락)를 별도 집계.
- A의 진술·수정·동의 철회가 B의 기억, 다른 대화, 캐릭터 기본 정책, 전역 모델 가중치에 누출되는 사례 **0**.
- 하나의 허용 채널 밖 메시지가 기억·경험 저널·학습·송신·검색 경로에 들어오는 사례 **0**.
- GPU 공정 큐로 서로 다른 conversation의 응답이 뒤바뀌지 않음. 생성 시작과 송신 직전에 source/consent/revision/epoch/identity stamp 확인.
- 실제 Discord 연결·메시지 수집·송신은 사용자 명시 승인 후에만 실행. 지금 단계는 합성 이벤트 및 격리 Runtime 검증.

## 8. 구현 순서

**우선** 채널 고정 정책과 멀티 화자 대화 그래프/권한·동의 경계를 Runtime 통합 QA로 고정한다. 이후 경험 후보를 실제 대화 분리 결과와 연결하고, 삭제/철회 원자성 또는 복구 가능한 전달·읽기 게이트를 구현한다. 그 다음에야 Lime 생성에서 경험 기반 자기모델 변화와 능동 참여 품질을 평가한다.

기존 다중 서버·채널 지원 기능을 코드에서 파괴할 필요는 없지만 새 기능의 RELEASE 범위는 명시한 한 채널로만 한정한다. 이 원칙은 새로운 구현보다 우선 적용한다.
