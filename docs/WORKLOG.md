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

## 2026-10-18 — 단기 대화 연속성 상태 구현
- 사용자 Windows 테스트 30개 통과 보고.
- 채널/스레드별 대화 상태 및 TTL·화자·답장 메타데이터·스냅샷 버전 모듈 생성.
- 합성 테스트 5개 추가: 범위 격리, 중복/역순 제한, 최대수/시간 경계, stale 버전, 화자 및 답장 표현.
- 실제 Discord 봇 네트워크 통합과 대화 내용의 의미적 판단은 아직 미구현. 신규 단위 테스트 실기기 검증 필요.

## 2026-10-18 — 대화 기억 범위 확장
- 사용자 실기기 35개 unittest 모두 OK 확인.
- 사용자 RAM 32GB 환경에서 채널/스레드별 대화 버퍼 기본 500턴/24시간으로 상향. 실제 LLM 입력은 별도 문자 예산 16000으로 제한해 큰 메모리를 통째로 입력하지 않음.
- 100턴 보존/작은 프롬프트 버짓 및 잘못된 예산 입력 테스트 2건 추가.
- 주의: 문자 예산은 tokenizer의 토큰 한도 보증이 아니며 `num_ctx`/VRAM/요약·검색은 후속 작업. 신규 Windows 테스트 결과는 아직 없음.

## 2026-10-18 — 대화 흐름 평가기 추가
- 사용자 Windows 37개 테스트 OK.
- 현 대화 흐름을 Qwen 로컬 모델로 JSON 평가하는 `context_assessor.py` 구현. 실패한 평가는 침묵으로 처리.
- `autonomy_probe.py`(합성 대화 프로브) 및 파서/오류/전달 검증 단위 테스트 7개 추가.
- 실제 Discord 메시지, 실제 사람 대화에 대한 품질 검증/봇 연동은 아직 없음. Windows QA 요청 예정.

## 2026-10-18 — Ollama 실문맥 침묵 확인 및 발언 오케스트레이션
- 사용자 Windows unittest 44개 모두 OK.
- Qwen 실문맥 샘플(보스 모집→9시 가능→9시 확정): sensitive=false, useful=false, interrupt=false, 결과 no_useful_contribution 침묵.
- `turn_pipeline.py` 새 단일 턴 오케스트레이터 구현: 대화 스냅샷→활동 제어→맥락 평가→조건부 생성→stale 검사; 전송은 하지 않음.
- 6개 합성 테스트 작성(정상 생성, 민감 차단, 비활성, 동시 새 메시지, 예외, 빈 컨텍스트). 사용자 Windows 새 테스트 미확인.

## 2026-10-18 — Windows 50개 QA 통과, stale 회복 및 페르소나 우선 계획
- 사용자 Windows unittest 50개 모두 OK.
- 새 모듈 stale_recovery.py: 생성 중 새 메시지 발생 시 유한 재평가, 기본 최대 2회, 불확실 시 침묵; 합성 테스트 5건 추가(Windows 아직 미실행).
- 웹 검색은 필요한 경우만 opt-in 및 외부 전송 최소화. 페르소나 Style Profile v1부터 다음 작업 시작. docs/SEARCH-AND-PERSONA-PLAN.md 작성.
- QLoRA/모델 학습 및 Discord/Web 실제 연결은 이 변경에 포함되지 않음.

## 2026-10-18 — Style Profile v1 착수
- Windows 기존 55개 unittest 모두 OK.
- 로컬 JSON N개를 대상으로 최근 가중치 기반 말투 집계만 저장하는 Studio Style Profile 코드 추가.
- Qwen 단발 대화 probe에 선택적 스타일 프로필 입력 옵션 추가. 회귀 테스트 3건 작성, Windows 미검증.
- 원문 텍스트를 저장하거나 Ollama 학습에 넣는 기능 아님. 페르소나 품질 비교용 기준선.

## 2026-10-18 — 페르소나 출력 품질 실패 분석 및 교정
- 사용자 Windows unittest 58개 OK, Style Profile 생성 OK. 모델 답변: 존재하는 메이플스토리를 서비스 중단으로 오인, 비자연스러운 긴 존댓말 및 사용빈도에 안 맞는 이모지.
- 프롬프트를 짧은 한국어 채팅체·일상 초대 해석·검증 없는 서비스 상태 단정 금지 방향으로 수정. 스타일 안내는 평범한 반응 기본/이모지 드물게 사용.
- 지연 진단용 `chat_probe --timing` 추가; 프롬프트 회귀 테스트 1개 추가.
- Lost in the Middle 및 3개 유사 프로젝트 조사/현행 적용 여부 문서 작성. 근본적인 사실성/유사도 보장 전 실제 다중 사례 평가 필요.

