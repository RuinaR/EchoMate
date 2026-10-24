# 실제12B 학습 가능성·진단 보존 대조 — 2026-10-24

시작 main/local/remote `f2436756c76d46df50cc503f73aaa9b710f89226`, clean. 실행 앱 소스·운영 모델/설정/DB는 유지하고 오프라인 연구 도구만 추가했다. 현재 **DEVELOPMENT / RELEASE BLOCKED**. 이전 [학습·안정화 QA](TRAINING-STABILITY-QA.md)의 기본 준비 경로 기각과1시간 결과는 해당 버전 근거로 보존한다.

## 목표와 채택 경계

1. FP32 embedding 준비 비용을 줄일 수 있는 별도 recipe를 작은 모델에서 먼저 검증한다.
2. 자원 예산을 지킨 실제12B backward/save/resume가 가능할 때만 제한 학습한다.
3. 새 개발 질문의 인격·사실성이 함께 개선되지 않으면 어댑터는 기각한다.
4. 진단 보존/측정 도구의 영향을 분리한 뒤 실경과2시간 CPU/mock을 확인한다.8시간·실제 GPU 장기·실서버와 구분한다.

실제 Discord 인증/조회/Gateway/명령/송신은0회다. 게임/다른 앱의 창·화면·입력·프로세스 목록/내부/파일/패킷에 접근하지 않는다. 시스템 집계 자원과 자체 테스트만 읽으며 게임 FPS/제재 가능성을 인증하지 않는다. 운영4파일+기존 소비 장부5개의 시작 SHA256은 private `local_data/training-feasibility-v2-20261024/preserved.json`에 봉인했다.

## 확인한 병목과 선택

