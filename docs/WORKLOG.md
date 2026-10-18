# 작업 로그

## 2026-10-18 — Phase 0 초기화
- 요청: GitHub `RuinaR/EchoMate` 초기 구조, 프로젝트 정의, AI 작업 지침, 인수인계 문서화.
- 결정: 최초 대상 사용자 본인/단일 화자 메시지. 로컬 Ollama. 지정 스레드. 확장형 페르소나.
- 추가: README, AGENTS, docs/PROJECT-DEFINITION, ARCHITECTURE, DATA-GOVERNANCE, ROADMAP, AI-HANDOFF, WORKLOG, .gitignore, 소스/테스트 placeholder.
- 테스트: 없음 (실행 코드 미구현).
- 남은 이슈: Discord 데이터 패키지 미수령, 사용 권한 검토, Discord 봇 앱/토큰 미생성, 성능 검증 미수행.

## 2026-10-18 — 참고 프로젝트 조사 및 설계 확장
- 검토: Disclone, discord-inference-bot, Archimedes, discord-persona-bot, MarkBot, DiscordChatExporter 공개 문서.
- 생성: docs/REFERENCE-PROJECTS.md, docs/DATA-ACQUISITION-OPTIONS.md.
- 수정: ROADMAP, AI-HANDOFF에 스트리밍·메모리 TTL·성능 통계·관리자 제어·데이터 import 검증·원자적 페르소나 전환·자율 응답 취소 설계 반영.
- 규정: 사용자 토큰 자동화·무허가 AI 학습을 구현하지 않음.
- 검증: 문서 기반 검토만 수행. 실제 소스 코드 통합·봇 동작 테스트는 미실시.

## 2026-10-18 — 관계별 개인화 추가 및 DiscordChatExporter 경로 검토
- 관계별 스타일 설정 요구에 따라 docs/RELATIONSHIP-PERSONALIZATION.md 추가, 프로젝트 정의/로드맵/인수인계 갱신.
- Discord 공식 self-bot 금지, 개발자 정책 §16 관계 프로파일링 금지와 §21 AI 학습 허가 요건 재확인.
- 권장: 공식 봇 계정 사용, 수동 관계 선호 설정. 별도 일반 계정으로 제한을 우회하는 방식은 지원하지 않음.
- 검증: 문서 갱신만 완료; 실행 코드와 실제 데이터 기반 테스트 미실시.

## 2026-10-18 — 관계 자동 분석 요청·공식 Bot 경로 검증
- 사용자 요구: 수동 친밀도 지정 대신 실제 대화의 호칭/농담/분위기에서 자연스럽게 반응 차별화.
- 설계 선택: 실시간 대화에 기반한 임시 상대별 톤 적응은 지원, Discord API 수집 데이터 기반 장기 관계 프로파일링은 금지 대상이므로 보류.
- 공식 Developer Portal bot 사용. DiscordChatExporter의 bot-token 내보내기 가능성과 AI 훈련 허가 조건을 구분.
- 문서 검토/수정만 수행, 구현·실행 검증 없음.

## 2026-10-18 — 단일 페르소나 중심 재정의
- 사용자 요청: 본인 페르소나 하나만 개발하고 Discord 웹에서 과거 대화 내역 전체 확보 가능성 검토.
- 공식 Discord 검색은 작성자 필터 제공, 다만 일괄 내보내기 불가. self-bot 및 비공식 웹 자동 수집 정책 위험을 분명히 함.
- 새 문서 docs/SINGLE-PERSONA-PLAN.md; 프로젝트 정의/로드맵/인수인계의 최신 우선순위 변경.
- 구현된 데이터 추출기 없음. 원본 메시지 수집·AI 학습 미수행.

## 2026-10-18 — 운영 중 지속 적응 설계
- 추가 요청: 봇이 미래 대화에서 상대별 반응·친밀도를 조금씩 갱신했으면 함.
- 신규 설계 docs/CONTINUOUS-ADAPTATION.md 작성 및 관련 문서 갱신.
- 분리: 실시간 대화 톤(임시) / 명시적 본인 피드백으로 누적되는 스타일(지속) / 사용자 직접 선호. API 메시지에 기반한 장기 관계 프로파일링은 구현하지 않음.
- 실제 코드/테스트 없음.

