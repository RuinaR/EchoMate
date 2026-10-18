# AI 인수인계서 — EchoMate 현재 상태

마지막 갱신: 2026-10-18
저장소: https://github.com/RuinaR/EchoMate
진행: **Phase 1 Studio 전처리**, 실제 학습과 Bot 실행은 아직 시작 전.

## 반드시 유지할 최신 결정
1. **EchoMate Bot과 EchoMate Studio 완전 분리.** 봇은 읽기 전용 모델 로더/Discord 자율 대화만, Studio는 오프라인 분석·학습/캐시.
2. Studio가 허용된 데이터 파일 내 작성자 목록을 보여주고 사용자가 고른 사람을 별도 페르소나로 제작하는 확장 계획. 첫 검증 대상은 본인. **Studio 입력은 JSON N개(최소 1개, 상한 고정 없음)**이며 **파일당 채널 하나**라는 경계를 보장.
3. Discord 현재 대화의 문맥은 범용 로컬 LLM이 해석, 과거 단일 화자 자료는 표현 습관 재현에 활용하는 방향.
4. 최근 자료에 높은 가중치. 파일별 채널 경계 보존. Unicode 기본 이모지만 출력; GIF·스티커·첨부·커스텀 이모지 금지.
5. 모델 버전/데이터 기준일/갱신 상태를 명시하고 품질 검증 후 교체. 운영 중 모델 학습 금지.
6. 관계별 톤은 현재 대화에 임시 적응할 수 있지만 Discord API 데이터로 사람 간 영구 친밀도 프로파일링 금지.
7. 사용 허가가 확인되지 않은 Discord 자료를 무단 AI 학습에 투입하지 않는다.

## 실제로 구현된 것
- `src/echomate_studio/analyze.py`: JSON 구조/ID/시간 검증, 파일별 통계, URL·멘션·커스텀 이모지 제거, 반감기 가중 평균 문자 길이, 연속 발언 후보 그룹 수.
- `tests/test_analyze.py`: 기존 합성 입력 단위 테스트 5개 + 신규 3개 채널 CLI 인수 테스트 1개(신규 테스트 실행 미확인).
- `docs/STUDIO-QUICKSTART.md`: PowerShell 실행법.
- GUI 없음, 페르소나 아티팩트 없음, QLoRA·RAG 미구현, Discord 봇 실행 코드 없음.

## 실측 자료 및 Windows 확인
사용자가 제공한 **첫 2개 검증용 파일**(각 파일 = 별도 채널, 단일 화자) 메시지:
- messages1: 244,976건, 필터 후 텍스트 223,737건, 기간 2021-02-27 ~ 2026-10-16, 발화 묶음 후보 114,009
- messages2: 60,021건, 필터 후 텍스트 47,252건, 기간 2023-07-04 ~ 2026-10-17, 발화 묶음 후보 28,588
- 총 304,997건, 필터 후 270,989건
- 2026-10-18 Windows PowerShell: `python -m unittest discover -s tests -v` 5개 모두 `OK`, 분석 명령 실행 성공.
- 실제 `report.json` 수신·확인. 원본 메시지·개인정보·첨부 URL/해시는 GitHub에 올리지 않음.
- 이 검증은 전처리만 해당, 학습/실제 AI 품질 검증이 아님.

## 다음 작업
1. 데이터 스트리밍 파서와 개인정보 필터 품질 테스트.
2. Bot/Studio 간 페르소나 아티팩트 계약과 Ollama 기준선 평가.
3. 적법하게 이용할 수 있는 사례로 스타일 분석/RAG/선택적 QLoRA 성능 비교.
4. 지정 채널/스레드에서 자율 대화하는 Discord Bot 별도 구현 및 Windows 실기기 QA.

## AI 작업 규칙
변경 전 README → PROJECT-DEFINITION → ARCHITECTURE → ROADMAP → HANDOFF → WORKLOG 확인.
진행 시 합성 데이터 테스트를 수행하고, 완료 후 WORKLOG와 HANDOFF 갱신. 테스트하지 않은 것을 완료로 선언하지 않는다.
원본 데이터/봇 토큰·비밀/로컬 아티팩트는 절대로 공개 GitHub에 올리지 않는다.

현재 설계의 기술적 참고 자료는 REFERENCE-PROJECTS와 각 활성 설계 문서에만 둔다. 폐기된 과거 요구 문서 5개는 현재 브랜치에서 삭제되었다. JSON 입력은 `nargs='+'`로 최소 1개, 여러 개 지원. 각 파일을 별도 채널로 취급. 추가된 6번째 테스트는 아직 Windows 실행 확인 전.

## 2026-10-18 후속 구현: 스트리밍 JSON 파서
- `src/echomate_studio/analyze.py`의 `json.load` 방식에서 증분 JSON 배열 파싱(`iter_json_array`)으로 전환. 본문은 길이만 유지하고 파일 SHA-256도 청크 단위로 계산.
- 기존 통계 출력 JSON 키와 계산 규칙 유지. 서로 다른 파일은 서로 다른 채널로 계속 처리.
- 테스트 3개 추가: 대형 배열/청크 경계, 문법 오류 감지, 파일 1개 처리. **현재 9개 테스트로 증가; Windows 재실행 전 검증 미완료.**
- 여전히 통계용 `(timestamp,length)`와 메시지 ID 집합을 RAM에 유지. 완전한 상수 메모리 아님.
- 다음 조치: 사용자 Windows QA 결과, 원본 2개 JSON에 대한 `report-v2.json`과 기존 보고서 통계 대조.

## 2026-10-18 — 로컬 Ollama 기준선 추가
- 사용자 Windows 분석기 9개 단위 테스트 OK. `report-v2.json` 수치 및 SHA-256가 이전 `report.json`과 전부 일치함을 확인.
- 새 코드: `ollama_client.py`, `conversation.py`, `chat_probe.py`; 새 모킹 테스트 `tests/test_conversation.py` 6개.
- 현재 총 15개 테스트가 예정됨. **추가된 6개와 실제 Ollama 생성은 사용자 PC 검증 전**이며 실행 성공 단정 금지.
- 모델 호출은 localhost 제한, 한 턴 현재 대화/설정된 짧은 스타일 지침을 사용. 원본 Discord 기록은 전달하지 않음. 학습·페르소나 모델·Discord 봇 코드 없음.
- 다음 확인: `python -m unittest discover -s tests -v` / `python -m echomate_studio.chat_probe --model ... --message ...` 출력.
- 이후 평가 세트/시간 계측, 명시적 스타일 프로필, 아티팩트 버전 관리 및 Discord Bot 순차 구현.

## 2026-10-18 긴급 오류 수정 + 반응 기능 추가
- 사용자 Windows QA: 15개 중 13개 OK, 2개 실패(`sanitize_output`이 한글/이모지 전부 지움). 모델 CLI 또한 빈 답변. 원인: `conversation.py`의 공백 정규식 이중 백슬래시. `r"[^\\S\\n]+"`를 `r"[^\S\n]+"`로 수정.
- Ollama 모델 공유: AITrader와 EchoMate가 동일한 Ollama 모델을 사용할 수 있으나 동시 추론 경쟁/VRAM/대기 지연 주의. Qwen3.5 thinking-only 응답 대비 요청 `think=false`, 빈 응답은 `OllamaError`로 명시.
- 신규 코드: `echomate_studio/reactions.py` 독립 정책 게이트; 기본 비활성, 개별 채널/스레드 allowlist, 반응 확률/쿨다운, 기본 Unicode 이모지, 봇/자기 메시지/opt-out 제외.
- 요구사항: 봇의 자율 이모지 반응 기능, 대화 발언과 별도 활성화/빈도/활동 범위 설정. Discord API 연동·문맥 기반 이모지 선택은 아직 미구현.
- `tests/test_conversation.py` 신규 2개, `tests/test_reactions.py` 신규 6개. **기존 15개 대비 총 23개 테스트 예정, 사용자 PC 미검증.**
- 다음 사용자 실행: `git pull origin main`, `$env:PYTHONPATH="src"`, `python -m unittest discover -s tests -v`, `python -m echomate_studio.chat_probe --model "qwen3.5:9b-q4_K_M" --message "오늘 메이플 할래?"`.

## 2026-10-18 — 자율 발언 침묵 게이트 추가
- 사용자 실기기 QA: 23개 단위 테스트 전부 OK, 실제 Ollama `qwen3.5:9b-q4_K_M` 응답 `좋아! 오늘 메이플 갈까? 🍁` 확인.
- 사용자 요구: 활발함 설정에서도 대화 분위기가 안 좋거나, 끼어들 필요가 없거나, 너무 조용하면 침묵.
- `src/echomate_studio/participation.py`는 확률을 강제 발언 수단으로 쓰지 않고 상황 평가와 차단 규칙을 먼저 적용. 대응 테스트 `tests/test_participation.py` 7개 신규 작성.
- **현재 ContextAssessment 값은 실제 Discord 대화로부터 계산되지 않음**. 생성 판단 파이프라인/라이브 Bot은 미구현. 테스트 7개는 사용자 Windows 검증 전이며 총 30개 예상.
- 다음: 상황 평가기 작성 및 Bot과 연결, 자연스러움/실수로 끼어듦/침묵의 정확도 테스트.

## 2026-10-18 — 대화 연속성 모듈
- 사용자 Windows QA로 기존 30개 unittest 모두 OK 확인.
- 추가 최신 요구: 자율 개입 전후로 대화 맥락 연속성 유지, 화자/답장 관계 분리, 최근 상황 변화에 따라 생성 중 답변 취소.
- `src/echomate_studio/dialogue_state.py` 구현: 채널/스레드별 TTL 및 최대 메시지 수, 중복/역순 이벤트 제한, 화자 라벨·답장 참조를 LLM 컨텍스트로 정리, 상태 버전 검증.
- `tests/test_dialogue_state.py` 5개 추가. 총 35개 테스트 예정. **신규 테스트는 아직 Windows 실행 확인 전**.
- 맥락 의미 이해나 실제 Discord 입출력은 아직 구현되지 않았음. 모델에 붙이는 구체적 통합은 후속 작업.