[PEFT quantization](https://huggingface.co/docs/peft/developer_guides/quantization)은 prepare_model_for_kbit_training을 권장한다. 설치 PEFT0.21.2의 함수는 모든 비양자화 BF16/F16 parameter를 FP32로 바꾼다. 기존12B embedding262144×3840의 저장만1.875→3.75GiB로 늘고, 변환 순간 기존BF16 약1.875GiB도 겹친다. tied lm_head를 독립적인 두 가중치로 중복 계산하지 않는다. 표준 helper를 고치거나 라이브러리를 monkeypatch하지 않았다.

별도 실험 `qlora_recipe.prepare_frozen_bf16`는 공개 API로 base를 freeze하고 BF16 저장·기존 Gemma norm의 내부FP32 연산·tied head를 유지한다. non-reentrant gradient checkpointing과 명시적인 use_cache=False를 사용한다. LoRA는 text q48/v40·rank4/alpha8/dropout0·2,596,864 trainable로 FP32다. 이것은 표준 helper와 수치적으로 같은 경로라는 주장이 아니며 앱의 기본 로더/LoRA 지원 계약으로 승격하지 않는다.

[Gemma4 forward 계약](https://huggingface.co/docs/transformers/model_doc/gemma4)과 설치 Unified의 logits_to_keep를 사용해 **다음 토큰 label이 -100이 아닌 위치**만 logits로 만든다. 입력/문맥/정답은 자르지 않는다. sliced logits에 원래 labels를 그대로 주면 위치가 틀리므로 직접 FP32 cross entropy를 계산한다. 작은 CPU 모델에서 중간 ignore label도 포함한 full loss/모든 parameter gradient가 일치했다. 학습 target mask는 기존 실제 template 경계 검사도 통과한다.

| 계획 | 준비 가중치 | 변환 중첩 | 전체 VRAM reserve |
|---|---:|---:|---:|
| 기존FP32/64tokens/full logits |9.66GiB|1.875GiB|14.53GiB|
| frozenBF16/64tokens/16 supervised positions |7.684GiB|0|12.147GiB|
| frozenBF16/128tokens/32 positions |7.684GiB|0|12.561GiB|
| frozenBF16/1800tokens/48 positions |7.684GiB|0|21.808GiB|

같은 allocator/driver1GiB+안전2GiB·보수적인 checkpoint/backward reserve를 유지했다. 이 수치는 계획이며 완전한 activation 상한이나 GPU peak 측정값이 아니다. 당시 실제 가용 VRAM은 약13.4GiB였고 단계별 RAM≥3GiB/commit≥2GiB/VRAM≥2GiB 및 기존 온도/admission/단일 lease를 확인했다. batch1에서 accumulation·optimizer offload·rank 축소로 큰 embedding/activation 비용이 없어지는 것은 아니다. rank4 adapter/gradient/Adam/save 전체 계획은약49.5MiB라 optimizer만 옮기는 이득은 작다.

CPU embedding/head offload는 이번에는 실행하지 않았다. [Accelerate big model inference](https://huggingface.co/docs/accelerate/concept_guides/big_model_inference)는 해당 자동 offload가 학습 지원이 아님을 명시한다. 공개 inference device_map 허용을 backward 지원으로 해석하지 않는다. 이 경로는 host FP32 embedding·중간 복사/PCIe·tied head/autograd를 따로 검증해야 한다. 단순 offload를 강행하는 대신 한 GPU frozenBF16 경로부터 실제 검증했다. 새로운 패키지·모델·시스템 설정은 설치/변경하지 않았다.

## 실제 단계별 검증

- 초소형 전체 Unified/NF4:896 trainable, BF16 embedding/tied head·유한 gradient·기본 tensor 불변·안전 optimizer 경계 저장·해제/재로딩·Adam step2·logits roundtrip PASS. 실제12B 품질 근거가 아니다.
- 실제677텐서 분할12B:64token·16 supervised positions의 backward/Adam step1·새 private checkpoint·해제/재로딩·Adam step2 PASS.62.422초. 학습 숫자 token smoke로 대화 품질을 측정하지 않는다.
- 새 확장 조건의 같은12B:128token backward PASS.256token은 현재 자원 여유+보수적 계획 gate가 맞지 않아 **로딩된 상태에서도 실행하지 않았다**. 같은64token을 근거 없이 반복한 것이 아니라 저장/재개 뒤 길이 확장 경로를 별도 프로세스에서 확인한 것이다.
- 실제12B 짧은 조건부 학습:새16train/8개발 검증·최대94tokens·최대target25tokens, 예산은128/32로 봉인. AdamW lr0.0001·두 epoch 총32step,16step 후 저장/모델 해제·재로딩/Adam 상태 재개, 최종 private adapter 저장 PASS.225.125초. 긴 Runtime 입력과 동등하지 않다.

실제12B의 base 복제는 하지 않고 모든 frozen parameter version counter와 각 tensor의 제한된 sentinel이 학습 첫 epoch에서 불변임을 확인했다. tiny에서는 전체 frozen tensor를 대조했다. 실제 원본 파일은 읽기 전용 from_pretrained로만 사용하며 기본 모델 저장/덮어쓰기/운영 선택 변경이 없다. sentinel 검사를 전체 가중치 암호학적 검증으로 확대하지 않는다. CUDA 커널 도중 강제 중단/OS crash 회복은 NOT VERIFIED다.

| 실제12B run | 자체 private peak(OS) | 자체 working-set peak(OS) | GPU allocated/reserved 관측최대 | 단계 최대온도 |
|---|---:|---:|---:|---:|
|64token backward/resume|14.013GiB|5.513GiB|7.329/7.461GiB|41°C|
|길이 확장128/256 gate|14.012GiB|5.510GiB|7.339/7.539GiB|43°C|
|32step compact 학습/A-B|14.344GiB|5.825GiB|7.357/7.533GiB|47°C|

GPU 수치는100ms 샘플의 관측최대이며 샘플 사이의 모든 순간 피크를 보장하지 않는다.128token 별도 reset_peak에서 allocated7,938,173,440bytes를 확인했다. compact의 단계별 최소 host 가용RAM8.083GiB/commit13.993GiB·최소 전체 가용VRAM5859MiB였으며 안전 중단은 없었다. 자체 private/working set/전체 system commit/GPU VRAM을 혼동하지 않는다. 전체 system commit 관측최대58.373GiB는 다른 사용자 작업을 포함하며 EchoMate 단독 비용이 아니다. 모델은 순차 로딩했으며 GPU 실험이 끝난 뒤2시간 CPU 운용을 시작했다.

## 원본 자료·품질 A/B: 학습 가능, 후보 기각

기존52train/8개발 validation·1650공개 평가·최종 미사용316개는 보존했다. 별도 `compact_training.json`은 직접 작성한 MIT 원본16train/8개발 validation·4캐릭터·6원천 그룹이다. 새 자료와 합쳐 관리상68train/16개발 validation이지만 **두 자료의 입력 형식/메모리 요구가 달라 하나로 학습했다고 주장하지 않는다**. 기존1800token 자료는 학습하지 않았다. compact는 핵심 반응 조건과 현재 발언/명시적 근거만 담은 축소 실험이며 전체 카드/기분/관계/Lorebook/Runtime을 대표하지 않는다. 예산 초과는 거절하고 자르지 않는다. 개인정보/실제 Discord 대화·유료/외부 API·평가 원문 재사용은 없다.

train은 노력/실패·정직성·확인되지 않은 공동 등산·전화 미지원, 별도 개발 질문은 초대 거절/거짓말·조회 실패/예약 미확인이다.24개 전체를 tokenizer/마스크 검사한 뒤16개만 두 epoch 학습했다.8개 개발 사례는 이번 비교에서 소비됐으며 미사용 최종 평가로 재분류하지 않는다.316개 소비0이다.

같은 모델/캐릭터 조건·greedy/max_new_tokens96에서 before8/after8 실제 GPU 응답을 생성했다. loss7.0730→2.8190은 품질 점수가 아니다. 명시적 근거 검토에서 조회 실패를 빈 데이터로 승격하거나, 확인되지 않은 과거 약속/미이행/확인 실행을 단정한 경계 위반이 해당4개에서 **baseline3/4·후보3/4**였다. 자동 NLP 판별기/AI 평가자가 아니라 고정된 상태와 원문을 대조한 엔지니어링 주석이며 일반 오류율이 아니다. 초기3/4 screen의 baseline 직설형은 사용자 주장 수용과 확인된 과거 약속의 단정이 모호해, 세부 재검토에서는 baseline 확정2/4+모호1/4·후보 확정3/4로 구분했다. 인용/수용을 무조건 사실 확인으로 세지 않으며 어느 해석에서도 후보 기각은 같다. 수치만으로 자연어 판별 신뢰도를 인증하지 않는다. 인격도 일반 질문으로 수렴하거나 상태 라벨을 따라 쓰고 thought marker가 노출되는 문제가 남았다. **동시 개선 근거 미충족으로 후보 기각**, 운영 생성/모델/프로필/권한/송신 경로에 적용하지 않았다. adapter와 raw 전후 출력은 private에 보존한다.

|원시 generate 지표(n=8)|baseline|후보|
|---|---:|---:|
|원시 생성 p50/p95|13.859/16.780초|2.446/4.750초|
|TTFT p50/p95|0.172/0.645초|0.172/0.207초|
|출력 token p50/p95|96/96|17.5/33.9|
|96token 상한 도달|8/8|0/8|

출력 길이가 달라 throughput/동등한 응답 지연 개선으로 주장하지 않는다. baseline은 모두 출력 상한에 닿아 완결성 비교도 제한된다. 더 많은 token을 주면 품질이 해결된다는 근거도 없다. 이 후보를 같은 개발 질문에 계속 맞추지 않고, 긴 입력의 안전한 예산과 더 충분한 원천 분리 행동/근거 자료를 다음 연구 조건으로 남긴다. AI blind 점수나 사람 만족도 PASS는 없다.

## 메모리 원인 분리와 운용 체크포인트

기존 Runtime의 trace1000/diagnostics200/job100/latency100 보존 한계는 유지한다. 임시 soak 도구는 샘플 전체를 list에 계속 보관하던 것을 **RAM 최근256개+전체 private samples.jsonl**로 바꿨다. 이는 측정 도구의 지속 할당 요인을 제거한 것이며 제품 Runtime 누수 수정으로 세지 않는다. sample 수·stream 수·실패/취소·최종 판정을 회귀로 확인했다. 진단 보존 해제 군은 trace/diagnostic 결과를 각 반복 뒤 비우는 것으로 계산·권한/동의 검사를 제거하지 않는다.

첫240회 탐색은 시간 기반 재시작이라 두 군의 재시작 수가 달랐다. 이를 보편적인 인과 결과로 채택하지 않고, 반복60회마다 재시작해 **240회/4재시작·모든 사건 count 동일**인 대조를 추가했다. 보존 ON private25.21→31.21MiB·마지막 trace1,719,162bytes, OFF25.32→28.53MiB·trace10,373bytes였다. 양쪽 포인터 타입23·반환 후 Runtime 참조0. 진단 보존이 관측 증가 일부에 영향을 주는 근거이며 남은 차이를 전부 누수/allocator로 단정하지 않는다.

별도 tracer 탐색에서는 private 증가와 tracer metadata 약5~6MiB가 추가됐다. net 할당 상위에 lazy import와 pathlib intern table약1.25MiB가 있었다. tracer 실행 시간/재시작이 다른 초기 결과와 실제2시간의 크기를 직접 비교하지 않는다. 원문 allocation 경로는 private에만 저장한다.

최초 `6fce56e`의 실경과7200초 CPU/mock ON/OFF 두 run은 아래 예약 quota fixture 문제로 약73분에서 실패 종료했다. 수정 도구의 새7200초 run으로 다시 검증하며, 완료 전 PASS로 쓰지 않는다. GPU 작업은 모두 종료했다. 각기 다른 임시 설정/SQLite·모의 transport이며 사용자 Desktop/운영 DB/Discord와 분리한다.5초 전후 샘플에서 자체private>256MiB/전체RAM<3GiB/commit<2GiB면 그 자체 검사만 실패 종료한다. `checkpoint.json`과 각 progress/stream을 확인하며 완료 전 PASS로 쓰지 않는다.2시간도8시간/GPU 장기/실서버 인증이 아니다.

## 현재 회귀·재개

`6fce56e` 전체829검사 OK276.079초, 이후 고정 반복 재시작 대조 경로는 관련6검사 OK5.493초다. 변경은 연구 tools/tests이며 앱 실행src는 f243675 그대로다. 이전 번들83검사는 해당 동일 실행 소스 근거로 보존하고 불필요하게 반복하지 않는다. 최신 코드/문서·Portable·보존/공개 감사·최종 Git 마감과2시간 완료 결과는 아래에 누적한다.

다음 우선순위는1) 2시간 후반의 stream/객체·증가율 분석,2) 긴 캐릭터 입력의 activation/host 예산을 안전하게 입증하는 추가 근거,3) 인격과 근거 상태를 함께 학습할 충분한 새 원천 자료다. 불충분한 짧은 학습의 loss만 낮추거나 기존316개로 튜닝하지 않는다. 실제 Discord `/동의` 비표시·인격 수렴·일반 허위 주장·사회적 판단·다른 Windows/GPU 장기는 계속 릴리즈 차단이다.

