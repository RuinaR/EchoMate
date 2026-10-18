# EchoMate 개발 로드맵 — 현재 기준

기준일: 2026-10-18

## Phase 0 — 설계/기반
- [x] README, 프로젝트 정의, AGENTS, 인수인계, 데이터·아키텍처 정책
- [x] Bot(운영)과 Studio(오프라인 제작) 책임 분리
- [x] DiscordChatExporter와 공식 개인 데이터 패키지의 사용 경로 검토
- [ ] Python 패키징·CI·환경 설정 및 Windows 실행/배포 자동화

## Phase 1 — Studio 전처리 [진행 중]
- [x] JSON 메시지 구조 검증 및 SHA-256 메타데이터 집계 CLI
- [x] 파일당 한 채널, 여러 JSON 입력(nargs+), 미디어/URL/멘션 필터, 최근 반감기 통계, 발화 그룹 후보 통계
- [x] 합성 데이터 단위 테스트 5개 및 사용자 Windows에서 OK
- [x] 원본 2개 파일 분석(304,997건; 필터 후 270,989건) 및 report.json 확인
- [ ] 스트리밍/저메모리 처리, 개인정보·민감 발언 필터 검증
- [ ] 사용자 선택/데이터 출처·허가 검증, GUI 및 실제 학습셋 생성(조건 충족 후)

## Phase 2 — 로컬 AI·페르소나 제작
- [ ] Ollama Qwen 기준선, 추론 지연/VRAM 평가
- [ ] 허가된 데이터로 스타일 프로필·샘플 검색/선택적 QLoRA 비교
- [ ] 아티팩트 manifest/데이터 기준일/버전별 캐시·품질 평가·롤백
- [ ] 최근 데이터 시간 가중치 실험, 원문·평가 데이터 누수 방지

## Phase 3 — Discord Bot
- [ ] 정식 봇 인증·최소 권한·사용자 친화적인 Windows 설정 UI
- [ ] 서버 별명/아바타(지원 범위 확인), 로컬 아티팩트 로드
- [ ] 채널/스레드 allowlist·발언 빈도·침묵/쿨다운·중지
- [ ] 최근 대화 문맥만 사용, 중복 이벤트·자기 메시지 루프·오래된 생성 결과 방지
- [ ] 텍스트/기본 Unicode 이모지 전용 출력 필터
- [ ] 장애 복원 및 장시간 회귀 테스트

## Phase 4 — 릴리스 QA
- [ ] 사람 평가를 포함한 자연스러움/스타일 유사성/부적절 응답·반복률 비교
- [ ] 모델 교체·롤백, 권한 및 삭제·동의 철회 테스트
- [ ] Windows 배포용 실행 파일/사용자 가이드, privacy-safe 로그 검증

폐기된 과거 요구 문서는 제거. 본 문서가 현재 개발 기준이다.

## 스트리밍 파서 후속 상황 (2026-10-18)
- [x] JSON 배열 증분 읽기, 전체 원문 적재 제거, 청크 SHA-256
- [x] 대형 JSON/오류 입력/파일 1개 추가 회귀 테스트 작성
- [ ] Windows 신규 9개 테스트와 원본 JSON 통계 회귀 검증
- [ ] 더 큰 파일에서 메타데이터 메모리와 처리 시간 측정 및 최적화

## 로컬 대화 엔진 구현 현황 (2026-10-18)
- [x] Ollama localhost API 클라이언트 및 오류 처리 작성
- [x] 현 대화 문맥과 스타일 프롬프트 분리, 미디어/커스텀 이모지 출력 필터
- [x] CLI 모델 응답 시험 도구 및 모킹 단위 테스트 6개 작성
- [ ] Windows 실제 Ollama 응답과 전체 테스트(기존 9개 + 신규 6개) 검증
- [ ] 평가/타이밍 계측, 페르소나 모델 아티팩트 제작
- [ ] 실제 Discord Bot 및 자율 참여 로직

## 최신 기능/수정 (2026-10-18)
- [x] 채팅 출력 공백 정규식 오류 수정(정상 한글·Unicode 이모지가 전부 지워지는 문제)
- [x] Ollama 요청에 `think=false`, 기본 생성 토큰 512 지정, 빈 응답 원인 오류 표기
- [x] 회귀 테스트 2건 추가(정상 한국어·이모지 보존, 빈 AI 응답 검출)
- [x] 독립적 Emoji Reaction Gate 정책 코드 및 테스트 6건 작성
- [ ] 신규 전체 테스트 Windows 검증(기존 15개에서 8개 추가: 총 23개)
- [ ] Ollama 단발 모델 답변 실제 표시 확인
- [ ] Bot에서 별도 반응 설정 UI/Discord Add Reactions 권한·API 연결
- [ ] 메시지 문맥에 따른 적절한 반응 선택·중복/한도 및 사용자 opt-out QA

