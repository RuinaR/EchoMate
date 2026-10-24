# QLoRA Admission 항목 감사·단계 계측 — 2026-10-25

시작 main/local/origin `dbfc2073f7132c540077fffc9207881991782910`, clean. 원격 fetch로 일치를 확인했다. [이전 전체 학습](QLORA-RESUME-QA.md), [공개 자료](PUBLIC-TRAINING-DATA-QA.md), [릴리즈 게이트](RELEASE-CHECKLIST.md)를 기준으로 한다. 앱src·운영 no-LoRA·동의/송신 정책·기존 모델/LoRA는 변경하지 않는다. 실제 Discord 인증/REST/Gateway/명령/송신과 다른 앱/게임의 목록·창·화면·입력·내부/파일/패킷 접근은 하지 않았다.

## 최신 결론 — 준비 검사의 eval/train 불일치 수정, 품질 후보는 기각

초기 집계만으로 Admission을 낮추지 않은 뒤, **준비 backward가 eval 상태라 gradient checkpointing이 실제로 작동하지 않는 결함**을 확인했다. 기존 실학습은 `train_window()`의 `.train()`으로 checkpointing이 동작했다. 준비 검사와 실학습의 실행 조건이 달랐다. 연구 도구에서 내부 전체 layer의 train/non-reentrant checkpoint 활성화를 검사하고, 한정된 opt-in checkpoint-input 예산을 추가했다. 앱src·운영 추론·기본 예산은 변경하지 않았다.

실제12B 전체GPU 경로에서 **64응답/16유효업데이트/105.515초**, step8 저장→step9 재생→최종 저장을 완료했다. 준비 계획12.692780GiB(427token/target45)는 드라이버·allocator1GiB와 **기존 안전2GiB**를 포함한다. GPU allocated/reserved 피크8.814240/8.904297GiB, 단계별 free 최솟값4,923MiB, 최고61°C였다. 이는 이번 구성의 자원 검증이며 대화 품질 개선 판정이 아니다. 앞선 CPU I/O fresh64·warm64 품질 후보는 모두 기각했다. **DEVELOPMENT / RELEASE BLOCKED**, 운영 no-LoRA 유지.

## 초기 감사: allocated 차이만으로 요구량을 낮추지 않는다

기존 사전14.195160GiB와 allocated11.985758GiB를 직접 비교하면 안전 여유와 allocator/드라이버 사용을 빠뜨린다. **reserved는 allocated를 포함**하므로 둘을 더해서도 안 된다. 이전 전체264/399token/cache run의 단계 기록을 `training_profile.audit_report`로 읽기 감사했다.

|서로 다른 측정량|GiB 또는 MiB|
|---|---:|
|사전 요구량, 안전 여유 포함|14.195160GiB|
|이전 PyTorch allocated/reserved 피크|11.985758 / 12.181641GiB|
|reserved 피크 + 기존2GiB|14.181641GiB|
|시작 freeVRAM / 최소 **단계 표본**|15,020 / 2,266MiB|
|시작−최소 free 변화 + 기존2GiB|14.455078GiB|
|사전 − 위 집계 envelope|−266.156067MiB|

reserved+2GiB와 사전값 차이는 약13.844MiB에 불과하다. 한편 집계 free 변화로 만든 envelope는 사전값보다 크다. 집계에는 실행 중 다른 GPU 사용 변화·드라이버 등도 포함되므로 EchoMate 고유 요구량으로 확정하지 않는다. 이 표본은 연속 최소 free도 아니다. **과도한 보수성 때문에 이번 학습이 막혔다고 입증되지 않았으며**, 단일 성공의 allocated만으로 사전 문턱을 내리지 않았다. 이전 cache OFF 준비는 free2,020MiB로 실제 실패했다는 반례도 보존한다.

## 항목·수명주기 감사

기존 공식을 그대로 유지하고 `training_budget.estimate`에 합계가 맞는 `components`와 수명주기 식을 추가했다. 아래 값은 원본264 학습의399token/정답44/rank4에 대한 **추정 항목**이며 개별 텐서 실측으로 둔갑시키지 않는다.