## 2026-10-18 — 32GB RAM 환경 메모리 확장
- 사용자 Windows에서 직전 35개 단위 테스트 전부 통과.
- 요구: 대화 흐름과 정보를 더 오래 기억해도 됨(PC RAM 32GB).
- `DialogueState` 기본 보관 한도 40→500개 메시지, 1800→86400초 변경. `recent_context`로 RAM 기록과 LLM 프롬프트 기본 16000자 예산 분리.
- 합성 테스트 2건 추가, 현재 총 37개 예정. **신규 Windows QA 전**.
- 실제 Ollama 컨텍스트 창/토큰 수는 자동 확장된 것이 아니며 토큰 상한/주제 요약 로직은 미구현. 영구 저장/장기 개인정보 프로파일링 기능 없음.

## 2026-10-18 — ContextAssessor 초안
- 사용자 Windows에서 기존 37개 단위 테스트 OK 보고.
- `echomate_studio.context_assessor`: 로컬 Qwen에게 현재 대화를 전달하고 세 가지 Boolean(민감, 기여 가능성, 개입 적절)을 JSON으로 요구; 실패/형식 오류 시 발언 차단.
- `echomate_studio.autonomy_probe`: 여러 `--message` 합성 대화 입력으로 판단·침묵 게이트 직접 시험하는 CLI.
- `tests/test_context_assessor.py` 단위 테스트 7개 작성. **Windows 신규 테스트 및 실제 판단 결과 미검증**. 예상 테스트 총 44개.
- 이 모듈은 현재 과거 데이터로 학습하지 않으며 Discord API와 연결하지 않는다.
- 다음 단계: 로컬 CLI 테스트·실전 정확도 확인, Discord Bot에 통합하기 전 이벤트/레이스·취소 설계 테스트.

## 2026-10-18 — 문맥 평가→생성 파이프라인 연결
- 사용자 Windows: 44개 단위 테스트 모두 통과. 실제 Qwen 문맥 테스트에서 메이플 보스 일정 확정 대화에 `no_useful_contribution` 침묵 반환 확인.
- 신규 `src/echomate_studio/turn_pipeline.py`: 버퍼 스냅샷, 범위/빈도 게이트, 문맥 평가, 답변 생성, 생성 전후 오래된 스냅샷 검사, 텍스트 출력 제한, 오류 침묵을 묶는 독립 파이프라인.
- 신규 `tests/test_turn_pipeline.py`: 6개 테스트 작성. 총 50개 테스트 예정(추가 테스트 사용자 Windows 실행 전).
- 실제 Discord Gateway/이모지 반응 API/토큰 설정/동시성 직렬화는 아직 구현되지 않음. 실전 사용 전 송신 직전 버전 재확인 및 채널별 잠금도 필요.
- 개발 주의: 빈도 확률은 유효한 대화 판단 전에 적용하므로 구현 세부의 호출 비용/침묵율을 테스트로 확인할 것. 과도한 발언 방지 기본값은 off.

## 2026-10-18 최신: Windows QA, 생성 중 수정 및 페르소나 우선순위
- 사용자 Windows unittest 50개 모두 OK. 신규 stale_recovery.py는 재시도 횟수 제한으로 새 메시지 발생 시 무한 생성 방지, 테스트 5건 신규(총 55건 예상). **신규 테스트 Windows 미확인.**
- 실제 Discord 전송 시 잠금 안에서 스냅샷 재검증 필요. 현재 복구 모듈은 오프라인.
- 사용자는 필요한 경우 인터넷 검색을 원함. 웹 검색은 opt-in, 질의 최소화, 출처/날짜, 실패 안전 정책으로 진행(아직 미구현).
- 사용자는 페르소나 학습 시작 시점을 질문. **다음 1순위는 Style Profile v1 및 Qwen A/B**. 실제 모델 가중치 QLoRA 학습은 데이터 이용 허가 검증, GPU/품질 평가 후 단계적으로 결정.
- 설계: docs/SEARCH-AND-PERSONA-PLAN.md.

## 2026-10-18 — Style Profile v1 최초 코드
- 직전 Windows 55개 테스트 모두 OK.
- `style_profile.py` 로컬 다중 채널 JSON 입력/최근 시간 반감기(기본 365일)/짧은 메시지/웃음·울음·질문·감탄·기본 이모지 사용률을 집계. 원문 메시지나 ID를 결과에 저장하지 않음.
- `chat_probe.py --profile`로 요약 집계값에서 파생한 스타일 지침을 생성 모델 프롬프트에 적용할 수 있음.
- `tests/test_style_profile.py` 3건 신규 작성, 총 58건 예상(Windows 검증 전).
- **기존 Qwen 모델 가중치 학습/QLoRA 아님**. 통계형 프로필 프롬프트의 품질 평가 다음 작업.
- 실행: `python -m echomate_studio.style_profile "C:\\Users\\user\\Desktop\\학습데이터\\messages1.json" "C:\\Users\\user\\Desktop\\학습데이터\\messages2.json" --output local_data/style-profile.json` 후 `python -m echomate_studio.chat_probe --profile local_data/style-profile.json --message "오늘 메이플 할래?"`.

## 2026-10-18 스타일 QA 실패 / 연구 기반 수정
- 사용자 Windows 58개 테스트 OK. 생성된 style-profile.json은 2개 채널, 304,997 원본, 270,989 텍스트, 평균 7.25자, 웃음 0.0402, Unicode 이모지 0.0039.
- 모델이 '메이플 서비스 종료'라는 거짓 단정을 하고 길고 격식 있는 답변 생성. 테스트 통과와 실제 품질을 구분할 것.
- `conversation.py` 시스템 프롬프트: 일상 초대 의도/짧은 캐주얼 채팅/검증 없는 서비스 종료 추측 금지.
- `style_profile.py`에서 과장된 특성 대신 짧고 담백한 기본 반응을 권장. `chat_probe.py --timing` 추가.
- 새 테스트 1개 추가(예상 총 59개, 사용자 Windows 확인 전).
- 문헌·프로젝트 검토: docs/PERSONA-RESEARCH-AND-QA.md (Lost in the Middle, mimic-bot, PersonaAgent, llmcord).
- 실제 품질 향상과 지연 개선은 미검증; 별도 다중 프롬프트 A/B QA 필요.

## 2026-10-18 — 교차 A/B 재평가 단계
- 사용자 Windows unittest 59개 OK.
- 기본 모델 `오늘 메이플 할래?`: `네, 지금 바로 시작할까? 준비됐으면 같이 들어올게.` 4.55초. 스타일 프로필 적용: `그거 지금 언제 하는 거야?` 0.23초.
- 프롬프트 하나로 평가 불가능. 캐시/모델 로딩 영향 때문에 시간 차이를 모델 유형의 속도차로 해석하지 않을 것.
- `conversation.py`에 AI가 게임에 실제 접속하는 듯 약속하는 것을 금지하고, 이미 이해한 초대는 되묻지 않도록 수정.
- `echomate_studio.ab_probe` 신규: 기본 vs 프로필을 4개 시나리오에서 번갈아 테스트하여 `local_data/ab-results.json` 생성. CLI 실기기 미검증.
- 다음은 사용자 Windows A/B 결과 보고 반복, 부적절성, 속도 분포 및 개인 말투 적합성 평가. 모델 미세조정은 아직 착수 전.

## 2026-10-18 — A/B 16개 결과 분석 및 내용 우선 프롬프트 재설계
- 사용자 Windows 단위 테스트 59개 전부 OK. 4개 질문 × 2회 × 기본/프로필 = 16개 실제 응답 확인.
- 중앙값 기본 0.31초, 프로필 0.29초. 프로필 사용 여부의 성능 차이로 볼 근거 없음. 둘 다 역할 혼동, 약속 환각, 화제 이탈 및 어색한 답변 발견.
- `conversation.py`: 반복된 과잉 지침을 단순화하고 내용·역할·문맥을 말투보다 우선하는 짧은 시스템 프롬프트로 변경.
- `reply_quality.py`: 실제 게임 접속 주장/서비스 종료 단정/힘든 상황에서 게임으로 화제 이탈/이모지/과장 길이 후보 검사(자동 오류 확정 아님).
- `ab_probe.py` 리포트에 `quality_flags` 추가. `tests/test_reply_quality.py` 4개 신규 테스트. 총 63개 예상. **신규 Windows QA 및 품질 개선 여부는 아직 검증 전**.
- 다음에는 동일 A/B 실행·수동 품질 점수와 지연 분포 비교. 집계형 스타일 프로필만으로 실제 페르소나 재현이 어렵다는 사실을 계속 분명히 할 것.

## 2026-10-18 — 63개 테스트 중 1개 회귀, A/B 품질 판단
- 사용자 Windows 63개 중 1개 실패: 시스템 프롬프트 리팩토링 후 테스트가 옛 문구 `AI 디스코드 봇`을 기대함. 구현 고장이 아니라 테스트 고정 문자열 불일치. `EchoMate AI 봇`을 검사하도록 테스트 수정(재검증 필요).
- 사용자 A/B 16회: 양측 중앙 응답시간 약 0.3초, 그러나 엉뚱한 게임 참여 약속/격식체/조악한 문장/과도한 이모지. 9B 로컬 모델 품질과 집계 통계 프롬프트 한계를 구분할 것.
- 우선순위: 검증 사례 확대, 다른 로컬 모델과 블라인드 A/B(32GB RAM, RTX 4070 실행 부담 고려), 스타일 통계 넘어 상황별 반응 모델 평가. 페르소나 모델 가중치 학습이라고 주장 금지.

## 2026-10-18 — Gemma 3 12B 로컬 설치 성공, 모델 비교기 구현
- 사용자 Windows `ollama pull gemma3:12b` 결과 sha 검증·manifest 기록·success. 상단 `mlx_compile_cache_new_` 경고는 남았지만 설치 완료.
- `src/echomate_studio/model_compare.py` 두 모델에 동일 말투 프로필과 5종 질문을 번갈아 적용하고 답변/지연/QA 경고 저장.
- `tests/test_model_compare.py` 3개 신규. 기존 사용자 63개 테스트 OK이므로 **총 66개 예상**, 신규 Windows 검증 전.
- 모델 변경 결정은 한국어 자연스러움, 상황 이해, 사실성, 4070 실행 중 GPU/RAM 사용량과 지연으로 평가. Gemma 12B가 빠르거나 우수하다는 결론 아직 없음.
- `local_data/model-comparison.json`은 생성 내용 포함해 무조건 로컬 보관.