## 상황별 침묵 판단 요구 및 착수 (2026-10-18)
- [x] 발언 확률과 실제 발언 허용을 구분하는 `ParticipationPolicy`·`ContextAssessment`·Decision 모듈 작성.
- [x] 높은 빈도에도 민감/불필요/부적절/장시간 침묵 상황에서 발언하지 않는 단위 테스트 7개 작성.
- [ ] 사용자 Windows 전체 30개 테스트 확인(기존 23개 + 신규 7개).
- [ ] 실제 최근 Discord 대화로부터 신뢰할 수 있는 ContextAssessment 생성(휴리스틱·로컬 LLM 평가 검증).
- [ ] Discord 봇 연결 및 대화 발언·이모지 반응의 각각 다른 독립 활동 설정/실전 QA.

## 대화 연속성 작업 (2026-10-18)
- [x] 채널/스레드별 bounded TTL 대화 상태(말한 사람, 답장 참조, 봇 발언 보관) 구현
- [x] 발언 전 스냅샷 버전과 최신 버전 비교로 오래된 생성 결과 감지
- [x] 중복·역순 이벤트/채널 격리/TTL/스냅샷/화자 분리 단위 테스트 5개 추가
- [ ] Windows 총 35개 테스트 실행 확인 (기존 30개 + 신규 5개)
- [ ] 자연어 기반 현재 대화 평가기: 화제 추적, 말 걸린 상대 판단, 침묵 판정, 흐름 유지
- [ ] Discord 이벤트 수신 및 답변 전 재검증과 동시성 제어·부하 QA

## 컨텍스트 용량 확장 (2026-10-18)
- [x] 채널별 기본 단기 버퍼 500개/24시간, 생성 프롬프트 16,000자 분리.
- [x] 100개 발언 유지·작은 프롬프트 예산으로 일부만 입력하는 추가 테스트 2건 작성.
- [ ] Windows 전체 37개 테스트 실행 확인(기존 35개 + 2개).
- [ ] 모델 컨텍스트 토큰 제한과 실제 Ollama `num_ctx` 연동 및 초과 방지.
- [ ] 주제 전환/중요 발언 추적, 허가된 범위에서 대화 요약·연속성 강화 및 CPU/RAM 프로파일링.

## 2026-10-18 — 실제 문맥 평가기 초기 구현
- [x] 로컬 Ollama를 이용한 현재 대화 기반 삼중 판단: 민감 분위기, 보탤 말, 끼어들기 적절성.
- [x] JSON 응답 형식 엄격 검사 및 응답 오류 시 침묵하는 fail-closed 처리.
- [x] `python -m echomate_studio.autonomy_probe` 실험용 CLI(합성 입력, Discord 미연동).
- [x] 문맥 평가기 테스트 7개 작성.
- [ ] 사용자 Windows 전체 44개 테스트 확인(기존 37개 + 신규 7개).
- [ ] 실전 대화 예시별 평가 정확도와 민감도 검사/오판 개선.
- [ ] Bot 메시지 수신→상태→판단→스냅샷 재검증→선택적 발언 연결.

## 2026-10-18 — 발언 파이프라인
- [x] 실제 Qwen 판단 예시 성공 및 기존 44개 Windows 테스트 OK
- [x] 메모리/참여 게이트/맥락 평가/생성 연결용 독립 TurnPipeline
- [x] 상황 변화에 따른 생성 결과 폐기 및 예외 침묵 테스트 6개 작성
- [ ] 신규 총 50개 테스트 Windows 확인
- [ ] Discord 공식 봇의 안전한 이벤트/권한/채널 allowlist·반응 분리 통합
- [ ] 송신 직전 최신 스냅샷·동시성 락·발언 쿨다운 지속 상태 QA

## 2026-10-18 우선순위 재정렬
- [x] Windows 50개 테스트 통과, 실제 Ollama 맥락 평가 성공.
- [x] 생성 중 문맥 변경 시 유한 재시도 정책 모듈과 테스트 5건 작성.
- [ ] Windows 전체 55개 테스트 확인.
- [ ] **차기 개발 1순위: Studio Style Profile v1 및 기본 Qwen A/B 평가.**
- [ ] Discord Bot 연결 시 송신 전 락/세대 검증, 중복 방지, 반응 독립 설정.
- [ ] 사용자 opt-in 선택적 인터넷 검색 연동(출처, 질의 최소화, 실패 정책).