## 2시간 중 검토한 후속 후보 — 아직GPU 미검증

짧은 compact 후보를 같은 질문에 맞춰 반복 학습하는 대신, 원래52/8의 최대1800token 입력을 보존하는 **마지막4개 층 q/v LoRA**를 검토했다. 실제 헤더상7대상/214,016 trainable이며 앞44층이 autograd graph를 보존하지 않을 때만 계획 reserve 약12.700GiB다. 기본 all48 계획21.808GiB를 임의로 낮춘 것이 아니라, gradient 깊이를 바꾸는 별도 후보다. 숫자만으로 실행 허가하지 않는다.

첫 CPU 증명은 prefix 출력에 requires_grad=True가 붙어 실패했다. 설치 Transformers5.20.1의 gradient_checkpointing_enable이 embedding-output gradient hook을 자동으로 붙이는 원인이었다. non-reentrant·frozen embedding·suffix LoRA만 학습한다는 제한에서 공개 disable_input_require_grads API를 사용한 뒤 CPU prefix=False/suffix=True·유한 nonzero gradient를 확인했다. 라이브러리 forward를 바꾸거나 checkpoint 구현을 패치하지 않는다. 실패 로그와 수정 로그를 별도 보존했다.

새 도구는 실제 작은NF4 prefix proof가 없으면 전체12B suffix 실행을 거절하고, 실제12B에서도 짧은 forward/backward로 prefix=False/suffix=True를 먼저 확인한 뒤 긴 입력을 허용한다. 재개 후에도 다시 확인한다. full export의 source/토크나이저/파일 hash·원천/ID 중복·학습/검증 분리·prompt label -100·최대1800/target48을 검사한다. 2시간CPU run이 끝나기 전 새GPU 실험을 시작하지 않는다. tinyNF4/실제12B 자원·prefix proof가 통과하는 경우에만 다음 단계로 진행하며 아직 학습/품질 PASS가 아니다.

