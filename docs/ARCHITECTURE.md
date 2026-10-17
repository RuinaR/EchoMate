# 아키텍처 (계획)

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