## 2026-10-18 Studio 페르소나 프로필 구현 착수
- [x] Windows 사용자 55개 테스트 OK 확인.
- [x] JSON N개 입력, 파일별 채널 경계 및 최근 반감기 가중 집계형 Style Profile v1 작성.
- [x] 로컬 Qwen chat_probe에 프로필을 적용하는 --profile 옵션 추가.
- [x] 집계/최근 가중치/중복 입력 테스트 3개 작성. 현재 총 **58개 테스트 예상**(신규 Windows 미검증).
- [ ] 실제 사용자 PC 프로필 생성과 기본 Qwen/스타일 적용 Qwen의 A/B 비교.
- [ ] 실전 봇 연동/인터넷 검색 기능은 별도 진행.

## 2026-10-18 페르소나 품질 회귀 대응
- [x] 사용자 Windows 58개 테스트 통과 및 집계 프로필 생성 확인.
- [x] 실제 대화 QA에서 사실 환각/말투 불일치 및 느린 응답 확인.
- [x] 스타일 프롬프트 일상 초대 의도/간결함/이모지 최소화 수정.
- [x] 단발 CLI 생성시간 계측 추가, 프롬프트 회귀 테스트 1건 추가(총 59개 예정).
- [x] 관련 연구·오픈소스 4건 검토 요약 문서 작성.
- [ ] Windows 59개 테스트 + A/B 프롬프트 사실성/자연스러움/지연 검증.
- [ ] 생성 길이/모델 컨텍스트/keep-alive를 세부 계측 후 최적화.
- [ ] 승인된 원본 스타일 자료에 한해 더 정교한 표현 분포와 선택적 예시/미세조정 평가.

## 2026-10-18 실제 답변 품질 대응
- [x] 59개 Windows 테스트 OK, 기본/프로필 모델의 자연스러움 실패 및 시간 편차 확인.
- [x] 실제 플레이 가능하다는 허위 암시와 불필요한 되묻기 억제 프롬프트 수정.
- [x] 교차순서 A/B 진단 CLI 구현(실행 검증 전).
- [ ] 실제 Windows A/B 다중 프롬프트 평가 후 말투/속도 개선.
- [ ] 생성 전 의도 판별과 대화 연속성, 상황별 최소 응답의 신뢰성 평가.
- [ ] 허가된 데이터로 더 풍부한 스타일 모델 제작/평가 및 필요시 미세조정.

## 2026-10-18 실측 A/B 후 우선 과제
- [x] 59개 기존 Windows QA OK, A/B 실출력 16건 확인.
- [x] 역할/내용 우선 최소 프롬프트 재설계.
- [x] 사람이 검토할 필요가 있는 환각·화제 이탈 후보를 표시하는 QA 진단기.
- [ ] Windows 전체 63개 테스트 및 A/B 반복 실험으로 실제 개선 여부 확인.
- [ ] 페르소나 유사도 평가용 동의된 참조 응답/비교 평가 도구.
- [ ] Discord Bot 통합은 실전 대화에서 오발언 방지 품질 게이트를 갖춘 뒤 진행.

## 2026-10-18 로컬 모델 선정
- [x] 사용자 Gemma 3 12B 다운로드/등록 성공.
- [x] 기존 Qwen3.5 9B vs Gemma3 12B 동일 조건 모델 비교 CLI 작성.
- [x] 모델 비교 테스트 3개 추가(현재 총 66개 예상).
- [ ] 사용자 Windows 66개 테스트, 실제 Qwen/Gemma 응답·속도 A/B.
- [ ] 메모리·GPU 사용량 관찰 후 적합한 기준 모델 선택.
- [ ] 페르소나 학습/미세조정 모델 호환성과 데이터 허가 확인.

## 2026-10-18 멀티턴 사실성 평가
- [x] 사용자 Qwen/Gemma 비교 20응답 및 Windows 테스트 66개 OK.
- [x] 다중 턴/없는 약속/시간 변경/중국어 출력 QA 시나리오 작성.
- [x] 대화 근거 없는 시간 단정 금지 및 한국어 우선 프롬프트.
- [ ] Windows 70개 테스트 및 로컬 8회 멀티턴 모델 비교.
- [ ] 직접 검증된 다중 턴 결과로 기준 모델 선정, 페르소나 학습 경로 검토.

## 2026-10-18 컨텍스트 오염 QA
- [x] 사용자 Windows 70개 테스트 OK 및 Qwen/Gemma 멀티턴 비교 실측.
- [x] 시스템 프롬프트에 테스트 답 `10시`를 제공했던 오염 가능성 수정.
- [x] 프롬프트 하드코딩된 시간 누수 방지 테스트 1건 추가.
- [ ] Windows 71개 전체 테스트 및 멀티턴 비교 재실행.
- [ ] 외부 지식 검증/장기 대화 사실성 및 페르소나 학습 모델 선정은 위 회귀 후 결정.

## 2026-10-18 추가 회귀 대응
- [x] 사용자 71개 Windows unittest 통과, 멀티턴 실측 비교 완료.
- [x] QA 정규식에서 정상적인 '시간 정보가 없습니다' 문장 오탐 교정과 단위 테스트 추가.
- [ ] Windows 72개 테스트 실행.
- [ ] 폭넓은 다중 화자/문맥 QA 후 Gemma 모델 채택 판단 및 실제 페르소나 학습 설계.

