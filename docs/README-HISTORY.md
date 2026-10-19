# 이전 README 기록

이 문서는 모델·캐릭터 분리 전 기록을 보존합니다. 현재 설치/모델/UI 안내는 [최신 README](../README.md)를 따르세요.

최신 대화 상대·언급/청자 분리 변경은 [사회적 청자 엔진](SOCIAL-ROUTING.md)과 [실제 QA·한계](SOCIAL-ROUTING-QA.md)를 먼저 읽으세요. 실제 Discord에는 접속하지 않았고 전체 실사용 판정은 보류입니다.

최신 변경은 [후속 릴리즈 QA](FOLLOWUP-RELEASE-QA.md)를 먼저 읽으세요. 일일 발언 한도를 제거하고, 동의 기반 다중 턴 요약과 무료 공개 원문 검색을 추가했습니다. 뉴스 검색 가용성·장시간 실사용은 미검증입니다.

최신 릴리즈 후보는 [전수 감사](RELEASE-CANDIDATE.md)와 [개인정보 동의](PRIVACY-COMMANDS.md)를 먼저 읽으세요. Discord에는 본인용 `/동의` 하나만 정의하고 나머지는 Windows 앱으로 관리합니다. 스티커 송신은 제거했습니다. 실제 서버 명령 정리는 아직 실행하지 않았습니다.

서버 구성원의 호칭·청자·멘션·원본 답장 분리와 소유자 별명 관리는 [구성원 호칭 계층](MEMBER-ADDRESSING.md)을 참고하세요. 후보 별명은 자동 확정하지 않으며 타인의 기억·알림 권한으로 사용하지 않습니다.

명확한 이름 호출·문장부호 없는 후속·그룹 평가·기분 표현의 최신 변경과 검증 범위는 [의미 중심 참여](SEMANTIC-ROUTING.md)를 참고하세요. 실제 서버 테스트 없이 로컬 GPU·모의 환경으로 검증했습니다.


다중 사용자 요청·고정 원본 답장·공정한 단일 GPU 큐의 최신 구현은 [병렬 대화 문서](PARALLEL-CONVERSATIONS.md), 실제 검증과 릴리즈 NOT VERIFIED의 근거는 [릴리즈 QA](RELEASE-QA.md)를 먼저 읽으세요.

공통 대화·관계·선택 기억·자연어 예약의 최신 구현/검증/사용법은 [통합 문서](COMPANION-MEMORY-REMINDERS.md)를 참고하세요. 자동 기억은 기본 꺼짐이며 실제 Discord 1분 알림 시험을 완료했습니다. 모델 최종 선정과 장시간 품질 승인은 별도입니다.

성격과 기분 화면은 개인 말투/기본 Gemma 4/성인 유머의 세 선택지와 공통 성별 설정을 제공한다. 성인 유머는 현재 기본 Gemma 4+정책 대안이며 새 GGUF를 실사용으로 승인한 것이 아니다. 연령 제한 채널에서만 성인 정책을 사용한다. [검증과 제약](ADULT-MODE-QA.md).

로컬 AI를 사용하는 Discord 자율 대화 봇과 **독립된 오프라인 페르소나 제작 도구(Studio)**.

> **최신 상태:** `EchoMate.vbs`로 콘솔 없이 다크 관리 앱 실행 (`EchoMate.cmd`는 호환용). 서버·채널·스레드 선택, 캐릭터/활동, 처리 상태, Unicode 반응과 기본 OFF인 실험 시각 분석을 지원합니다. 등록 미디어 기능은 제거했습니다. [앱 안내](DESKTOP-UI.md) · [Bot 실행법](DISCORD-BOT.md) · [실제 검증 상태](CURRENT-STATUS.md) · [모델 품질 미확정 근거](ML-EXPERIMENTS.md). 아래 날짜별 기록은 당시 상태입니다.

처음 확인할 때는 [새 앱 테스트 방법](TESTING-DISCORD-APP.md)을 따르세요. 다음 개발자는 [AI 인수인계서](AI-HANDOFF.md)의 최신 절부터 읽으세요. 구현·GPU 합성 시험·실제 Discord 확인을 구분하며, 과거 기록의 제거된 기능을 현재 기능으로 해석하지 않습니다.

