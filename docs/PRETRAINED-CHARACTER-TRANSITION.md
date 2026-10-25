# 사전 학습 캐릭터 제품 전환 — 단계별 구현 및 QA

## 2026-10-25 후속 구현 — 현재 상태

후속 [Runtime 통합 QA](CHARACTER-RUNTIME-INTEGRATION-QA.md)가 아래 초기 구현의 미연결 항목 일부를 대체한다. concrete Lime GGUF/InstanceLease/fair queue/manager/Runtime epoch, 캐릭터별 임시 SQLite·legacy snapshot·원자 삭제, 새 모드의 로컬 `/캐릭터` 계약을 연결했다. 실제 Lime 취소/idle/해제/순차 reload·짧은 이름5턴은 확인했으나 semantic 청자 gate가 FAIL이다. 새 Windows selector/installer/첫 controller handoff와 운영 migration·장시간·다른 Windows는 여전히 미완료다. 세 모델 READY/정식 RELEASE를 선언하지 않는다.

시작 코드 `92e01dd` (main/원격 일치, 기존 작업 트리 clean). 현재 **RELEASE BLOCKED**.
이 문서는 학습 중심 연구 계획을 대체하는 현재 제품 전환 계획이다. 과거 학습 자료와 결과는 삭제하지 않는다.

## 현재 제품 계약

개발자가 선정한 사전 학습 여성 캐릭터 중 한 명만 활성화한다. 대화 사용자는 여러 명일 수 있으며 서버·채널·사용자 문맥은 분리한다. GPU 모델 한 개, 기존 fair queue, 기억·친밀도·동의·예약·reply·분할 발언 보호를 유지한다. 캐릭터별 이름은 내부 ID와 분리한다. 기존 운영 Gemma 선택과 개인 자료는 자동 변경하지 않는다.

새 제품 전환이 완료되기 전 기존 Windows 앱은 **레거시 호환 실행 경로**다. 신규 카탈로그에 있다는 사실은 설치/활성화/품질 검증 완료를 뜻하지 않는다. UI에서 세 모델을 이미 사용할 수 있다고 표시하지 않는다.

## 공식 원천 감사

2026-10-25 Hugging Face의 모델 API `?blobs=true`와 제공 README/LICENSE를 확인했다. 고정 revision·공개 LFS SHA256·바이트 수는 `character_models.py`에 기록한다. 원문/메타데이터/다운로드는 비공개 로컬 자료로만 보관한다.

