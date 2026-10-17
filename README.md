# EchoMate

로컬 AI를 사용하는 Discord 자율 대화 봇과 **독립된 오프라인 페르소나 제작 도구(Studio)**.

> **현재 구현:** Studio의 JSON 메타데이터 분석 CLI와 5개 단위 테스트. Discord 봇 실행, 모델 학습, Studio GUI는 아직 구현되지 않았습니다.

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
- [최신 프로젝트 정의](docs/PROJECT-DEFINITION.md)
- [실행 봇과 Studio 분리](docs/DEPLOYMENT-SEPARATION.md)
- [데이터 및 출력 규칙](docs/TEMPORAL-STYLE-AND-MEDIA.md)
- [데이터 지침](docs/DATA-GOVERNANCE.md)
- [개발 로드맵](docs/ROADMAP.md)
- [AI 작업 지침](AGENTS.md)
- [인수인계](docs/AI-HANDOFF.md) · [작업 로그](docs/WORKLOG.md)
- [Studio CLI 실행법](docs/STUDIO-QUICKSTART.md)

과거 요구에만 해당하는 폐기 문서는 제거했다. 저장소 문서는 현행 기능·요구사항을 기준으로 유지한다.