## 제품 구성
| 구성 | 책임 |
|---|---|
| EchoMate Studio | 입력 파일 검사, 화자별 자료 확인(지원 예정), 스타일 분석, 허용된 데이터로 오프라인 페르소나 제작·품질 평가, 모델 버전 관리 |
| EchoMate Bot | 검증된 모델을 읽기 전용으로 불러와 지정한 채널/스레드에서 자율 대화. 서버 별명·프로필, 활동 빈도, 시작/중지 |
| DiscordChatExporter | 독립된 외부 백업 도구(선택 사항). EchoMate Bot에 과거 기록 수집 기능을 내장하지 않음 |

최초 검증은 본인 단일 화자 메시지 2개 파일로 수행했다. **실제 Studio 입력 개수는 1개 이상 제한 없이 확장**하며, JSON 파일 하나를 독립적인 채널 하나로 취급한다. 여러 파일은 같은 페르소나의 자료로 합산 가능하고 채널 간 메시지는 연속 발화로 병합하지 않는다. 추후 권한/동의가 확인된 파일의 작성자 목록을 표시하고 선택해 페르소나를 제작하는 방향으로 확장한다. 여러 페르소나가 동시에 발언하는 기능은 초기 범위 밖.

## 데이터와 대화 품질
- 각 JSON 파일은 각각 별개의 채널에서 작성한 한 사람의 메시지 기록. 상대의 발언이 없으므로 실제 질문과 답변 관계를 복원할 수 없다.
- 현재 Discord 대화의 맥락은 일반 LLM이 처리하고, 페르소나는 표현·어휘·문장 길이·반응 습관에 영향을 주는 방식으로 평가한다.
- 최근 기록을 더 반영할 수 있는 시간 가중치(기본 실험 반감기 365일). 오래된 메시지도 일부 보존.
- 출력은 텍스트와 일반 Unicode 이모지로 제한. 이미지·GIF·스티커·커스텀 서버 이모지는 제외.
- 사람의 실제 정체를 가장하지 않고 AI 봇임을 표시한다.

## 첫 실제 데이터 분석 결과 (2026-10-18)
| 소스 | 원본 메시지 | 미디어/링크/멘션 필터 후 텍스트 후보 | 기간 |
|---|---:|---:|---|
| messages1.json | 244,976 | 223,737 | 2021-02-27 ~ 2026-10-16 |
| messages2.json | 60,021 | 47,252 | 2023-07-04 ~ 2026-10-17 |
| 합계 | **304,997** | **270,989** | |

Windows PowerShell에서 사용자가 `unittest` 5건 `OK` 및 실제 JSON 분석 `report.json` 생성을 확인. 실제 학습 데이터 품질이나 모델 성능을 검증한 결과는 아니다. 원본과 보고서의 개인정보/파일 경로는 GitHub에 올리지 않는다.