## 2026-10-18 — Qwen/Gemma 대조 실측 + 다중 턴 QA
- Windows 66개 테스트 OK. 사용자 model-comparison.json에 20회 응답 포함.
- Qwen 중앙값 1.07초, Gemma 0.76초. 모델 교체/초기 로딩 시간 포함. Gemma의 단문 한국어 반응 우세 경향은 있으나 7시를 근거 없이 두 번 지어내는 결함 확인. Qwen은 웃음 메시지에 중국어 반복.
- 기존 model_compare의 '아까 몇 시?' 사례는 앞선 대화가 없는 단발 질문으로 설정돼, 실제 문맥 기억 능력을 평가할 수 없었음.
- 추가 `context_compare.py`: 단일 무정보 질문 / 9시 확정 / 9→10시 변경 / 웃음 등 합성 다중 턴 시나리오. `quality_hints`는 일부 패턴만 감지하는 QA 후보 도구.
- `conversation.py`: 대화 근거 없는 시간/참석자 발명 금지, 가장 최근 확정된 사항, 한국어 우선.
- 신규 tests/test_context_compare.py 4개. **현재 70개 테스트 예상, Windows 검증 전**.
- 다음: 사용자 `context-comparison.json` 받아 사실성·자연스러움 판단, GPU 메모리와 지속 실행 부담 고려해 모델 결정. 실제 미세조정/Discord 연동은 미완료.

## 2026-10-18 — 70개 통과 / 시간 예시 프롬프트 누수 수정
- 사용자 Windows 70개 단위 테스트 전부 OK, `context-comparison.json` 8답변 제공.
- 무정보 시간 질문: Qwen은 근거 없음 답변, Gemma는 `10시에 만나요` 허구. 9시만 확정된 시나리오에선 두 모델이 `10시로 변경`이라고 허구의 변경을 주장했고, 9→10시 실제 변경은 두 모델 모두 맞힘.
- **원인 후보 발견:** 당시 `conversation.py` 시스템 프롬프트 자체에 `9시였다가 10시로 변경되면 ... 10시`라는 구체 예시가 있었다. 실제 대화에 없는 10시 정보를 프롬프트에서 오염시켰을 수 있음. 모델 결함만으로 단정 금지.
- 예시 제거하고 `현재 대화 기록에서 가장 마지막으로 확인된 내용`이라는 일반 규칙으로 대체. `tests/test_conversation.py`에 시스템 프롬프트의 9시/10시 누수 방지 테스트 1건 추가. **71개 예상, 새 Windows 검증 전**.
- Gemma는 자연스러운 한국어 응답 후보이나 무정보 질문에서 10시 허구 응답이 여전히 중요. 수정 후 비교 반복, 모델 선정 보류.

## 2026-10-18 — 71개 테스트 통과 / Gemma 문맥 개선
- 사용자 Windows 71개 테스트 OK. 프롬프트 시간 예시 제거 후 실제 context_compare: Gemma unknown_time은 기록 없음, known 9시는 9시, changed 10시는 10시로 정확한 답변. Qwen unknown은 기록 없음, known 9시에는 결정된 게 없다고 오답, 변경 10시는 정확.
- 기존 QA 정규식이 `시간 정보가 없습니다` 안의 `보가 없...`가 아니라 `한 시` 같은 부분과 겹치는 문제로 정상적인 부정 표현을 시간 창작으로 오탐. 시각 경계/접미어 조건을 강화하고 회귀 테스트 1개 추가.
- Gemma3 12B를 현 페르소나 대화 모델 우선 후보로 둘 근거가 강화되었지만 표본은 아직 매우 작음. 조기 확정과 파인튜닝 성공 주장 금지.
- 다음 Windows 전체 72개 테스트 확인, 테스트 정확성/더 넓은 대화 평가 후 모델 선정 및 허가된 데이터 학습 실험.

## 2026-10-18 — 사용자가 원본 메시지의 실제 미세조정 활용 요청
- 사용자 Windows 기존 72개 테스트 OK.
- 목표에 Gemma 3용 LoRA/QLoRA 미세조정 실험을 명시적으로 추가하되 **아직 학습 시작 안 함**.
- Discord 개발자 정책 §21은 API로 수집된 메시지의 AI 학습에 Discord 명시적 허가 요구. 공식 개인 데이터 패키지의 AI 학습 허용 범위는 명확하게 확인되지 않아 별도 출처·권리 검토가 필수. https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy
- Gemma 공식 QLoRA 문서: https://gemma.ai/tuning/ 와 https://gemma.ai/tuning/qlora/ . Ollama GGUF를 그대로 튜닝하는 게 아니라 학습 가능한 모델 가중치·별도 프레임워크 필요.
- 신규 `style_diagnostics.py`: 다중 채널 스트리밍 입력의 글자 수 분포와 문장 종료 패턴 최근 가중 집계. **내용·예시·고유 ID·시각·단어는 내보내지 않음**. 정규식 이스케이프 교정까지 완료. Windows 아직 미검증.
- 신규 `tuning_readiness.py`: 로컬 권리·보안·분할·환경·QA 준비상태 리포트. 실제 학습/원문 출력 없음. 테스트 4개 추가(기존 72개 + 신규 4개 = 76개 예상). 원본 JSON/비공개 파일 GitHub 커밋 금지.
- 다음: 76개 테스트와 진단 리포트 사용자 Windows 실행 확인, 권리 확인 이후에만 안전한 데이터셋 추출 및 학습 파이프라인 구현.

## 2026-10-18 — Windows 76개 QA 및 스타일 진단 정규식 오류 수정
- 사용자 Windows 76개 테스트 모두 OK. 로컬 style-diagnostics.json: 원본 304,997건, 필터된 텍스트 270,989건. 최근 가중 길이 0–5자 48.18%, 6–12자 38.76%, 13–25자 11.68%, 26–50자 1.31%, 51+자 0.07%.
- 그러나 ending_rates 전체 0.0: `style_diagnostics.py` 정규식이 raw string 안에서 `\\s`/`\\.`로 이중 이스케이프되어 정상 문장 끝을 감지하지 못한 것 확인. 정규식 교정하고 `tests/test_style_diagnostics.py` 3건 추가. 기존 76 + 신규 3 = 총 79개 예상, Windows 실행 전.
- 튜닝 준비 보고서 status not_ready: rights_reviewed, owner_reviewed, training_data_screened, train_validation_split, compatible_base_weights_ready, qlora_environment_ready, baseline_quality_comparison_ready 모두 미완료. 실제 학습은 실행되지 않음.
- 다음: 79개 테스트 및 사용자 원본 2개에서 style_diagnostics 재실행, 출력 확인. 데이터 사용 허가 판단 전 QLoRA 실학습은 보류.

## 2026-10-18 — 사용자 원본 파일 직접 분석 허용 / 79개 검증
- 사용자 Windows unittest **79개 모두 OK**. 정상화된 ending_rates: 질문 0.1098, 감탄 0.0021, 마침표 0.0525, 웃음 0.0389, 울음 0.005, 말줄임 0.0235. 최근 가중 12자 이하 0.8694.
- 사용자가 **본인 메시지 원본 2개는 어시스턴트가 직접 검토해도 됨**, 단 GitHub 업로드 금지를 명시적으로 허용함. 대화 파일 검색으로 `messages1.json`(약 32.3MB), `messages2.json`(약 8.8MB) 현재 대화 파일에 존재함을 확인. 사용자 재업로드 요구하지 말 것.
- 공개 GitHub에는 원본/발언 인용문/비공개 학습·평가 코퍼스를 올리지 않고, 개인 식별 콘텐츠의 로그 출력/커밋 방지. `.gitignore`에 messages*.json, 파생 JSONL 학습 파일, 모델 산출물 제외 추가. 이미 추적 중인 파일은 .gitignore만으로 막히지 않으므로 별도 git status/repo 확인 필요.
- 사용자 허락은 파일 검토 및 저장소 비공개 원칙에 관한 것이며 Discord 데이터 학습 사용 허가의 법적 확인을 대체하지 않음. 실제 QLoRA 미실행.

## 2026-10-18 — 실제 원본 2채널 직접 검사 / 코퍼스 QA 구현
- 사용자 요청: 판단에 따라 계속 개발, 원본 파일 직접 검토 허용, GitHub 원문 업로드 금지.
- mounted original `messages1.json`(244976 records; 2021-02-27..2026-10-16) and `messages2.json`(60021 records; 2023-07-04..2026-10-17) inspected programmatically. Both reversed chronological. Raw nonempty 228342 / 52788. Many repeated short texts; message gaps <=10 sec 120915 / 23812, but do not infer reply-pairs since author-only.
- `corpus_audit.py` added: per channel record counts, reverse ordering, repeated normalized messages, 10s adjacency, URL/mention/long-numeric/email candidate counts. Only aggregate counts, no raw strings, IDs, quotes or samples output. Regex corrected; `tests/test_corpus_audit.py` three synthetic tests.
- Previously Windows 79 tests OK, new **82 expected**, Windows not yet run.
- CRITICAL: user permission to inspect uploaded data is not a blanket claim of permission to train under Discord rules. Continue source/rights review. No fine-tuning or export yet. Direct corpus is available on current conversation mount, no need re-upload.

## 2026-10-18 — Bot @멘션 응답 경로
- 사용자가 @bot 멘션을 받으면 답하도록 추가 요청. `mention_reply.py`에서 정확한 Discord bot user ID와 `<@id>`/`<@!id>` 멘션을 검사하며 채널/스레드 허용 목록·opt-out·self-bot·쿨다운 반영.
- `turn_pipeline` 명시적 멘션 분기는 자율 대화 확률이나 enabled 상태와 별개이지만 민감도, 범위, stale, 모델 오류는 차단. 오프라인 정책이며 Discord 송수신은 미구현.
- 신규 테스트 9개로 사용자 마지막 79개 통과 기준 총 **88개 예상**. Windows 미검증.
- corpus-audit.json: 채널1 244976 / text 223737 / distinct 156163 / repeated 78024, 채널2 60021 / text 47252 / distinct 36864 / repeated 12607. 공개 GitHub에 원본 미업로드.