- 후속 지연 개선 시도: chat single-turn `max_tokens=128`로 생성 상한 감소(기존 512). 실제 지연 개선/응답 부족 여부는 Windows 테스트 전이며, 필요하면 옵션화할 것.

## 2026-10-18 — 59개 QA 후 페르소나 응답 재검토
- Windows 59개 unittest 모두 OK. 기본 Qwen: `네, 지금 바로 시작할까? 준비됐으면 같이 들어올게.` (4.55초), 프로필 Qwen: `그거 지금 언제 하는 거야?` (0.23초).
- 둘 다 품질 불충분. 기본은 실제 게임 접속할 수 있는 듯한 표현, 프로필은 초대를 불필요하게 되묻는 반응. 워밍/캐시 차이로 4.55초와 0.23초를 모델/프롬프트 속도 우열로 판단 금지.
- `conversation.py`: 게임 접속 약속 금지, 이미 이해된 초대는 불필요하게 재질문 금지.
- `ab_probe.py`: 여러 질문, 번갈아 순서를 바꾸는 반복 A/B 응답/시간 측정과 로컬 JSON 리포트 생성. 사용자 Windows 시험 전.

## 2026-10-18 — 16회 A/B 품질 불안정 대응
- Windows 59개 테스트 OK. A/B 기본 중앙값 0.31초, 프로필 중앙값 0.29초, 응답 내용은 둘 다 불안정.
- 프롬프트에서 세부 금지사항 반복을 줄이고 현재 문맥·질문 의도·물리적 행동 불가·자연스러운 짧은 답변을 우선.
- 자동 QA 플래그 도구 및 모킹 불필요 순수 테스트 4개 추가. A/B JSON에 기계적 품질 경고 첨부.
- 개선된 응답의 실제 품질 및 테스트 63개는 사용자 PC 미검증.

## 2026-10-18 — Qwen/Gemma 모델 비교 환경
- 사용자 Windows에 `gemma3:12b` 설치 성공(7.3GB 모델 레이어 및 854MB 기타 레이어), 기존 Qwen 9B 유지.
- 모델별 말투 프롬프트 동일 조건 반복 교차 비교 CLI 및 합성 테스트 3개 작성. Windows 신규 테스트와 비교기 실제 실행 전.
- GPU 메모리 및 모델 로딩 교체가 지연에 영향을 줄 수 있으므로 중앙값 결과는 설명과 함께 판단 예정.

## 2026-10-18 — 모델 비교 및 실제 다중 턴 확인 기반
- 사용자 Windows 총 66개 테스트 OK, Gemma 12B 설치 후 로컬 20회 비교 성공.
- Gemma는 자연스러운 단문 답변 경향. 그러나 제공하지 않은 '저녁 7시' 반복 생성, 사실성 문제. Qwen3.5는 `ㅋㅋㅋㅋ`에 중국어로 응답하는 문제 확인.
- 기록 없는 약속을 창작하지 않고, 9시를 10시로 변경한 경우 최신 확정 내용을 반영하도록 프롬프트 보강.
- 순수 합성 다중 턴 평가 도구 및 4개 단위 테스트 구현. 신규 테스트 실기기 검증 전.

## 2026-10-18 — 다중 턴 대조 QA 결과와 프롬프트 오염 수정
- 사용자 Windows 70개 테스트 전부 통과; 현 대화 평가 8건에서 Gemma 무정보 시간 추측(10시), 9시 확정 사례 두 모델 모두 10시라고 잘못 응답.
- 시스템 프롬프트에 9→10시 예시가 들어 있던 것을 발견. 해당 하드코딩 예시가 모델의 답변에 섞일 가능성을 없애도록 일반적 변경 원칙으로 교체.
- 하드코딩된 시간 예시 재도입 방지 테스트 1개 추가. 신규 테스트 실기기 미검증.

## 2026-10-18 — 프롬프트 오염 제거 후 실측
- 사용자 Windows 71개 단위 테스트 OK. Gemma3 12B: 없는 시간 → 없음, 9시 약속 → 9시, 변경 → 10시. Qwen3.5 9B: 없는 시간 → 없음, 9시 약속 → 미결정(오답), 변경 → 10시.
- 자동 QA에서 정상 문구 `시간 정보가 없습니다`에 근거 없는 시간 플래그를 붙이는 오탐 확인. 정규식 정밀화, 회귀 테스트 추가. Windows 새 테스트 미실행.

