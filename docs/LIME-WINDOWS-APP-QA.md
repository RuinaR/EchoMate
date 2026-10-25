# Lime Windows 제품 앱 연결 QA — 2026-10-25


### LOCAL_CHAT 마감 근거와 다음 작업

실제 능동10턴과 별도 scripted100회 연속 생성(장기50 포함), 기억20·예약20·인칭20·일상30 시나리오를 구분해 기록했다. 모델의 이전 이름 수용·근거 없는 조회/미래 약속은 남아 있어 RELEASE BLOCKED다. 실제 stream 취소·기억 삭제 경합·재시작 stale 세션 거절을 확인했다. 긴 문맥 native 사전 계산을 같은 선택 메시지 기준32초→약1.4초로 줄였으며 생성 속도 개선과 구분한다. 현재 세션 중복 모델 소유와 외부 고정 파일 가져오기도 보호했다. 최종 결과·실패 로그·Portable·정확한 재개는 [LOCAL-CHAT-QA](LOCAL-CHAT-QA.md)를 따른다.

우선순위: (1) 원천 분리 사회적 시퀀스로 DISCORD_AUTONOMOUS의 오개입/누락 개선, (2) 기존 receipt 기반 기능 경로와 자유 생성의 거짓 약속 구분, (3) 이름 유도·긴 대화 사실성, (4) 최종 소스 장기 GPU/2·8시간·다른 Windows. 실제 Discord는 마지막 별도 승인이다. 재학습·새 모델 탐색으로 범위를 확장하지 않는다.

## 2026-10-25 LOCAL_CHAT 분리·실제 대화 검증 — RELEASE BLOCKED

청자 자격 실패가 로컬 채팅까지 막던 결합을 분리했다. 파일/자원/이름 기술 검사를 통과하면 LOCAL_CHAT을 사용하며 Discord 자율 참여는 계속 BLOCKED다. 로컬 채팅 UI·합성v8 저장소·명시 기능/영수증·native 토큰 예산·저장 세션의 삭제/철회 재생성 방어를 연결했다. 실제 능동10턴과 별도 scripted 기억/예약/일상/장기 대화를 수행했지만 자유 생성 사실성은 미해결이다. 제한 Direct GPU→SDK mock7이벤트/의도한4reply·오류0은 자율 참여의 PASS가 아니다. [검증 범위·실패·원문 위치·재개](LOCAL-CHAT-QA.md).


시작 `32cf372` main/origin 일치·clean. 현재 **RELEASE BLOCKED / 실사용 테스트 준비 미완료**. 이 문서는 과거 'Windows installer 미연결' 기록을 대체하지만 청자/사실성 품질 gate를 해제하지 않는다.

## 실제 구현

- `EchoMate.vbs`와 PowerShell 기본 진입점을 `echomate_bot.lime_desktop`으로 연결했다. `/legacy` 또는 `-Legacy`로 과거 앱/자료에 명시적으로 접근할 수 있다. 과거 Gemma/학습·성격 편집은 새 주요 화면에 없다.
- 새 `LimeController`는 기존 Controller/Discord Runtime/공정 큐/CharacterStores를 재사용한다. 기존 ROOT 아래 별도 `lime/` 저장소를 사용하고 기존 InstanceLease는 공유하므로 레거시와 중복 모델을 실행하지 않는다. 기존 운영 설정/DB는 자동 이관하지 않는다. 새 캐릭터 DB는v8, 공통 동의·예약과 캐릭터별 기억·관계를 유지한다.
- 고정 revision/hash의 Lime GGUF와 공식 b11721 CUDA12.4 엔진 ZIP 두 개를 조건 확인 후 다운로드하거나 기존 파일에서 복사한다. 원본은 이동/수정하지 않는다. HTTPS 출처/redirect 제한, 크기/SHA256, disk reserve2GiB, 부분 파일/206 검증·200 재시작, 취소 후 파일 보존을 구현했다. 호스트 전역 설정·인증 정보는 사용하지 않는다.
- ZIP 경로 탈출·symlink·Windows 장치명·중복 경로·팽창 한도를 거부하고 fresh staging만 사용한다. 설치 후 엔진의 모든 파일 hash와 실행 파일 고정 hash를 재검사한다. 손상 파일은 자동 덮어쓰기하지 않는다. 명시적 복구에서 해당 설치 폴더의 손상/부분 파일을 `.rejected`로 보존하고 중간 이동 실패 시 rollback한다. 이전 보존본은 덮어쓰지 않는다.
- 파일 검증→기술 GPU 준비→자기 이름→기존 strict semantic probe 순서다. 청자 실패 시 해제하고 실행을 금지한다. 로컬 미리보기와 봇 켜기 모두 이 gate를 우회하지 않는다. Ready는 재시작 후 복원하지 않고 재검증한다.
- 이름 저장은 모델/Runtime rename·epoch와 연동하고 저장 실패 시 이전 이름으로 복귀한다. 복귀 실패는 RecoveryRequired다. 건강한 모델에서 정상 rollback된 관리 오류는 Ready 상태를 유지하면서 오류를 표시한다. Discord 프로필 API는 호출하지 않는다.
- UI는 설치→이름→모델 로딩→Discord 설정, 관계/기억/예약/상태 흐름이다. 비동기 작업·취소·검증 실패·설치 복구·긴 이름/오류를 표시한다. `/동의`·`/캐릭터`의 새 모드 계약을 안내한다. 기존 token 설정은 DPAPI 로컬 저장 단계와 실제 연결을 구분한다.
- GGUF가 생성한 자체 자식만 Windows unnamed Job에 넣어 소유자 종료 시 정리한다. 다른 프로세스를 열거하지 않는다. 할당 실패는 로딩 실패로 처리한다. 정상 종료 및 자체 테스트 부모의 강제 종료 뒤 자식 종료를 확인했다. Popen 직후 Job 연결까지의 짧은 간격이 있어 무조건적인 원자적 crash 보장은 아니다.

