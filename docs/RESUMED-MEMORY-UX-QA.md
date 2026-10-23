# 개발 재개 — 로딩 메모리·Windows 인터랙션 QA (2026-10-23)

## 범위와 진행

시작 main/local/remote `046ed12`, 작업 트리 clean. 사용자 재개 요청으로 이전 잠정 중단을 해제했다. 운영 자료·모델 선택을 유지하며 계측 → 병목 분석 → 안전한 후보 검토 → 공통 입력 수정 → 실제 격리 렌더 → 회귀 → Portable 공개 소스 갱신 순서로 진행한다. 실제 Discord 인증/조회/변경/송신은 금지한다. 정식 릴리즈는 **BLOCKED**다.

## 로딩 메모리 — 추가 절감은 채택하지 않음

읽기 전용 설정의 `model=base`, 추가 모델 루트 없음. 실제 선택은 HF 캐시의 **원본 단일 Safetensors**(23,919,549,408 bytes)였다. 이전 QA의 분할 복사본이 존재한다는 사실은 앱이 그것을 선택했다는 뜻이 아니다. 운영 선택을 자동 변경하지 않았다. UI의 기본 복귀 버튼을 **원본 기본 모델**로 명확히 했다. 분할 복사본 사용은 사용자가 AI 모델에서 해당 폴더를 선택하고 검증 후 적용해야 한다.

설치된 Transformers 5.20.1 소스를 확인했다. Windows native Safetensors 읽기는 이미 CPU/pread 경로이고, 실행 시 NF4 변환은 이미 순차 처리다. 따라서 순차 환경변수를 추가하는 것은 새로운 절감이 아니다. mmap 비활성화는 전체 파일 읽기/merged state를 만들 수 있어 채택하지 않았다. allocator warmup을 비공개 monkeypatch로 생략하거나 admission을 낮추는 후보도 채택하지 않았다. 원본 677개 텐서의 최대 단일 텐서가 1.875GiB이므로, 텐서를 보존하는 현 방식에서 2GiB shard를 512MiB로 줄일 수 없다. 새 가중치 복사·재다운로드·양자화 변경은 하지 않았다.

실제 InstanceLease를 확보하고 단일 backend로 기존 검증된 분할 복사본을 한 번 로딩했다. 로딩 전 집계 여유 RAM 약7.51GiB, commit31.75GiB, VRAM12,854MiB, GPU39°C였다. 원본의 약34.28GiB admission은 충족하지 않아 원본 재시도를 하지 않았다. 분할 프로필의 약16GiB admission은 유지했다. 다른 프로그램을 조사/종료하거나 시스템 설정을 변경하지 않았다.

|관측|이번 결과|해석|
|---|---:|---|
|분할 모델 로딩·준비|26.157초, 1회 성공|최소 probe 포함, 중복 상주 없음|
|OS process private commit high-water|13.015GiB|과거 분할13.01/12.92GiB 재현 범위, 추가 절감 아님|
|OS process working set high-water|4.819GiB|commit과 물리 RAM은 다른 지표|
|표본 private peak / WS peak|10.998 / 1.710GiB|50ms 표본은 순간 피크를 놓치므로 high-water 대신 쓰지 않음|
|전체 system commit 표본 peak|49.185GiB|다른 앱 포함, 모델 단독 사용량 아님|
|GPU allocated peak / reserved 표본 peak|7.209 / 8.031GiB|VRAM 할당과 예약 구분|
|해제 후 private / working set|약2.969 / 1.520GiB|Python/CUDA 런타임 잔류 포함, 프로세스 정상 종료|
|해제 후 GPU allocated / reserved|1KiB / 2MiB|이번 단일 수명주기, 장시간 누수 인증 아님|