## 2026-10-18 — DiscordChatExporter GUI 사용 설명
- Windows v2.48.0의 로그인 화면 기준으로 공식 봇 토큰 생성·초대·최소 권한·스레드 표시·JSON 출력 절차 정리.
- docs/DISCORDCHATEXPORTER-GUIDE.md 생성.
- 보안: 토큰/GitHub 업로드 금지, 개인 계정 self-bot 금지, AI 모델 학습과 단순 백업 구분.
- 실제 내보내기·코드 빌드·학습 테스트 미실시.

## 2026-10-18 — Bot/Studio 프로세스 분리 결정
- 사용자: EchoMate Bot을 표시 이름/프로필 사진·모델 로드·대화 빈도/대상 채널/스레드 기능으로 축소하고, DiscordChatExporter 파일을 이용하는 오프라인 학습 도구와 분리 요청.
- docs/DEPLOYMENT-SEPARATION.md 신규, PROJECT-DEFINITION/ARCHITECTURE/ROADMAP/AI-HANDOFF 정합성 갱신.
- 모델 아티팩트 형식, 캐시/검증/롤백, 봇 allowlist와 학습 분리 경계 명시.
- 설계만 완료. Discord/학습 동작 테스트 미수행.

## 2026-10-18 — 채널별 데이터/최근 가중치/미디어 출력 제한
- 사용자 확인으로 입력 2개 JSON이 각각 단일 채널의 기록임을 문서화.
- 신규 문서 docs/TEMPORAL-STYLE-AND-MEDIA.md: 최근 스타일 가중치 반감기 후보, 파일별 발화 묶기 주의, 기본 Unicode 이모지 허용/커스텀 이모지·GIF·스티커 금지.
- 원본 JSON/GitHub 업로드 없음. 구현 및 학습 시험 미실시.

## 2026-10-18 — EchoMate Studio 분석기 첫 구현
- 코드: src/echomate_studio/__init__.py, src/echomate_studio/analyze.py
- 테스트: tests/test_analyze.py (합성 데이터 5건 단위 테스트 통과), 본인 제공 대용량 JSON 2개 분석 성공
- 문서: docs/STUDIO-QUICKSTART.md
- 입력: 각 파일은 단일 채널, 총 304,997건, 파일 내부 메시지 ID 중복 0건.
- URL/멘션/커스텀 이모지 제거 후 텍스트 후보 270,989건.
- 기능은 개인정보를 제외한 *통계 분석*이며 모델 학습·RAG/QLoRA 구현 아님. Discord 정책상 학습 이용허가 판단도 하지 않음.
- 주의: 메모리 내 전체 JSON 적재 방식은 향후 streaming으로 최적화 예정. 출처에 채널 ID 및 UTC 오프셋이 없어 임의 추정 금지.

## 2026-10-18 — Windows 검증 보고서 수령 및 문서 기준선 정리
- Windows PowerShell에서 Studio unittest 5개 모두 OK, 실제 두 JSON으로 `report.json` 생성 완료. 사용자가 보고서를 전달했고 필드·수치 확인.
- messages1: 원본 244,976 / 필터 후 223,737 / 발화 묶음 후보 114,009.
- messages2: 원본 60,021 / 필터 후 47,252 / 발화 묶음 후보 28,588.
- 합계: 원본 304,997 / 필터 후 270,989. 독립된 채널의 단일 화자 기록.
- README.md, PROJECT-DEFINITION.md, ROADMAP.md, AI-HANDOFF.md를 최신 방향으로 재작성. 이전 단일 페르소나 한정 등 상충하던 과거 결정을 현재 계획과 명확히 구분.
- 최신 기준: EchoMate Studio(오프라인 허가된 데이터 학습 및 버전별 아티팩트 제작) + EchoMate Bot(읽기 전용 모델 로드와 자율 대화). 첫 자료는 본인 것, 향후 적격 사용자별 페르소나 선택 가능.
- 정책: 백업/파일 소유와 AI 학습 사용 허가는 구분. 본인 데이터 패키지에 대한 무조건적 사용 허가를 주장하지 않음.
- 이번 변경은 **문서만 수정**. 추가 코드 기능 구현이나 모델 학습 테스트는 수행하지 않음.

