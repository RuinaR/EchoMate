# AI 인수인계서 / CURRENT STATUS

**갱신일:** 2026-10-18
**단계:** Phase 0 — 프로젝트 초기 문서/구조
**저장소:** https://github.com/RuinaR/EchoMate

## 최신 확정 사항
- 첫 페르소나는 프로젝트 사용자 본인.
- **단일 화자의 과거 Discord 메시지만** 제공 가능한 것으로 가정. 상대방 메시지/문맥 없음.
- 로컬 Ollama 기반, 유료 API 필수화 금지. GPU 추론/성능 추후 검증.
- 특정 스레드만 활동, 자율 반응, UI는 검색 가능한 페르소나 리스트박스.
- 봇 서버 표시명은 `EchoMate(해당 서버의 닉네임)`.
- 추후 친구 여러 명 확장 가능하지만 처음에는 한 번에 하나의 활성 페르소나.
- 데이터 패키지 신청을 사용자가 직접 진행 예정. 데이터가 아직 도착하지 않음.

## 완료
- 저장소 초기 README, AGENTS, 정의서, 설계서, 데이터 지침, 로드맵, 작업 로그 작성.
- 기본 소스/테스트 폴더 위치를 위한 placeholder 생성(구현은 아직 없음).

## 미완료 / 주의
- 실행 코드 없음, 테스트 수행 없음, Discord 앱 ID/토큰 없음.
- 실제 데이터 미입수, 샘플 구조 확인 전. 메시지 수 및 품질 추정 금지.
- Discord 데이터 패키지의 AI 학습 이용 조건은 최종 확인 전. 허용되었다고 선언하지 않음.
- 저장소가 PUBLIC이므로 개인정보 커밋 금지.

## 다음 작업 순서
1. 저장소/문서 읽고 Python 프로젝트 최소 스켈레톤과 pytest 구성.
2. 합성 ZIP을 이용한 단일 화자 패키지 분석기부터 개발.
3. Discord 데이터 패키지 도착 시 로컬에서 필요한 파일만 식별·스키마 점검.
4. Ollama 연결/벤치마크 및 Discord 지정 스레드 MVP.
5. 데이터 권한이 확인된 다음 스타일 프로필/RAG/QLoRA 품질 검증.

## AI 다음 대화 체크리스트
- 현재 main 브랜치 파일/마지막 커밋을 다시 읽는다.
- WORKLOG 최신 항목으로 현재 상태 검증.
- 계획과 구현을 구분해 결과 보고.
- 변경 후 인수인계와 로그 갱신.

## 2026-10-18 추가 조사 및 반영
- 신규 문서: docs/REFERENCE-PROJECTS.md, docs/DATA-ACQUISITION-OPTIONS.md.
- 조사 대상: Disclone, discord-inference-bot, Archimedes, discord-persona-bot, MarkBot, DiscordChatExporter.
- 채택할 설계: 스트리밍, 단기 기억 TTL, Ollama 상태/성능, persona manifest, 관리자 제어, 권한·삭제 처리, 자율참여 Gate 및 stale 답변 폐기, importer 인터페이스.
- 공식 데이터 패키지 이전 대안: 본인 작성 사례로 AI 기능 테스트, 이미 적법하게 보유한 자료 검토, 실시간 스레드 MVP. 사용자 토큰 self-bot/전체 기록 스크래핑은 지원하지 않는다.
- 코드 구현·테스트는 아직 착수하지 않음. 다음에는 Phase 1의 합성 데이터 분석기 또는 Phase 3의 지정 스레드 MVP를 구현.

## 2026-10-18 관계별 대화 설정 추가
- 신규 문서: docs/RELATIONSHIP-PERSONALIZATION.md.
- 사용자가 페르소나-상대방 관계/친밀도에 따른 응답 스타일 요구.
- 구현 방식: 당사자 수동 선택의 관계별 **대화 스타일 선호도**, 닉네임/호칭, 장난 허용 범위. Discord API 메시지로 관계를 자동 추정/점수화하지 않는다.
- DiscordChatExporter: 공식 **봇 토큰** 접근과 일반 유저 토큰 자동화는 별개. 새 일반 계정 self-bot도 금지. 내보내기 기술 가능 여부와 AI 학습 허가를 혼동 금지.
- 구현되지 않음: UI, 관계 DB, DiscordChatExporter 연동, 데이터 학습.

## 2026-10-18 최신 사용자 선호 및 정책 판단
- 사용자는 수동으로 관계를 지정하는 것보다 **실제 대화내용에 따라 자동으로 자연스럽게 상대별 반응**하기를 원함.
- 안전한 현재 구현 범위: 지정 스레드의 현재 대화에서 말투/분위기 임시 적응. API 기반 수년치 관계/친밀도 장기 프로파일 자동 추론은 개발자 정책 §16 때문에 제외.
- Discord Developer Portal 공식 bot 계정 채택 방향. DiscordChatExporter의 공식 bot-token 지원은 사실이나, export된 API 메시지의 AI 훈련에는 Discord 명시적 허가가 필요함(§21).
- 추가 설계: docs/RELATIONSHIP-PERSONALIZATION.md의 2026-10-18 보완 참고.