추가된 계측은 원래 인자와 반환값을 그대로 유지하며 allocator warmup 시작/끝을 기록한다. 단계 표본 private은 초기화1.759GiB → warmup직전1.762GiB → 직후9.031GiB → 파일 열기9.031GiB → NF4변환9.469GiB → 로딩 완료9.479GiB였다. 큰 증가가 파일 열기보다 warmup에서 관찰됐다. 다만 OS high-water의 짧은13.015GiB 피크를 특정 단계에 정확히 귀속할 수는 없다. 전송/NF4 변환은 설치 라이브러리 내부에서 결합돼 있어 완전히 독립된 할당 비용으로 분해했다고 주장하지 않는다.

probe2회와 합성 텍스트2회, 실제 생성4회 모두 완료했다. 생성 시간0.843/1.328/0.375/4.734초, TTFT0.718/0.750/0.141/0.125초, 출력2/6/3/40tokens, 큐대기0초다. 마지막 설명 응답은8.45tokens/s였으며 짧은2~6토큰 probe의 속도를 대표 성능으로 삼지 않는다. 이 수치는 Discord E2E p50/p95가 아니다. 계산/정밀도/가중치/큐를 바꾸지 않아 이번 후보 간 출력 동등성 비교 자체가 없으며, 이전 사회적 평가를 새 평가로 재사용하지 않았다.

**결론:** 기존 원본31.35GiB → 분할13.01GiB는 과거 최적화 근거다. 이번에는 약13GiB 이하로 더 낮추는 안전한 공개 로딩 옵션의 유효성을 입증하지 못했으므로 기존 로더를 유지한다. 새 기능은 실제 준비 단계의 읽기 전용 UI 표시와 진단 계측이다. 실제 게임 병행·반복 GPU 전환/실패 복구·장시간 자원 추세는 이번에 새로 검증하지 않았다.

## UI 원인과 실제 변경

- 메인/프로필/폼 footer/미리보기의 press 즉시 실행을 제거했다. 원래 누른 활성 버튼 안에서 release할 때 실행한다. 밖으로 드래그하거나 포커스/화면을 잃으면 취소한다. 비활성 전환·이전 화면의 오래된 region도 실행하지 않는다.
- Space는 누름 상태를 유지하고 해제 시 한 번 실행한다. 키 반복으로 중복 제출하지 않는다. Tab/Enter, 슬라이더 키보드, 선택 목록/세그먼트의 기존 의미와 Escape 취소는 유지한다.
- 반환 Future 또는 Controller 제출 Future를 추적해 해당 액션을 처리 중으로 잠근다. 성공을 미리 표시하지 않고 완료 후 스냅샷/기존 오류 경로를 따른다. 저장 실패의 편집값 보존·삭제 확인은 기존 폼 계약을 유지한다.
- 400ms마다 새 상태 없이 전체 화면을 그리던 poll을 변경했다. 새 스냅샷/완료 Future가 있을 때 갱신하며, 누름 중에는 잠시 적용을 보류하고 2초 상한 뒤 취소/최신 상태 적용한다. 백엔드 안전 검사나 정지는 지연하지 않는다. 목록의 선택/스크롤과 열린 편집기는 기존 계약을 따른다.
- 내비게이션은 기본 테두리를 줄이고 선택된 위치에 지속 표시를 둔다. hover/pressed/focus와 선택 표시를 분리했다. Tk/Canvas는 유지하며 프레임워크 교체는 하지 않았다.
- 최초 설정은 세 단계와 짧은 설명으로 나누고 긴 안내는 상세 창으로 옮겼다. 모델 빈 상태가 목록 아래 가려지는 문제와 없어진 모델 선택 잔류를 수정했다. 모델 선택/파일 검사/실제 GPU 준비는 계속 구분한다.
- 150%/작은 창에서 캐릭터 설정 라벨과 값, 진행 상황 카드와 통계/진단 버튼, 응답 방식 설명과 명령 버튼, 관계 목록 제목의 겹침을 실제 이미지로 확인해 수정했다. 페이지별 다음 행동 안내와 단위/표현도 정리했다.

## 검증과 경계

