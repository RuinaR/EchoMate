# 외부 프로젝트 조사 및 EchoMate 반영 사항

조사일: 2026-10-18. 공개 README/프로젝트 문서 기반 검토. 코드를 빌드하거나 실제 서비스 통합 테스트한 결과는 **아님**. 타 프로젝트의 라이선스와 데이터 처리 방식은 독립 검토가 필요하다.

## 조사한 프로젝트
### 1. Disclone — https://github.com/DrewThomasson/Discord-llm-clone
- 관찰: 별도 로컬 내보내기 자료, 페르소나 선택, 텍스트/비전 모델, 학습 결과를 로컬 보관하는 형태.
- 채택: 페르소나별 분리 데이터·체크포인트·실험 결과, 학습 데이터와 모델의 분리.
- 보류: GPU 학습·멀티모달·전체 UI 복제. 데이터 접근 권한 및 모델 라이선스 확인 전 데이터 학습 금지.

### 2. discord-inference-bot — https://github.com/burdena0/discord-inference-bot
- 관찰: Ollama 로컬 추론, 응답 스트리밍, 채널별 단기 기억, SQLite + 임베딩 검색, 모델 시작/종료, 지연시간 통계.
- 채택: 로컬 백엔드, 모델 시작/종료 및 상태 확인, 채널/스레드 메모리 범위 분리, 통계 로깅, 재접속/타임아웃 처리, RAG 명시적 opt-in.
- 주의: 프로젝트 README 자체가 모든 참여자의 충분한 동의와 민감 채널 배제를 요구함. 저장소에 일반 재사용 라이선스가 없어 코드를 그대로 복사하지 않는다.

### 3. Archimedes — https://github.com/HiLleywyn/Archimedes
- 관찰: 멘션·답장·선택적 자율 참여, 관리 명령, 문맥·메모리, opt-in/opt-out, 프롬프트 인젝션 방어, 오프라인 테스트.
- 채택: 설정 권한 관리, 침묵 가능 자율 참여, 기록 삭제/동의 철회 동선, 입력과 출력 분리 검사, 오프라인 회귀 테스트.
- 보류: 범용 플러그인 런타임·PostgreSQL·Redis·OpenRouter 의존성 등 초기 규모를 넘는 구조. 프로젝트는 2026-06-15 아카이브됨.

### 4. discord-persona-bot — https://github.com/HeyTahsin16/discord-persona-bot
- 관찰: JSON 페르소나 정의, 슬래시 명령, 권한 있는 운영자, 대화 중 모델 변경, 지속 기억.
- 채택: 사람이 읽을 수 있는 persona manifest, 모델/페르소나 전환 시 원자적 설정 변경, 관리자만 설정 수정.
- 보류: 필요 없는 다수 유료 API와 이미지 생성 기능.

### 5. MarkBot — https://github.com/claabs/markov-discord
- 관찰: 과거 메시지 학습, 선택 채널 운영, JSON 파일 가져오기, 자체 호스팅.
- 채택: importer 플러그인 인터페이스와 개인정보를 고려한 로컬 우선 설계.
- 미채택: 마르코프 체인을 본 대화 엔진으로 사용(문맥 이해가 약함). 해당 프로젝트의 전 서버 이력 수집 패턴을 EchoMate에 그대로 가져오지 않는다.

### 6. DiscordChatExporter — https://github.com/Tyrrrz/DiscordChatExporter
- 관찰: GUI/CLI, JSON/CSV/HTML 내보내기, 공식 봇 토큰 방식도 설명. 사용자 토큰을 쓰는 방법은 계정 자동화 관련 약관 위반 위험을 명시.
- 채택: *허가된 기존 내보내기 파일의 오프라인 가져오기 형식*을 지원할 수 있도록 importer 인터페이스 추상화.
- 미채택: 사용자 계정 토큰 추출·self-bot·스크래핑·정책 우회 방식. '내보내기 도구가 지원'한다는 사실이 AI 학습 허가를 뜻하지 않음.

## 적용할 기술 설계
- PersonaManifest: persona_id, discord_user_id(선택), display_name, style_profile_version, model_id, adapter_id, consent_state, provenance.
- DatasetImporter: package_json / manually_authored_examples / permitted_export, 입력 스키마/출처·허가 상태 검증 및 preview-only 우선.
- ConversationState: (guild_id, thread_id)로 분리, TTL, 최대 메시지 수, 중복 ID 제거.
- ParticipationGate: 이벤트·멘션·대화량·침묵·쿨다운·상한을 고려. 모델 호출과 디스코드 전송을 분리.
- GenerationQueue: 스레드당 최대 1개 생성 작업, 취소·오래된 결과 폐기, 전송 전 대상/활성 페르소나 재확인.
- LocalModelProvider: Ollama 연동, 스트리밍과 non-streaming, 상태 확인, 모델 unload, timeout.
- Moderation/PrivacyGate: 서버 범위/역할/옵트인/출처 확인, 개인정보 비로그, 삭제·opt-out 경로.
- QualityHarness: 합성 데이터 단위 테스트와 권한이 확인된 실제 사례 평가 분리. 스타일 유사도뿐 아니라 관련성/반복/자율 참여 품질 기록.

## 단기 우선순위
P0: 공식 Discord 봇 + 지정 스레드 + 로컬 Ollama MVP, 개인정보 보호 설정.
P1: 단일 화자 패키지 preview-only 분석 + 페르소나 리스트박스 + 스타일 통계.
P2: 동의·권한 확인된 자료에 한하여 RAG, LoRA; 기준선 비교 평가.
P3: 장시간 운용·재연결·성능 회귀·삭제·백업.