### 추가 GC·executor 대조

고정240회/4재시작의 tracer 대조는 retained69.687초·released62.609초였다. 동일 count여도 tracer 비용/처리 시간이 달라 시간당 메모리나 throughput을 같은 지표로 비교하지 않는다. 마지막 tracer metadata는약5.86/5.29MiB, post-close 추가GC는170/169객체를 회수했고 관측된 프로젝트 객체는 SilenceReason/Kind enum 상수뿐이었다. Runtime/DialogueState/Event/Turn 참조 누적이 남았다는 근거는 없었다. lazy module 수269→400이 양쪽 동일해 초기 import/cache 증가도 포함됨을 확인했다. tracer 종료 뒤 private 변화는 JSON/snapshot/allocator 관측 비용까지 섞여 한 숫자로 누수/해결을 확정하지 않는다.

별도2.5초 CPU/mock의 thread 수는 loop전1·내부종료4·asyncio.run 반환후1이다. 기본 executor의 loop 수명과 영구 thread 누수를 구분하는 좁은 근거이며2시간/GPU 종료 회수를 대신하지 않는다. 모든 과정은 자체 Python 프로세스만 관찰했다.

### 평가 계약 오류의 사후 교정 — GPU 재생성 아님

후속 실제 입력/출력 경로 감사에서 앱은 ended 확인 뒤 특수 토큰을 보존한 decode와 inference.visible을 쓰지만 초기 연구 evaluate는 skip_special_tokens=True였음을 확인했다. 그래서 위 compact raw text/속도 표를 실제 Runtime의 유효 응답·실제 송신 품질로 세지 않는다. 저장된16개 token ID를 모델 재로딩 없이 실제 visible 계약으로 재분류하면 baseline8/8은 미완료이고, 후보는7/8 visible-format·1/8 채널 차단이다. 채널 표식이 나온 것은 차단 전 원시 모델 출력이며 실제 Discord 노출이 아니다. 후보의 유효 형식인 예약4개에는 확인되지 않은 잊음/조회 약속·조회 실패→빈 데이터·미확인→미이행의 확정 위반3개가 남는다. baseline의 유효 사실성 분모는0이므로 raw2/4+모호1/4를 유효 응답 오류율로 비교하지 않는다. 이 검토는 Codex의 근거 대조이며 사람 평가/검증된 NLP 판별 정확도 인증이 아니다.