`test_resume_memory_ui.py`: 마우스 누름·해제/드래그 취소, Space 반복/포커스 해제, redraw된 stale action, 누르는 중 snapshot 보류/idle redraw 생략, 비동기 중복 방지, 모델 빈 상태/선택 제거, 로더 실패 단계 복구를 추가했다. 기존 workflow 테스트도 press뿐 아니라 release까지 실제 Tcl binding을 실행한다. 초기 관련48검사 중 기존 색상 테스트가 페이지 전환 전 region을 계속 참조해1실패했다. 동작을 숨기지 않고 색상 검사와 실제 실행 검사를 분리했다. 실패 로그는 로컬에 보존했다. 이후 관련 통합27검사 통과.

격리 Tk 매트릭스는 **420조합 PASS**, callback 오류0, 최장 합성 렌더175.333ms다. 10화면×2창크기×3Tk배율×7상태이며 실제 OS 전체 DPI 변경은 아니다. 독립된 비활성 Windows Desktop에 테스트 프로세스를 붙이고, 자기 PID의 HWND만 PrintWindow해 **66개 화면과 표현 설정 popup**을 렌더했다. Desktop 전환·전역 입력·사용자 화면 캡처는 없다. 숨긴 창의 blank 캡처와 Desktop 부착 실패는 검증 성공으로 세지 않고 중단한 뒤 격리 방법을 보강했다.

직접 시각 검토는 작은150% 설정/모델/캐릭터/응답 방식/진행 화면과 표현 popup, 서버/기억 화면을 중심으로 했다. 66개 전부를 사람이 조작했거나 화면낭독기를 검증한 것은 아니다. 장문·다수 목록/오류/로딩은 별도 매트릭스와 입력 회귀 범위다. native 파일 선택창은 mock 경계이고 실제 사용자 조작감과 다른 Windows는 **NOT VERIFIED**다. 로컬 원본/PNG/프로파일은 비공개 `local_data/`에만 보존한다.

## 명령 비표시 — 원격 원인 미확정

새 `test_command_sync_payload.py`는 `CommandTree.sync/fetch_commands`를 통째로 대체하지 않고 실제 SDK 직렬화와 결과 객체 생성을 사용하며 HTTP만 mock한다. 전역 payload는 `/동의`1개, 서버별 payload는 빈 배열이고 서버 정리가 전역 mock 목록을 삭제하지 않음을 확인했다. 빈 로컬 전역 tree는 bulk 호출 전에 차단한다. 실제 인증/원격 조회/등록/삭제/sync는0회다. **이 결과로 실제 사용자 서버가 복구됐다고 주장하지 않는다.**

후속은 기존 인수인계대로 실행 버전·Application·비공개 감사 단계 확인 → 별도 승인된 읽기 전용 원격 목록 대조 → 대상/변경 전후 검토 → 별도 변경 승인 → 최소 복구·재조회·사용자 `/동의` 화면 확인 순서다. 연결 허가와 명령 변경 허가는 별개다.

## 참고한 공개 UX와 채택 범위

