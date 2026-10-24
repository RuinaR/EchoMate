# 학습 자원·Unified 호환성·Runtime 진단 누수 — 2026-10-24

시작 main/local/remote `9561e78507ff22992a3d4e6b43fcb56cf6b9ff5d`, clean. 카운터 수정 `72546e4`/부분 저장 실패 정리 `84c47d8`, 연구 도구/원본 합성 자료 `675f517`. DEVELOPMENT / RELEASE BLOCKED. 운영4파일과 최종 평가 소비 장부의 SHA256을 private `local_data/training-stability-20261024/preserved.json`에 봉인했다. 실제 Discord/운영 설정·DB/기존 모델·LoRA 변경·다른 프로그램 조사/입력/화면/프로세스 조작은 하지 않는다.

## 우선순위와 실제 수정

1. 학습 전 정적 자원/라이브러리 계약을 확인하고 안전 기준 미충족 단계는 실행하지 않는다.
2. 이전20분 private 증가를 재현·분해해 코드 결함을 수정한다. 모의 이벤트를 빠르게 돌린 것과 실제 경과 안정성을 구분한다.
3. 소형 Unified CPU/NF4 역전파·체크포인트 복구와 원본 조건부 학습 자료를 준비한다. 학습 API 통과를 품질 개선으로 세지 않는다.
4. 관련/전체 회귀·같은 호스트 Portable 증분/번들·공개 감사/보존을 마감한다. UI 변경은 없으며 과거 GUI 렌더를 재실행했다고 주장하지 않는다.

### 확인된 진단 메모리 누수

`loader_memory.memory_snapshot()`이 매 호출마다 Windows ctypes Structure 3개를 정의하고 POINTER(Structure)를 만들었다. ctypes 전역 포인터 타입 캐시가 그 타입을 보존해 GC 후에도 증가했다. 1000회 반복+종료 조회에서 포인터 타입3003개/private21,262,336 bytes 증가를 재현했다. 같은 함수의 수치 조회 자체가 누수를 만들었으므로 이전 soak의 private 상승을 전부 Runtime 대화/DB 객체 탓으로 단정할 수 없었다.

추론 진단의 `telemetry.process_ram_mib()`도 별도 Counters를 매번 만들어1000조회에서1000타입 증가를 재현했다. 두 실패 회귀를 보존했다. Windows 구조체/WinDLL 함수 바인딩을 잠금 안에서 한 번 초기화하고 샘플은 별도 값 객체만 사용하도록 수정했다. 추론 RAM도 공통 조회의 working-set MiB를 사용하며 조회 실패는None으로 처리한다. 전역 ctypes 캐시를 지우거나 시스템/allocator 설정을 바꾼 것이 아니다. RAM/commit/VRAM/온도 admission 숫자와 실패 시 안전 중단 계약은 유지한다.

수정 후 같은1000조회에서 포인터 캐시/private 증가0 관측. 회귀는 가변적인 OS private 크기 자체를0으로 강제하지 않고 실제200개 동시 조회의 포인터 타입 집합 안정성과 단위/오류 처리를 확인한다. 관련18검사 OK0.106초. 초기 sandbox의 비동기 표적 실행은 멈춰 자체 세션을 중단했으며,90초 faulthandler 한계의 승인된 오프라인 실행에서 통과했다. 다른 프로세스를 종료하지 않았다.

같은 프로세스에서 이전/수정 RAM 진단을200쌍 교대 측정한 p50/p95는이전0.0197/0.0495ms·수정0.1686/0.2943ms였다. 공통 조회의 system commit/전체 RAM 확인까지 사용해 단일 RAM metric은약0.149ms p50 비용이 늘었다. 값의 단위/조회 실패 계약을 지키며 호출당 작은 비용을 명시한다. 이것은 AI E2E 지연/출력 속도 개선 측정이 아니다. 더 중요한 누수 수정 뒤 낮은 가치의 미세 최적화를 반복하지 않는다.

### 추가 확인: 부분 JSON 쓰기의 실패 복구

`settings.atomic_private_json()`은 임시 파일의 write_text가 try/finally 밖에 있어, 일부 bytes를 쓴 뒤 예외가 나면 임시 파일이 남았다. 실제 운영 파일 대신 합성 target에 부분 쓰기 오류를 주입해 재현했다. `84c47d8`은 쓰기부터 기존 정리 구간에 포함하는 최소 수정이다. 기존 target bytes 보존·temp 제거·replace 잠금의5회 재시도/기존 backoff를 확인했다. 예외를 숨기거나 실패를 완료로 표시하지 않는다. OS crash/전원 차단·정리 권한 상실까지 완전 복구를 보장하는 것은 아니다. 관련6검사 OK0.027초, 최초 실패 로그도 보존했다.

