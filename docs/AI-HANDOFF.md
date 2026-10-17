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