## 실제 실행 근거

비공개 증거는 `local_data/lime-product-app-20261025/`에 보존한다. 원문/캡처/모델/로컬 진단은 공개 커밋하지 않는다.

| 검사 | 결과와 범위 |
|---|---|
| 고정 GGUF·엔진 실제 가져오기 | PASS: 원본 유지, 별도 임시 제품 저장소에 복사/검증/55개 엔진 파일 설치,28.219초. 모델6,217,263,584bytes. |
| 공식 HTTPS downloader | PASS: pinned Lime LICENSE10,002bytes 실제 다운로드·전체 SHA256. 부분 파일을 둔 상태의 처리 확인. 실제 원격 응답이206인지200인지는 기록하지 않아 원격 range 재개 인증으로 주장하지 않음. 정확206/무시200은 mock 경계 검사. 전체6GB 새 network 설치는 NOT VERIFIED. |
| 실제 Controller→Lime GPU | 기술 로딩3.672초·유나 자기 이름 확인 PASS. strict semantic FAIL→실제 해제/비상주, start 차단. 모델 품질 READY 없음. |
| 자원 | 집계 최소freeVRAM7,132MiB, RAM5.49GiB, commit20.185GiB, 최고48°C. 종료 후freeVRAM11,183MiB. PyTorch allocated/reserved가 아닌 native 경로의 집계 수치다. 다른 앱 영향을 단정하지 않음. |
| 새 저장소/재시작 | 합성 A/B 기억 격리·친밀도80/20, 이름유나 재시작 보존→하루 변경 뒤 기억 소유권 유지. 재시작은 모델 재검증 필요. 운영 migration은 미실행. |
| 설치·Controller·UI·소유 자식 표적 | 58개 OK10.818초. 비활성 Desktop·외부 socket 차단. 최초34검사의 경로 정규화 fixture 실패는 수정 후 보존, 제품 기대값 완화 없음. |
| 격리 UI | 소유 HWND만9장(초기/실패/긴 이름×100/125/150%),1040×740. 150% 실패/긴 이름 화면 시각 확인. 모델 실패 payload의 이전 file-label 오류는 소스에서 고쳤지만 기존 실제 payload 원본은 수정하지 않음. |
| 실제 Discord | 미실행. 실제 토큰 인증/REST/Gateway/명령 등록/송신 없음. 합성 자격 정보는 로컬 DPAPI 저장만, 인증 차단. |

최초 표적 실행에 활성 Desktop의 withdrawn Tk 검사가 포함된 실수가 있었다. 전역 입력/캡처는 없었지만 격리 조건에 맞지 않으므로 해당 GUI 결과는 채택하지 않았고 이후 모든 UI/전체 회귀는 검증된 비활성 Desktop에서 실행했다.

## 최종 소스·번들 회귀

전체1,018개 OK301.405초(전용 비활성 Desktop/외부 socket·DNS 차단), 번들94개 OK8.705초(실제 번들 import 경로 assertion·전용 Desktop)다. 이는 CPU/mock/UI 검사이며 Portable GPU·다른 Windows 검증이 아니다. 운영 설정/bootstrap/두 DB/평가 소비 장부5개 SHA256과 원본 Lime SHA256은 작업 전후 일치했다. 기존 다른 모델/LoRA는 사용·변경하지 않았다.

## 새로운 합성10턴 실제 생성 진단