|항목|계획 GiB|범위|
|---|---:|---|
|NF4 가중치·scale allowance|5.710144|linear 4.5bits/parameter 보수식; 실제 double-quant storage의 개별 실측 아님|
|frozen BF16 embedding|1.875000|embedding 한 번; tied head를 별도 full matrix로 더하지 않음|
|기타 floating 가중치|0.197998|FP32 보수 예약|
|LoRA parameter / gradient|각0.009674|rank4/qv|
|Adam moments / adapter save copy|0.019348 / 0.009674|최악 중첩 가정 유지|
|checkpoint activation|2.191772|층×sequence×hidden 경험식; 실측 아님|
|선택 logits workspace|0.171875|전체399가 아닌 정답44위치 사용|
|backward workspace|1.000000|라이브러리 workspace/미측정 오차 예약|
|allocator·driver|1.000000|런타임/캐시/미측정 비용 allowance; 실제 분해 미완료|
|실행 안전 여유|2.000000|유지|

공식은 `max(prepared+upcast_overlap, prepared+adapter_state+backward_planning)+allocator_driver+safety`다. 로딩 upcast와 학습 workspace를 무조건 합산하지 않는 기존 max 구조를 확인했다. frozenBF16은 upcast_overlap=0이다. embedding/기타 floating 및 adapter 항목은 합계가 기존 prepared/adapter_state와 정확히 맞는 회귀를 추가했다. activation/workspace와 allocator 사이 실제 중복, 저장 복사본과 다른 임시 텐서의 비중첩은 **입증하지 못했다**. 아직 측정하지 않은 수명주기를 가정해 항목을 제거하지 않는다.

## 구현과 적용 경계

- `training_profile.py`: 오래된 보고서의 allocated/reserved/free envelope 감사. 모든 결과는 `reusable_admission=false`다. 부정/NaN/bool 카운터와 비어 있는 stage를 거절하고 reserved에 allocated를 이중 합산하지 않는다. 보고서가 성공했다는 사실과 재사용 가능한 Admission 증거를 구분한다.
- `run_persona_pilot.py --phase-profile`: 기본OFF의 연구용 계측. 로딩/양자화 반환 직후, frozenBF16 준비, adapter 초기화, optimizer lazy 초기화, 첫4개 forward/backward, optimizer step, step8 저장/복원, 반복 update/최종 저장을 구분한다. 계측은 CUDA synchronize와 peak counter reset만 사용한다. 이전 피크를 별도로 누적해 기존 recorder의 전체 peak를 잃지 않는다. phase의 시작/끝 기준을 `phase`/`until`로 명시한다. 로더 내부 양자화 텐서 수명 전체를 별도로 계측했다고 주장하지 않는다.
- 첫 window의 live graph 경계에도 기존 free2GiB/RAM3GiB/commit2GiB/온도85°C 미만 검사를 적용한다. 원래 조건을 낮추지 않는다. 오류 때 반쯤 끝난 update를 성공 체크포인트로 저장하지 않으며, 마지막 완성·검증 저장 경로를 `latest_checkpoint`로 남긴다. CUDA 오류 중 강제 저장/재시도는 하지 않는다.
- 기존 상향 전용 `--admission-proof`는 이제 실행 라이브러리 버전도 대조한다. 다른 cache 정책·data/header/shape/library의 실패 증거는 재사용하지 않는다. 성공 보고서 하나를 저렴한 예산으로 자동 승격하는 경로는 만들지 않았다.
- `--cache-hygiene`는 여전히 기본OFF다. 계산 **전** 공개 synchronize/empty_cache, 활성 allocated 불변 검사, 계산 **후** 동일 safety guard를 유지한다. 새 호출 시간 기록을 추가했으나 실제12B의 호출 비용/throughput 영향·동일 부하 반복 비교는 이번에 미검증이다. 운영 추론/Worker에는 적용하지 않는다.