## 2026-10-18 — 미세조정 범위 승인과 준비 단계
- 사용자 Windows 72개 전체 테스트 통과.
- 사용자 요청에 따라 향후 Gemma 3 QLoRA 미세조정 목표 추가. Discord 개인 데이터 패키지의 AI 학습 권한 불명확; API 데이터는 개발자 정책 §21 명시 허가 필요. 현재 권리 확인 전 실제 모델 학습/개별 발언 추출은 보류.
- 스트리밍 집계형 style_diagnostics(분포/종결 표현), 튜닝 준비상태 체크 CLI 및 4개 단위 테스트 작성. 새 테스트 미검증.

## 2026-10-18 — 76개 QA 성공, Ending 분석 결함 수정
- 사용자 76개 unittest OK, 원본 메시지 2개 스타일 심화 분석 및 QLoRA readiness 보고서 생성 확인.
- 길이 구간 12자 이하 86.94% (최근 가중치). Ending 지표 전부 0 → 소스 정규식의 백슬래시 중복 이스케이프 버그 확인, 수정 및 테스트 3건 추가. 수정 뒤 실제 Windows 통계는 미확인.
- readiness not_ready 유지, 원본 메시지 추출/모델 학습 미시작.

## 2026-10-18 — 원본 직접 분석 및 안전 QA
- 사용자 원본 2개 파일의 메타데이터를 로컬에서 확인: 244976 + 60021건, 각 파일 역시간순, 채널별만 취급. 빈 문자열 제외 228342 + 52788건; 반복문구가 많음.
- 학습 전 원본 문자열을 저장하지 않는 corpus_audit CLI / 합성 단위 테스트 3건 추가. 실데이터 자동 QA와 학습 권한 점검은 별도. 82개 테스트 예상, Windows 검증 전.

## 2026-10-18 — 멘션 테스트 오류 및 활성 대화 연속성
- Windows 91개 실행에서 7개 실패: mention 정규식의 백슬래시 이중 이스케이프. 수정.
- 자율 첫 참여와 활성 대화의 후속 응답 구분: 이어가기에는 확률/자율 쿨타임을 적용하지 않고 봇 대상·같은 주제·시간제한·안전 조건 확인.
- 신규 5개 테스트 작성. 예상 총 96개, 검증 전.

## 2026-10-18 — 96개 QA 중 3개 실패 수정
- 직접 봇 멘션 경로에서 자율 발언 유용성 조건을 적용해 오차단하던 버그 수정. 멘션은 응답 기회지만 위험 상황에서는 침묵.
- 활성 대화 만료 테스트의 expected reason을 cooldown→frequency_gate로 정정, 민감도 테스트는 실제 180초 이내로 입력 수정. 96개 재확인 필요.

## 2026-10-18 — Discord 대화 맥락 우선 연속성
- 사용자 96개 Windows 테스트 전부 통과.
- 활성 대화 기본 180초 타임아웃 제거(max_gap_seconds=None). 봇 대상·주제 연속성·실제 이전 참여 상태로 후속 답변 판단. 오랫동안 이어진 대화도 유지 가능, 몇 초 내 주제 전환은 연속성 해제.
- 연속성 회귀 1개 추가 및 기존 테스트 수정. 실환경 결과 미검증.

## 2026-10-18 — 대화 상대 판별 근거 강화
- 사용자 97개 Windows 테스트 모두 OK. 최근 시간 간격만으로는 이어가기 판단하지 않는 상태.
- 신규 engagement_evidence: 실제 `reply_to`가 봇 발언을 참조하는 경우만 이어가기 후보로 인정; 주제 연결성은 별도 입력 필요.
- 턴 파이프라인 연동과 테스트 6개 추가. Windows 103개 QA 필요.

## 2026-10-18 — 연속 대화 로컬 AI 판정 연결
- Windows 기존 103개 테스트 OK.
- 실제 bot reply 대상과 인간 답장의 주제 연속성을 로컬 Ollama JSON 분류로 평가하는 `topic_assessor.py` 추가; 잘못된 데이터/추론 장애 시 false.
- 기존 TurnPipeline에 선택적 assessor 함수 주입, 신규 회귀 테스트 6개. 총 109개 예상, 사용자 Windows QA 전.

## 2026-10-18 — 109 테스트 통과 및 Gemma 주제판정 실측 준비
- Windows 109개 unittest 모두 OK.
- 실제 Ollama를 대상으로 6가지 합성 답장/대화 전환 상황에서 topic_continues 성능을 측정하는 CLI와 2개 테스트 추가. 111개 Windows QA 및 `local_data/topic-qa.json` 실측 대기.

