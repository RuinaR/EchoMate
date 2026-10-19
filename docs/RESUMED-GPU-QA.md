# 메모리 여유 확보 후 GPU·Portable QA 재개 — 2026-10-19

시작 main/HEAD/원격 `263eedc`, clean·fetch 차이0/0. 실제 Discord 로그인·송신·명령 동기화 없이 RTX4070Ti SUPER16GB/Windows에서 검증했다. 운영 설정·토큰·DB·모델·개인 LoRA는 보존한다. **메모리 때문에 중단했던 실행은 재개했지만, 사회적 청자 품질과 다른 Windows 검증이 남아 정식 릴리즈는 BLOCKED다.**

## 로딩과 메모리: 실제 확인 및 수정

공식 Gemma4 no-LoRA의 native NF4 로딩·최소 출력·구조화 수신자 probe가 통과했다. 첫 계측의 backend load25.969초는 그 함수 구간이며 프레임워크 최초 import와 앱 전체 시작 시간을 뜻하지 않는다. 원본 단일 파일22.28GiB를 그대로 사용했다. weight 변경·shard 변환·추가 다운로드는 하지 않았다.

- 첫 전체 로딩 process private commit의 OS peak **31.35GiB**, peak working set **4.81GiB**, CUDA allocator peak allocated **7.72GiB**. 반복 로딩에서는 process peak 약**32.6GiB**도 관측했다. private commit/RAM/GPU 메모리를 같은 지표로 섞지 않는다.
- Transformers5.20.1이 Safetensors를 열기 전 caching allocator를 예열했다. pre-open process private가 약9.03GiB였고, 여기에 일시적인22.28GiB COW 예약이 겹쳤다. **기존 weight+2GiB는 전체 로딩 admission으로 부족했다.** 50ms system counter만으로는 순간 예약을 놓치므로 OS process peak도 사용했다. [기존 원인 감사](LOADER-MEMORY-QA.md).
- 준비 비용은 관측9.03GiB를 올림한10GiB와 기존 margin2GiB를 반영한다. 새 프로세스의 단일 공식 파일 기준 약**34.28GiB commit 여유**를 요구한다. import/processor 이후에는 이미 사용한 process private 증가를 중복 계산하지 않는다. 같은 backend의 재로딩에서도 최초 기준을 유지해 상주 framework/cache의 비용을 다시 요구하지 않는다. 환경별 성공 보장은 아니며 RAM/온도/VRAM 검사는 유지한다.
- 최초 성공 뒤 host 여유가 약22GiB로 줄어 한 실행이 admission에서 차단됐다. GPU 반복 로딩을 하지 않고 사용자가 추가 여유를 확보한 뒤 약36.82GiB에서 재개했다. page file/다른 앱/운영 자료는 변경하지 않았다.

## 해제 후 VRAM 잔류의 별도 원인