[Windows Button](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/buttons)의 누름/해제·키보드 상태, [NavigationView](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/navigationview)의 선택 지속 표시, [Fluent](https://learn.microsoft.com/en-us/windows/apps/design/basics/)의 계층과 여백, [LM Studio](https://lmstudio.ai/docs/app/basics)의 파일 준비와 모델 로딩 구분, [Discord 안내](https://support.discord.com/hc/en-us/articles/360045138571-Beginner-s-Guide-to-Discord)의 서버/채널 계층을 참고했다. 기존 다크 테마와 서버/채널 master-detail을 유지하며 외형을 복제하지 않았다. [HF 분할 로딩 문서](https://huggingface.co/docs/transformers/v4.48.1/big_models)는 원리 참고이고 현재5.20.1의 실제 소스와 별도로 취급했다.

## 남은 차단과 다음 순서

사회적 오개입·정정/우려/농담/전달문 질문 누락·잘못된 대화 연결, 실제 `/동의` 비표시 원인/복구, 실제 사용자 UI/친구 서버 재시험, 다른 Windows·장시간 운용은 미해결 또는 미검증이다. 넓은 의미 평가를 이번 UI 수정으로 통과시켰다고 하지 않는다. 원본 대신 분할 모델을 쓰려면 사용자 선택이 필요하며 메모리 admission은 그대로다. 운영 자료를 보존한 오프라인 사용자 확인 이후, 승인 범위를 나눠 명령 접근 장애부터 해결한다.

## 최종 회귀 기록

- `PYTHONPATH=src;tests;tools`로 `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`: **670검사 OK224.711초**. 추가 UI/로더 상태6개와 실제 SDK payload2개를 포함한다. 이전 첫 전체 실행670개는 누름만 전달하던 기존 미리보기/프로필 테스트2개에서 실패했다. 완전한 Tcl press/release 계약으로 수정 후 해당5검사 OK2.423초, 전체를 재검했다. 프로그램 동작이나 기대 저장/취소 후조건을 완화하지 않았다.
- `tools/verify_ui_functional_audit.py --output <private>`:420조합 PASS. `tools/render_isolated_ui.py --output <fresh-local_data-directory>`:66화면+표현 popup, callback 오류0. 출력은 비공개이고 public source에 이미지/개인 경로를 넣지 않는다.
- `tools/verify_ui_actions.py --output <private>`:210디스패치 중209개 오류 없음,1개는 미연결 명령 조회의 정확한 안전 차단이었다. 이를 최초 결과에서 실패로 보존한 뒤 도구가 성공 동작과 예상 차단을 구분하도록 고쳤다. `--page outputs` 표적 재검16개 PASS, 그중 명령 버튼은 `command_review`1회/SDK HTTP0회/외부0회/연결 필요 안내를 단언했다. 전체210개를 무조건 성공한 실사용 시나리오로 합산하지 않는다.
- `tools/verify_loader_memory.py --mode full --model-path <existing-private-shard> --output <private>`:기존 분할 모델1회 로딩/생성4회/정상 해제 PASS. 이후 추가한 `load_phase`는 읽기 전용 상태 필드이고 계산 인자/가중치/추론/큐/동의 로직은 변경하지 않았다. 운영 DB 마이그레이션이나 실제 Discord는 실행하지 않았다.

## Portable·보존 마감

`tools/build_portable.py --refresh-public --output dist/EchoMate-rc-utterance`로 확정된 공개 실행 소스/문서를 기존 런타임에 한 번 반영했다. manifest21,549파일/4.542GiB, src87파일(가중치 없음)·docs58파일이다. 이후 마감 문서만 복사하고 해당 manifest 항목을 다시 계산한다. 실행 소스와 manifest 해시를 대조하며 공개 소스 바이트가 같은지 확인한다. `local_data/`, `models/`, `.git/` 항목은 없고 운영 자료를 복사하지 않았다.

번들 Python·번들 src·별도 빈 DATA_HOME/작업 디렉터리에서 입력/고급 설정/저장·취소·실패/프로필/SDK payload **35검사 OK9.962초**. 최초 harness는 DATA_HOME과 테스트의 상대 `local_data`를 서로 다른 곳으로 지정해21개 경로 보호 오류가 발생했다. 보호 조건을 낮추지 않고 격리 CWD/DATA_HOME을 일치시켜 재검했으며 첫 실패는 로컬 로그로 보존한다. 실제 제품의 데이터 경로 검사를 우회한 결과가 아니다. 두 VBS `/check`는 PASS지만 창이나 봇을 실행하는 검사는 아니다.

운영 settings/bootstrap/Companion DB/sent DB의 시작·종료 SHA256은 **4/4 동일**. 모델·LoRA·토큰은 수정/삭제/외부 업로드하지 않았다. 이번 번들에서 실제 GPU 재로딩/로컬 미리보기 생성은 다시 하지 않았다. 소스의 실제 GPU4생성과 번들35모의/위젯 검사를 구분한다. 실제 사용자 화면·다른 Windows·장시간 누수와 실제 Discord는 계속 NOT VERIFIED이며 정식 릴리즈는 BLOCKED다.