## 2026-10-18 — 지속 참여 중 자율 확률/쿨타임 분리
- 사용자 요청: 봇이 이미 자연스럽게 참여 중이면 자율 진입 확률·쿨타임에 영향받지 않고 대화를 이어가야 함. 단 무조건 발언은 아님.
- 사용자 Windows 91 tests 중 7 FAIL: `mention_reply.MENTION` regex에서 `\\d` 이중 이스케이프 때문에 Discord `<@ID>` 인식 실패, 파이프라인 관련 연쇄 실패. regex 수정.
- 신규 `engagement.py`: 최근 참여 상태, 봇에게 말이 향하는지, 주제 지속 여부, 180초 기본 만료에 따른 대화 이어가기 판단. 파이프라인은 이어가기 중 진입 확률/쿨타임/끼어들기 평가를 건너뛰되 유용성, 민감도, allowlist, opt-out, 봇 자기발언, stale 검사 유지.
- **중요:** ongoing_engagement / addressed_to_bot / topic_continues를 이벤트+맥락으로 신뢰성 있게 산출하는 구현과 Discord API 연동은 아직 미완성. 단순 최근 발언만으로 활성 상태로 취급 금지.
- 테스트 tests/test_engagement.py 2개 + tests/test_turn_pipeline.py 3개, 기존 91개에서 5개 추가해 **96개 예상**, Windows 미검증.

## 2026-10-18 — 96개 테스트 중 3개 실패 원인 수정
- 사용자 Windows 96개 실행 중 3 FAIL. `test_direct_mention_bypasses_autonomous_frequency`는 직접 멘션임에도 자율 참여용 `has_useful_contribution=false`에서 차단된 문제. `turn_pipeline`에서 direct mention은 자율 유용성·끼어들기 조건을 우회하되 민감한 순간·scope·optout·멘션 쿨타임·오류·stale 검증 유지하도록 수정.
- `test_engagement_expires_or_changes_topic`: 참여 지속 만료 300초는 cooldown 180초도 이미 지나 일반 자율 확률 0 때문에 `frequency_gate`가 맞음. 테스트 기대값 수정.
- `test_engagement_still_respects_safety`: 테스트의 마지막 발언 300초 후는 기본 180초 연속성 TTL 초과였음. 5초로 변경해 실제 지속 참여 중 민감도 차단 검증.
- 기존 코드 기준 96개 테스트 유지, 수정 후 Windows 재검증 전. 멘션·참여 지속은 아직 Discord Gateway 미연동.

## 2026-10-18 — 활성 참여 판단: 시간보다 실제 대화 맥락 우선
- 사용자 Windows 96개 unittest 전체 OK 확인.
- Discord 대화에서 몇 분 이상의 텀도 자연스러움: 기본 `EngagementPolicy.max_gap_seconds=None`으로 하드 타임아웃 제거. 선택적으로 양수 제한 설정 가능.
- `continue_engagement`는 이전 참여 상태, 봇에게 향한 발언, 주제 연속성이라는 **세 신호 모두 참일 때만** 확률/자율 쿨타임 우회. 단순 시간 근접만으로 참여 상태를 만들 수 없으며, 시간이 길어도 세 신호가 살아 있으면 연속 대화로 허용.
- tests/test_engagement.py: 1시간 연속성, 즉각 주제 전환 종료; tests/test_turn_pipeline.py: 기본 300초 이어짐, 관련 증거 없으면 자동 진입 안 함 테스트 추가. **총 97개 예상, 새 Windows 검증 전.**
- 중요: 실제 Discord 이벤트 기반으로 발언 대상/스레드/답장 대상/주제 연속성 판정하는 구현은 여전히 미연결. 이 세 인자를 무조건 true로 전달하면 안 됨.

## 2026-10-18 — Windows 97개 통과 / 실제 답장 참조 기반 참여 판별 착수
- 사용자 Windows 97개 unittest 모두 OK.
- `engagement_evidence.py`: 같은 채널/스레드의 `DialogueState.Turn.reply_to`가 실제 bot turn ID를 가리키는지 확인. 연결된 봇 응답이 있으면 addressed_to_bot 및 ongoing_engagement 근거로 삼고, `topic_continues`는 별도 실제 맥락 판단이 반드시 True여야 유효. 다른 사람 답장/인접 메시지/모르는 ID는 연속성 근거 불인정.
- `turn_pipeline`은 `state.snapshot()`에서 reply 대상 확인 후 명시적 봇 대상이면 이어가기 분기에 반영. 단 현재 topic_continues 외부 판정과 실제 Discord 수집·송신은 미구현.
- tests/test_engagement_evidence.py 5개 + tests/test_turn_pipeline.py 1개. 기존 97개에서 총 **103개 예상**, Windows 새 QA 전.
- 원본 Discord 데이터와 비공개 학습 내용 GitHub 비업로드 원칙 유지.

## 2026-10-18 — 103개 통과 / 로컬 주제 연속성 판정기
- 사용자 Windows 103개 unittest 모두 OK.
- `topic_assessor.py`: 실제 같은 채널/스레드 `reply_to` 대상 봇 발언과 사용자 답장을 로컬 Ollama Gemma3:12b에 전달하여 JSON 단일 boolean `topic_continues`를 엄격 판독. 모델 오류/부정확한 JSON은 False. 시간/인접성만으론 연속성 불인정.
- `turn_pipeline.evaluate_turn`에 선택적 topic_assessor 콜백을 추가. 실제 bot reply reference가 있는 경우 평가기를 호출하고 에러는 연속성 거부. 기존 외부 명시 조건 호출은 호환 유지. 네트워크 Discord Gateway/발신 미구현.
- tests/test_topic_assessor.py 4개, tests/test_turn_pipeline.py 2개 추가. **109개 예상, Windows 실행 미확인**. 실제 Ollama 판정 정밀도는 따로 실측 필요.
- 비공개 Discord 원본 및 발언/모델 평가 로그를 GitHub에 올리지 않음.

## 2026-10-18 — 109 tests OK, 실모델 주제연속성 QA CLI
- 사용자 Windows 109개 unittest 전부 통과.
- 신규 `src/echomate_studio/topic_qa.py`: 개인 메시지 원본을 포함하지 않는 합성 Discord 대화 6건(보스 시간·변경·주제 전환·사냥 후속·타인 대화·짧은 맞장구), 로컬 Gemma 3 12B의 topic_assessor 실제 판정/소요시간/정답 여부를 `local_data/topic-qa.json`으로 기록.
- `tests/test_topic_qa.py` 2건 추가, **111개 예상**. 실제 Ollama QA 및 Windows 신규 테스트 미검증. 이 6건만으로 실제 운용 안정성 단정 금지.
- 원본 메시지와 비공개 학습셋 GitHub 업로드 금지, 개인 정보 제거 원칙 유지.

## 2026-10-18 — 실제 Gemma 주제 판정 6/6 및 111 unittest 확인
- 사용자 Windows `python -m unittest discover -s tests -v`: **111 tests OK**.
- 사용자 로컬 `python -m echomate_studio.topic_qa --model gemma3:12b`: 합성 6개 중 **6개 정답**, `boss_time_reply` 9.306s 최초 요청, 이후 0.249~0.285s (외부 호출 없는 다른 사람 답장 경로 0.0s). 성공 사례: 시간 제안/변경, 주제 전환, 게임 후속, 타인에 대한 답장 제외, 짧은 `ㅇㅋ`.
- 근거는 표본 6개일 뿐 실전 정밀도/재현율 보장하지 않음. 다음 우선순위: 여러 사람이 말하는 복합 상황, 주제 전환, 답장 없는 구어체 후속, 부정사례를 평가하는 테스트 확장 후 Discord Gateway 연동. 개인정보/사용자 원본은 GitHub 업로드 금지.

## 2026-10-18 — Windows 111 OK / 암묵적 대상 판정 1차 연결
- 사용자 Windows 111 tests OK 및 실제 Gemma topic QA 6/6. 원본 메시지 Github 미업로드.
- `implicit_address.py`: 멘션이나 명시적 reply-to 없는 최근 인간 발언에 대해 로컬 Gemma가 addressed_to_bot/topic_continues 두 boolean을 반환하는 엄격 JSON 분류 도구. 봇이 최근 맥락에 참여한 경우만 호출하며 미확실·모델 오류는 False/False.
- `turn_pipeline`에 선택적 `implicit_assessor` 콜백 연결. 두 필드 모두 true인 경우만 확률/자율 쿨타임을 우회하며 채널 범위, 민감도, 타임스탬프 버전 검사는 그대로 적용. **아직 Discord Gateway 이벤트와 자동 연결되지 않았음.**
- 합성 테스트 4개 추가해 현재 **115개 예상**(Windows 미검증). 실제 모델 오판 가능성 있으므로 실서버 도입 전에 평가 케이스 보강 필요.

## 2026-10-18 — 사용자 요청: 간단한 부탁 수행, 나중에 멘션
- 사용자 Windows `114 tests OK` (직전 예상 115는 테스트 개수 산정 오류). 새로운 기능 요구: 사용자가 `오늘 2시간 후에 나 멘션해줘`라고 하면 자신에게 예약 멘션.
- `reminders.py`: 제한된 한국어 상대시간 명령(시간/분, 최대 7일)을 결정론적으로 추출, 요청 원본 Message ID를 UNIQUE 처리, 사용자 본인 Discord ID·길드·채널·UTC due_at를 로컬 SQLite에 저장, 재시작 복구. claim_due 선점으로 중복 수신/발송 방지, 실패는 failed 종결(중복 방지 우선, 강제종료 시 누락 가능). 메시지 원문은 DB에 저장하지 않음. `.gitignore` *.db,*.sqlite3 이미 제외.
- `tests/test_reminders.py`: 명령 파싱, 범위 제한, 재시작 복구, 중복 수신/선점, 실패 후 자동 재시도 금지 테스트 4건. 총 **118개 예상**, Windows 확인 전.
- 실제 Discord Gateway에서 신뢰할 수 있는 author ID/channel/guild 검사, 봇 권한, allowed_mentions 제한, 발송 워커 및 앱 재시작 스케줄러 연결은 **아직 미구현**. 실제 멘션이 간다고 주장하면 안 됨.

## 2026-10-18 — 예약 조회·선택 취소·전체 취소 및 기존 DB 마이그레이션
- 사용자 Windows **118 tests OK** 확인.
- `ReminderStore.list_pending(guild_id, requester_id, limit)`은 해당 서버/요청자 소유의 pending 예약만 ID·채널·UTC 실행시각으로 반환; `cancel(guild_id, requester_id, reminder_id)`는 pending만 원자적으로 cancelled; `cancel_all`도 본인/서버 pending만 변경.
- `reminder_commands.py`는 `내 예약 확인`, `예약 목록`, `예약 1 취소`, `내 예약 전부 취소` 등의 제한된 한국어 명령을 오프라인 파싱. 먼저 허용 채널 확인. 결과는 구조화된 status이며 Discord 안내 메시지 전송은 아직 미연결.
- 기존 SQLite 테이블 CHECK에 `cancelled`가 없으므로 ReminderStore 초기화 시 이전 테이블을 트랜잭션으로 재구성해 기존 항목을 보존하는 마이그레이션 추가.
- `tests/test_reminder_management.py` 5개(소유자/서버 범위, 선택/전체취소, claimed 불가, 구형DB 보존) 추가. 기존 118+5=**123개 예상**, Windows 새 버전 미검증.
- 중요: claimed 이후의 취소는 불가, 발송 도중 프로그램 종료 시 누락 가능; 중복 발송 방지가 우선인 임시 설계. 공식 Discord 발송 워커/취소 명령 연결/안전한 allowed_mentions, 토큰·원본 비공개 관리 등 작업 남음.

## 2026-10-18 — 페르소나 미세조정 우선순위 재설정 / Windows SQLite 잠금 수정
- 사용자 질문: '페르소나 학습은?' 핵심 미완료 상태를 명확히 설명해야 함. 현재 완료: 원본 304997건/정규화 텍스트 270989건 품질·스타일 진단 및 개인 자료 검사, 로컬 Gemma 3 12B 기본 모델 품질 실측. **미완료: 실제 LoRA/QLoRA 훈련, 학습셋 선별, 가중치 체크포인트, 학습 전후 A/B 성능 증거**. 프롬프트 기반 스타일 반영과 미세조정은 다른 것임.
- 공식 Discord 개인 데이터 패키지/Discord API 정책 등 출처별 모델 훈련 이용 권한은 별도 검토해야 한다. 실제 원본 학습데이터·비밀 키는 GitHub에 커밋하지 않음. 사용자 본인 메시지 원본 열람은 허락했지만 AI 훈련 허용 권한을 확정한 것은 아님.
- 다음 **최우선 기술 과제**: (1) 데이터 출처 및 훈련 이용 권한 검토, (2) 개인정보·중복·반복·짧은 맞장구를 고려한 로컬 학습셋 품질/검수 설계, (3) Windows RTX4070 용량 확인과 4B급 QLoRA feasibility, (4) baseline vs adapter A/B 검증, (5) 로컬 체크포인트 Studio/Bot 배포. 학습 진행 중 사용자 원본 외부 전송 금지.
- 사용자 최신 Windows 123 tests 1 ERROR: 구형 SQLite 마이그레이션 테스트가 Windows 임시 `old.db` 삭제 중 WinError32. 원인은 `with sqlite3.Connection`이 커넥션 close를 보장하지 않음. 모든 `with self._connect() as db`을 `with closing(self._connect()) as db`로 변경해 명시적으로 close. 아직 Windows 재실행 미검증.

## 2026-10-18 — Windows 123 중 1 ERROR 지속, 테스트 측 SQLite 핸들 확정 수정
- 사용자가 수정 뒤에도 Windows 123개 중 1개 ERROR 보고: `test_legacy_schema_migrates_without_losing_data`에서 `old.db` 삭제 중 WinError32.
- 원인은 `tests/test_reminder_management.py`의 `with sqlite3.connect(p) as db:` 구문. Python SQLite connection context manager는 commit/rollback만 수행하고 close를 보장하지 않음. Windows에서는 임시 파일 잠금이 남음.
- 테스트에 `from contextlib import closing` 추가하고 구형 DB 생성에 `with closing(sqlite3.connect(p)) as db:` 사용, `db.commit()` 명시. 기존 `ReminderStore` 측 closing 패치 유지. **123개 테스트 Windows 재실행 미확인.**
- 사용자의 핵심 목표인 원본 메시지 페르소나 QLoRA 학습은 여전히 미시작. 예약 QA 이슈 해결 뒤 개인정보 보호/권한 확인/학습환경 준비에 집중.

## 2026-10-18 — Windows 123/123 OK, 실제 페르소나 준비 재개
- 사용자가 SQLite Windows 파일 잠금 수정 후 unittest **123 tests OK** 확인.
- `persona_eligibility.py`: 원본 JSON을 로컬 스트리밍해 채널별 분석용 후보/중복/반복글자/짧은 글/개인식별 의심(연락처·이메일·긴 숫자)/빈 메시지를 **숫자로만 집계**. 원문·ID·시간·예시·학습셋은 출력하지 않음. 기존 사용 권한 점검 미완료이므로 실제 LoRA/QLoRA는 여전히 시작하지 않음.
- `tests/test_persona_eligibility.py` 합성 테스트 3건 추가. 전체 **126개 예상**, Windows 검증 전. 개인정보 검출 정규식은 근사치이며 민감 내용 전체를 탐지한다고 주장 금지.
- 실행: `python -m echomate_studio.persona_eligibility "C:\\Users\\user\\Desktop\\학습데이터\\messages1.json" "C:\\Users\\user\\Desktop\\학습데이터\\messages2.json"`; 출력 `local_data/persona-eligibility.json`.
- 차기 우선순위: 데이터 권리 검토, 학습 데이터 검수·시간 분리·중복 방지 설계, 로컬 QLoRA 환경과 baseline QA. 텍스트 기반 프롬프트 스타일은 모델 가중치 학습과 다름.

## 2026-10-18 — 페르소나 원본 적격성 실측 (126 tests OK)
- 사용자 Windows unittest **126 tests OK**. 로컬 `persona_eligibility` 집계 실행 성공. 원본 메시지 합계 304,997.
- 채널1: 전체 244,976 / needs_human_review 150,888 / empty 21,239 / too_short 38,293 / duplicate 31,883 / repetition 1,399 / private hints 1,274.
- 채널2: 전체 60,021 / needs_human_review 34,720 / empty 12,769 / too_short 7,162 / duplicate 4,392 / repetition 188 / private hints 786 / oversized 4.
- 합: **검수 후보 185,608**, 초단문 45,455, 중복 36,275, 빈 값 34,008, 개인식별 의심 2,060, 반복 1,587, 긴 문장 4. 이는 서로 배타적인 우선순위 분류 집계. 검수 후보=학습 승인 아님. 단일 화자 메시지로 가상의 상대방 Q/A를 만들지 말 것.
- 실제 fine-tuning 미시작. 다음: 데이터 사용 허가/훈련 대상 문장 수동 검수·시점 분할·국소 학습 환경 점검·baseline 설계. 사용자 원문 GitHub/모델 API에 전송 금지.

## 2026-10-18 — Emoji reply alternative
- User wants emoji-only replies within ongoing conversation (e.g. mentioning bot then saying love you => ❓ reaction). Added reaction_reply.py ResponseChoice, selecting one of reaction/text/silent from validated conversation signals and ReactionPolicy allowlist; no Discord send yet. Tests/test_reaction_reply.py adds 5 cases. Expected 131 total, Windows QA pending. Existing automatic emoji reactions remain separate; actual integration must prevent double responding and validate contextual emoji selector; reaction is not based on arbitrary randomness.

## 2026-10-18 — Contextual emoji replies Windows QA
- User ran Python unittest suite: **131 tests, OK**. All five new reaction_reply tests pass.
- Offline text/reaction/silent choice verified. Semantic emoji selection and real Discord API sending remain unimplemented; never imply these work in Discord already.
- Next top priority remains permission-aware persona fine-tuning preparation and local QLoRA feasibility. Current persona audit: 304,997 messages, 185,608 human-review candidates; training NOT started.

## 2026-10-18 — QLoRA 학습 환경 진단 시작
- 사용자 Windows **131 tests OK** 확인, reaction/text/silent 오프라인 테스트 모두 정상. 실제 Discord API와 학습 가중치 업데이트는 아직 미연결.
- 신규 `qlora_environment.py`: Python, Windows/OS, torch/transformers/peft/trl/accelerate/bitsandbytes/datasets 패키지 설치 버전 확인 및 옵션 nvidia-smi GPU 정보 조회. 설치/다운로드/학습/개인 메시지 접근 없음.
- tests/test_qlora_environment.py 신규 3개, 예상 **134개 Windows unittest**. Python 버전과 CUDA 가능 여부는 사용자 Windows 보고서로 확인 필요.
- 후보 기반은 Gemma3 4B 모델이며 학습 가능한 HF base weights 및 게이트 접근·약관 검토가 필요. Ollama GGUF는 직접 QLoRA 대상 아님. 권한/민감자료 검토 전 개인 메시지 학습셋 생성 및 훈련 시작 금지.
- CLI: `python -m echomate_studio.qlora_environment --gpu` -> `local_data/qlora-environment.json`.

## 2026-10-18 — QLoRA environment Windows QA 134 tests, 1 failure
- User reported `Ran 134 tests`: all passed except `test_gpu_query`; assertion observed timeout=None from mock's last call despite code supplying subprocess.run(timeout=10).
- Updated test to look for the NVIDIA query-specific call within mock.call_args_list rather than assuming last call. No production GPU inspector behavior changed. Windows 134-test rerun needed; GPU diagnostic report has not yet been supplied.

