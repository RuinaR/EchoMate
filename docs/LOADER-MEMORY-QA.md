# Windows 1455 로더 메모리 감사 — 2026-10-19

시작 HEAD/원격 main `f1c0ec6`, main clean·fetch 후 차이 0/0. **정식 릴리즈 BLOCKED**. 실제 Discord 로그인/송신/동기화와 사용자 데스크톱 조작을 하지 않았다. 운영 설정·토큰·DB·개인 LoRA·원본 모델을 보존했다.

## 실패 지점과 기존 경로 비교

이전 성공 소스와 원본 실패 traceback을 비교했다. 두 경로 모두 같은 Gemma4 멀티모달 클래스, BF16 compute, NF4 double quantization, device 0, SDPA로 기본 가중치를 먼저 읽는다. 기존 PEFT는 이 로딩이 끝난 뒤 붙는다. 새 경로는 로컬 snapshot 지정, trust_remote_code=False, loading_info 검사와 레지스트리/메모리 검사를 추가했다. 따라서 **LoRA 제거가 NF4 기본 가중치 자체의 크기를 증가시킨다는 근거는 없다**. 새 경로의 정상 완주 GPU A/B는 수행하지 못했다.

기존 오류는 Transformers `_load_pretrained_model`의 `safe_open(..., backend='pread', device='cpu')`에서 발생했다. NF4 변환 및 PEFT 전 단계다. 설치 버전은 Torch 2.9.1+cu128, Transformers 5.20.1, Safetensors 0.8.0이다. Safetensors 0.8.0의 [공식 소스](https://github.com/huggingface/safetensors/blob/v0.8.0/bindings/python/src/lib.rs#L642)는 pread 분기 **전** 전체 파일 `map_copy_read_only`를 실행한다. Windows는 copy-on-write view 전체에 system/process commit을 예약한다. [Microsoft 문서](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-mapviewoffile).

이는 이름이 pread라고 해서 파일 전체의 commit 예약이 사라진 것은 아님을 보여준다. 원래 실패 순간의 연속 메모리 표본은 없으므로 당시 정확한 피크를 소급 계산하지 않는다. 아래 실측은 이 실패 지점과 일치하는 메커니즘을 독립적으로 재현한 것이다.

## 실제 측정 — 작은 합성 파일, GPU 사용 없음

각 행은 새 프로세스다. 기존 전체 회귀 종료 후 순차 실행했으며 사용자 프로그램은 그대로 두었다. 시스템 다른 작업의 commit 변동이 있으므로 프로세스 자체 private commit/OS peak counter를 함께 사용한다. 50ms 표본만으로는 짧은 예약을 놓칠 수 있다.

| 입력 / backend | 열기 순간 private commit 피크 증가 | open 반환 후 유지 증가 | 닫은 뒤 증가 |
| --- | ---: | ---: | ---: |
| 64MiB / pread, 2회 | 각각 64.13MiB | 0 | 0 |
| 256MiB / pread, 2회 | 각각 256.50MiB | 0 | 0 |
| 512MiB / pread, 1회 | 513.01MiB | 0 | 0 |
| 256MiB / mmap, 1회 | 513.01MiB | 256.51MiB | 0 |

전체 파일 크기에 거의 비례하는 **순간 예약**을 확인했다. mmap으로 되돌리는 대안은 이 측정에서 더 큰 예약/유지를 보이므로 채택하지 않았다. disable_mmap=True도 설치된 Transformers에서는 전체 파일을 bytes로 읽는 다른 경로이므로 메모리 해결책으로 임의 적용하지 않았다. 1MiB slice 출력에서도 pread의 RAM 피크는 원본 합성 tensor 크기만큼 증가했다(512MiB 파일 프로세스 peak working set 982.61MiB). 반환 tensor 크기만으로 전처리 피크를 계산하면 안 된다.

프레임워크 import 비교는 새 프로세스에서 같은 공통 import 뒤 기존 경로에만 PEFT를 추가했다. no-LoRA private commit 1432.73MiB / peak working set 572.25MiB, PEFT 포함 1546.89MiB / 658.97MiB였다. PEFT 제거 쪽이 private commit 약114MiB 작다. 실제 모델 초기화·NF4·완료 모델의 RAM/VRAM 또는 속도 비교를 뜻하지 않는다.

## weight bytes + 2GiB 기준의 판정

실제 원본은 23,919,549,408 bytes(**22.28GiB**), 단일 Safetensors, 677 tensors, 최대 tensor 1920MiB다. 현재 검사 기준은 26,067,033,056 bytes(**24.28GiB**). 실제 admission 측정은 여유 commit **13.37GiB**, 부족 **10.90GiB**로 종료했고 **GPU 모델 로딩 시도 0회**였다. 물리 RAM 여유만으로 Windows commit 여유를 대체하지 않는다.

- 파일 크기 항은 이 버전의 단일 파일 COW 예약과 비례하는 근거가 있다. 작은 파일에서 확인한 비례성을 22.28GiB 전체 파일의 성공 측정이라고 쓰지 않는다.
- **+2GiB는 전체 로딩 피크가 검증된 보장치가 아니다.** imports, model meta/buffer 초기화, CPU tensor materialization, NF4 임시 GPU/CPU 메모리와 각 수명이 다르다. 이들을 모두 더하는 것도, 양자화 후 VRAM 크기만 사용하는 것도 잘못이다.
- 기존 최초 검사를 통과해도 import 이후 여유가 줄어들 수 있다. 동일 기준을 **import 이후와 processor 준비 이후에 다시 검사**한다. 기준을 낮추지 않았다.
- 이 측정의 import 약1.40GiB를 고려하면 fresh process 시작 시 약**25.68GiB** 이상의 commit 여유가 필요할 수 있다. 측정 시점의13.37GiB와 비교하면 약12.30GiB 추가 여유의 계획값이다. 환경 변동 및 미측정 초기화/NF4 비용을 포함한 성공 보장은 아니다. 실행 직전 재검사해야 한다.
- RAM 3GiB 검사도 admission 하한이다. 실제 모델 RAM 피크를 검증한 권장 사양으로 표시하지 않는다.

사용자는 직접 불필요한 작업을 마치거나, 저장 후 Windows를 재시작하여 여유를 확인할 수 있다. page file 변경을 자동 수행하지 않았고 필요한 고정 page file 크기를 추측하지 않는다. 여유를 충분히 확보할 수 없다면 별도의 검증된 header/streaming 로더 또는 원본을 보존한 shard 변환의 연구가 필요하다. 이번에는 의존성 패치·모델 재작성·cache 삭제를 하지 않았다.

## 수정 사항과 계측

- `loader_memory.py`: GetPerformanceInfo의 system commit used/limit, GlobalMemoryStatusEx의 RAM available, GetProcessMemoryInfo의 private/peak private와 working set/peak를 bytes로 구분한다. Win64 handle/size 시그니처를 명시했다.
- bounded recorder는 stage와50ms 표본 및 OS process peak를 기록한다. 한도 초과 표본 수를 표시하며 집계 peak는 계속 갱신한다. 일반 앱에서 이 샘플링을 자동 실행하지 않는다.
- `verify_loader_memory.py`: 새 private output만 허용, offline, 합성 파일512MiB 한도, fresh-process mapping/import/guarded full/probe/unload. full에서만 native safe_open/NF4 convert를 감싸 계측하며 인수·반환·backend를 변경하지 않는다. 이미 초기화된 CUDA의 allocated/reserved/peak만 관찰한다. 이 full 계측 후반부는 현재 자원 때문에 미실행이다.
- 실패 traceback이 부분 양자화 모델을 소유한 채 남는 경로를 정리했다. 완료된 실패 frame의 locals를 비우고 model/processor/cache/검증 상태를 해제한다. 예외 종류와 stack 위치는 유지한다.
- 사전 차단/종료 시 Torch가 아직 import되지 않았다면 cleanup에서 새로 import하지 않는다. 정상 모델 재사용과 단일 GPU worker는 유지한다.
- Windows 앱에는 안전한 숫자 필드로 실제 commit 여유/검사 기준을 표시하며 임의 예외 본문·경로·토큰은 노출하지 않는다.

## 검증 범위와 남은 차단

| 항목 | 이번 결과 |
| --- | --- |
| 기존490 전체 회귀 | 490 OK61.101초 |
| 합성 mapping/반복·import 비교 | 실제 Windows CPU 계측 완료 |
| 새 no-LoRA 전체 모델 로딩/최소 추론 | BLOCKED: commit admission 미달, GPU retry 없음 |
| NF4 순간 RAM/VRAM·실제 meta 초기화/모델 해제 피크 | NOT VERIFIED: 해당 단계에 진입하지 않음 |
| 실패 traceback/processor/metadata 정리 | 모의 회귀 검증, 실제 부분 GPU 모델 해제는 NOT VERIFIED |
| 독립 청자20/캐릭터12/전체 E2E A/B9 | BLOCKED, 기존 고정 문항·seal 보존; 새로운 점수 없음 |
| 모델 전환/실패 복구, 다중 요청·공정 큐 | 전체 모의 회귀 포함. 최신 실제 GPU 검증은 BLOCKED |
| Portable 모델 로딩/로컬 생성 미리보기 | NOT VERIFIED. import/첫 설정 성공과 구분 |
| 다른 Windows 깨끗한 환경/업데이트/드라이버 조합 | NOT VERIFIED. 격리 PATH는 다른 Windows OS가 아님 |
| 실제 Discord | NOT VERIFIED, 로그인·송신 금지 유지 |

전체 최종 검사와 패키지 일치는 DISTRIBUTION-QA 최신 절을 따른다. 비공개 원본은 `local_data/loader-qa-20261019/`, 기존 실패/평가 자료는 `local_data/distribution-qa-20261019/`에 보존한다. 둘 다 Git 제외다.

## 재현과 다음 순서

개발 환경에서 PYTHONPATH=src;tests 후 `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`. CPU 프로파일은 PYTHONPATH=src;tools에서 `tools/verify_loader_memory.py --mode mapping --mib 64 --output local_data/<새이름>.json` 또는 `--mode imports`를 사용한다. 기존 output 덮어쓰기를 거부한다. PEFT import 비교만 `--legacy-imports`를 추가한다.

메모리 여유와 운영 GPU lease를 확인한 뒤에만 `--mode full --output local_data/<새이름>.json`을 한 번 수행한다. admission 실패 후 같은 조건의 GPU 재시도를 반복하지 않는다. full 성공 후 독립 청자 → 캐릭터 → 모델 전환 → 같은 조건 E2E/공정 큐 → Portable 실모델/미리보기 순으로 기존 고정 프로토콜을 진행한다. 실제 Discord는 허용하지 않는다. 완료 전 정식 릴리즈를 승인하지 않는다.