공통 저장 helper 변경이 추가돼 최종 전체를 다시 실행했고 **818검사 OK247.043초**, 최신 Portable에 settings까지 공개 소스3개를 반영한 **번들83검사 OK13.133초**다. 이전816/81 결과는 그 버전의 근거로 남긴다. 1시간 메모리 run은 그보다 먼저 시작한 카운터72546e4/도구675f517 버전이며, 새 부분 쓰기 오류 경로는 별도 오류 주입/전체/번들 회귀로 검증했다. 한 run을 모든 최신 코드의 장시간 인증으로 확대하지 않는다.

## 실제12B 정적 학습 예산

[공식 Gemma 가이드](https://developers.googleblog.com/gemma-4-12b-the-developer-guide/), [PEFT NF4 학습 계약](https://huggingface.co/docs/peft/developer_guides/quantization), [Transformers bitsandbytes](https://huggingface.co/docs/transformers/quantization/bitsandbytes)와 설치 소스를 확인했다. 공식 지원은 이 Windows/16GB의 학습 성공 보장이 아니다. torch2.9.1+cu128/Transformers5.20.1/PEFT0.21.2/bitsandbytes0.50.2 그대로이며 새 의존성/모델은 설치하지 않았다.

검증된 분할 복사본의 config/index/Safetensors 헤더만 읽었다. tensor data 로딩/변환·운영 모델 선택 변경은 없다. 677텐서/11,959,730,224 parameters, text48층·hidden3840·vocab262144. q48개/v40개를 실제 헤더에서 선택하며 모든 층에v가 있다고 가정하지 않는다. 텍스트 q/v만 rank4이면2,596,864 trainable/88대상이다. 영상/오디오/embedding은 스타일 어댑터 대상에서 제외한다. PEFT 기본 대상 추정에 의존하지 않고 실제 language_model 경로를 명시한다.

`training_budget.py`는 읽기 전용 계획 도구다. 알려진 projection만NF4로 계산하고 나머지는 보수적으로fp32로 계산한다. NF4 scale 여유4.5bit/parameter, fp32 adapter/gradient/Adam/save20bytes/parameter, checkpoint 입력/연산·logits workspace, allocator/driver1GiB와 안전 여유2GiB를 포함한다. 활성화의 수학적 완전 상한이 아니며, 충분하다는 결과도 실제 단계별 검증 없이 학습 PASS가 되지 않는다.

| 항목 | 계획 수치 |
|---|---|
| 조건 | batch1,64tokens,rank4,gradient checkpointing |
| 준비 후 가중치 |10,370,351,296 bytes|
| 최대fp32 변환의 구형BF16 텐서 중첩 |2,013,265,920 bytes|
| 어댑터/gradient/optimizer/save |51,937,280 bytes|
| backward 계획 workspace |1,719,664,640 bytes|
| 전체 VRAM 계획 reserve |15,604,842,688 bytes ≈14.53GiB|
| 당시 가용 VRAM |13,639,876,608 bytes ≈12.70GiB|

임베딩262144×3840의 BF16→fp32 변환은 현재 PEFT 준비 소스에서 확인했다. 단순히 batch/sequence를 더 줄여도 준비 중 큰 텐서 중첩 자체는 사라지지 않는다. 기존 host RAM/commit 로딩 gate도 확인했지만, **VRAM 계획 미충족으로 실제12B 준비/학습은0회**다. 추론13GiB private 피크를 학습 요구량으로 재사용하지 않았다. 이것은 현재 경로·자원에서의 안전한 보류이며 어떤16GB 환경에서도 학습이 불가능하다는 판정이 아니다.

대안인 CPU embedding offload는 검토만 했다. 설치된4bit quantizer는 혼합 device_map에 명시적인 fp32 CPU-offload 옵션을 요구한다. 공식 문서의 주된 offload 예시는8bit이며, map 허용이NF4 backward 성공을 증명하지 않는다. 임베딩만fp32 약3.75GiB/변환 중 BF16 중첩 약1.875GiB를 추가로 host에 두게 될 수 있어 RAM·commit·PCIe·tied lm_head와 gradient 흐름을 따로 검증해야 한다. 작은 모델/다른 양자화도 기존 Qwen 기본 품질 기각을 뒤집는 근거가 아니므로 운영 교체·무거운 대안 실험은 하지 않았다.

## 초소형 Unified CPU/NF4 실제 호환성

`probe_unified_training.py`는 새 무작위 Unified의 전체 multimodal wrapper를 만들되 텍스트 q/v만 학습한다. 원본12B/운영 LoRA/개인/평가 자료를 읽지 않는다. 하위 socket와 외부 다운로드를 차단하며, CUDA 실험은 기존 InstanceLease·RAM/commit/온도 확인, 한 모델씩·단계별 메모리 기록·180초 한계를 적용했다. 장시간 CPU soak와 GPU 학습은 겹치지 않았다.

첫32차원 CPU/NF4는448 trainable로 저장/복원했지만 NF4 비정렬 fallback 경고가 있었다. 실제 기본 모델의64배수 경로와 다르므로 그것만으로 커널 호환을 확대하지 않았다. 새64차원 조건으로 CPU와CUDA NF4를 순서대로 실행했고896 trainable/텍스트4대상에서 gradient 유한·기본 텐서 불변·checkpoint safetensors 재적용 logits 일치·Adam 상태 복원 후step2를 확인했다. 새 폴더의32/64 결과를 모두 보존했다.

64차원 GPU는 준비→step1→해제→복원step2 약1.750초(프레임워크 import 별도), 단계 allocated 최대17,500,160 bytes/reserved23,068,672 bytes, 해제 지점 allocated1536 bytes였다. OS private high-water3,206,053,888 bytes는 대부분 framework/CUDA 초기화 비용이며12B 학습 피크가 아니다. seed20261024, q/v rank2, bf16 NF4/double quant, eager, CPU한 스레드, 동일8개 합성 정수token만 사용했다. 실제1step 후 안전 경계에서 저장·종료하고 재개한 것이며 CUDA 커널 도중 강제 취소/OS crash 복구를 인증하지 않는다. loss4.09281은 학습 API smoke 수치일 뿐 대화 품질이나 학습 효과가 아니다.

12B 학습 어댑터가 없으므로 **학습 전후 인격/사실성 A/B는 미실행**이다. 소형 무작위 어댑터는 운영에 적용하지 않았고 기존 생성 정책·프로필·권한/기억·GPU Worker는 유지한다. 기존 인격 수렴·거짓 미래 약속·기능 상태 오판은 여전히FAIL이다.

## 원본 조건부 자료·분리·품질 한계

기존1650개는 BST 개발200/표준1130(BST+LoCoMo)/KoED최종320이며 기존 장부의 소비4/미사용316을 확인했다. CC BY4.0/NC 조건과 파생 원천 관계를 보존했다. 공개 평가 원문을 학습/재배포하지 않고 이번에는 새 다운로드도 없다.

`tests/fixtures/conditioned_curriculum.json`은 직접 작성한 MIT 원본 합성 자료다. 4가상캐릭터×6학습 시나리오=24 target, 별도2개 개발 validation 시나리오×4=8 target이다. 가치관/직업 배경/반응 습관을 조건으로 제공한다. 열린 산책 선택·확인되지 않은 퍼즐 공동 기억·알림 ready/미실행·동의/저장 성공 receipt·관찰 없는 인용·불편 표현 중단, validation은 미설정 취향·가상 배경/피곤함을 다룬다. 성공 상태는 실제 gold receipt로 말하고, 기록 부재를 사건 부재로 바꾸지 않으며 모두 같은 거절문만 쓰지 않도록 수작업 작성했다.

이는32개 pilot이지 충분한 장기/다양한 기분·관계 학습 데이터나 독립 최종 평가가 아니다. 같은 저자의 scenario 단위 분리이며 원천 family가 독립인 대규모 벤치마크로 부르지 않는다. 새 validation도 공개 개발 자료이므로 최종316개와 혼동하지 않는다. 자유 자연어 target의 사실성을 코드가 완벽하게 판별했다고 주장하지 않는다.

`conditioned_curriculum.py`는 source group 교차·중복 target·잘못된 본인 receipt/동의·형식/개인 식별 패턴을 거절하며, 캐릭터/상태/user/target을 학습·validation 파일로 분리해 hash를 봉인한다. 학습/운영 자동 연결은 없다. 첫 export는 Windows newline 변환 때문에 메모리 문자열 hash와 실제 파일 bytes가 달랐다. write_bytes로 고치고 실제 bytes hash 회귀를 추가했으며 실패 export와 수정 export를 별도 보존했다. 이 검사는 주석/파일 계약이며 NLP 판별기나 학습 품질 합격 점수가 아니다.

## 할당 출처와 실경과 안정성

120.140초 가속 probe(대기.001초/재시작10초)에서496반복/독립reply992·재시작11·잔류0. tracemalloc5프레임과 자체GC 객체/Runtime weakref를 사용했다. 첫 진단은 일부 Python 타입의 __module__이 문자열이 아닌 경우를 처리하지 못해 실패했고 타입 검사를 고쳐 새 폴더에서 실행했다. 제품 Runtime 실패로 세지 않는다.

수정된 포인터 캐시는24샘플 모두23개, 옛 Runtime 생존0·함수 반환 후 관측한 Runtime weakref0이다. 마지막32 Conversation/DialogueState, Event4/Turn88로 진행 상태의 범위를 확인했다. 보존 trace는2→1102개/약10KB→3,783,609 bytes, tracemalloc 자체 metadata도약5.2→10.4MB 증가했다. 주요 할당 출처는 pathlib intern table/runtime decision·stage/telemetry trace였다. 이 실행의 private38,944,768→103,084,032 bytes는 tracer/스냅샷/가속 workload의 영향을 포함하므로 이전20분과 직접 크기 비교하지 않는다. 잔여 증가를 전부 누수나 전부 allocator 탓으로 단정하지 않는다.

별도의 같은20분/1초 간격/60초 재시작 CPU mock 비교는 tracer 없이 포인터 수·퇴역 Runtime·보존 trace를 관측한다. 최종 결과는 아래에 누적한다. 20분을1시간/8시간/GPU 장기 인증으로 바꾸지 않는다.

수정 후20분은1200.016초/1038반복, 독립reply2076·범위/중복 veto2076·재시작19·errors/잔류 Task0으로 통과했다. 포인터 타입은 전 샘플23개, 관측한 퇴역 Runtime0·반환 후 Runtime weakref0이다. private26,550,272→41,906,176 bytes(약25.3→40.0MiB), 마지막 측정 trace 약7,253,928 bytes였다. 이전26.5→42.4MiB와 단순 비율 개선으로 주장하지 않는다. 새 observer의 deep-size/weakref도 할당에 영향을 주며, 누수 원인 하나가 제거됐어도 진단/allocator 등의 증가를 더 오래 확인해야 한다.

이 결과를 바탕으로 별도 CPU/mock **실경과3600초** run을 시작했다. GPU 실험은 모두 종료했고 중복 모델/학습/추론 부하는 없다. 자체 progress·RAM/commit/포인터/퇴역 객체만 감시하며 불안정하면 이 테스트만 중단한다. 실제 완료 결과는 완료 후 기록한다. 1시간 통과도8시간/실제 Discord/GPU 장시간 운용 PASS가 아니다.

## 마감·재개

최종 전체/번들·20분·Portable·보존/공개 감사·재개 절차는 실제 완료 후 누적한다. 정식 릴리즈는BLOCKED이며 인증된 Discord 조회/Gateway/명령/송신은0회다. 게임/다른 프로그램의 상태·FPS·제재 위험을 인증한 것이 아니며 시스템 집계 자원과 자체 테스트 프로세스만 확인했다.

### 회귀·번들 실행

최신 전체816검사 OK245.663초(exit0), `PYTHONPATH=src;tests;tools`에서 `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`로 실행했다. 새 카운터·자원/자료 계약과 기존 SDK HTTP mock·동의·원본 reply·취소·UI 경계를 포함한다. 긴 async callback 경고는 로그에 보존하고 제품/품질 FAIL과 혼동하지 않는다.

공개 실행 소스2개(loader_memory/telemetry)만 먼저 Portable에 증분 복사해 번들 Python/번들src81검사 OK13.158초(exit0)를 확인했다. 기존65개 기억/예약/카드/명령/SDK mock/UI workflow에 loader_memory16개를 추가한 범위다. 첫 실행은 새 private fixture 디렉터리 생성 누락으로63setup error가 났다. 제품/테스트 조건을 완화하지 않고 동일 검사에 필요한 디렉터리만 만든 뒤 새 로그로 재실행했다. `ECHOMATE_DATA_HOME=<이번private root>/local_data`, `cwd=<이번private root>`, 해당 data 디렉터리를 먼저 생성하고 `PYTHONDONTWRITEBYTECODE=1`로 실행해야 한다. 재현 문서에 이 준비 조건을 남겨 같은 실수를 반복하지 않도록 한다. 초기 bundle.log와수정 bundle-fixed.log를 보존한다.

UI 실행 소스/설계는 바꾸지 않았으므로 새 GUI 렌더/사용자 Desktop 검사는 하지 않았다. 기존 격리 GUI 근거와 이번 이벤트 회귀를 구분한다. 실제12B 추론·학습 품질/새Portable GPU/다른 Windows/1시간·8시간 운용도 이번 작은검사로PASS 처리하지 않는다. 앱에 진단 누수 수정을 반영하려면 사용자가 재시작해야 하며 DB 마이그레이션/설정 변경은 없다. 앱을 대신 종료·재시작하지 않았다.