## 2026-10-18 — Windows 111/111 및 실제 Gemma 6/6
- 사용자가 111개 unittest OK와 실제 Ollama Gemma 3 12B topic_qa 6/6 정답 보고. 첫 호출 9.306초, 이후 대부분 약 0.25~0.29초. Discord 실환경 일반화 불확실.

## 2026-10-18 — 명시적 답장 없는 대화 연속성 판정
- 111개 Windows QA 및 Gemma 6/6 결과 확인. 로컬 모델 기반 implicit-address 검증 및 선택적 파이프라인 경로 구현. 두 개의 boolean 필드 모두 참이어야 대화 이어가기 가능. 회귀 테스트 4개 추가, 115개 예상.

## 2026-10-18 — 예약 멘션 로컬 코어 추가
- 사용자 114개 Windows 테스트 OK, 2시간 뒤 본인 @멘션 등 간단 부탁 자동처리 요구.
- 상대 시간 파싱/SQLite 저장·복구/중복 방지/claim 처리와 합성 테스트 4개 추가. 총 118개 예상, Windows 미검증. Discord 실제 발송 미연동.

## 2026-10-18 — 예약 관리 및 영속성 호환
- 사용자가 118 tests OK 보고 후 예약 취소/조회 확대 요구.
- 본인 소유 예약만 조회·취소하는 저장소 API, 한국어 예약 확인/선택취소/전부취소 명령 분기, 기존 sqlite CHECK 제약 마이그레이션 구현. 5개 회귀 테스트 추가, Windows 총 123개 재검증 필요.

## 2026-10-18 — 페르소나 학습 상태 재정리 / SQLite 잠금 QA
- 페르소나 학습은 아직 실제 파인튜닝 미시작. 기존 것은 원본 분석, 통계/프로필, 로컬 Gemma 추론 및 품질 평가. 이후 진행의 우선순위를 실제 가중치 학습 검증으로 재설정함.
- Windows 사용자 로그: 123 tests 중 1 ERROR, `old.db` 임시폴더 삭제시 WinError32; DB 연결을 contextlib.closing으로 명시 종료하도록 수정, 재검증 필요.

## 2026-10-18 — Windows 임시 SQLite 테스트 파일 잠금 수정
- Windows 123개 중 1 ERROR 재발. 테스트 자체의 sqlite3.connect 컨텍스트가 커넥션을 닫지 않아 old.db 임시 파일 삭제 실패. closing + 명시 commit으로 수정, 재검증 대기.

## 2026-10-18: 123 Windows QA green, persona preparation
- Added local aggregate-only eligibility audit and three unit tests. 126 total expected; fine-tuning not started.

## 2026-10-18 — 실제 페르소나 원본 분석 실측 반영
- 사용자 Windows 126개 unittest OK. 두 원본 합계 304,997개 중 추가 검수 후보 185,608개. 나머지 초단문 45,455, 동일 문자열 중복 36,275, 정규화 뒤 빈 메시지 34,008, 개인식별 의심 2,060, 반복 단일문자 1,587, 과도한 장문 4.
- 이 수치는 상호배타적 분류별 건수이지 미세조정 승인 수가 아니다. 개인정보 휴리스틱은 완전하지 않고 실제 QLoRA는 미시작.

## 2026-10-18
- Implemented reaction_reply.py for exclusive text, emoji, or silence decisions. Five offline tests added; Discord send integration pending.

## 2026-10-18 — 131 tests OK / QLoRA environment diagnostics
- Added read-only qlora_environment CLI with optional nvidia-smi and seven local package version checks. No weights download, no data extraction, no training. 3 tests added; expected 134 Windows tests.

## 2026-10-18 QLoRA GPU mock regression
- Windows 134 tests, 1 test_gpu_query failure checking last subprocess mock call timeout. Test now checks matching NVIDIA query call, rerun required.

## 2026-10-18 GPU QA
- Windows 134 tests OK. Local GPU: RTX 4070 Ti SUPER, 16GB, 12.7GB free. Python 3.10.11, torch CPU-only, 5 training packages absent. Isolated CUDA environment needed. No training yet.

## 2026-10-18 CUDA persona bootstrap
- User 134 Windows tests OK. GPU RTX 4070 Ti SUPER 16GB, torch CPU-only. Added isolated Python 3.10 environment PowerShell setup, CUDA tensor verification, optional training libraries, 3 tests. Expected 137 tests; user GPU result pending. No dataset or model weights involved.

## 2026-10-18 — CUDA GPU ready, toolchain pending
- Windows user reports 137 tests OK, isolated torch 2.9.1+cu128 runtime 12.8 RTX 4070 Ti SUPER CUDA calculation success. NumPy missing warning observed; optional install now includes NumPy and import smoke test. Actual QLoRA fine-tuning not started.