## 2026-10-18 페르소나 QLoRA 추진
- [x] 사용자 72개 Windows 테스트 OK.
- [x] 실제 모델 가중치 미세조정 요구 수용; Gemma 3 QLoRA 공식 문서 검토.
- [x] 로컬 자료의 최근 가중 집계형 스타일 심화 진단기 작성(원문 출력 없음).
- [x] 데이터 출처·허가·민감정보·분할·모델 가중치·환경·A/B 품질 게이트 스키마 및 4개 테스트 작성.
- [ ] Windows 총 76개 테스트, style-diagnostics.json, tuning-readiness.json 검증.
- [ ] Discord 공식 개인 데이터 패키지 AI 학습의 허용 범위 확인 후 허가된 텍스트만 학습/검증 분리.
- [ ] Gemma 3 호환 학습용 가중치 및 저메모리 QLoRA 환경 확보, 학습 전후 맥락/환각/말투 QA.

## 2026-10-18 실제 데이터 통계 회귀
- [x] 사용자 Windows 76개 테스트 통과, 로컬 원본 304,997건 스타일 길이 구간 분석.
- [x] Ending 값 전부 0 오류의 원인 정규식 이중 이스케이프 수정.
- [x] Ending 인식 및 원문 누출 방지 테스트 3개 추가.
- [ ] Windows 총 79개 테스트, corrected style-diagnostics 재실행.
- [ ] 미세조정 권한 및 데이터 안전성 확인 후 학습 파이프라인 착수.

## 2026-10-18 원본 코퍼스 직접 QA
- [x] 79개 Windows 테스트 OK, 재분석 ending rates 정상.
- [x] 사용자 원본 JSON 2채널 직접 프로그램 분석, 역시간순 정렬·반복 패턴 확인.
- [x] 원문 유출 없이 구조·중복·민감 후보 분포를 보고하는 corpus_audit CLI와 테스트 3개 작성.
- [ ] Windows 총 82개 테스트 및 실제 local_data/corpus-audit.json 검증.
- [ ] 저품질 중복 메시지 가중치 조정, 대화 응답 쌍 가정 금지, 분리된 검증셋 설계.
- [ ] 권한 요건 검토 후만 실제 학습셋 생성 및 QLoRA 단계 시작.

## 2026-10-18 활성 참여 후 대화 연속성
- [x] 잘못 이스케이프된 봇 멘션 ID 패턴 수정.
- [x] 봇 최초 자율 참여와 ongoing engagement 구분하는 정책/파이프라인 및 5개 테스트 작성.
- [ ] Windows 96개 테스트 전체 통과 검증.
- [ ] Discord 이벤트의 실제 발화 대상/답장 참조/주제 추적을 바탕으로 ongoing engagement 판단 및 만료 검증.
- [ ] 사용자별 멘션·대화 연속성 로그/설정 및 실전 채널 QA.

## 2026-10-18 자율 참여/멘션/이어가기 게이트 QA
- [x] Windows 96개 실행 시 3개 실패 진단: direct mention usefulness veto, 만료 후 확률 게이트 테스트 오기대, 안전 테스트의 만료된 활성 대화.
- [x] 코드 1건 및 테스트 기대조건 2건 수정.
- [ ] 사용자 Windows 96개 재검증.
- [ ] Discord 실제 mention payload와 발언 대상/주제 이어짐 판별의 회귀 QA 및 이벤트 연동.

## 2026-10-18 시간보다 맥락으로 활성 대화 판정
- [x] Windows 96개 unittest 통과.
- [x] 180초 기본 강제 만료 제거; 기존 제한은 선택적 설정으로 유지.
- [x] 장시간 동일 대화/즉시 주제 전환/근거 없는 연속성 방지 테스트.
- [ ] Windows 전체 97개 테스트 확인.
- [ ] Discord 이벤트에서 발언 대상/답장 참조 및 실제 주제 이어짐을 구현하고 false-positive 평가.

## 2026-10-18 Discord reply-to 문맥 증거
- [x] Windows 97개 QA 모두 통과.
- [x] 단순 발언 간격 대신 실제 bot message reply-to 연결 기반 참여 증거 판별.
- [x] 다른 인간에게 답장, 명시적 답장 없는 인접 발언, 모르는 메시지 ID를 제외하는 테스트 6개 작성.
- [ ] Windows 103개 테스트.
- [ ] 최근 메시지의 주제 연속성을 판단하는 별도 컨텍스트 평가와 Discord Gateway 이벤트 실제 연결.

