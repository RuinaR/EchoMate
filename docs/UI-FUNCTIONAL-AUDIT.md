# Windows UI 기능 연결 감사 — 2026-10-20 후속

시작 HEAD `3829408`. 아래는 전수 기능 **목록과 확인 범위**이며 전체 사용자 조작 PASS가 아니다. 실제 Discord 로그인·송신·명령 동기화 및 사용자 데스크톱 입력은 수행하지 않았다. 운영 자료를 수정하지 않고 임시 저장소와 withdrawn Tk를 사용했다.

## 확인 결과

- 시작 소스 전체 523검사 OK60.304초. 1차527 OK59.774초, 추가 수정 후530 OK66.786초 및 상세 재확인530 OK60.860초.
- 초기60 및 확장300 검사는 withdrawn root의 packed Canvas가1×1에 머무르는 QA 결함이 있어 **두 크기 모두를 실제 검사했다는 주장을 철회**했다. 원본 로그를 보존하고 도구를 수정했다. 창을 표시하지 않고 Canvas를 명시적으로 배정하며 실제 치수 일치를 assert한다.
- 수정된 `verify_ui_functional_audit.py`는 10화면 × 실제1040×740/1180×820 × scaling 4/3·5/3·2(96DPI 기준100/125/150% 상당) × 빈 목록/대량 목록/로딩/오류/준비 중5상태 = **300조합**을 검사했다. 긴 합성 이름·사람500명·기억500·알림500·모델128개. 활성 클릭 영역 이탈 및 버튼 글자의 창 밖 잘림0건.
- 수정 후 render+idle p50 4.750ms / p95 121.929ms / 최대260.551ms. 서로 다른 화면·상태를 합친 단일 실행 분포이며 전후 속도 개선 근거가 아니다. 실제 모니터 DPI 변경·사람의 가독성 평가는 미검증이다.
- 선택한 기억이 삭제되거나 검색 조건이 달라졌을 때 선택 키와 삭제/수정 대상이 남는 결함을 수정했다. query/kind가 현재 조회와 다른 이전 스냅샷을 보여주지 않는다. 선택을 지정한 뒤 그려서 목록의 실제 하이라이트와 대상도 일치시킨다.
- 캐릭터 편집은 저장과 설정 적용을 별도 요청하던 경로를 `profiles/save_apply` 단일 Controller 요청으로 바꿨다. 서명 프로필 저장이 성공해야 설정을 적용한다. 저장 실패 시 이전 설정을 유지하는 실제 임시 저장소 검사를 추가했다. 두 파일을 아우르는 트랜잭션을 의미하지 않으며 설정 저장만 실패하면 새 복제 프로필은 남을 수 있다.
- 저장한 캐릭터 팝업이 비동기 조회 이전 목록에 고정되는 경로를 수정했다. 최신 스냅샷을 반영하고 유효한 선택을 유지하며 기본 프로필 삭제를 차단한다. 닫힐 때 갱신 타이머를 해제한다. 숨긴 위젯의 실제 Tcl 등록 바인딩으로 검사하며, 매핑되지 않은 창의 event_generate가 전달되지 않는 점을 데스크톱 입력으로 우회하지 않았다.

## 기능 연결 표

|화면 / 동작|실제 경로|이번 확인 및 남은 범위|
|---|---|---|
|최초 설정 / 토큰 등록|setup_credentials → setup → create_installation·Settings|코드 추적·렌더·기존 DPAPI 회귀. 실제 새 사용자 화면/Discord 인증 미검증|
|봇 켜기·끄기·응답 허용|start/stop/settings → LocalController → EchoClient·Runtime|모의 수명주기 회귀. 실제 Gateway 금지|
|서버·채널·스레드 선택 / 저장|SelectionList → select_guild/select_channels/save_scope → scope → Settings|선택·초안·허용 범위 회귀. 실제 서버 목록/권한 변경 미검증|
|서버 이름 / 별명·시간대|name / companion server_options → 검증·서명 설정|코드 추적·기존 회귀. 실제 닉네임 API 미검증|
|모델 검색·폴더 등록·적용|models / settings model → Registry·Validator·Backend 준비/probe|구조·실패 회귀. 이번 새 GPU 전환 미검증|
|성격·기분·성별·활동|settings → 검증·서명 저장 → 공통 정책|기존 회귀·렌더. 이번 말투 GPU 비교 미실행|
|프로필 편집·복제|profiles save_apply → ProfileStore 저장 → Settings 적용|새 실제 임시 저장소 성공/쓰기 실패 회귀 통과|
|프로필 선택·복원·삭제·파일|profiles apply/restore/delete/import/export|비동기 목록 도착·선택·삭제 바인딩·기본값 삭제 차단 신규 Tk 검사. 파일 선택/모든 팝업 실제 조작은 미완료|
|로컬 미리보기|preview → 단일 Backend·작업 → preview 스냅샷|기존 회귀. 이번 GPU 미실행, 창 닫기와 생성 취소의 완전한 UX 감사 미완료|
|사람·친밀도·호칭 후보|companion refresh/affinity/member_alias → SQLite → snapshot|기존 로컬 DB·권한 회귀. 실제 관계 데이터 UI와 사람 검토 미검증|
|기억 검색·종류·수정·삭제|companion refresh/memory_* → SQLite → snapshot|새 stale-filter·삭제 후 선택 제거 Tk 회귀. 저장·조회 오류는 기존 검사|
|대화 요약·발췌·설정|summary_*·memory_defaults → 동의/버전·SQLite|기존 회귀. 다중 사용자 실제 자료 검토 미검증|
|예약 목록·수정·취소·유예|reminder_* → 서비스·SQLite|기존 독립 서비스/재시작 회귀. 실제 송신 금지|
|반응·검색·출력 설정|settings → Action/Research/Output 검증|기존 SDK HTTP mock·코드 출력 제한 회귀. 실제 Reaction 금지|
|진행 상황·작업·대화 상세|runtime.monitor/social_monitor/scheduler → _publish → draw_status|기존 선택/스크롤 회귀·60조합 렌더. 모든 실제 병목 단계 UI 대조 미완료|
|실험 기능·캐시|settings vision / visual_cache|렌더·코드 추적. 기본OFF 유지, 활성화·확장하지 않음|
|진단·오류·명령 정리 승인|diagnostics / command_sync_pending → 다음 승인된 연결|기존 비식별 회귀. 실제 명령 동기화 금지|
|앱 종료|shutdown → 작업 drain·Backend close → closed → destroy|기존 회귀. 이번 GPU 종료/장시간 운용 미실행|

## 남은 릴리즈 차단

모든 팝업의 키보드·취소·빠른 연속 조작, 실제 DB/API 오류와 화면 대응, 대량 모델/기억/알림 목록, 완전한 미리보기 취소, 실제 사용자 화면의 접근성·가독성은 전수 완료가 아니다. 본 표를 전부 PASS로 해석하지 않는다. 사회적 청자 품질도 이전32문항26/32의 누락/연결 오류가 남아 **BLOCKED**다.

비공개 원본: `local_data/social-ui-qa-20261020/`. 재현: `PYTHONPATH=src;tests;tools`에서 `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`; UI 도구는 `tools/verify_ui_functional_audit.py --output <새 local_data JSON>`.