## 2026-10-18 — 134 green; isolated CUDA training bootstrap
- User verified Windows unittest 134 OK. Actual local report: Windows Python 3.10.11; RTX 4070 Ti SUPER 16GB (16376 MiB total, 12746 MiB free); torch 2.6.0+cpu and transformers 5.9.0, remaining five training dependencies absent.
- Added tools/setup_persona_training.ps1: creates .venv-train isolated Python 3.10, installs PyTorch CUDA 12.8 wheel torch==2.9.1, verifies CUDA calculation before optional -InstallTrainingLibraries. No private corpus or base weights used. tools/verify_training_cuda.py and three mocked tests added; expected 137 tests Windows QA pending. .gitignore now excludes .venv-train.
- Run PowerShell: `.\tools\setup_persona_training.ps1`, optionally later `-SkipTorchInstall -InstallTrainingLibraries`. Driver/PyTorch wheel compatibility to confirm from results. Do not claim actual CUDA works yet. No persona model trained; training rights review still outstanding.

## 2026-10-18 — CUDA setup verified in user Windows
- User Windows `Ran 137 tests ... OK` confirmed.
- `.venv-train` creation succeeded. PyTorch 2.9.1+cu128 installed, CUDA runtime 12.8, actual tensor operation succeeded on NVIDIA RTX 4070 Ti SUPER. PyTorch emitted warning `No module named numpy`; this warning did NOT fail CUDA test.
- Updated optional training library installation to include `numpy>=1.26,<3`, `pip check`, and import smoke test for NumPy, Torch, Transformers, PEFT, TRL, Accelerate, bitsandbytes, datasets.
- Next Windows step: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`; `.\tools\setup_persona_training.ps1 -SkipTorchInstall -InstallTrainingLibraries`. Confirm output before any model download; training data permissions/manual review remain pending. No training performed.

## 2026-10-18 — Windows full QLoRA stack install succeeded; PowerShell import check quoting bug
- User: local torch 2.9.1+cu128 RTX 4070 Ti SUPER GPU test OK, Python packages numpy 2.2.6 / transformers 4.57.6 / peft 0.21.2 / trl 0.29.1 / accelerate 1.15.0 / bitsandbytes 0.50.2 / datasets 4.8.5 installed. `pip check`: No broken requirements found.
- Setup errored ONLY at Python inline `-c` PowerShell quote parsing; imports not tested. Replaced with local tools/verify_training_stack.py and added 3 mocked tests; 140 expected user Windows tests. Avoid repeating multi-GB torch downloads; run `.venv-train\Scripts\python.exe tools\verify_training_stack.py` and `python -m unittest discover -s tests -v`.
- Real fine-tuning / weights downloads have NOT started. Dataset rights and manual private data review still pending.

## 2026-10-18 — 140 Windows tests, training imports OK; synthetic NF4 verification
- User confirmed `Ran 140 tests OK` and local `.venv-train` imports OK for numpy/torch/transformers/peft/trl/accelerate/bitsandbytes/datasets. Actual CUDA tensor test had already passed on RTX 4070 Ti SUPER 16GB.
- Added `tools/verify_nf4_gpu.py`: synthetic torch/bitsandbytes NF4 Linear4bit CUDA operation, checks finite output and reports peak allocated/free MiB in ignored `local_data/nf4-gpu-probe.json`. No internet, model files or personal Discord text. Failure is nonzero exit.
- Added three unit tests. Expected Windows unittest total 143, NOT YET confirmed. Run `.venv-train\\Scripts\\python.exe tools\\verify_nf4_gpu.py` after `git pull` and share report.
- Passing tiny NF4 would verify kernel basics, NOT full Gemma 3 4B QLoRA trainability or VRAM fit. Real training data source rights and human privacy review remain outstanding.

## 2026-10-18 — NF4 physical GPU smoke test verified
- User Windows 143 unit tests OK. Local `tools/verify_nf4_gpu.py` status=ok: RTX 4070 Ti SUPER; quant_type=nf4; output shape=[2,128]; peak PyTorch allocated=0.08 MiB; reported free after=15073 MiB. This is only tiny synthetic kernel memory, not Gemma model memory or QLoRA VRAM readiness.
- GPU CUDA 12.8, torch 2.9.1 cu128, PEFT/TRL/bitsandbytes imports and simple NF4 kernel verified. Next: inspect Gemma 3 base model access/license and gated weights, determine safe model loading/memory testing before persona training. Discord private data source training rights and sensitive review remain blockers. No weight download/training done.

## 2026-10-18 — Gemma 3 4B opt-in real weight loading probe
- User Windows 143 unittest OK, NF4 CUDA real probe OK on RTX 4070 Ti SUPER: peak allocated 0.08 MiB for *tiny synthetic* operation, 15073 MiB free after. Tiny result not indicative of full-model fit.
- Official Hugging Face model `google/gemma-3-4b-it` is gated: individual must review/accept Gemma license and authenticate locally. This cannot be bypassed or presumed accepted.
- Added `tools/probe_gemma4b_load.py` opt-in `--allow-download` model load using Gemma3ForConditionalGeneration, bitsandbytes NF4 and GPU VRAM report to ignored local_data. No Discord data, no training, no upload. Without flag: report not_run; tests/test_probe_gemma4b_load.py 2 tests. New Windows unittest expected 145, not yet verified.
- Model download is multi-GB. User should first visit https://huggingface.co/google/gemma-3-4b-it and accept terms, then authenticate using `.venv-train\\Scripts\\hf.exe auth login` if offered in venv, avoiding pasting tokens into chat or terminal logs. **Do not run --allow-download without acceptance and explicit consent.** Model loading success != training or VRAM headroom for gradients.

## 2026-10-18 — Real Gemma 4B model load failed after 145 QA
- User Windows tests 145 OK, no-download probe not_run expected. HF CLI `auth whoami` succeeded; canceled `auth login` with KeyboardInterrupt (not a login failure).
- `--allow-download` failed OSError, 15111 MiB VRAM free before loading. Old diagnostic hid exception detail. Failure cannot yet be attributed to HF gating, network, cache, or compatibility.
- Updated probe to classify exception into safe categories with no original exception strings or credentials, and changed deprecated `torch_dtype` to `dtype`; added 2 tests (147 expected, Windows unverified). User should verify access acceptance to google/gemma-3-4b-it and rerun probe once to share `failure_category`. No proof of successful download or QLoRA training yet.

## 2026-10-18 — Hugging Face gated Gemma diagnosis
- User Windows 147 tests OK. Real model loading failed OSError classified model_access_not_granted; VRAM free before load 15111 MiB. Previous Hugging Face CLI `auth whoami` succeeded, but token validity does NOT ensure this gated model has been granted or a fine-grained token covers gated repos.
- Added tools/check_gemma_access.py to request ONLY google/gemma-3-4b-it/config.json, no weight downloads; outputs sanitized local_data/gemma-access.json. Two tests added; expected 149 tests (Windows unverified).
- User should log into the same Hugging Face account on browser, explicitly accept/access model terms at https://huggingface.co/google/gemma-3-4b-it ; for fine-grained tokens check public gated repositories permission. No token values in chat/log. Recheck tiny config before retrying multi-GB load. Actual training rights for Discord messages are separate and remain unresolved.

## 2026-10-18 — Gemma gated config access recovered
- User Windows unittest 149/149 OK and local `check_gemma_access.py` successfully fetched google/gemma-3-4b-it/config.json (855 bytes), `status=ok category=authorized_for_config`.
- This verifies authenticated config access only, not weight-file access nor model loading. Earlier full load failed under model_access_not_granted. Next user step is opt-in retry `python tools/probe_gemma4b_load.py --allow-download` with .venv-train Python, share gemma4b-vram.json. May download many GB; avoid printing credentials.
- Real persona tuning remains NOT started; Discord dataset training rights and private data review remain unresolved.

## 2026-10-18 — Real Gemma 3 4B NF4 loading SUCCESS
- User confirmed real gated model weights downloaded (~8.6GB across two shards) and NF4 load succeeded on RTX 4070 Ti SUPER 16GB.
- Local report status=ok, GPU VRAM free_before=15111.0 MiB, total=16375.5 MiB, free_after=10845.0 MiB, delta=4266.0 MiB, PyTorch peak allocated=4100.9 MiB.
- Model loading proves inference-weight quantization fits; gradient/LoRA optimizer activation overhead not yet measured. Next: synthetic, private-data-free LoRA backward and tiny optimizer step, with memory/length guards, no Discord messages. Source training-use rights/privacy review remains unresolved.

## 2026-10-18 — Synthetic Gemma QLoRA step prepared
- Added tools/smoke_gemma4b_lora.py: explicit --allow-synthetic-step, use cached google/gemma-3-4b-it weights (local_files_only), NF4 PEFT q_proj/v_proj adapters, a tiny synthetic token sequence, a single forward/backward/AdamW optimizer step, aggregate VRAM/loss report only. No private chat data, no checkpoint writes. 3 preflight tests, expected 148 total; Windows unverified.
- Warning: Gemma3 multimodal wrapper, PEFT task and gradient checkpointing compatibility remain unproven. Execution may fail; do not claim actual QLoRA works before observed successful run. Train-data permissions still unresolved.

## 2026-10-18 — Real Gemma NF4 LoRA backward optimizer smoke SUCCESS
- User Windows suite 152/152 OK (note 152, not expected earlier count 148). Local `gemma4b-lora-smoke.json`: status=ok; model google/gemma-3-4b-it; synthetic_only=true; seq_len=32; trainable_params=1,611,776; loss=2.49 (NOT quality score); peak_allocated=5660.7 MiB; free_after=8235.0 MiB. Full forward/loss/backward/AdamW optimizer step ran successfully on RTX 4070 Ti SUPER 16GB.
- PyTorch gradient checkpoint emitted use_reentrant warning. Changed smoke tool prepare_model_for_kbit_training to explicit gradient_checkpointing_kwargs={use_reentrant:False}; this change needs Windows revalidation.
- This establishes technical viability for tiny synthetic LoRA step, NOT final corpus training fit/quality. Next work: data rights and private content review, robust chronological splits and safe local-only training preparation, plus longer context/memory experiment as justified. No real-user text fine-tuning yet.

## 2026-10-18 — Repeat synthetic LoRA report after checkpoint setting change
- User provided another local gemma4b-lora-smoke.json: status ok; google/gemma-3-4b-it, synthetic seq_len32, trainable params 1,611,776; loss 2.49; peak allocated 5660.7 MiB; free after 8235 MiB.
- JSON does not include console warning status, so cannot verify absence of use_reentrant warning. No real private chat model training occurred.
- Next priority: review official Discord-data AI training rights and user privacy selection, design leak-resistant chronological train/eval partitions; do not fabricate multi-speaker Q&A from single-speaker archives.

## 2026-10-18 — Persona corpus gate after synthetic GPU LoRA success
- User supplied second `gemma4b-lora-smoke.json` status ok (synthetic 32-token step). Model training on real Discord messages remains NOT authorized/started.
- Official Discord Developer Policy §21 API-obtained messages require Discord express permission for model training; personal user-requested Data Package is a distinct path, but cannot automatically be deemed trainable. See docs/DATA-GOVERNANCE.md. Revisit policy if new information/approval obtained.
- Added `src/echomate_studio/persona_split_audit.py`: reads private messages locally, validates timestamps, performs per-file chronological 90/10 split, hashes normalized eligible text transiently to count duplicates within and across splits. Writes only counts and high-level notes to ignored `local_data/persona-split-audit.json`; never exports message text, IDs, hashes, or timestamps. More robust contextual privacy and rights review necessary before actual dataset creation.
- Added 3 synthetic tests. Previous Windows suite reportedly 152 tests; new expected 155 (not Windows verified).
- Windows command: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -v; python -m echomate_studio.persona_split_audit '<local path to messages1.json>' '<local path to messages2.json>'`. Return ONLY aggregate JSON. Do not upload the raw files to public repository.