## 2026-10-18 답장 내용 기반 주제 연속성 판정
- [x] Windows 103개 QA 전체 통과.
- [x] 봇 메시지에 실제 답장했을 때 로컬 AI로 두 메시지의 주제 연속성 판정(엄격 JSON, 실패 시 거부).
- [x] 파이프라인 optional topic_assessor 지원 및 6개 모킹 테스트.
- [ ] Windows 총 109개 테스트 확인.
- [ ] 실제 Gemma 12B 다양한 한국어 Discord 대화 연속성/주제 전환 사례 검증.
- [ ] Discord Gateway 이벤트/채널·스레드 별 메시지 수신, 봇 메시지 ID 적재, 실제 전송 연결.

## 2026-10-18 실제 Gemma 맥락 판정 QA
- [x] Windows 109개 unittest 통과.
- [x] 합성 문맥 6건 실제 Ollama 평가·소요시간·정답률 로컬 저장 CLI.
- [ ] Windows 총 111개 QA 및 `python -m echomate_studio.topic_qa --model gemma3:12b` 실행.
- [ ] 실측 오판 기반 문맥 판별 고도화, 명시적 답장 외 대화 상황과 Discord Gateway 연동.

## 2026-10-18 QA 기준 갱신
- [x] Windows unittest **111개 전체 통과**.
- [x] 로컬 Gemma3:12b 주제 연속성 합성 6건 **6/6 정답**.
- [ ] 발언 대상 모호성, 주제 변경, 짧은 한국어 반응, 답장 없는 연속 발언 등에 대한 다중 화자 검증 확장.
- [ ] 실제 Discord Gateway 수신/안전한 참여 상태/발신 연동 및 로그 QA.

## 2026-10-18 암묵적 대화 상대 추적
- [x] Windows 111개 테스트, 6개 Gemma 실측 모두 성공.
- [x] 멘션과 Discord reply-to 없이 대화가 이어지는지 보는 로컬 모델 판정기 및 fail-closed 파이프라인 콜백.
- [ ] Windows 115개 테스트 및 다중화자·모호한 발언 대상 실제 Gemma 평가.
- [ ] 실제 Discord Gateway 이벤트 수집/봇 메시지 ID와 발신 연동. 가짜 지속 대화 오탐 검증.

## 2026-10-18 간단한 부탁 자동 처리
- [x] '오늘 2시간 후에 나 멘션해줘' 파서 및 채널 제한, 원요청 Discord ID 중복 처리.
- [x] 로컬 SQLite 영속 예약과 선점 처리, 개인정보 원문 저장 금지, 테스트 4건 추가.
- [ ] Windows 118개 단위 테스트 확인.
- [ ] Discord Gateway에서 요청자/채널 확인, 명시적 예약 확인 응답, 발송 워커, allowed_mentions로 요청자만 태그, 예외 및 종료/재시작 검증.
- [ ] 예약 취소/조회 및 권한/스팸 제한, 서비스 중단·미발송 안내 정책.

## 2026-10-18 예약 멘션 관리
- [x] 기존 Windows 118개 unittest OK.
- [x] 서버/요청자별 예약 목록, 예약 ID 선택 취소, 내 예약 전부 취소.
- [x] 취소와 발송 선점의 경합 안전성(상태 pending 검사), 재시작 기존 SQLite 마이그레이션.
- [x] 자연어 명령 파서와 합성 회귀 테스트 5개.
- [ ] 사용자 Windows 123개 unittest 실행 및 레거시 SQLite 이동 확인.
- [ ] Discord 이벤트/실제 발신 워커 연동, 예약 확인/취소 응답, 실시간 스케줄 재기동, 허용 멘션 지정, 재시작/실패 QA.

## 2026-10-18 페르소나 모델 실제 학습 — 최우선
- [x] 사용자 Discord 본인 메시지 2개 분석: 원본 304,997건, 텍스트 후보 270,989건, 스타일 통계 및 반복/민감 필터 후보 수집.
- [x] 로컬 Gemma3:12b 기본 문맥 성능 QA 소규모 실측.
- [ ] 실제 QLoRA/LoRA 미세조정 **미시작**: 출처별 모델 훈련 권한 확인, 민감정보 검수, 유효 데이터 구성 및 시점 분리 검증셋.
- [ ] RTX 4070 리소스 기반 학습 가능한 base weights/4B급 Gemma QLoRA 툴체인 검증 후 로컬 어댑터 학습.
- [ ] Gemma 추론 기준선과 미세조정 어댑터의 문맥 정확도·말투·반복/유출 검사 A/B 평가.
- [ ] Windows 123개 테스트 중 SQLite WinError32 수정본 재검증.

## 2026-10-18 Windows 구형 DB QA
- [x] ReminderStore의 SQLite 연결 명시적 close.
- [x] 테스트가 직접 생성하는 `old.db` 연결도 closing + commit으로 수정.
- [ ] Windows 123개 테스트 통과 확인.
- [ ] 페르소나 실제 학습 데이터의 적법한 사용 조건/학습 파이프라인 작업으로 복귀.