## 2026-10-18 — 폐기 요구 문서 정리 및 N개 채널 파일 입력 명확화
- 과거 요구에만 해당하는 문서 5개 삭제: SINGLE-PERSONA-PLAN, RELATIONSHIP-PERSONALIZATION, CONTINUOUS-ADAPTATION, DATA-ACQUISITION-OPTIONS, DISCORDCHATEXPORTER-GUIDE.
- README, PROJECT-DEFINITION, ROADMAP, AI-HANDOFF, TEMPORAL-STYLE-AND-MEDIA, STUDIO-QUICKSTART, ARCHITECTURE, DATA-GOVERNANCE에서 기존 2개 고정으로 보일 수 있는 서술을 **JSON 1개 이상, 입력 개수 제한 없음, 파일 하나 = 채널 하나** 기준으로 변경.
- 기존 Studio CLI의 argparse `nargs="+"`가 임의 개수 입력을 이미 지원함을 확인. 입력 파일은 각각 별개 보고 항목이며 채널 간 발화 병합 기능 없음.
- 회귀 테스트 추가: `test_cli_accepts_three_independent_channel_files` (합성 채널 3개를 CLI에 전달하는 검증).
- **신규 테스트는 커밋되었으나 사용자 Windows 실행 확인 전**, 기존 5개 테스트의 통과와 구분한다.
- 과거 기록 자체는 Git 커밋 이력에 남을 수 있으나 현재 브랜치에서는 삭제됨.

## 2026-10-18 — JSON 파서 메모리 경량화
- 증분 JSON 배열 리더와 청크 단위 SHA-256 계산 도입. 콘텐츠 문자열 장기 저장 제거.
- 추가된 합성 테스트: 650 레코드 이상의 청크 경계, 잘못된 배열 문법/후행 데이터, 단일 채널 입력.
- 이전 6개 Windows 테스트 OK(사용자 제공), 신규 3개는 Windows QA 확인 전.
- 실제 JSON에서의 종전 수치와 신규 계산 수치를 비교하도록 `report-v2.json` 출력 절차 작성.
- 설계 제약: 메타데이터 정렬/ID 중복 검사 RAM 사용은 여전히 데이터 수에 비례.

## 2026-10-18 — 데이터 분석 회귀 완료 및 Ollama 기준선 코드
- 사용자 Windows 테스트 9개 전부 OK; 업로드 `report-v2.json`을 이전 `report.json`과 비교해 양쪽 파일 SHA-256/통계 값 모두 일치.
- 구현: 로컬 Ollama `/api/chat` 동기 클라이언트, 대화 문맥 프롬프트 빌더, AI 봇 고지, 커스텀 이모지/URL/이미지 마크다운 출력 필터, 대화 CLI.
- 신규 모킹 단위 테스트 6개 작성. 신규 테스트와 모델 실기기는 아직 미실행/검증 전. 학습 데이터의 이용 허가 여부와 분리해 진행.
- 새 문서 LOCAL-BASELINE.md; README/ROADMAP/HANDOFF 최신화.

## 2026-10-18 — 채팅 텍스트 소거 버그 해결 및 이모지 반응 정책 설계
- 사용자 검증: 기존 15개 테스트 중 2개 실패, 두 번의 Ollama 단발 생성 모두 출력 공백. 오류는 출력 공백 정규식이 정상 문자까지 제거하는 것이 직접 원인.
- `conversation.py`의 정규식 수정. `ollama_client.py` think=false 지정, 생성 토큰 예산 확대, 빈 모델 출력 진단 메시지 추가.
- 테스트: 정상 한국어/기본 이모지 보존, thinking-only 빈 응답 오류 검증 2개 추가.
- 자율 Discord 기본 이모지 반응 요구 반영: 반응 채널/스레드·확률·쿨다운 별도 설정, 자신·봇 메시지/opt-out 제외. 정책 모듈과 합성 단위 테스트 6개 추가.
- 이번 커밋의 신규 테스트는 Windows 실행 미검증. 봇 전송/Discord 반응 기능은 아직 없음.

## 2026-10-18 — Windows Ollama 실기기 통과 및 발언 판단 모듈
- 사용자 Windows 테스트 23개 모두 통과; 로컬 Ollama Qwen 9B 실제 자연어 답변 성공.
- 새 요구: 활발한 모드여도 민감하거나 끼어들 필요 없거나 장기간 조용한 대화에는 침묵.
- `participation.py`에서 권한/범위·옵트아웃·봇 제외·쿨다운·장시간 비활성·민감 분위기·기여도·개입 적절성·확률 순으로 평가하여 결정.
- 새 합성 테스트 7개 작성. **Windows 신규 테스트 미확인**; 실제 맥락 평가기/Discord Bot 구현된 것으로 간주 금지.