## 2026-10-18 — Windows 155 QA and chronological corpus audit confirmed
- User Windows unittest **155 tests OK**. Local persona_split_audit across 2 personal Discord exports (304,997 total messages) finished without exporting private text.
- Aggregate: candidate message instances 221,883; training_unique_candidates 164,662; validation_unique_candidates 20,356; cross_split_duplicate_unique_texts 2,130; validation_unique_after_overlap_removal 18,226; training_duplicate 35,182; validation_duplicate 1,683; empty 34,008; too_short 45,455; single-character repeats 1,587; identifier hints 2,060; too_long 4.
- Note different audit stages: earlier persona_eligibility human review candidates 185,608 excluded channel-internal duplicates before labeling, whereas split audit counts eligible instances and reports duplicates separately. These metrics are NOT approved training data. Cross-split overlaps should be excluded from final validation.
- Training remains NOT STARTED. Source rights for AI training and additional human privacy screening need clarification before any local private dataset generation or adapter training. Single-speaker messages must not be falsely recast as paired interlocutor dialogue.

## 2026-10-18 — User-directed corpus inclusion policy
- User explicitly requested retention of health, sexual, and aggressive language in their own historical voice corpus; do NOT exclude based solely on these semantic categories. Continue identifying actual credentials, identifiers, private third-party disclosures, and corrupted/repeated data separately. Production response safety is distinct from training-corpus topic inclusion.
- Re-read official Discord Developer Policy §21: limitation specifically concerns API-obtained messages; current exports are owner-requested Data Package. Must not assert this specific clause bans their use. Nor claim a definitive license grant for training. Address remaining terms/privacy issues independently.

## 2026-10-18 — Persona academic research protocol
- New docs/PERSONA-RESEARCH.md summarizes LoRA (Hu), QLoRA (Dettmers), DoRA (Liu), unintended memorization (Carlini), TRL and PEFT implementations. Protocol: owner-only language modeling, no fake Q&A, chronological held-out validation, privacy and memorization testing, baseline vs adapter. Subject matter (health/sexual/aggressive) not automatically removed per user preference. Actual owner message fine-tuning not started.

## 2026-10-18 dataset builder
- Added double-gated local-only single-speaker JSONL corpus builder, three synthetic regression tests. Holdout strings excluded from training. No real private messages processed into training dataset. 158 Windows tests expected, not yet confirmed.

## 2026-10-18 — Windows 158 tests confirmed
- User ran `python -m unittest discover -s tests -v`: 158 tests OK. `persona_dataset.py` synthetic approval, chronological split and leakage tests passed. Actual private data corpus export and QLoRA on owner data remain NOT executed. Next: contextual privacy/near-duplicate review and measured adapter evaluation.

## 2026-10-18 — Local owner-data LoRA trainer added, not run
- User confirmed Windows 158 tests OK. Added tools/train_persona_lora.py gated `--approve-private-training` and existing local_data/train+validation files. Offline Gemma 3 4B NF4 q/v LoRA rank4, max 100 steps/seq512 (defaults 20 steps/128), local-only PEFT checkpoint, single held-out loss smoke comparison. Must not claim full model evaluation from one example.
- New tests/test_train_persona_lora.py 3 tests. Expected Windows suite 161, not yet verified. **No private corpus export, actual user-message training or final evaluation performed.** The dataset builder requires independent rights and privacy-review flags. Need improve sensitive contextual data handling, near duplicate leakage, training sample quality and evaluation before user flags are asserted.

## 2026-10-18 Windows syntax blocker fixed in repository
- Initial Windows QA: 159 tests with one discovery module error at tools/train_persona_lora.py:51 unmatched parenthesis. Rewrote validation token sample selection using an explicit loop. Needs user Windows rerun; expected 161 tests OK. No private corpus training run.

## 2026-10-18 — Windows regression now green
- User confirmed `Ran 161 tests in 0.400s OK` after syntax fix in tools/train_persona_lora.py. This confirms unit tests only; real owner-data training, complete privacy review and model quality validation are still pending.

## 2026-10-18 — Gemma 4 12B transition (NOT YET WINDOWS VALIDATED)
- User selected Gemma4 12B IT as primary candidate. Official HF model google/gemma-4-12B-it, standalone ~23.9 GB safetensors download; official current Transformers examples use multimodal auto model. Official Transformers Gemma4ForConditionalGeneration class available on supported recent releases. Source: https://huggingface.co/google/gemma-4-12B-it and https://huggingface.co/docs/transformers/model_doc/gemma4 .
- Keep existing fully verified Gemma3 4B scripts and .venv-train intact; installed transformers 4.57.6 previously, so Gemma4 might require newer version in a new isolated environment, do not silently update other project envs.
- Added tools/probe_gemma4_12b.py: lightweight config access/CUDA/class preflight by default. To explicitly download and load ~24GB weights requires BOTH --allow-load and --allow-download. Results to local_data/gemma4-12b-probe.json. Added tools/smoke_gemma4_12b_lora.py synthetic cached NF4 LoRA optimizer test, --allow-synthetic-step, no user messages. Added 4 static unit tests. Expected Windows total 165 (previous 161), not verified.
- Gemma4 12B NF4 and LoRA compatibility/VRAM not verified! User must run staged checks and share sanitized reports before selecting training strategy. Hardware 16GB RTX 4070 Ti SUPER; 12B QLoRA OOM is possible, do not promise it fits. Local approved corpus and private training still not run.

## 2026-10-18 — Gemma4 library import blocker mitigation (Windows pending)
- Chosen model: google/gemma-4-12B-it, initial conversation-focused preference over base google/gemma-4-12B, subject to empirical comparison.
- Official model instructions use AutoModelForMultimodalLM. Transformers 4.57.6 Gemma4 direct-class import failed in user report; separate .venv-gemma4 setup uses Transformers >=5.10,<6 and existing CUDA torch baseline, without changing .venv-train.
- Updated probe and synthetic smoke loader; created tools/setup_gemma4_env.ps1, tests/test_gemma4_staged.py, docs/GEMMA4-SETUP.md; .gitignore protects separate environment.
- Confirmed user Windows previous 165 tests OK. Newly added 3 tests and modified probes NOT yet executed on RTX 4070 Ti SUPER. No 12B weight load/LoRA training proof; no owner-message training.
- Next: run isolated installation, unittest, small-file config preflight; review diagnostic JSON before opting into 23.9GB download, NF4 load and synthetic backward.

## 2026-10-18 — User Windows Gemma4 preflight verified (NO WEIGHTS YET)
- New independent .venv-gemma4 successfully installed: torch 2.9.1+cu128, transformers 5.20.1, accelerate 1.15.0, bitsandbytes 0.50.2, peft 0.21.2, huggingface_hub 2.2.0. pip check clean; CUDA True.
- User ran unittest discovery: **168 tests, all OK** (0.441s), including 3 new staged probe regression tests.
- User-provided JSON: model google/gemma-4-12B-it, status ready_for_optional_load, weight_download_allowed=false; config_model_type=gemma4_unified, config_access=ok; VRAM free_before=15111.0 MiB, total=16375.5 MiB.
- This verifies environment imports and small official config access only. No Gemma4 weights downloaded, NF4 loading measured, optimizer step or private owner-data tuning. Next: explicitly opt into weight download/NF4 measurement using --allow-download --allow-load, examine aggregate report; do not start actual persona tuning yet.

## 2026-10-18 — Gemma4 12B IT full weight NF4 GPU load VERIFIED
- User Windows PowerShell loaded official google/gemma-4-12B-it checkpoint (23.9GB reconstructed), 677/677 weights; probe status=ok, stage=nf4_load, CUDA=True on RTX 4070 Ti SUPER 16GB.
- Aggregate JSON: free_before_mib=15111.0, total_mib=16375.5, peak_allocated_mib=7381.7, free_after_mib=7621.0. These are actual NF4 load measurements; model successfully loaded, but no backward pass or optimizer update yet.
- Existing separate .venv-gemma4 with Transformers 5.20.1 succeeded; preserve .venv-train/Gemma3 4B.
- Next: cached-weight synthetic one-step LoRA test (seq_len32) under GPU monitoring, diagnose any OOM or multimodal PEFT incompatibility. Do not train private Discord data until separate corpus reviews.