## 2026-10-18: Persona priority
- [x] Windows 123 tests OK.
- [x] Aggregate-only privacy/duplicate eligibility audit implemented.
- [ ] Windows 126 tests and local report; verify data usage rights; prepare QLoRA environment.

## 2026-10-18 — Confirmed persona QA and reaction replies
- [x] Windows unittest 126/126, local 304,997-message audit complete.
- [x] 185,608 records marked for human review, NOT cleared for training.
- [ ] Verify training rights, review sensitive data, prepare local QLoRA and A/B tests.
- [ ] Implement mutually exclusive emoji reaction vs text response and Discord integration.

## 2026-10-18 — Persona QLoRA local environment
- [x] User confirmed 131 Windows unittest OK.
- [x] Read-only GPU/package diagnostic CLI, 3 unit tests.
- [ ] User Windows 134 tests + qlora-environment report.
- [ ] Model rights and local data training permission assessment; private training data review.
- [ ] Prove CUDA/bitsandbytes/transformers/PEFT compatibility, memory feasibility before actual Gemma QLoRA.

## 2026-10-18 QLoRA environment verification
- [ ] Re-run all 134 Windows tests after mock assertion adjustment.
- [ ] Run local GPU report and assess CUDA/packages; no model training yet.

## 2026-10-18 local persona training environment
- [x] 134 Windows unittest OK; GPU diagnostic RTX 4070 Ti SUPER 16GB, torch CPU-only.
- [x] .venv-train isolation, CUDA PyTorch setup with fail-fast tensor check and optional PEFT/TRL stack installation.
- [ ] User Windows 137 unittest and CUDA bootstrap confirmation.
- [ ] Verify training dataset rights, sensitive-data review, compatible Gemma base weight access, and adapter A/B.

## 2026-10-18 — Windows CUDA validation
- [x] 137 unittest passed; isolated CUDA PyTorch installed and GPU tensor test passed.
- [x] Optional training dependencies include NumPy plus pip/import checks.
- [ ] Install/verify full local QLoRA dependencies, evaluate CUDA/bitsandbytes compatibility.
- [ ] Confirm source AI-training permissions and inspect sensitive data before generating training corpus or downloading base model.

## 2026-10-18 — QLoRA package imports
- [x] Python training packages installed into .venv-train; pip check clean.
- [x] Windows PowerShell -c quote issue replaced by standalone package import script.
- [ ] Confirm actual native DLL imports and 140 tests on Windows.
- [ ] GPU bitsandbytes 4-bit quantization dry-run (no model download), training rights review, then controlled base-model access.

## 2026-10-18 — NF4 GPU kernels
- [x] 140 Windows tests and local training stack imports succeeded.
- [x] Synthetic CUDA bitsandbytes NF4 operation and VRAM probe added.
- [ ] Windows 143 tests and actual GPU NF4 report.
- [ ] Model access/rights and memory-constrained controlled 4B QLoRA feasibility, after private dataset review and source policy checks.

## 2026-10-18 — Verified GPU NF4 baseline
- [x] Windows 143/143 unit tests and synthetic bitsandbytes NF4 kernel succeeded.
- [ ] Verify actual Gemma 3 base weights access/license, local 4-bit model load and VRAM.
- [ ] Verify user export training rights and sensitive content screening before creating private tuning dataset.

## 2026-10-18 — Model load and access gate
- [x] Windows 143 tests and bitsandbytes NF4 GPU kernel verified.
- [x] Opt-in Gemma 3 4B NF4 actual weight load/VRAM diagnostic CLI, defaults to no download.
- [ ] User Windows 145 tests, review/accept Gemma license, authenticate locally, opt-in multi-GB base model load.
- [ ] Confirm VRAM and module placement; then safe small synthetic LoRA backward test without user messages.
- [ ] Obtain clarity on training permissions and user privacy review before real data preparation/training.

## 2026-10-18 Gemma 3 4B load investigation
- [x] 145 Windows tests passed, Hugging Face auth identity verified.
- [ ] 147 Windows tests and categorized real model load result.
- [ ] Verify Gemma model access accepted; determine OSError cause without exposing tokens or raw exception dumps.
- [ ] Only after full loading and VRAM checks, attempt synthetic adapter training; personal data rights not verified.

## 2026-10-18 HF Gemma access gate
- [x] 147 Windows tests pass; real model load failure categorized access denial.
- [x] Tiny authenticated config-only gated access probe implemented.
- [ ] Browser acceptance on same account and fine-grained token scopes; 149 tests and config probe result.
- [ ] Once granted, opt-in model load VRAM and synthetic adapter gradient QA. Discord corpus rights and privacy gating still pending.