생성 후 모델을 해제해도 **8.125MiB cuBLAS workspace**가 allocator의 큰 split segment를 붙들었다. 합성512MiB 블록+작은 행렬 연산에서 reserved512MiB가 남고 workspace 해제 후0이 되는 것을 재현했다. 이는 단순 model=None/empty_cache만으로 사라지지 않았다. PyTorch2.9.1 [공식 구현](https://github.com/pytorch/pytorch/blob/v2.9.1/aten/src/ATen/cuda/CublasHandlePool.cpp#L98)은 workspace를 전역 map에 보관한다.

단일 GPU worker가 종료·배출된 시점에만 synchronize → capability 확인한 `_cuda_clearCublasWorkspaces` → empty_cache를 수행한다. CUDA 초기화 전의 사전 차단에서는 새 CUDA 초기화를 하지 않는다. 일반 응답마다 workspace를 지우거나 환경변수를 바꾸지 않는다. 내부 API이므로 다른 Torch 버전의 동작을 보장하지 않으며 지원 여부를 검사한다. cleanup 실패는 원래 로딩 예외를 보존하고 backend를 안전 비활성화한다.

실제 모델 생성·여러 차례 전환 이후 해제 비교: 이전 PyTorch reserved **7507804160 bytes(약6.99GiB)** → 수정 후 **2097152 bytes(2MiB)**, allocated1024 bytes. 남은 것은 작은 양자화 cache다. 이는 **PyTorch allocator 수치**이며 CUDA driver context 전체가2MiB라는 주장이 아니다. 반복 검사는 제한된 횟수이며 장시간 누수 없음 인증을 뜻하지 않는다.

## 사회적 청자: 완료한 평가와 남은 차단

| 단계 | 결과 | 의미 |
| --- | --- | --- |
| 이전에 봉인한 미사용20, 수정 전 | 19/20, 오개입1·누락0 | 과거 요청 전달을 현재 요청으로 오인 |
| 첫 수정 뒤 새 고정24 | 21/24, 오개입1·누락2 | 새로운 미사용 평가; 이후 개발 문항으로만 사용 |
| 최종 수정 뒤 새 미사용12 | **11/12**, 오개입0·누락1 | 기존 상대의 조건부 우려/반박 누락 |
| 이전44문항 최종 개발 재검 | **40/44**, 오개입1·누락3 | 일반화 최종 점수로 사용하지 않음 |
| 추가 합성 의미 예시 후보 | **REJECTED** | 최소 human 수신자 probe부터 실패; 개발56/미사용8 점수 없음 |

세트 점수를 합쳐 하나의 정확도/개선율로 보고하지 않는다. 다른 사람에 관한 전달·인용과 현재 발언 목적을 분리하도록 의미 지침을 보강했다. 또한 호칭 판단이 간접인용의 동사 어간만 보고 현재 부탁까지 과거 보고로 취급하던 오류를 수정했다. 현재 요청은 deterministic 직접 호출 경로를 유지하고, 명사화된 인용 발언은 의미 판정 후보로 둔다. 전달 표현만으로 무조건 침묵하지 않는다.

추가 GPU 호출을 늘리거나 문항 문자열로 응답을 하드코딩하지 않았다. 마지막 후보는 사전 채택 기준(개발53/56 이상·오개입 증가 없음·별도8 통과)을 적었지만 최소 probe에서 실패했으므로 앱에 넣지 않았다. 미사용8 봉인은 유지한다. 최종 청자 오류는 여전히 릴리즈 차단이다. 동일한 개발 문항을 계속 튜닝해 PASS로 만들지 않는다.

## 캐릭터: 생성 성공과 품질 구분

동일 no-LoRA 모델에서 네 프로필×세 합성 질문을 생성했다. **12/12 전송 mock 완료**, 재생성0, 코드 출력/종료 토큰 검사를 통과했다. 이12/12는 스타일/사실성의 사람 평가 점수가 아니다. 반말/존댓말·감탄·설명 구성 차이는 확인했지만 일부 짧은 인사는 같았다. 모든 성격 슬라이더가 충분한 차이를 만든다고 판정하지 않는다. 기술 설명은 약22~27초가 걸렸고 짧은 인사와 같은 속도 표본으로 비교하지 않는다.

원문·프로필 매핑과 섞은 블라인드 평가지를 로컬에 만들었다. 사람 평가는 **미실시**이며 개인 말투 모델/최적 캐릭터 승격은 없다.

## 전체 응답 파이프라인 및 같은 GPU A/B

입력3종×3회, 각 질문의 워밍업 pair를 제외했다. 같은 model/processor/캐릭터/컨텍스트/greedy decoding/max_new_tokens와 같은 resident GPU를 쓰고 bare/disabled-PEFT 순서를 교차했다. PEFT adapter 전환·동기화는 요청 측정 밖이며 adapter는 merge하지 않았다. 실제 LoRA 스타일 효과와 wrapper 비용 비교는 다르다.

| 지표 | no-LoRA bare, n9 | PEFT wrapper·adapter 비활성, n9 |
| --- | ---: | ---: |
| 수신→mock 송신 완료 p50 | **4.047초** | **4.234초** |
| p90 / p95 | 4.572 / **4.715초** | 4.640 / **4.797초** |
| TTFT 근사 p50 / p95 | .531 / .560초 | .547 / .578초 |
| 생성 전체 tokens/sec p50 | 8.314 | 8.172 |
| peak allocated MiB p95 | 7985.1 | 8025.8 |
| 성공 / 재생성 | 9/9 / 0 | 9/9 / 0 |

출력9쌍은 모두 일치했다. 작은 표본의 기술통계이며 유의한 대규모 속도 개선으로 주장하지 않는다. TTFT는 첫 stopping callback의 wall time으로 엄밀한 GPU timestamp가 아니다. tokens/sec는 prefill을 포함한 generation 전체 평균이다. 실제 Discord 네트워크 지연과 최초 모델 로딩은 제외다.

별도 전체9요청 재검은 초기6/9 → 현재 호출 오류 수정 후**9/9**, p50 4.218/p95 4.865초. text stage p50 4.203/p95 4.846초로 대부분을 차지했다. idle queue p50/p95 0, sending mock p95 .016초, 재생성0. 시계 해상도 아래 stage0은 비용이 문자 그대로 없다는 뜻이 아니다. 이 수치를 청자 분류만 한1~2초 결과와 혼합하지 않는다. A/B는 직접 호출 경로이므로 마지막 의미 지침 변경에 대한 모든 경로의 속도 인증도 아니다.

## 전환·공정 큐·실제 요청 보존

- 두 채널/스레드·세 사용자·네 독립 GPU 요청: 원본 대상 `[100,101,102,103]`, 순서·계산 결과·중복0 통과. 최종 의미 지침에서도 재검했다. 다른 사람을 향한 추가 메시지는 GPU 발언 요청으로 승격하지 않았다.
- 같은 원본 가중치의 다른 로컬 경로를 **실제 reload**하고, 새 로딩 실패를 주입한 뒤 이전 모델을 실제 reload/probe했다. 실패한 모델 ID는 저장되지 않았고 복구 후 계산 응답도 성공했다. 다른 모델 아키텍처의 품질 인증이 아니다.
- 생성 중 두 독립 요청이 존재할 때 모델을 전환했다. 취소 후 재검증·재개를 거쳐 원본901/902에 순서대로 한 번씩 전송했다. `switch_while_busy`와 `pending_targets_preserved` 모두 true. 전체 복구/전환 시나리오105.031초는 한 번의 로딩 시간으로 쓰지 않는다.

## Portable·Windows·검사 범위

번들 Python3.10.11/Torch2.9.1+cu128/Transformers5.20.1/discord.py2.7.1, 시스템 Python 없는 PATH·새 DATA_HOME·실제 기존 HF cache에서 검사했다. **기본 모델 발견1/실제 로딩/숨긴 Tk 로컬 캐릭터 미리보기/합성 첫 설정/DPAPI/프로필 저장/설정 복원/종료**를 통과했다. 미리보기의 관계·기억·알림 생성 없음, Discord 연결false. 설치 검사 자체의 중복 lease와 초기 비동기 속성 조회 오류를 수정한 뒤 v3에서 통과했다. 이전 실패 로그는 보존한다.

사용자 데스크톱 조작·실제 Discord/깨끗한 다른 Windows VM/다른 GPU·드라이버/장시간 운용/일반 사용자 더블클릭 전 과정은 **NOT VERIFIED**다. 격리 PATH와 새 저장소는 다른 OS 검증을 대체하지 않는다. 전체 최종 회귀 **506 OK55.636초**. 새 테스트 fixture의 가변 snapshot 참조 오류가 있었던 중간502 실행은 실패로 남기고 수정 후 전체를 다시 실행했다.

## 산출물과 재현

비공개 원본은 `local_data/resumed-qa-20261019/`. `loader-full.json`, 각 suite manifest/source hash·progress·summary, A/B 응답/trace, lifecycle-final, portable-gpu-v3, 폐기 후보 사유/미사용 seal, 캐릭터 블라인드 원문을 보존한다. Git에 넣지 않는다. 기본 생성·평가 파일이 어떤 소스 후보에서 만들어졌는지는 각 manifest를 따른다. 중간 후보를 전부 최종 코드의 평가로 간주하지 않는다.

개발 검증은 PYTHONPATH=src;tests;tools 후 `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`. GPU 프로토콜은 충분한 자원과 운영 instance lease를 확인한 뒤 `tools/verify_resumed_release_gpu.py --help`, 로딩 계측은 `tools/verify_loader_memory.py --help`를 따른다. 항상 새 output을 사용한다. Portable GPU 검사는 격리 DATA_HOME/운영 GPU 잠금/Discord 강제 차단 하에서만 `-m echomate_bot.distribution_check <비공개output> --gpu`를 사용한다.

최종 패키지/공개 감사와 commit은 DISTRIBUTION-QA의 최신 마감 절을 따른다. 운영 DB 초기화·개인 자료 삭제·자동 모델 승격·정식 릴리즈 파일 공개는 수행하지 않는다.