## 2026-10-18 — Gemma4 12B IT synthetic QLoRA optimizer step VERIFIED on Windows
- User Windows executed `.venv-gemma4\\Scripts\\python.exe tools/smoke_gemma4_12b_lora.py --allow-synthetic-step --seq-len 32`; 677/677 weights loaded and command returned `Gemma4 12B LoRA: ok`.
- Local private-data-free JSON report: model google/gemma-4-12B-it, status=ok, synthetic_only=true, seq_len=32, trainable_params=2,596,864, loss=32.8467, peak_allocated_mib=11163.6, free_after_mib=2418.9.
- Confirms a single NF4 LoRA forward/loss/backward/AdamW optimizer step on RTX 4070 Ti SUPER 16GB. Loss is from repeated synthetic tokens and NOT a language quality score. Free-after is only ~2.36 GiB; longer sequences/batches, concurrent GPU apps and full corpus training remain unverified/OOM risks.
- Keep `.venv-train` and Gemma3 fallback unchanged. Next: conservative length32 multi-step synthetic GPU memory/stability, validate tokenizer/actual Gemma4 text-only label masking, ensure private reviewed corpus governance, then small approved offline training and held-out baseline/adapter evaluation. No personal Discord messages trained yet.

## 2026-10-18 — Gemma4 synthetic training stabilization code (GPU rerun pending)
- Existing user Windows Gemma4 12B IT synthetic seq32 NF4 LoRA optimizer SUCCESS: 2,596,864 trainable params, peak PyTorch allocated 11,163.6 MiB, free_after 2,418.9 MiB.
- Extended `tools/smoke_gemma4_12b_lora.py` with opt-in 1..3 sequential optimizer steps and `--tokenizer-smoke` to exercise official tokenizer on a fixed synthetic Korean sentence; retains local cached weights, no user messages, failure stage/error class only. Three synthetic/no-download unit tests added in `tests/test_gemma4_extended_synthetic.py`.
- Prior 168 Windows tests passed; new expected count 171 if tests discovered. Neither new tests nor extended GPU run has been independently executed on user's Windows device; do not report success yet.
- Immediate next: run 171 unittests; 2 optimizer steps at seq32 with `--tokenizer-smoke`, inspect local JSON. Limit GPU concurrency; stop if OOM. Actual Discord corpus training still requires reviewed local dataset and rights confirmation.

## 2026-10-18 — Windows Gemma4 tokenizer + two-step QLoRA success
- User Windows unittest: 171/171 OK (0.606s).
- User Windows `.venv-gemma4\\Scripts\\python.exe tools/smoke_gemma4_12b_lora.py --allow-synthetic-step --seq-len 32 --steps 2 --tokenizer-smoke`: 677/677 cached weights loaded; `status=ok`, `synthetic_only=true`, `tokenizer_smoke=true`, 2 optimizer updates.
- Private-free JSON: 2,596,864 trainable parameters; losses [22.9326, 22.8617]; peak_allocated_mib=11163.6; free_after_mib=2344.8. Loss decrease in repeated synthetic example is not heldout quality proof; longer sequences, realistic owner corpus, VRAM stability and memorization checks NOT verified.
- Next: build strictly reviewed corpus readiness/preflight and a Gemma4-specific offline trainer with careful tokenization, data split, failure cleanup and evaluation. Do not silently train on owner Discord content. Protect `.venv-train` / Gemma3 fallback.

## 2026-10-18 — Gemma4 private persona training implementation (NOT EXECUTED)
- Created `tools/train_persona_gemma4.py` separate from proven Gemma3 trainer. Cached `google/gemma-4-12B-it` NF4 base with multimodal auto loader, q/v rank4 PEFT, text-only owner single-speaker LM, 1..10 steps, seq16..64 (default 2/32), one held-out loss before/after update, saved private adapter and aggregate report.
- Requires **three explicit gates** (`--approve-private-training --confirm-rights --confirm-privacy-review`) AND existing reviewed local_data JSONL train and validation. Never automatically extracts Discord exports or uses remote API/weight download; outputs only inside local_data. Pretraining single-speaker lines are not converted into fake Q&A.
- Added `tests/test_train_persona_gemma4.py` (3 no-GPU unit tests): 171 previous Windows green; new expected 174, Windows/GPU training NOT verified. Validate actual external data rights, privacy, exact/near duplicate risk independently. Do not run approval flags until actual human review/authorization.

## 2026-10-18 — User Windows 174 QA green; synthetic E2E trainer test prepared
- User reported `Ran 174 tests in 0.681s OK`. Confirms new Gemma4 trainer validation unit tests, NOT its GPU training/saving path.
- Added `tools/run_gemma4_synthetic_e2e.ps1` creating only fixed invented Korean single-speaker train/validation JSONL inside ignored local_data, then invoking the gated Gemma4 private trainer at 2 steps, seq32. The three flags in this script certify **only synthetic test inputs**, never user-data authorization. Script refuses to overwrite an existing adapter.
- Two no-GPU script tests added. Expected Windows unittest count now 176; script's GPU E2E and adapter saving NOT YET EXECUTED.

## 2026-10-18 — Windows PowerShell 5.1 encoding fix
- User Windows unittest 176/176 OK (0.397s). Synthetic E2E .ps1 stopped during parsing, before training; PowerShell displayed corrupted Korean source and unterminated quote. This is a script encoding defect, NOT evidence of a Gemma4 training/GPU failure.
- Changed tools/run_gemma4_synthetic_e2e.ps1 source to ASCII-only and reconstructs fixed synthetic Korean phrases from Base64 UTF-8 bytes. Generated JSONL remains UTF-8. No real owner messages used.
- Added regression test test_powershell_51_source_is_ascii; expected suite now 177 tests, NOT yet Windows verified. Retry the same E2E command. Old output directory may exist from script parse failure only if an earlier run created it; do not overwrite any existing adapter automatically.

## 2026-10-18 — Gemma4 synthetic end-to-end adapter save SUCCESS
- User Windows `python -m unittest discover -s tests -v`: 177/177 OK (0.402s).
- `tools/run_gemma4_synthetic_e2e.ps1` succeeded after ASCII PowerShell encoding fix; 677/677 weights loaded, `trained_local_smoke`, actual optimizer and adapter save completed locally.
- Uploaded training summary: `google/gemma-4-12B-it`, synthetic single-speaker LM, steps=2, seq_len=32, trainable_params=2596864; heldout synthetic loss before=23.6352, after=23.6266; last train loss=27.0271, PyTorch peak allocated=11163.6 MiB, free after=2454.3 MiB.
- Independently inspected uploaded adapter_model.safetensors header: 176 float32 tensors, 2,596,864 scalar weights, ~10.4MB; q_proj and v_proj LoRA layer keys; adapter_config.json confirms base model and rank 4. Header structure is consistent, but reloading adapter and inference are NOT YET verified.
- This is NOT owner-message persona training, and synthetic one-sample validation loss is NOT evidence of conversational quality. Next highest priority: test saved adapter reload with cached Gemma4 NF4 and fixed safe synthetic prompt; then strengthen corpus privacy/near-duplicate audit and approved real owner-data study.

## 2026-10-18 — Pre-owner-training tools staged (NOT GPU verified)
- Added `tools/probe_gemma4_adapter_reload.py`: validates private saved adapter config for Gemma4 12B IT rank4 q/v, optionally reloads cached NF4 base+LoRA and compares base-disabled vs adapted loss on two fixed invented Korean prompts with `--run-gpu`. Default is metadata-only. No real owner texts, no network download intentionally.
- Added `tools/gemma4_corpus_preflight.py`: audits private train/validation JSONL, exact cross-split overlap, duplicate counts, basic URL/identifier hints and bounded approximate near duplicates. Writes only aggregate JSON; cannot prove chronology or privacy compliance or legitimate source rights. Flags **never authorize training**.
- Added 3 new no-GPU regression tests `tests/test_gemma4_pretraining_gates.py`. Previously Windows 177 tests OK; expected count 180. New suite and adapter GPU reload have NOT yet run on Windows. Existing synthetic adapter in local_data remains untouched, original Gemma3 environment unchanged.
- Next: Windows 180 tests and `probe_gemma4_adapter_reload.py --run-gpu` using saved synthetic adapter, inspect local report; separately run corpus preflight ONLY on locally reviewed derived data. Do not switch on real personal corpus training automatically.

## 2026-10-18 — Windows Gemma4 saved-adapter reload VERIFIED
- User Windows ran 180/180 unit tests OK (0.515s), then `tools/probe_gemma4_adapter_reload.py --run-gpu`; 677/677 cached Gemma4 12B IT weights loaded and adapter reload status=ok.
- Uploaded private-free report: synthetic_only=true, sample_count=2; base-disabled losses [23.795, 22.2657], saved adapter losses [23.7906, 22.196], free_after_mib=7585.0. Both losses decreased on fixed synthetic examples, but this is not blind evaluation, natural conversation quality, or personal style proof. GPU inference/reload path is verified.
- Model infrastructure milestone: NF4 base load, rank4 q/v synthetic backward, two updates, checkpoint save, checkpoint reload and adapter-on/off loss comparison all completed on Windows RTX 4070 Ti SUPER.
- Remaining gate BEFORE real owner-message training: review lawful source/use and third-party privacy, improve near duplicate and sensitive context screening, construct local-only approved chronological corpus, audit train/val leakage and sample representativeness, then deliberate owner approval. DO NOT call training ready solely from this synthetic test.

## 2026-10-18 — Private corpus safety hardening before real training
- Added refusal to overwrite an existing nonempty `local_data/persona-dataset` output in `persona_dataset.py`; prevents accidental erasure of previously prepared confidential JSONL.
- Expanded `gemma4_corpus_preflight.py` bounded near-duplicate bucket to compare text suffix as well as prefix (detects samples with altered openings); still not exhaustive or a substitute for source/permission/context privacy review.
- Two new no-GPU regression tests check no-overwrite and changed-prefix near-duplicate flagging. Previously 180 Windows tests OK; expected 182 after this change, not executed on Windows. No actual private data used, no training started.
- Last technical GPU test verified cached synthetic adapter reload with base vs LoRA losses. Remaining human gates: source use rights, third-party contextual privacy, chronological split/provenance and near-duplicate audit on reviewed private data.

## 2026-10-18 — Windows 182 test suite GREEN
- User reported `Ran 182 tests in 0.439s` and `OK` after JSONL newline test correction. Previous regression failure resolved.
- Owner supplied two private Discord export files for local review only; never commit raw texts, derived private data or train adapters to GitHub. No owner-data model training yet.
