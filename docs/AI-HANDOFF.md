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
