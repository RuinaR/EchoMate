# EchoMate Studio 첫 구현 — 로컬 JSON 구조 분석

상태: **실행 가능한 메타데이터 분석기**. 모델 학습·RAG·Discord 접속 구현은 아직 없음.

## 설치
- Python 3.11 이상 권장. 외부 Python 패키지는 필요 없음.
- 이 저장소 루트에서 PowerShell 실행

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m echomate_studio.analyze "C:\\data\\channel1.json" "C:\\data\\channel2.json" "C:\\data\\channel3.json" --output "local_data\\report.json"
```

**파일은 1개부터 원하는 만큼 공백으로 나열할 수 있다.** 예시의 3개를 모두 사용할 필요는 없다. 각 파일은 별도 채널이다. 같은 페르소나의 데이터라도 채널 간 발언을 하나의 그룹으로 합치지 않는다. 실제 경로에 맞춰 수정. 메시지 원문은 출력하지 않으며 소스 파일을 변경하지 않는다.

## 입력 계약
- 최상위 JSON 배열, 레코드별 `ID`, `Timestamp`, `Contents`, `Attachments` 필수.
- **파일 하나 = 채널 하나**로 분석한다. 파일 수는 고정하지 않는다. 다른 채널과 시간 가까운 발언을 혼합하지 않는다.
- 단일 화자 기록이므로 가까운 메시지는 발화 묶음 *후보*일 뿐 상대방의 실제 발언을 복구한 것은 아니다.
- 빈 본문, 순수 URL, 사용자 멘션, 커스텀 이모지, 미디어 링크는 텍스트 분석 대상에서 제외한다. Unicode 이모지와 원문의 구어체는 보존한다.
- 타임스탬프에 타임존이 없다면 출처에 타임존이 없는 상태로 유지하고 임의로 변환하지 않는다.
- 결과 보고서는 파일별 집계 수치와 원본 해시만 포함한다. 이름/민감 발언/첨부 URL은 출력하지 않는다.
- 최근 가중치는 반감기 365일 기본값이며 --half-life-days로 변경 가능. 보고서에 **가중 평균 문자 길이**가 표시되며 아직 모델 학습에는 사용하지 않는다.

## 향후
- 개인정보를 식별하는 단어 및 문자열 제거 강화
- 스트리밍 파서로 대형 파일 RAM 사용량 절감
- 1인 연속 발화 묶기 검증 및 학습용 샘플 생성(사용 허가 확인 후)
- EchoMate Bot과 독립 실행되는 Studio GUI 및 버전 캐시

**주의:** Discord 데이터 패키지를 분석할 수 있는 것과 AI 학습에 이용할 수 있는 것은 별개이다. 자료의 사용 조건을 확인하기 전에는 모델 훈련이나 영속 RAG 생성에 투입하지 않는다.

## 대용량 JSON 파서 v2 확인 (2026-10-18)
- `analyze.py`는 JSON 배열을 스트리밍 처리한다. 전체 원문/첨부 URL을 통째로 메모리에 보관하지 않고 레코드 단위로 읽는다.
- 파일별 메시지 ID, 시각, 본문 **길이**와 가중 통계 메타데이터는 정렬/중복 제거를 위해 메모리에 남는다. 따라서 메모리 소비가 완전한 상수는 아니다.
- 입력 1개 이상 허용, 한 파일당 한 채널. 출력 포맷은 기존 `channels` 배열을 유지한다.
- 증분 JSON 파싱 경계, 잘못된 JSON, 단일 파일 입력 회귀 테스트 추가. 원본 보고서와 동일한 통계가 나오는지 Windows에서 재확인 필요.

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m echomate_studio.analyze "C:\\Users\\user\\Desktop\\학습데이터\\messages1.json" "C:\\Users\\user\\Desktop\\학습데이터\\messages2.json" --output "local_data\\report-v2.json"
```

기존 `report.json`을 덮어쓰지 않는다. 숫자 변화가 있다면 신규/구버전 코드 차이 및 입력 변경 여부를 점검한다.
