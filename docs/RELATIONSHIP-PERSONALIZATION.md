# 관계별 대화 스타일 / 친밀도 설계

작성일: 2026-10-18
상태: 설계안, 구현 및 테스트 미실시

## 목적
선택된 페르소나가 대화 상대에 따라 다른 호칭·말투·농담 강도·반응 길이를 사용할 수 있게 하여 자연스러운 대화를 구현한다.

## 엄격한 경계
- Discord API 메시지 데이터에서 사용자 간 친밀도, 사적인 관계, 인간관계 네트워크를 추론·점수화하지 않는다. Discord Developer Policy §16에서 API 데이터를 통한 사용자/관계 프로파일링을 금지한다.
- 친밀도는 **페르소나 당사자가 직접 선택한 대화 스타일 선호도**다. 상대방의 실제 감정, 성격, 관계의 진실을 나타내는 지표가 아니다.
- 관계별 설정은 대상 당사자의 동의와 적절한 역할 기반 권한을 확인하고 로컬에서 최소한만 저장. 설정 삭제 및 opt-out 지원.
- 제삼자에게 사용자 관계 추측이나 비밀 정보 노출 금지. 디스코드 데이터에서 자동 계산하지 않음.

## 개념 모델
PersonaRelationPreference:
- persona_id: 내부 ID
- target_discord_user_id: 상대 user ID (또는 별도 그룹 ID)
- target_alias: 대화용 별칭 (선택)
- closeness_preference: 1~5, 명시적 설정값만 허용
- speech_register: casual | polite | mixed
- teasing_level: none | light | moderate (당사자 동의 범위 내)
- preferred_address: 호칭 텍스트 (선택)
- response_style: concise | normal | elaborate
- taboo_topics: 대화에서 피할 주제 (로컬 설정, 비공개)
- enabled, updated_at, source: manual
- consent_state

## UI
- 활성 페르소나 검색 가능한 리스트박스.
- 선택한 페르소나의 관계별 목록에서 대상 Discord 사용자 선택.
- 친밀도(1~5), 기본 말투, 장난 강도, 별명, 응답 길이, 피해야 할 주제 설정.
- 설정이 없는 상대는 기본 중립 프로필.
- 현재 닉네임은 표시용, user ID는 참조용.
- 관리자 외 설정 수정 금지, 운영 중 안전한 초기화 지원.

## 응답 파이프라인
1. 지정 스레드의 허용된 현재 메시지를 처리
2. 현재 화자 ID로 **수동 입력된** 관계별 설정 조회
3. 발언 여부 판단. 친밀도 점수 자체가 자동 응답 우선순위를 무한히 높이지 않도록 제한
4. 안전한 스타일 프롬프트 구성: 명시적 별명/말투/농담 허용 범위
5. 로컬 추론 및 출력 검사, 과도한 공격성·사생활 정보·정체 혼동 방지
6. 출력 및 privacy-safe 메트릭 저장

## 테스트 계획
- 알 수 없는 사용자: 기본 중립 스타일
- 닉네임 변경 시 사용자 ID 유지
- 페르소나 전환 시 설정 누수 없음
- 설정 삭제 즉시 기본값 복귀
- 명시적 장난 금지 설정/상대방 opt-out 준수
- 외부 메시지로 관계 점수 자동 갱신 불가
- DM/다른 스레드의 기록을 몰래 참조하지 않음

## 공식 근거
https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy
