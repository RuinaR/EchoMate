# 아키텍처 (계획)

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