[PyTorch CUDA 메모리 관리](https://docs.pytorch.org/docs/2.9/notes/cuda.html#memory-management)와 [empty_cache](https://docs.pytorch.org/docs/2.9/generated/torch.cuda.memory.empty_cache.html)의 범위를 확인했다. 미사용 캐시 반환은 활성 모델 텐서 절감이 아니며 단편화 개선을 항상 보장하지 않는다. 이번에는 추가 패키지·드라이버·전역 allocator 설정·라이브러리 패치를 도입하지 않았다.

## 초기 실행 — 아래 후속 실험 전의 기록

시작 시스템 집계 free14,123MiB/42°C, RAM가용 약16.77GiB/commit약43.55GiB였다. 초소형 Unified/NF4 모델에서 실제 cache/phase 관측·dropout/accum4·저장/재개를 실행했다. phase 경계18개, active allocation 불변 cache3회, peak allocated17,420,288bytes/reserved23,068,672bytes, 표본 free최소13,971MiB였다. 계측 없는 step과 재개 후 계측 step의 loss/gradient/learning-rate metric·어댑터 가중치가 완전 일치했다. **초소형 API 검증이며12B 피크/품질 검증이 아니다.** CPU에서도 observer 유무의 dropout metric/가중치 완전 일치와 guard 오류 때 optimizer/scheduler 실행0을 검증했다.

동일 원본376/학습264의 export/data/lineage/mask를 실제 runner로 다시 대조했지만 사전 free14,260MiB<필요14,535.844MiB로 `BLOCKED_STATIC_VRAM`, **model_load_attempts0**이었다. 실제12B 추가 학습·단계별 계측·새 체크포인트·학습 전후 GPU A/B는 실행하지 않았다. 새로운 작은 길이 curriculum으로 실패 후보를 재학습하거나 안전 여유를 낮추지 않았다. 이 사전차단은 CUDA OOM이나 학습 실패가 아니다. 차단 보고서는 버전 수집 보강 직전 실행이며 당시 기록하지 않은 버전을 소급 삽입하지 않는다.

## 새 데이터: 조회 상태·주체·시점 편집 초안

기존376/264 train 및 이전32초안을 수정하지 않았다. 별도 MIT 원본 **10원천/40응답, train32/development8**을 개별 작성했다. 기억 미조회(포장 선호), 조회 실패(이동 이유), 성공한 빈 조회(전시 제목), 확인된 기억(회의 전 재촉), 알림 조회 실패(택배), 빈 결과(이사), 실제 항목(공구 반납), 타인 완료 보고 인용을 학습용에 넣었다. 조건부 벽화 관람·미래 발표의 화자 정정은 별도 개발 원천이다. 같은 사실의 네 응답에서 선택권·놀이/비유·추론 기준·책임/경계를 다르게 다뤘다. 기분·관계 일부를 함께 지정했지만 인과적 대조나 장기 대화를 충분히 확보한 것은 아니다.

기존 schema/claim span/operation·scope·owner·consent·근거/target·표면중복·원천 분할 계약을 통과했다. 실제 로컬 tokenizer/template로 train352–399token/정답28–43, 개발375–438/정답31–42를 검증했다. 입력 전체와 마지막 응답 정답만 유지하고 절단/padding/packing은 없다. 초안은 **미학습**이며 기존376에 합치지 않았다. 원문/target/토큰/리포트는 private에만 있다. Codex 편집 검토와 자동 계약은 사람 평가·완전 의미 중복 제거·NLP 사실성 보증이 아니다. 개발438token을399token 학습 예산으로 무조건 덮지 않는다.

기존 독립56/최종 미사용316의 모델 입력은0이다. 최종 장부를 보존한다. 기존 모델의 인격/사실성 실패는 그대로이며 새 어댑터·운영 기본 변경도 없다.

## 초기 체크포인트 — 아래 후속 실험으로 갱신

최종 전체 회귀·Portable·보존·Git 결과는 아래 마감 절에 기록한다. private root `local_data/admission-20261025`에 원래 hash/단계 감사/새 초안·tokenizer export/tiny GPU/실제 preflight/로그/재개 체크포인트를 보존한다. 테스트 소스와 연구 도구만 공개하고 정답·운영 경로·모델·adapter·원문·진단은 커밋하지 않는다.

다음은 충분한 사전 자원이 확보된 별도 실행에서 새 tiny proof와 `--cache-hygiene --phase-profile`로 실제12B의 전체 phase를 계측하는 일이다. 모델 전체 파일 hash·GPU/driver/library/workload/cache 정책 binding과 여러 독립 실행을 갖추기 전에는 실측 예산을 낮춘 Admission 프로필로 사용하지 않는다. 부분 일치/미검증 구성은 기존 정적 예산·실제 단계 guard를 유지한다. 소폭 변경된 데이터의 개발 최대길이도 별도로 확인한다. 데이터 편집과 인격/사실성 공동 개선 신호가 나온 후에만 확대/독립평가를 진행하며, 같은 실패 adapter의 LR/epoch 증가로 대체하지 않는다. **DEVELOPMENT / RELEASE BLOCKED** 유지.

## 후속 원인 분석: checkpoint flag와 실행 상태는 다르다

설치된 Transformers5.20.1의 checkpoint layer는 `.training`이 참일 때만 checkpoint를 수행한다. `from_pretrained`의 eval 상태에서 PEFT wrapper의 겉 `training=True`만 보고 활성화됐다고 간주할 수 없다. CPU 실제 Unified 구조 관측과 tiny NF4 GPU 검사로 재현했다. `training_checkpoint_mode()`는 모든 decoder layer의 train 상태·checkpoint flag·공개 설정으로 지정한 non-reentrant 구현을 확인한다. 라이브러리 파일 monkeypatch는 없다.

실제12B128token/target16에서 train checkpoint ON/OFF의 loss·전체 LoRA gradient **완전 일치, 최대 차이0**를 확인했다. forward 저장 storage 상한은 eval flag-only1,560,085,508bytes, train/no-checkpoint1,603,339,268bytes, train/checkpoint74,334,468bytes였다. 중복 storage를 제외하되 opaque autograd ctx·CUDA workspace·드라이버는 포함하지 않는 진단값이다. 이 숫자를 전체 activation 실측이라고 부르지 않는다. bitsandbytes0.50.2의 MatMul4Bit 소스도 확인했다. backward를 위해 quantized B를 보존하고 dequantized temporary를 사용하며 다른 버전에 일반화하지 않는다.

기존 `layers × sequence × hidden × FP32 × 8` 포괄 activation 추정 대신, 한정된 `checkpoint_train_inputs_v1` 경로만 FP32의 전층 hidden·최대 K/V·RoPE·causal mask 상한을 따로 계산한다. backward workspace1GiB/allocator-driver1GiB/안전2GiB는 유지했다. 원래 NF49/16 scale 허용량·frozen BF16 embedding·선택 logits4배 workspace·adapter/gradient/Adam/save copy도 유지한다. CPU offload와 혼합하지 않으며 rank4/길이≤512/한정 Unified geometry/정확한 라이브러리 버전만 허용한다. **512token 실학습을 검증한 것은 아니다.**

새 옵션은 `--checkpoint-budget --cache-hygiene --phase-profile`로 명시해야 한다. tiny NF4 gradient 증거와 버전 일치가 필요하고 실제128token parity도 사전에 수행한다. 부분 일치·미검증 구성·다른 모델/길이에 이번 reserved 피크를 재사용하지 않는다. 전체 모델 헤더·자료/토크나이저/컴파일러·코드 버전과 실행 설정은 private 보고서에 결합한다. 기존 관측 실패 Admission은 여전히 상향 전용이며 eval 준비 증거를 새 train 준비 경로에 동일 조건인 것처럼 결합하지 않는다.

## 대안: frozen tied embedding/head CPU I/O

기존 allGPU 계획을 유지한 상태에서 별도 CPU I/O 경로도 검증했다. tied BF16 embedding/head1.875GiB를 실제 CPU로 이동하되 원본 가중치를 저장하거나 수정하지 않는다. 입력 embedding의 Gemma scale 보존, decoder device로의 결과 이동, CPU head의 역전파, tied weight·frozen 상태를 확인했다. 공유 GPU 메모리를 전용 VRAM으로 계산하지 않는다. CPU 추가 reserve3.051GiB와 별도 RAM/commit gate를 적용했다.

초기 tiny 구현의 embedding scale 누락은 loss/gradient 불일치로 기각·수정했다. 수정 tiny에서는 GPU/CPU loss와 모든 gradient 차이0, 저장·재개·3token 생성이 일치했다. 실제12B 첫 실행은427token backward를 통과했으나 Transformers가 `self.device`로 position IDs를 이동하는 generation 단계에서 중단했다(40.328초/optimizer0). 원인 재현 뒤 모델 root에 **0개 원소의 frozen decoder-device parameter**를 공개 API로 등록해 primary execution device를 명시했다. 원본 텐서/라이브러리 패치는 없고 연구 자식에서만 적용한다. adapter 저장은 embedding을 포함하지 않는다. 이 경로는 추가 CPU 지연 때문에 운영에 적용하지 않는다.

## 데이터와 두 품질 pilot

신규40 원본 MIT 응답에 실제 저장 영수증·동의 철회2원천8응답을 더하고, 이전 미학습32 초안을 합쳐 **80응답/16원천가족/20상황, train64/dev16**을 구성했다. 네 캐릭터20개씩이며 같은 상황의 캐릭터 변형은 같은 분할이다. train274–427/target28–45, dev314–438/target31–42. 마지막 assistant 응답만 loss에 넣고 문맥/system/user/이전assistant는 -100으로 마스킹했다. 절단·padding·packing은 없다. 동일 입력의 상태 대조2쌍은 같은 가족에 유지하고 cross-split 표면중복 경고0을 확인했다. 기존376은 변경하지 않았다. 자동 계약/편집 검토는 자연스러움·완전 의미 중복·NLP 사실성 보증이 아니다.

기분·관계·후속 대화와 조회 미실행/실패/빈 성공/실제 항목/실제 저장/철회를 넣었지만 충분한 장기 대화나 인과적 기분 효과를 입증하지 못한다. 수량을 맞추기 위한 대량 변형은 하지 않았다. 새 원본은 MIT이며 warm 초기화의 과거264에는 기존 MIT·CC BY 원천이 포함돼 해당 출처 이력을 유지한다. 원문/정답/adapter는 공개하지 않는다. 독립56·최종316의 **모델 입력0**, 소비장부 보존.

두 후보 모두 rank4/alpha8/dropout0.05, text q/v88모듈·2,596,864학습파라미터, BF16/NF4/AdamW1e-4, batch1/accum4/clip1, cosine/warmup5%, 1epoch·16유효step·2,330정답token이다. step9 재생을 포함하면17물리update다. LR 탐색은 반복하지 않았다. fresh는 새 adapter, warm은 기존264 adapter 가중치만 초기화하고 새 optimizer/scheduler를 사용했다.

|CPU I/O 실제 pilot|fresh64|warm64|
|---|---:|---:|
|총 경과 초|946.985|974.297|
|동일16개 dev baseline loss|4.595216|4.595216|
|후보 dev loss|3.973841|2.340865|
|GPU allocated/reserved 피크 GiB|10.446432 / 10.652344|10.446432 / 10.652344|
|own private 피크 GiB|15.942314|15.959684|
|최소 RAM/commit 여유 GiB|9.810333 / 27.048126|9.954914 / 27.157146|
|단계 free최소 MiB / 최고°C|3,148 / 65|3,144 / 65|
|저장·재개 metric/adapterweights|완전 일치|완전 일치|
|채택|기각|기각|

fresh는16입력×no-LoRA/기존264/새64=48생성, warm은 여기에 이미 소비된 reminder 조회실패4개를 추가한20×3=60생성이다. 새로운 개발 자료를 독립 평가로 부르지 않는다. fresh는 일반 조언 수렴·분석형2개 불완결, warm은 조언 요청으로 전환해도 해결책을 고르지 말라고 하거나 일반적인 할 일 하나로 수렴했다. 조회실패 회귀에서 warm은1개 올바른 상태 설명/2개 근거 없는 비어있지 않음 단정/1개 출력채널 차단이었다. 조건부 계획 응답의 미래 기록 의사도 실행 영수증 없는 약속 위험으로 기록했다. 이를 완료 저장 주장과 혼동하지 않는다. **loss 감소로 인격·사실성 동시 개선을 인증하지 않고 두 후보를 기각했다.**

fresh의 p50/p95초는 baseline20.766/30.187, 이전2648.711/10.321, 새6419.016/30.172였다. warm20개에서는 baseline22.516/30.125, 이전2649.047/10.550, warm후보9.148/12.513이었다. CPU head와 출력 길이·30초 제한·순서/일부 CPU회귀 동시부하가 섞여 운영 속도 개선으로 해석하지 않는다. warm은 선택logits1을 모든 arm에 적용했고 TTFT약4초가 남았다. fresh와 warm의 kernel 설정 차이도 기록했다. 차단/불완결 출력은 유효한 대화 응답으로 세지 않는다.

## 전체GPU 자원 재검증 — 품질 시험과 분리

correct train checkpointing·새 정적 예산·cache hygiene만 사용하고 CPU I/O·warm·품질 생성을 제외한 별도 실행이다. 시작free14,336MiB/40°C, RAM가용16.746GiB. 실제64/16step·105.515초, step8저장·복원→step9 dropout/RNG/optimizer/scheduler 재생 metric·가중치 완전 일치, 최종 저장을 통과했다. 순차 단일모델이며 기본 가중치 version/sentinel도 유지했다.

|측정|결과|
|---|---:|
|427token/target45 기존 포괄계획 → 명시 checkpoint-input 계획|14.352875 → 12.692780GiB|
|GPU allocated / reserved 피크|8.814240 / 8.904297GiB|
|own private / working set OS 피크|13.033112 / 4.838154GiB|
|표본 최소 RAM / commit 가용|11.910854 / 31.771400GiB|
|단계별 free 최솟값 / 최고온도|4,923MiB / 61°C|
|16유효업데이트 첫/마지막 window loss|4.513750 / 4.514903|

free/온도는 단계 표본이고 continuous worst-case 보장이 아니다. recorder0.2초 표본과 PyTorch interval peak도 드라이버 전체 피크와 동일하지 않다. 로딩/양자화 반환/준비/첫forward/backward/optimizer/저장/복원/반복단계의 allocated/reserved/free·RAM/commit은 private phase report에 보존했다. 다른 호스트·512이상·다른 모듈/버전의 요구량으로 일반화하지 않는다. 이 adapter는 **RESOURCE_TRAINING_COMPLETE_NOT_QUALITY**로 표시하며 blind report 도구도 품질 완료로 받지 않는다. 개발 loss/독립/품질 생성0, 운영 적용0이다.


### 단계 실측: 전체GPU resource run

피크는 직전 stage부터 해당 경계까지의 PyTorch interval peak, free는 해당 경계의 시스템 전체 표본이다. 별개 측정값을 더하지 않는다. 전체 피크는 학습427보다 **128token checkpoint ON/OFF 비교**에서 발생했다.

|단계|allocated/reserved interval peak GiB|경계 free MiB|
|---|---:|---:|
|`loaded_quantized_before_prepare`|7.2087 / 7.2793|6666|
|`loaded_single_base`|7.1520 / 7.2793|6663|
|`smoke_adapter_initialized`|7.1617 / 7.2891|6652|
|`checkpoint_gradient_comparison128`|8.8142 / 8.9043|4923|
|`backward_length_128`|7.4273 / 8.9043|6194|
|`backward_length_256`|7.5198 / 7.6719|6199|
|`backward_length_427`|7.6387 / 7.8145|6040|
|`optimizer_initialized_lazy_state`|7.2242 / 7.8145|6578|
|`lr-0.0001_first_forward_1`|7.4629 / 7.5488|6312|
|`lr-0.0001_first_backward_1`|7.5887 / 7.6738|6192|
|`lr-0.0001_first_optimizer_step`|7.2685 / 7.8047|6052|
|`checkpoint_saved_step8`|7.2438 / 7.8086|6047|
|`checkpoint_restored_step8`|7.2435 / 7.8066|6560|
|`checkpoint_saved_final`|7.2438 / 7.8066|6049|

계산 전 cache21회 총0.062초, 활성 allocated 불변을 확인했다. 이는 이번 호출비용이며 대조군 동일부하 throughput 비교나 단편화 해결 일반 보장은 아니다. cache 정책은 연구용 명시 옵션이며 운영 추론에는 적용하지 않는다.

## 마감과 다음 우선순위

최종 회귀·Portable·보존·Git 결과는 아래 마감 기록에 연결한다. 더 이상의 동일64 학습률/epoch 반복은 하지 않는다. 다음에는 조회실패가 빈/비어있지 않음 어느 쪽도 뜻하지 않는다는 상태 대비, 요청 변경을 따르는 후속 전략, 캐릭터별 가치 판단을 충분히 담은 새로운 원천 자료를 보강하고 검증한 뒤 작은 pilot으로 확인한다. CPU I/O는 진단/대안으로 보존하고, 연구 학습은 검증된 train checkpoint 전체GPU 경로를 우선한다. 새 품질 후보에서 공동 개선 신호가 나오기 전에는 독립56/최종316을 소비하지 않는다.

실제 Runtime→SDK mock의 **새 adapter GPU 통합**, 새로운 GUI/Portable GPU/다른 Windows/2시간·8시간 soak/실제 Discord는 이번에 실행하지 않았으므로 NOT VERIFIED다. 기존 CPU/mock 회귀와 이전 실제 Runtime 근거를 별도로 유지한다. 인격 수렴·거짓 기억/기능 약속·사회적 판단·실제 `/동의` 접근 등 필수 차단 사항은 남아 있으며 RELEASE BLOCKED다.

## 최종 회귀·공개 파일·보존 기록

시작 `dbfc207` → 1차 연구 `6a2015c` → checkpoint/CPU I/O 연구 **`84ff0f3`**. 최종 문서 commit은 이 문서를 포함한 main 후속 commit으로 식별한다. 전체 **913개 OK248.654초**(private `full-checkpoint-final.log`), 이후 cache/phase 누락2개 사전거절(model load0)과 geometry4개 표적검사 OK10.551초를 확인했다. 전체 회귀 시작 뒤 마지막 변경은 cache/phase 필수 조건을 강화한 경계와 docstring뿐이다. 해당 조건을 별도 사전거절로 검증했으며 실제12B run은 이미 둘 다 활성화한 동일 실행 조건이었다. 이전899/905/908 통과는 중간 단계 근거로만 보존했다.

Windows 제한 실행에서는 asyncio loopback socketpair 대기와 원자적 checkpoint rename WinError5가 발생했다. 자체 중단된 테스트만 종료하고, 외부 연결을 막은 정상 로컬 권한에서 동일 기능을 다시 검증했다. 성공 검사만 남기거나 원자적 저장 계약을 약화하지 않았다. 전체 회귀는 localhost loopback 외 socket connect/DNS를 거절한 wrapper로 실행했다. 실제 Discord 인증/조회/Gateway/등록/송신0이다.

운영 설정/bootstrap/두DB/최종 소비장부 **5개 SHA256 동일**, 원본 모델12shard 전체 SHA256 동일, tokenizer/config4파일·이전264 adapter2파일·기존376자료 해시 동일을 확인했다. 새 자료/체크포인트/생성/진단/HTML은 private에만 보존한다. staged 파일명·전체 내용/diff·민감정보 패턴을 감사하고 명시된 코드/합성테스트/비식별문서만 일반 main push한다. 모델·adapter·원문·실제ID·개인 경로는 전송하지 않는다.

Portable은 앱src 변경 없이 공개 docs/README만 증분 반영한다. 공개src/docs·README/기본프로필 **174쌍**, manifest **21,576개 파일**의 크기/전체SHA256/금지파일 경계를 검사한다(private `portable-final.json`). 기존 번들83개 검사는 동일 앱src의 이전 근거로 유지하고 이번 재실행으로 표시하지 않는다. 신규 도구/자료/adapter는 번들에 넣지 않는다. 새로운 GUI·실제 Portable GPU·다른 깨끗한 Windows·2/8시간 안정성·실제 Discord는 NOT VERIFIED다.

재개는 `AI-HANDOFF` 최신 절과 private `checkpoint.json`의 자료/실행 source hash·기각 사유·재개 항목을 먼저 확인한다. 이미 성공한 자원-only64 학습을 이유 없이 반복하지 않는다. 새 원천 데이터의 상태 대비와 행동 정답을 감사·export한 후에만 **새로운 출력 폴더**, 동일 검증 환경의 `--checkpoint-budget --cache-hygiene --phase-profile`로 작은 품질 pilot을 준비한다. 반복 직전 aggregate RAM/commit/VRAM/온도와 원래 guard를 재검사한다. no-LoRA와 이전 후보의 같은 입력 비교에서 공동 개선 신호가 없으면 독립/최종 자료를 소비하지 않는다. 실제 Discord 권한은 별도 승인 단계로 남긴다.