## 2026-10-18 Gemma access cleared for config
- [x] Windows 149 tests OK and official Gemma3 4B config downloaded under current HF authentication.
- [ ] Confirm weight download and NF4 VRAM loading under real GPU; configure error diagnosis if failure persists.
- [ ] Synthetic backward LoRA test before private dataset training; rights and privacy review not complete.

## 2026-10-18 — Gemma NF4 load gate passed
- [x] Actual official Gemma 3 4B IT NF4 4-bit checkpoint loaded successfully on 16GB RTX 4070 Ti SUPER.
- [x] VRAM: 4266 MiB loading delta, 10845 MiB free afterwards.
- [ ] Validate LoRA backward and optimizer on entirely synthetic sequence; monitor VRAM/OOM.
- [ ] Training data rights and sensitive message review before any actual private corpus training.

## 2026-10-18 cached model LoRA smoke test
- [x] Opt-in synthetic LoRA one-step tool with cached 4B NF4 weights.
- [ ] Windows 148 tests and --allow-synthetic-step CUDA outcome.
- [ ] Evaluate stability, data rights and training set privacy before personal message training.

## 2026-10-18 — First complete synthetic LoRA step verified
- [x] Windows 152/152 tests OK and synthetic Gemma3 4B NF4 LoRA optimizer step OK.
- [x] Recorded peak PyTorch GPU allocation 5660.7 MiB for length32 and 1,611,776 trainable params.
- [ ] Verify explicit gradient checkpoint setting on Windows and run longer synthetic sequence VRAM stress when needed.
- [ ] Resolve source permission and privacy review; train/validation chronological split; actual local-only adapter tuning followed by measured baseline vs adapter comparison.

## 2026-10-18 — Approved persona data preparation track
- [x] Synthetic Gemma3 4B 4-bit LoRA forward/backward optimizer test succeeded on local RTX 4070 Ti SUPER.
- [x] Local aggregate-only chronology/cross-split duplicate auditing tool and 3 tests created.
- [x] Documented Discord API-training restriction vs owner official data package rights uncertainty.
- [ ] Windows 155 unittest checks and aggregate persona split report; examine leakage and sample adequacy.
- [ ] Source-use clarification, human review of private/sensitive information and explicit dataset approval BEFORE training corpora or LoRA.
- [ ] Privacy-safe validation with baseline comparisons and memory budget constraints before releasing trained adapter.

## 2026-10-18 — Chronological split verified
- [x] 155 Windows tests and 2-file local split audit run successfully.
- [x] Cross-split duplicate texts measured (2,130); validation candidates remaining after overlap removal: 18,226.
- [ ] Rights and privacy-review clearance before any real message-based QLoRA.
- [ ] Ensure final approved corpus deduplication actually enforces the split, not just audit estimates.

## 2026-10-18 — Owner-approved style retention
- [x] Retain health, sexual and aggressive expressions as stylistic content, without category-level automatic exclusion.
- [x] Differentiate official owner Data Package from API-obtained content under Discord Developer Policy §21.
- [ ] Keep identity/secret/third-party privacy filters, and maintain separate runtime response boundaries.

## 2026-10-18 — Evidence-based personalization
- [x] Research bibliography and EchoMate-specific persona experiment protocol in docs/PERSONA-RESEARCH.md.
- [ ] Local approved owner-only LM corpus, near-duplicate and privacy checks.
- [ ] Holdout baseline vs adapter evaluation and 16GB longer-context VRAM test.

## 2026-10-18 — Single-speaker private dataset implementation
- [x] Research-informed local-only, explicit-approval JSONL corpus tool implemented.
- [x] Exact holdout-leak prevention (held-out strings omitted from training), 3 synthetic tests.
- [ ] Windows 158 tests and source privacy/right review before enabling local personal corpus generation.
- [ ] Near-duplicate and contextual PII checks, private baseline/adapter evaluation, actual LoRA training only after gates.

## 2026-10-18 — Local QLoRA runner baseline
- [x] Local private-data LoRA runner and bounded approval flags, three tests.
- [ ] Verify 161 Windows tests; strengthen privacy, near-duplicate and temporal validation criteria.
- [ ] Build approved private corpus only after meaningful source and sensitive content review; run small LoRA and fixed-set A/B.

## 2026-10-18 — 12B model experiment
- [x] Gemma4 12B official repo verified; small config preflight and explicit opt-in NF4 load probe implemented.
- [x] Separate synthetic NF4 LoRA backward probe with cached weights and static QA.
- [ ] Windows 165 unit tests; Transformers Gemma4 compatibility preflight; NF4 download/load free VRAM check; synthetic LoRA optimizer step.
- [ ] Approve private corpus safety/rights, comparative heldout study vs validated Gemma3 4B.