제품 gate를 유지한 별도 기술 진단이며 Runtime→SDK 전체 인증이 아니다. 퍼즐/친구와 의견 차이/장난/후속 회상/미확인 공동 경험/이름·알림 질문10턴이 완료됐다. 마지막 자기 이름은 하루를 유지했고 마지막 알림 질문에서는 완료를 주장하지 않았다. 공동 경험을 창작하지 않았지만 미조회 상태에서 기억의 한계를 얼마나 정확하게 표현하는지는 추가 감사가 필요하다. 이 작은 두 고위험 질문을 일반 사실성 PASS로 해석하지 않는다. 사람 체감 품질은 미검증이다.

같은 resident의 입력 최대1,268token, 생성 p50 1.008초/p95(nearest rank)1.297초, TTFT p50 0.484초다. 다른 길이/부하와 속도 개선으로 비교하지 않는다. 최소freeVRAM7,110MiB/RAM6.015GiB/commit20.798GiB, 최고51°C, 종료/회수 확인. 10턴이지30분/장시간 검증이 아니며 최종316 holdout 소비0이다. `ten-turn-diagnostic/report.json`에 원문/metrics를 비공개 보존했다.

## 라이선스·배포

Lime 저장소 제공 Apache-2.0, llama.cpp MIT와 CUDA 런타임 이용 조건을 UI에 개별 표시한다. 사용자 확인을 자동 수락하지 않는다. 모델/엔진 가중치를 Public 저장소/Portable에 포함하지 않고 공식 URL에서 별도로 가져온다. 다운로드 가능과 재배포 허용을 동일시하지 않는다. 출처: [Lime 고정 repository](https://huggingface.co/naksyu/lime_Q6_K/tree/99280194d4593f0efe2d6a9ac79a697b0ec5e880), [llama.cpp b11721](https://github.com/ggml-org/llama.cpp/releases/tag/b11721), [CUDA EULA](https://docs.nvidia.com/cuda/eula/index.html), [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

## 남은 최우선 작업

1. S1: 실제 Runtime의 구조화 청자 근거와 semantic 판단을 source 분리 다자 시퀀스로 평가한다. 이전3후보/strict probe 실패를 반복 prompt 조정하거나 우회하지 않는다. startup gate 완화로 Ready를 만들지 않는다.
2. F: 자유 생성의 허위 미래 약속은 미해결이다. 결정적 실행 영수증 경로와 모델 출력 일반 사실성을 구분하고 부정·조건·인용/제안의 정상 대화를 오차단하지 않는 근거를 확보한다.
3. 실제 GPU→SDK mock의 확장10–30턴/여러 채널·스레드·권한/수정·삭제 경합,2048 native 문맥 한계와 보호할 사실·현재 발화 토큰 예산을 확인한다. 현재 긴 문맥 전체 보장은 없다.
4. 30분GPU/2시간/8시간 새 앱 운용, 실제 전체 다운로드 중단·재개, 손상 설정/백업·복구 UX, 다른 Windows/Portable GPU는 NOT VERIFIED. 이 단기 로딩 결과로 대체하지 않는다.
5. 다른 필수 gate 통과 후 실제 Discord 읽기/명령 변경/송신 각각 별도 승인 계획. 현재 승인 요청으로 개발을 대신하지 않는다.

재개: `.venv-gemma4/Scripts/python.exe -m echomate_bot.lime_desktop` (관리 UI만, 승인 전 봇 켜기/실제 연결 금지). 회귀는 `run_regression_final.py`, 번들 검사는 `run_bundle_isolated.py`의 전용 비활성 Desktop wrapper와 외부 socket 차단을 재사용한다. private checkpoint는 이 QA와 함께 확인한다.

## 배포·보존 마감

`dist/EchoMate-rc-utterance`의 공개 파일을 동기화했다. 전체 manifest21,592파일/4,877,839,932bytes의 membership·size·SHA256·금지 파일 감사 PASS다. 그 뒤 추가한 QA 문서 통계는 공개 문서 delta와 manifest만 갱신해 별도 hash 대조하며, runtime/모델 검증을 반복 실행한 것으로 세지 않는다. 소스/Portable 두 VBS `/check`는0 종료, 기본 Lime/명시적 legacy 진입점 확인. 이는 앱의 실제 사용자 Desktop 실행 또는 Portable GPU 실행 인증이 아니다. 번들에는 모델·토큰·운영 DB가 없다.

공개 stage의 파일 목록/전체 내용/전체 diff·개인 경로/토큰·private key·비공개 확장자를 검사했고 발견0이다. 새 자료 원문/10턴 출력/격리 캡처/설치 fixture/모델은 ignored local_data에만 유지한다. 마지막 운영5파일 hash는 일치하며 최종316 소비 장부도 그대로다. 다른 앱/게임 목록·화면·메모리·파일·입력·통신은 조사하지 않았다. 자체 창의 최초 withdrawn 검사 격리 실수와 이후 재검증은 위에 명시했다.