## 2026-10-18 — QLoRA library setup: quote bug fixed
- Training library installation and pip check succeeded. Final Python -c verification failed due to PowerShell quote parsing, NOT package installation. Replaced it with standalone import smoke test and three mock unit tests. New expected baseline 140.

## 2026-10-18 — QLoRA 140 QA pass and NF4 GPU probe
- Confirmed 140 Windows unit tests OK and isolated training stack imported fully. Added synthetic GPU NF4 Linear4bit operation probe with privacy-safe memory summary, 3 mocked unit tests. Next: 143 tests and native NF4 result, no model downloaded/trained.

## 2026-10-18 — NF4 actual GPU smoke QA
- User Windows 143 tests OK. Tiny synthetic bitsandbytes NF4 CUDA operation success on RTX 4070 Ti SUPER, max PyTorch allocated 0.08 MiB, free GPU memory after 15073 MiB. Not a full-model VRAM benchmark.

## 2026-10-18 — Real Gemma 3 4B loading probe prepared
- User confirmed 143 tests and real NF4 CUDA kernel OK, 15073 MiB GPU free after tiny probe. Added gated HF model NF4 load CLI opt-in only, 2 tests. Requires Google Gemma license acceptance; no weight downloaded/training executed.

## 2026-10-18 Gemma 4B gating debug
- 145 Windows tests OK. Local HF identity works but real NF4 Gemma load OSError; no proof of license grant/download. Added redacted failure category and removed torch_dtype deprecation warning, 2 new tests.

## 2026-10-18 Gemma 3 4B access diagnostic
- Windows 147 QA OK, full-model load OSError categorized as access denied; HF whoami succeeded. Added config.json-only auth probe and 2 tests, no weights download. Expected 149 Windows tests.

## 2026-10-18 Gemma config access OK
- User confirmed Windows 149 tests OK and google/gemma-3-4b-it config.json access succeeded. Real weight download/VRAM load still unverified; previously denied. Next is opt-in load retry.

## 2026-10-18 — Gemma 4B real NF4 load successful
- Two official gated model shards downloaded. Actual NF4 load OK, GPU memory delta 4266 MiB; free_after 10845 MiB; PyTorch peak 4100.9 MiB. Training step not tested yet.

## 2026-10-18 LoRA GPU optimizer dry-run
- Real Gemma3 4B NF4 load verified. Added opt-in synthetic-only, bounded LoRA backward/optimizer smoke test and 3 preflight tests. Expected 148 tests; device run pending.

## 2026-10-18 — First actual GPU LoRA optimizer step successful
- User 152 tests OK; synthetic Gemma3 4B NF4 forward/backward/AdamW succeeded. Trainable 1,611,776; seq len32; peak allocated 5660.7 MiB; free 8235 MiB. Loss=2.49 synthetic only. Explicit non-reentrant gradient checkpoint patch made; not rerun yet.

## 2026-10-18 — Synthetic LoRA repeat success
- Repeated private-data-free Gemma3 4B NF4 adapter training report status ok, peak allocation 5660.7 MiB; no real messages used. Console warning state unavailable from JSON.

## 2026-10-18 — Persona split audit and rights review
- After synthetic Gemma 3 4B QLoRA optimizer success, implemented local aggregate-only chronological train/validation and cross-split dedup analysis. Added 3 unit tests; expected 155. Current user personal Discord messages not trained. Official API content ML training requires Discord express permission; personal-data export route still requires independent review.

## 2026-10-18 — Real persona split audit QA
- 155 tests OK, 2 exports analyzed: eligible instances 221883; train unique 164662, val unique 20356, cross split overlap 2130, clean val unique 18226. No raw messages/hashes in reports. Rights/privacy gate remains open.

## 2026-10-18 — Persona research review
- Compared primary LoRA/QLoRA/DoRA papers, memorization risks, and TRL/PEFT examples. Created docs/PERSONA-RESEARCH.md with EchoMate-specific baselines and experiment gate. No private message uploads or model training.

## 2026-10-18 — Research-driven one-speaker dataset pipeline
- Implemented private, double-gated local JSONL export with chronological validation and exact cross-split dedup. Synthetic regression tests added (3). Previous 155 Windows OK; new 158 expected. Private corpus generation not executed.

## 2026-10-18 — Private local LoRA runner
- User 158 QA OK. Added offline Gemma3 4B NF4 LoRA training runner with explicit owner-data approval gate, private output paths, conservative step/token bounds and three unit tests. Expected 161 tests. No user data trained yet.