평가 도구는 실제 앱과 같은 EOS/end-of-turn·미완료/visible-channel 차단으로 수정하고, 채널 토큰을 지워 허용하지 못하도록 회귀를 추가했다. visible-format 통과가 권한/동의/송신 자격의 통과라는 뜻은 아니다. 후속 full suffix 비교는 별도 사전 조건 max_new_tokens128/max_time45/greedy로 양쪽을 맞추고, raw/visible 상태를 모두 private에 남긴다. 이는 앱 text 경로의768token 기본 budget/실제 Runtime 전체와 같은 시험이 아니다. 초기96token 결과를 새 조건의 성공으로 소급하지 않고, 기각된 compact 후보를 단지 점수 향상을 위해 재학습/재생성하지 않는다.

진단 wrapper도 result.passed=False를 파일에 남기고 exit0으로 끝낼 수 있어 실패 증거 저장 뒤 오류 종료하도록 수정했다. mock 미완료 결과를 주입한 양쪽 wrapper 회귀로 확인했다. 이것은 검증 도구 정확성 수정이며 제품 Runtime 결함 해결로 세지 않는다.

### 후속 실행 전 계획 보강·관측 비용 대조

확인된 BF16 embedding 외의 비양자화 가중치는 loader의 keep-FP32 가능성을 고려해 FP32로 reserve하도록 계획을 더 보수적으로 보강했다. 위 표의 초기 BF16 전체 저장 계획은 당시 실험의 근거로 남긴다. 마지막4층 후보의 신규 실행에는 초기12.700GiB보다 약0.099GiB 높은 계획을 적용하며, 모든 안전 여유는 유지한다. 이후 GPU 실험에는100ms 현재값뿐 아니라 PyTorch allocator의 누적 peak counter·기본 dtype별 storage numel·라이브러리/의존코드/모델header hash와 양 epoch의 base version/sentinel 불변성도 기록한다. uint8 storage numel을 원래12B parameter 수로 부르지 않는다.