## 2026-10-18 — Gemma4 isolated runtime
- [x] Add separate .venv-gemma4 Windows setup, official multimodal loader, staged config and NF4 checks, and regression tests.
- [ ] Run Windows tests, dependency import, config access, explicit NF4 loading; then synthetic LoRA step.

## 2026-10-18 — Windows Gemma4 isolated preflight success
- [x] New .venv-gemma4 install completed; torch 2.9.1+cu128, transformers 5.20.1, peft 0.21.2, bnb 0.50.2; pip check clean.
- [x] Windows unittest 168/168 OK (0.441s).
- [x] Gemma4 12B IT config-only probe ready_for_optional_load; type gemma4_unified; CUDA available; 15111 MiB free before load.
- [ ] Explicit opt-in weights NF4 load and measure GPU allocation. Do not infer 12B fits from config preflight.
- [ ] If successful: cached synthetic LoRA forward/backward/optimizer compatibility, memory and privacy-neutral diagnostics.

## 2026-10-18 — Real 12B NF4 model load passed
- [x] User Windows full 23.9GB Gemma4 IT checkpoint NF4 GPU load passed, 677 weights, 7381.7 MiB peak PyTorch allocated, 7621.0 MiB GPU free after.
- [ ] Synthetic LoRA forward/backward/optimizer on 12B with cache-only weights; inspect peak VRAM.
- [ ] Privacy-reviewed owner-data fine-tuning and baseline comparison (not started).

## 2026-10-18 — Gemma4 12B synthetic QLoRA GPU success
- [x] Windows cached-model NF4 LoRA seq32 forward/loss/backward/AdamW succeeds on RTX 4070 Ti SUPER; 2,596,864 trainable parameters, peak PyTorch allocation 11,163.6 MiB, GPU free after 2,418.9 MiB.
- [ ] Verify multiple synthetic optimizer steps and realistic tokenization/longer contexts without OOM; protect shared GPU usage.
- [ ] Review local owner-export data, privacy and training rights, chronological/near-duplicate leakage and holdout before actual persona QLoRA.

## 2026-10-18 — Gemma4 multi-step and tokenizer path
- [x] Add explicit synthetic tokenizer smoke and bounded 1..3 optimizer updates to cached Gemma4 12B QLoRA test tool; 3 regression tests written.
- [ ] Windows unittest suite now expected 171, then seq32 two-step tokenizer smoke; observe VRAM and classify failures; no large-context claim yet.
- [ ] Human-reviewed private corpus permission/privacy/leakage gates, approved fine-tune and held-out study remain open.

## 2026-10-18 — Two-step Gemma4 tokenizer test verified
- [x] Windows 171 unittests OK; Gemma4 official tokenizer, fixed synthetic Korean input, 2 NF4 LoRA optimizer steps OK (seq32), peak PyTorch 11,163.6 MiB, free after 2,344.8 MiB.
- [ ] Validate longer context/multiple diverse synthetic samples, measured OOM headroom.
- [ ] Implement Gemma4-specific private corpus training path with leakage/privacy checks, tokenizer-safe text formatting and rigorous held-out comparison; do not start private dataset training automatically.

## 2026-10-18 — Gemma4 trainer implementation
- [x] Separate triple-gated offline Gemma4 12B NF4 LoRA private JSONL trainer and 3 regression tests added.
- [ ] Windows 174 tests, approved synthetic end-to-end checkpoint save, memory and validation smoke.
- [ ] Independent private corpus rights and privacy review, representative held-out evaluation before owner-data training.

## 2026-10-18 — Synthetic trainer end-to-end QA
- [x] Windows user confirmed 174 unit tests all OK.
- [x] Add separate local-only PowerShell synthetic train/validation JSONL generator and end-to-end adapter-save runner; 2 tests added, expect 176.
- [ ] Execute 176 unit tests plus GPU synthetic trainer run, verify saved adapter and report. This is not private corpus training authorization.

## 2026-10-18 — PowerShell parsing regression
- [x] User 176 tests pass; identify PS 5.1 Korean encoding parse failure in synthetic E2E script.
- [x] Switch PowerShell source to ASCII-only with fixed UTF-8 Base64 synthetic Korean sentences; add regression test.
- [ ] Windows 177 tests and actual end-to-end GPU adapter save, report verification.

## 2026-10-18 — Gemma4 synthetic end-to-end successful
- [x] Windows 177/177 unittest OK and 2-step Gemma4 NF4 synthetic training with validated local safetensors adapter output.
- [x] Verify uploaded adapter header contains 176 float32 tensors, 2,596,864 scalar weights and expected q/v LoRA configuration.
- [ ] Reload saved LoRA into cached Gemma4 12B base and run controlled safe inference; compare no-adapter path on same fixed prompt.
- [ ] Review owner-data source rights and contextual privacy, near-duplicate/temporal leakage, then approved real-data training and held-out quality checks.