| 캐릭터 | 확인된 제공물 | 조건 및 차단 사항 |
|---|---|---|
| [Yaho](https://huggingface.co/ChanLumerico/EXAONE-3.5-7.8B-Instruct-Yaho) | revision `24a501c8107a07ea18c9657e84525a081741be02`, 제공자 GGUF Q4_K_M 4,770,651,872 bytes, Q6/Q8 및 Safetensors도 존재 | 제공 LICENSE는 EXAONE AI Model License 1.1-NC. 단순 무료/비상업 사용 일반 허용으로 해석하지 않는다. 연구 사용으로 제한된 grant를 확인했으므로 제품 사용·배포 검토가 필요하다. 학습 정체성은 카드상 갸루귀신이며 기본 표시 이름 야호와 차이가 있어 이름 오버라이드 실측이 필요하다. |
| [Lime](https://huggingface.co/naksyu/lime_Q6_K) | revision `99280194d4593f0efe2d6a9ac79a697b0ec5e880`, limechat GGUF Q6_K 6,217,263,584 bytes, 별도 template 파일 | 제공 LICENSE Apache-2.0, 카드도 같은 조건을 명시한다. [공식 Google E4B-it 카드](https://huggingface.co/google/gemma-4-E4B-it)의 Apache-2.0과 대조했다. 파생 카드의 `google/gemma-4-E4B` 표기만으로 정확한 upstream revision/tokenizer 동일성을 확정하지 않는다. 제공자 속도·품질 주장은 EchoMate 실측이 아니다. |
| [여성 IT 기획자](https://huggingface.co/92doolgi/Persona-Driven_Korean_Debate_Bot) | revision `3001bbc98605fbdb8754e16c17513cdc1724656f`의 README·학습/평가 Python 소스 | `adapter_config.json`·adapter weights·기본 weights가 없다. base 표기는 Gemma 4 E2B이지만 정확한 revision/실행 가능한 adapter가 없다. **BLOCKED: missing adapter**. 다른 E2B에 임의 LoRA를 붙이거나 직접 재학습한 결과를 제공 모델로 부르지 않는다. 카드 `gemma` 표기의 조건도 미해결이다. |

모델 파일은 Public GitHub/Portable에 포함하지 않는다. 공개 다운로드·연구 실행·일반 제품 이용·재배포는 서로 다른 판단이다. 접근 제한이나 동의 절차를 우회하지 않는다. Yaho와 기획자를 일반 제품용 Ready로 승격하지 않는다.

## 재사용 감사

| 기존 기능 | 분류 | 적용 방법/남은 조건 |
|---|---|---|
| CompanionStore/ReadReceipt/동의 epoch/삭제·정정/기억 선택 최신성 | 새 구조에 맞춰 수정 | 기존 권한 검증 재사용. 캐릭터 소유가 불명확한 자료는 legacy로 보존. 아직 새 모델에 개인 DB 연결하지 않음. |
| 관계·친밀도 | 수정 | 서버·사용자·캐릭터 키 필요. 친밀도를 권한으로 승격하지 않음. |
| 예약·알림·실행 영수증 | 재사용 + 전환 경계 수정 | Runtime 소유, 전환 중 claim/송신 보류, 시작 세대가 바뀌면 송신 거절. 생성 캐릭터의 가상 경험을 새 캐릭터에 귀속하지 않음. |
| fair queue/GPU 큐/취소 | 재사용 | 새 manager의 단일 GPU 실행 gate 바깥에서 기존 공정 스케줄 유지. 현재 연결은 미완료. |
| 메시지 조립·문맥 선택·사회적 판단·reply/중복 | 재사용 + epoch 연결 필요 | 입력 수신 시점부터 character/name stamp를 유지해야 함. 새 캐릭터로 기존 대기 발언 자동 재생 금지. 기존 사회적 품질 FAIL은 유지. |
| 모델 준비·해제 | 수정 | 기존 backend의 캐시 반환만으로 다른 엔진 프로세스 종료를 증명할 수 없음. 소유 backend의 drain/unload/reclaimed 증거 필요. |
| 로그·복구 | 재사용 | 일반 로그에 원문·개인 경로·개인 ID를 추가하지 않음. 불확실한 복구는 RecoveryRequired. |
| 기존 프로필·학습 도구 | 임시 호환/연구 기록 | 데이터 삭제·자동 변환 없음. 신규 선택 UI 연결 후 일반 편집 진입점을 단계적으로 비활성화. 아직 UI 변경 안 함. |
| slash commands | 임시 호환 | 현재 `/동의`·`/성격` 계약 유지. `/캐릭터`로 대체할 offline 버전 계획과 migration 구현이 다음 단계. 실제 Discord 등록/삭제/조회 안 함. |
| Windows UI/Portable | 수정 | 캐릭터 선택/설치/상태/이름 UI 필요. 기존 다크 위젯·비동기 controller 재사용, 새 UI 아직 NOT VERIFIED. |

## 구현 범위

`character_models.py`는 catalog/backend API 버전, 안정 ID, 이름/출처/revision/파일 hash/크기/backend/양자화/base/license/template/자원 미검증 상태를 분리한다. 파일 hash 검증은 실행·라이선스 승인이 아니다. 이름은 별도 명시 경로의 버전 문서에 저장하며 쓰기 실패 시 기존 파일과 RAM 선택을 보존한다. 운영 Settings/DB는 변경하지 않는다.

`character_manager.py`는 opt-in 수명주기 API다. Idle → SwitchingRequested → Quiescing → Cancelling → Unloading → Reclaiming → Loading → Validating → Ready 상태를 사용한다. 실제 자원 admission과 backend validation/health check는 필수다. model load 전 process 내 다른 manager 소유권을 확인한다. 이 소유권은 **기존 LocalBackend까지 자동 통합된 전역 GPU lease가 아니다**. 기존 앱의 InstanceLease와 실제 backend handoff 연결은 다음 단계다.

전환 시 기존 identity를 먼저 무효화하고 대기/진행 생성 취소 및 drain을 확인한다. 해제는 backend의 자기 소유 객체/프로세스 reclamation 확인이 있어야 완료된다. timeout을 무시한 작업은 참조를 유지하고 RecoveryRequired로 막는다. 새 모델과 겹쳐 로딩하지 않으며, 명시 recover가 성공하기 전 재전환하지 않는다. 이전 캐릭터 복구 성공을 추정하지 않는다. 이름 변경도 세대/이름 버전과 health check를 갱신한다. 생성 결과 반환 및 최종 송신 양쪽에서 stamp 확인이 필요하며, **새 manager의 Discord 송신 연결은 아직 미완료**다.

공통 Runtime의 실제 결함 하나를 수정했다. 기존 알림 전달은 `changing_model`을 검사하지 않았고 권한 await 사이 전환이 끝나면 이전 전달 시도가 계속될 수 있었다. 이제 모델 전환 세대를 올리고 알림 시작 세대/전환 상태를 권한 확인과 SDK 직전 freshness에서 대조한다. claim 전에는 scheduled를 보존한다. claim 이후 불확실한 송신은 기존 failed/중복 방지 정책을 유지하며 무조건 재시도하지 않는다.

## 검증 및 미완료

표적 검사: catalog/hash와 실행 승인 분리, ID별 이름 복원·저장 실패 보존, 이전 stamp 차단, 대기/진행 생성 취소, 취소를 무시하는 callback, 언로드 불확실성, 로딩 timeout·취소 후 명시 복구, manager 간 중복 상주 금지, 자원 거절, 모델 변경 도중 알림 권한/송신 경주를 합성 backend·임시 SQLite로 검증한다. 실제 SDK mock 알림 검사는 실제 Discord 호출이 아니다.

실제 GPU·전체 회귀·Portable·보존 결과는 마감 시 아래에 기록한다. 실행하지 않은 설치/UI/실모델 품질을 PASS로 승격하지 않는다. 신규 manager는 아직 구체 backend/기억 namespace/UI에 연결하지 않으므로 제품 전면 전환 완료가 아니다.

## 다음 실행 순서와 완료 조건

1. 제공자 GGUF의 파일 hash·template·엔진 아키텍처를 고정하고 Lime부터 격리 GPU 이름/한국어/사실성 smoke. 실패 모델은 Ready로 승격하지 않음.
2. 전용 backend adapter와 resumable installer: partial/hash/취소/디스크·자원 예산/진행 상태, 자체 PID 종료 및 reclamation. 기존 InstanceLease·fair queue와 연결하고 레거시 모델과 중복 로딩 금지.
3. **운영 DB에는 적용하지 않고** 임시 저장소에서 캐릭터 namespace/legacy 보존/공통 consent·예약/캐릭터별 관계를 검증. 철회·삭제는 캐릭터별 캐시/대기 작업까지 반영.
4. Runtime 수신/조립/생성/송신/알림에 identity stamp 연결. cross-character replay 차단, 이름 변경과 예약 표시 이름 경합 검증.
5. 캐릭터 선택·이름·설치 UI와 `/캐릭터` offline command 계약, legacy `/성격` 이관. 실제 Discord 동기화는 별도 승인까지 금지.
6. 모델별 실제 GPU/다중 턴/SDK mock·전체 회귀·격리 Tk·Portable 검증. 세 캐릭터 충족·사용성·사실성·사회적 판단 및 마지막 실제 Discord 검증이 남으면 RELEASE BLOCKED.

## 실제 Lime GGUF 개발 검사

제공자 Q6_K 파일 전체 SHA256 일치. Xet 전송 정체 후 이번 작업 소유 downloader만 종료하고 HTTP 전송으로 재시도하여 163.703초에 확보했다. 접근 제한·이용약관 동의 우회 없음. 원본 파일은 비공개 연구 폴더에 있고 운영 모델/설정/Portable에는 넣지 않았다.

GGUF3 metadata는 `gemma4`, 42 blocks, KV heads 2, key/value length 512, tokenizer `gemma4`, 720 tensors, limechat template를 확인했다. 공식 소스의 정확한 upstream revision/변환 계보 전체를 증명한 것은 아니다. 기존 프로젝트 소유 llama.cpp b11721/ff5a23376로 2048 context·단일 slot·batch128/ubatch64·ngl99 요청·greedy seed2026·최대 출력96에서 실행했다. engine의 control-looking token 두 개 type 보정 경고도 보존했으며 이 경고가 사실성 오류 원인이라고 단정하지 않는다.

자원 admission은 모든 파일 byte를 GPU weight로 계산하고, 전체42층/비공유 attention/FP16 KV 2048-token 상한 352,321,536bytes, workspace/driver2GiB, 기존 free 안전2GiB를 더한 **10,864,552,416bytes**였다. SWA/shared-layer 절약을 미리 차감하지 않았다. 별도 Windows commit 준비 예산과 실행 중 VRAM2GiB/RAM3GiB/commit2GiB/온도85°C 기준을 유지했다. PyTorch allocated/reserved는 이 네이티브 backend의 측정값이 아니므로 보고하지 않는다.

| 조건 | 입력/출력 | 로딩 | 응답 p50 / p95* | TTFT p50 | 최소 free VRAM | 최소 RAM / commit 여유 | 소유 서버 private 피크 | 최고 온도 |
|---|---|---|---|---|---|---|---|---|
| 이름 header + 별도 사실 system | 7응답/194출력tokens | 4.610초 | 0.518 / 0.751초 | 0.167초 | 8,725MiB | 5.467 / 25.907GiB | 7.529GiB | 46°C |
| 동일 사실을 첫 system header에 통합 | 7응답/202출력tokens | 3.079초 | 0.533 / 0.761초 | 0.173초 | 8,726MiB | 5.428 / 25.887GiB | 7.538GiB | 46°C |

*n=7의 nearest-rank p95는 표본 최댓값이다. 짧은 개발용 생성이며 Runtime/SDK 전체 지연이 아니다. 두 로딩의 cache 상태를 통제하지 않아 로딩 속도 개선이라고 주장하지 않는다. GPU free는 시스템 집계이며 다른 앱 사용 변화와 완전히 분리한 allocated가 아니다. 각 소유 서버 종료 후 free가 시작 값 수준으로 돌아왔다. 프로세스 종료/자체 handle 회수와 집계 free 관측을 구분한다.

이름 변경은 원래 라임 질문을 포함한 **3턴 모두 유나 유지**였다. 그러나 사실성 개발 질문에서 두 조건 모두 조회 실패를 데이터 없음처럼 설명했고, 알림 생성 API 미실행/영수증 없음에도 완료를 주장했다. 일반 고민은 공통 공감·조언형이었으며 여러 캐릭터 구별 비교는 아니다. 첫 system 통합은 role 계약 보호이며 사실성 해결책으로 채택하지 않았다. **Lime 제품 Ready 미승격**. 새 모델이 기존 Gemma보다 낫다는 근거는 확보되지 않았다. Yaho·기획자 실제 GPU, 세 모델 A/B, 새 backend Runtime→SDK 통합·장기 대화·새 UI는 NOT VERIFIED다.

비공개 실행 근거는 `local_data/pretrained-transition-20261025/`의 metadata/download, `lime-probe*/summary.json`, samples, responses와 engine log다. 실제 사용자 자료/운영 기억/최종316개는 입력하지 않았다.

## 회귀에서 발견한 기존 Windows 저장 결함

최초 전체945검사는 275.824초에 기존 `pilot_state.save`의 최초 디렉터리 게시 `os.rename` WinError5 한 건으로 실패했다. 같은 표적의 별도 실행은 통과하여 일시적 잠금 경로를 확인했다. 연구 기능은 계속 보존하며, Windows 5/32/33 오류만 최대5회/총0.2초 대기해 재시도하도록 수정했다. 목적지가 생기면 즉시 거절하고 ACL/시스템 설정/기존 체크포인트를 변경하지 않는다. 영구 실패는 기존대로 예외·자기 partial 정리다. 합성 일시/영구 잠금 및 불변 저장 표적을 추가했다. 최초 실패를 전체 PASS로 바꾸어 기록하지 않는다. 최종 결과는 아래 마감 기록을 따른다.

## 마감 검증

구현 커밋 `a80d67d`. 최종 문서 커밋은 Git 이력을 따른다. 전체948검사 OK257.519초, 표적35개 OK10.189초. 외부 DNS/socket 차단 harness 및 실제 SDK HTTP mock을 사용했다. 새 character 모델의 Runtime 생성→SDK 경로는 아직 NOT VERIFIED다.

Portable 기존 bundle의 공개 src/docs/README/profile만 동기화하며, 실제 번들 Python이 bundle의 manager/Runtime 소스를 import했는지 assert한 뒤24개 검사 OK3.632초였다. 최초 검사9오류는 격리 fixture의 상대 local_data 폴더 누락이었고 테스트 runner만 수정했다. 실패 로그는 비공개에 보존한다. 새 GUI 입력/시각검사, 다른 Windows 설치, Portable GPU, 장시간 model switching은 실행하지 않았다.

운영 설정/bootstrap/두 DB/최종 소비 장부 SHA256 5개와 원본 Gemma 모델12shard hash는 불변이다. 이번 GPU 입력은 새 합성 개발 질문뿐이며 실제 사용자 기억/최종316개 소비0, 실제 Discord0이다. 다른 앱/게임의 화면·입력·프로세스 내부·파일·네트워크를 조사하거나 조작하지 않았다. 집계 시스템 자원과 이번 작업 소유 downloader/server만 계측·종료했다. 게임 제재 위험0을 보장하는 검증은 아니다.

공개 diff에는 소스·합성 fixture·비식별 문서만 포함하고 모델/토큰/DB/원문/로컬 checkpoint는 포함하지 않는다. 전체 Portable manifest hash/파일 집합과 최종 공개 파일 일치는 비공개 `portable-final.json` 및 `portable-public-pairs.json`에서 확인한다. RELEASE BLOCKED: 모델 제공·제품 라이선스, 사실성, 기억 namespace, backend/Runtime/UI/명령 통합, 장기 안정성, 실제 Discord 검증이 남았다.