## 실행 방법 (현재 가능한 CLI)
Python 3.11 이상 권장. 저장소 루트에서:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m echomate_studio.analyze "C:\\data\\channel-a.json" "C:\\data\\channel-b.json" "C:\\data\\channel-c.json" --output "local_data\\report.json"
```

경로는 본인의 실제 로컬 파일 위치로 교체. 이 분석기는 원본 메시지 전문을 보고서에 기록하지 않고 집계 수치만 기록하며 모델을 학습시키지 않는다.

## 이용 조건과 보안
- 본인이 Discord에서 받은 데이터 패키지여도 그 자료를 AI 학습에 사용할 수 있는지 별도 확인이 필요하다. 특히 Discord API로 얻은 메시지는 Developer Policy의 별도 제한을 받는다. **백업/전처리 성공이 학습 허가를 뜻하지 않는다.**
- 상대방의 관계·친밀도 자동 영구 프로파일링은 초기 범위에 포함하지 않는다.
- Discord 토큰, 원본 JSON, 로컬 모델 캐시, 개인 식별 정보는 공개 GitHub에 절대 올리지 않는다.

## 기준 문서
- [최신 프로젝트 정의](PROJECT-DEFINITION.md)
- [실행 봇과 Studio 분리](DEPLOYMENT-SEPARATION.md)
- [데이터 및 출력 규칙](TEMPORAL-STYLE-AND-MEDIA.md)
- [데이터 지침](DATA-GOVERNANCE.md)
- [개발 로드맵](ROADMAP.md)
- [AI 작업 지침](../AGENTS.md)
- [인수인계](AI-HANDOFF.md) · [작업 로그](WORKLOG.md)
- [Studio CLI 실행법](STUDIO-QUICKSTART.md)

과거 요구에만 해당하는 폐기 문서는 제거했다. 저장소 문서는 현행 기능·요구사항을 기준으로 유지한다.

## 로컬 대화 생성 기준선 (2026-10-18)
- `src/echomate_studio/ollama_client.py`: PC 로컬 Ollama API 클라이언트.
- `src/echomate_studio/conversation.py`: 현 대화 문맥·스타일 프롬프트 및 텍스트 전용 출력 필터.
- `src/echomate_studio/chat_probe.py`: Discord 연결 없이 로컬 모델에 단발 대화 시험.
- `tests/test_conversation.py`: Ollama 호출을 모킹한 단위 테스트 6개 신규 작성. **Windows 실행 검증 전**.
- 실행법: [LOCAL-BASELINE.md](LOCAL-BASELINE.md). 실제 페르소나 학습 또는 Discord 연동은 여전히 미구현.

## 최신 개발 상태 (2026-10-18)
- Ollama 대화 출력이 빈 문자열로 나오던 공백 필터 정규식 버그를 수정. thinking-only/빈 응답에는 명시적 오류 반환.
- Bot의 **자율 메시지 이모지 반응** 요구를 추가: Discord 기본 Unicode 이모지만 사용, 일반 발언과 별도로 채널/스레드·반응 빈도·활성화 설정.
- 현재 이모지 반응은 오프라인 순수 정책 게이트·단위 테스트만 구현. 실제 Discord API 연결과 문맥별 이모지 선택은 아직 없음.
- AITrader와 Ollama 설치/모델 공유 가능하지만 두 프로그램의 동시 모델 추론 성능은 별도 검증 필요.

## 자율 대화 참여 판단 (개발 중)
- 활발함 설정은 봇이 말할 **기회를 더 자주 평가**한다는 뜻이지 매번 말을 한다는 뜻이 아니다.
- 분위기가 무겁거나, 의미 있게 보탤 말이 없거나, 개입이 어색하거나, 너무 오래 조용한 채널에서는 침묵하도록 판정 게이트를 추가했다.
- `echomate_studio.participation`은 **평가 결과를 적용하는 정책 로직**까지 구현. 실제 대화를 분석해 평가값을 만드는 모듈과 Discord 메시지 전송은 아직 미구현.

## 대화 연속성 기반 (개발 중)
- 지정한 채널·스레드의 최근 화자별 메시지와 답장 참조를 단기 상태로 관리하는 `DialogueState` 구현.
- 봇도 이전에 한 말을 포함하여 후속 대화를 이어갈 수 있도록 컨텍스트 형식을 준비.
- 새 메시지가 생성 중 들어오면 오래된 응답을 폐기하도록 상태 버전 확인 지원.
- 상태 관리 모듈만 구현된 것으로, 실제 Discord 메시지 연결 및 문맥의 의미적 이해/자율 개입 품질 검증은 아직 남음.

## 대화 기억 용량 (2026-10-18)
- 사용자 Windows RAM 32GB 환경에 맞춰 초기 메모리 기본값을 채널/스레드당 **최대 500개 메시지, 최근 24시간**으로 확장(설정으로 변경 가능). 이는 봇 프로세스의 **일시적인 대화 버퍼**이며 영구 저장이나 학습을 의미하지 않음.
- LLM 프롬프트는 별도 크기 예산(현재 16,000자 기본)을 적용해 최근 메시지부터 선택. 버퍼가 크다고 전부 한 번에 AI 모델에 입력하지 않음.
- 토큰 수·VRAM·처리 지연에 맞춘 실제 컨텍스트 길이 설정, 대화 주제별 요약/기억 검색은 후속 구현 예정.

## 대화 맥락 평가 실험 (2026-10-18)
- 로컬 Ollama를 통해 최근 대화가 민감한 상황인지, 보탤 말이 있는지, 끼어들기가 적절한지를 평가하는 모듈과 독립 CLI를 추가.
- LLM 응답이 JSON 계약을 지키지 않거나 연결 실패하면 **침묵**한다.
- 사용법: `python -m echomate_studio.autonomy_probe --model "qwen3.5:9b-q4_K_M" --message "오늘 보스 갈사람?" --message "나 가능"`
- 이 판단은 아직 실제 대화로 품질 검증되지 않았으며 Discord Bot에 연결되지 않았다.

## 실제 대화 생성 파이프라인 기반 (2026-10-18)
- `echomate_studio.turn_pipeline`을 추가해 최근 대화 상태 → 범위/쿨다운/빈도 확인 → Ollama 문맥 평가 → 선택적 답변 생성 → 최신 대화 상태 재확인을 하나의 실행 흐름으로 묶음.
- 모델 장애, 불필요한 개입, 생성 도중의 대화 변경은 침묵·답변 폐기.
- 현재 이 파이프라인은 오프라인 함수이며 실제 Discord 송수신은 아직 구현하지 않았다.

## 최신 개발 방향 (2026-10-18)
- Windows unittest 50개 모두 통과, 로컬 Qwen 문맥평가 성공.
- 생성 중 새 메시지 대응: `stale_recovery.py`에 최대 재평가/생성 2회 복구(1~3 설정 가능) 추가, 신규 테스트 5개 작성. 실전 Discord 송신 잠금/재검증은 미구현.
- 필요할 때만 사용하는 **옵트인 웹 검색**과 **페르소나 Style Profile v1 최우선 개발**을 계획. [SEARCH-AND-PERSONA-PLAN.md](SEARCH-AND-PERSONA-PLAN.md) 참고.

## Studio Style Profile v1 (2026-10-18)
- 새 `echomate_studio.style_profile`: JSON 파일 N개(파일당 채널 하나)를 로컬에서 스트리밍 순회하여 최근 반감기 가중 집계형 말투 통계 생성.
- 길이/웃음/울음/질문/감탄/기본 Unicode 이모지 사용률 등 집계값만 출력. 원문·특정 단어·ID는 프로필 파일에 포함하지 않음.
- `chat_probe --profile local_data/style-profile.json`으로 로컬 Qwen 프롬프트에 집계형 말투 지침 반영.
- **이는 모델 가중치를 변경하는 학습이 아니라 프롬프트 기반 스타일 기준선**. 정책/사용 허가 확인 전 데이터 원문을 학습셋으로 변환하지 않음.

## 2026-10-18 응답 품질 문제 개선
- 사용자 Windows 58개 테스트 모두 OK이지만 실제 페르소나 응답에서 메이플스토리가 종료됐다는 거짓 주장/과도한 설명/격식 말투 발생. 이는 품질 실패로 분류.
- 대화 초대 의도 우선, 짧고 담백한 한국어 채팅체, 근거 없는 서비스 종료 주장 금지 프롬프트 수정 및 프로필 가이드 조정.
- `chat_probe --timing`으로 생성 전체 소요시간 측정 가능. **품질/속도 개선은 아직 실제 Windows 재측정 전**.
- 관련 조사: [PERSONA-RESEARCH-AND-QA.md](PERSONA-RESEARCH-AND-QA.md).

## 실제 말투 A/B 품질 실험
- 단일 질문 1회 결과로 평가하지 않고, `python -m echomate_studio.ab_probe --profile local_data/style-profile.json --rounds 2`로 4개 합성 질문을 프로필 사용/미사용 교차순서로 비교 가능.
- 결과는 `local_data/ab-results.json`에 저장되며 **대화 예시와 생성 응답**이 포함되므로 GitHub에 올리지 말 것.
- 실제 품질 개선/속도 단축은 아직 Windows 반복 테스트 전.

## 2026-10-18 A/B 품질 경고 기반
- 이전 실험 16회에서 기본/스타일 프롬프트 모두 역할 혼동과 문맥 벗어남이 관찰돼 시스템 프롬프트를 단순화.
- `reply_quality.inspect_reply`는 게임 접속 약속·검증되지 않은 서비스 종료·화제 이탈 등 **검토 후보**를 자동 기록. 의미적 정확도 확정 판정기가 아님.
- `ab_probe` 출력 JSON에 `quality_flags` 추가. 신규 테스트 4개는 Windows 검증 전.

## Qwen/Gemma 동일 조건 비교 (2026-10-18)
- 사용자 로컬에 `gemma3:12b` 설치 성공.
- 새 `echomate_studio.model_compare`: 동일 Style Profile 및 질문 5개를 두 모델에 번갈아 적용, 시간·실제 답변·QA 경고를 `local_data/model-comparison.json`에 기록.
- 실행: `python -m echomate_studio.model_compare --models "qwen3.5:9b-q4_K_M" "gemma3:12b" --profile "local_data/style-profile.json" --rounds 2`
- 실행 결과에는 대화 샘플·응답이 포함되므로 GitHub 커밋 금지. 모델별 로딩/VRAM 교체 비용이 포함될 수 있으므로 이 테스트만으로 순수 추론 속도 결론 내리지 말 것.

## 2026-10-18 실제 Qwen vs Gemma 평가
- 사용자 Windows 단위 테스트 66개 OK. Qwen3.5 9B와 Gemma3 12B 동일 Style Profile 적용 20응답 실측.
- Gemma는 한국어 일상 반응이 상대적으로 자연스러우나 과거 정보가 제공되지 않은 질문에서 `7시`를 두 번 만들어 냄. Qwen은 `ㅋㅋㅋㅋ`에 중국어 응답 반복. 따라서 모델 선정은 보류.
- `context_compare.py` 추가: 약속 시각 미제공, 9시 확정, 10시 변경, 웃음 맞장구의 합성 다중 턴 입력을 두 모델에 동일 비교.
- 실행: `python -m echomate_studio.context_compare --models "qwen3.5:9b-q4_K_M" "gemma3:12b" --profile "local_data/style-profile.json"`
- 리포트 `local_data/context-comparison.json`은 생성 텍스트 포함하므로 비공개·로컬 유지. 테스트 추가 4개, 총 70개 예상(Windows 검증 전).

## 실제 페르소나 미세조정 준비 (2026-10-18)
- 목표: 적법하게 사용 가능한 본인 작성 메시지로 Gemma 3 LoRA/QLoRA 어댑터를 **로컬에서** 실험하고, 기본 모델 대비 검증 후 채택. 현재 실제 학습 실행 전.
- `python -m echomate_studio.style_diagnostics <채널JSON들> --output local_data/style-diagnostics.json`: 원문/고유 표현을 저장하지 않는 집계형 스타일 분석.
- `python -m echomate_studio.tuning_readiness --source-kind official-personal-data-package`: 학습 권한 및 안전성 준비 게이트 리포트. `--permission-confirmed`는 독립적으로 학습 권한을 확인하기 전에는 사용하지 말 것.
- 메시지 학습셋·원본·어댑터 및 개인정보는 GitHub에 커밋 금지. 학습 가능한 Hugging Face 기반 가중치는 Ollama 설치 모델과 별개.

## 원본 JSON 안전 코퍼스 점검
- 직접 확인한 두 공식 개인 메시지 파일은 각각 독립 채널의 역시간순 단일 화자 기록. 인접한 메시지를 대화 Q/A로 취급하지 않음.
- `python -m echomate_studio.corpus_audit <file1.json> <file2.json> --output local_data/corpus-audit.json`으로 중복 횟수·민감문구 가능성·시간 정렬 등을 집계(원문/ID/예시 출력하지 않음).
- 원본은 **절대 공개 GitHub에 커밋 금지**. `.gitignore`는 무심코 새로 추가하는 것을 줄일 뿐, 이미 추적 중인 내용을 삭제하지 않으므로 사전 확인 필요.

## 활성 대화 중 답변 규칙
- 봇이 처음 자율적으로 끼어들 때는 자율 확률/쿨타임을 적용하지만 이미 대화에 참여 중이면 `engagement.py`의 연속성 조건이 충족되는 한 그 제한을 재적용하지 않음.
- 무조건 모든 메시지에 반응하지 않도록 봇을 향한 말인지, 같은 주제인지, 최근 대화인지 구분하고 유용성·민감도·허용 범위와 최신 스냅샷을 확인.
- Discord gateway 실제 연속성 판별은 아직 연결 전. 기존 bot mention regex 오류 수정 및 테스트 보강.

## 대화 지속 시 맥락 우선
- 기본 활성 대화 경로는 경과 시간만으로 종료하지 않음(`max_gap_seconds=None`). 오래 지나도 실제 봇 대상 대화/주제 연속성이 확인되면 자율 발언 확률·쿨타임 우회 가능.
- 빠른 시간 간격만으로 연속성을 추론하지 않음. 이전 참여, 봇에게 한 말인지, 주제 연결이 모두 필요. Discord 이벤트 기반 실제 판정기는 후속 구현.

## 맥락 기반 대화 참여 증거
- `engagement_evidence.py`는 최근 같은 채널/스레드 대화에서 실제 봇 발언에 대한 Discord 답장을 확인하여 대상 추적. 단순 인접 메시지와 타인 간 답장은 참여 증거가 아님.
- 주제 연속성은 아직 별도 맥락 판정이 필요하며, 답장 여부만으로 무조건 발언하지 않음. 실제 Discord API 연동은 작업 전.

## 실제 주제 이어가기 판별 (오프라인)
- `topic_assessor.py`: Discord 봇 발언에 대한 실제 reply-to 메시지일 경우에만 로컬 Ollama(Gemma 3 12B)에 대화 화제 연속성 JSON 판단 요청. 잘못된 응답/오류는 이어가기 불승인.
- `turn_pipeline.evaluate_turn(..., topic_assessor=...)`에 콜백 주입 가능. 봇 멘션 및 일반 자율 발언과 구분. 실제 Discord 이벤트 수신/전송은 향후 작업.

## 로컬 Gemma 주제 연속성 실측
- `python -m echomate_studio.topic_qa --model gemma3:12b`로 합성된 6개 답장/주제 전환 시나리오를 실제 로컬 모델로 평가. 출력은 `local_data/topic-qa.json`; 현재 오프라인 QA이고 실제 Discord 연동/자연스러움 검증과는 별개.

## 간단한 부탁: 예약 멘션 (로컬 코어)
- `reminders.py`는 `오늘 2시간 후에 나 멘션해줘`, `30분 후에 알림 해줘` 등 일부 명확한 상대시간 요청만 파싱. 최대 7일.
- SQLite에 Discord 요청 메시지 ID, 요청자, 채널, 길드, 실행 시각과 처리 상태만 저장. 원문을 저장하지 않으며 `.gitignore`가 DB를 제외.
- 동일 요청이 반복 처리되어도 중복 생성되지 않도록 하고, 재시작 후 pending 유지. 발송 중 강제 종료는 중복 알림 방지 정책상 누락 가능.
- **아직 Discord 송수신과 실행 워커가 연결되지 않아 실제 예약 멘션은 발송되지 않음.** 해당 연결 및 권한/취소/조회 기능은 후속 단계.

## 내 예약 조회 및 취소 (로컬 코어)
- `reminder_commands.py`의 `handle_reminder_management`가 `내 예약 확인`/`예약 목록`, `예약 1 취소`, `내 예약 전부 취소`를 인식해 구조화된 결과를 돌려줌. 예약 번호는 조회한 항목의 `id` 사용.
- 예약은 서버와 요청자 ID로 범위를 한정해 다른 사람 예약 조회/취소를 차단. 이미 발송 선점된(claimed) 예약은 취소하지 않음. 이전 SQLite 예약 DB는 시작 시 데이터 보존 마이그레이션.
- 실제 Discord 메시지로 예약 목록을 보여주고 명령을 수신·전송하는 연결은 **아직 미구현**, 실서버 사용 가능 판정은 아님.

## 페르소나 QLoRA 로컬 환경 검사
- `python -m echomate_studio.qlora_environment --gpu`는 NVIDIA GPU와 PyTorch/Transformers/PEFT/TRL/Accelerate/bitsandbytes/datasets 설치 버전만 조사해 `local_data/qlora-environment.json` 생성. 다운로드·설치·학습하지 않음. Ollama GGUF 추론 모델은 훈련 가능한 가중치와 별개.

## Persona training environment bootstrap (not model training)
- Windows: `.\tools\setup_persona_training.ps1` creates ignored `.venv-train` using Python 3.10, installs CUDA PyTorch 2.9.1 from official cu128 index, and verifies a CUDA tensor operation; existing Python stays unchanged. Optional `-SkipTorchInstall -InstallTrainingLibraries` installs training toolchain only after CUDA check and pip dependency validation. Requires compatible NVIDIA driver and internet, potentially multi-GB downloads. No private data accessed or model trained; training rights and model access are separate gates.

## Optional Gemma 3 4B model load and VRAM diagnostic
- The official `google/gemma-3-4b-it` Hugging Face weights require accepting Google's Gemma license at https://huggingface.co/google/gemma-3-4b-it and local HF auth. Never paste credentials into GitHub or chat.
- `./.venv-train/Scripts/python.exe tools/probe_gemma4b_load.py` performs **no download** and reports `not_run`.
- Only after agreeing to the terms, logging in locally, and deciding to download several GB, run `./.venv-train/Scripts/python.exe tools/probe_gemma4b_load.py --allow-download`. Produces `local_data/gemma4b-vram.json`. This tests 4-bit loading only, not real fine-tuning or dataset permission.