trace 보존은 양군 모두 켠 추가2400회/40재시작 대조에서 deep_size 매60초 ON은584.594초·private25.621→40.172MiB, OFF는575.312초·25.648→39.586MiB였다. 최종 약0.586MiB 차이는 관측 비용의 일부 근거이며, 전체15MiB 증가가 크기 관측 때문이라는 가설은 지지하지 않는다. 가속 workload이고2시간 실경과와 직접 수치 비교하지 않는다. 양군 입력/사건 count·재시작을 맞췄으며 종료 후 Runtime 참조0이다. 임시 trace/history·lazy import와 allocator의 비용이 함께 있다는 좁은 결론만 남긴다.

## 첫 장시간 시도 실패·정상 예약 제한의 fixture 교정

최초 retained/released는4432.750/4377.734초·각3615반복에서 **FAIL(exit1)** 이다. 오류는 Daily reminder limit, 잔류 Task0이었다.8합성 사용자에게 반복 생성/취소한 예약이각30개/일에 도달했다. 취소 이력도 일일 생성 제한에 포함되는 기존 제품 계약이 올바르게 작동했는데, soak가 모든 예약 시도를 성공으로 가정했다. 이를 Runtime 결함이나2시간 PASS로 바꾸지 않는다. 원래 로그/summary/progress/SQLite를 보존한다.

새 fixture는 제품 제한/시계를 바꾸거나 사용자/예약 이력을 돌려 한도를 회피하지 않는다. 본인의 당일 생성 수를 확인해30개에서 정확한 Daily reminder limit만 기대하고, 거절 뒤 행 수 불변·실행 영수증0을 확인해 reminder_limit_veto로 센다. 다른 ValueError/DB 실패는 그대로 실패다. 허용된 생성은 영수증1/실제cancelled를 확인하고, DB 잠금 복구도 계속 검증한다. 임시 DB의31회 요청에서30개 취소 이력 보존·1회 거절을 회귀로 확인했고 관련8검사 OK6.087초다.

원래 두 프로세스가 종료한 뒤 tinyNF4 suffix(448trainable)에서 실제 prefix_requires_grad=False·유한 gradient·base 불변·저장/Adam step2 재개를 확인했다. 이후 긴 입력12B의 가용VRAM을 새로 조회한 결과11.914GiB<새계획12.799GiB라 **새12B model load0회/BLOCKED**다. 집계값으로만 판단하고 다른 프로그램의 원인/상태를 추정하지 않는다. 모델/안전 여유/시스템 설정을 바꿔 강행하지 않았다. 다음은 GPU 없이 수정 fixture의 새2시간 실경과 검증이다.
