# 조건부 캐릭터 자료·QLoRA pilot — 2026-10-24

시작 main/local/remote `e0e8e8259dafaad08f564269fc552c04fee3d5db`, clean. RELEASE BLOCKED. 앱 실행src·기본 Gemma/no-LoRA·운영 설정/bootstrap/두DB·기존 모델/LoRA는 변경하지 않는다. 실제 Discord 인증/조회/Gateway/명령/송신0회다. 다른 앱의 화면/창/입력/프로세스 목록·내부·파일·패킷은 조사하지 않았다. 집계 RAM/commit/VRAM/온도/부하와 자체 테스트만 계측한다.

## 목표·진행 순서

먼저 기존 [짧은 학습 후보 기각과 진단 중단](TRAINING-FEASIBILITY-V2-QA.md)을 확인했다. 데이터의 사실 근거와 행동 목적을 고정하고, 토크나이저/정답 마스크→소형 Unified CPU→소형 NF4→실제12B의 새 길이/한 변수 학습률 비교 순서로 진행한다. training loss나 학습 성공은 품질 합격 조건이 아니다. 최종 미사용316개와 기존1,650평가 자료를 학습으로 전환하지 않는다.

## 공식 자료·채택 판단

2026-10-24 공식 문서 확인. 이 PC의 설치 버전은 기존 torch2.9.1+cu128/Transformers5.20.1/PEFT0.21.2/bitsandbytes0.50.2를 유지하며 새 의존성·모델은 설치하지 않았다.

- [Gemma tuning](https://gemma.ai/tuning/)의 과제별 자료와 성공/실패/경계 테스트 분리를 채택했다. 옛 세대 notebook을12B Windows의 검증으로 간주하지 않는다. [12B Developer Guide](https://developers.googleblog.com/gemma-4-12b-the-developer-guide/)의 unified 구조·16GB 로컬 추론 설명은 해당 PC의 학습 메모리 보장이 아니다.
- [TRL SFT](https://huggingface.co/docs/trl/sft_trainer)는 assistant-only mask에 템플릿 generation block을 요구한다. 설치된 실제 Gemma 템플릿에는 generation/endgeneration block이 없어 이 기능의 호환성을 가정하지 않았다. 기존 inference prefix/assistant terminator를 실제 토크나이저로 검사하는 직접 loss 경로를 유지한다. 라이브러리를 교체하거나 템플릿을 패치하지 않았다.
- [TRL PEFT](https://huggingface.co/docs/trl/peft_integration)의2e-4/dropout0.05는 특정 예시의 설정이다. 이 값이 최적이라는 전제 없이5e-5/1e-4/2e-4만 비교하며 rank4/alpha8/qv·데이터·순서·seed·epoch는 고정한다. [Transformers NF4](https://huggingface.co/docs/transformers/quantization/bitsandbytes)의 추가 파라미터 학습 경계와 NF4/BF16/double quantization을 따른다. inference용 device_map=auto/offload로 학습을 강행하지 않는다.
- [QLoRA 논문](https://arxiv.org/abs/2305.14314)의 양자화 비용 절감은 참고하되 이 모델/Windows/카드의 품질을 보장하지 않는다. [LIMA](https://arxiv.org/abs/2305.11206)는 선별 자료 실험의 참고이며 다른 모델·자료의 결과를 EchoMate 성능으로 가져오지 않는다. 자료 수1,000이라는 숫자나 낮은 loss를 채택 기준으로 쓰지 않는다.

## 공개 데이터 라이선스·원천 분리

공식 원천의 현재 문서와 기존 [수집 manifest/고정 버전 기록](DIALOGUE-EVALUATION-QA.md)을 대조했다. 이번에는 원문을 새로 다운로드하거나 평가 원문을 정답으로 가공하지 않았다.

|원천|공식 조건·이번 판단|
|---|---|
|[BST](https://github.com/facebookresearch/ParlAI/blob/main/parlai/tasks/blended_skill_talk/README.md)|데이터 CC BY4.0. 성격/공감/지식의 혼합 범주는 참고하지만 기존 평가로 수집한 원천을 학습에 재사용하지 않음|
|[ConvAI2](https://github.com/facebookresearch/ParlAI/blob/main/parlai/tasks/convai2/README.md)|공식 task는 CC4.0 BY. PersonaChat의 모든 미러에 같은 조건을 확장하지 않으며 대사 미복사|
|[EmpatheticDialogues](https://github.com/facebookresearch/EmpatheticDialogues/blob/main/LICENSE)|CC BY-NC4.0. 공개 앱의 일반 배포 학습 자료로 허용됐다고 가정하지 않고 제외|
|[LoCoMo](https://github.com/snap-research/locomo/blob/main/LICENSE.txt)|CC BY-NC4.0. 현재 평가용 원천 유지, 학습/공개 fixture에 넣지 않음|
|[KoED](https://github.com/KUNLP/KoED)|ED 파생 CC BY-NC4.0을 명시. 기존 최종 봉인 자료와 분리, 학습 제외|
|한국어 AI Hub|기존 접근/개별 이용 조건 미확정 상태를 유지. 로그인/계정 접근 우회·원문 학습 없음|

새 `tests/fixtures/persona_evidence_pilot.json`은 **Codex가 새로 작성한 원본 합성 MIT**이며 실사용자 대화·번역·유명 캐릭터 대사를 사용하지 않았다. 외부 코드를 복사하지 않았다. 기존52/8·compact16/8은 덮어쓰지 않는다. 공개 자료를 자동으로 정답 취급하거나 기존 NC 자료를 MIT로 바꾼 것이 아니다.

## 실제 자료 규모와 품질 계약

최초 pilot v1은 **24개 고유 원천 상황·104개 캐릭터 조건부 응답**이다. 현재 공개 자료는 후속 v3의36원천/152응답(학습112/개발16/별도24)이며 아직 학습하지 않았다. v2의28원천/120응답과 학습한 v1은 아래에 버전별로 구분한다. 같은 상황의4~6캐릭터 응답을104개의 독립된 원천 대화라고 세지 않는다. 1,000~3,000개 고유 대화 구축 목표는 미달이다. 효과가 확인되지 않은 작은 자료를 문장 변형으로 증식하지 않았다.

다음 분포 표는 실제 학습에 사용한 **v1**이다. 최종 미학습 v3의 분포는 마지막 절을 따른다.

|분할|원천 상황|응답|용도|
|---|---:|---:|---|
|학습|16|64|4성격의 조건부 행동·근거 학습|
|개발|4|16|후보 손실/제한 생성 비교; 열람·활용한 개발 자료|
|별도 평가|4|24|다른 원천 상황·소심/호기심 가족2종 추가; 후보 조정에 사용하지 않는 고정 자료|
|기존 final holdout|기존 장부|미사용316 유지|학습·토큰 export·pilot에 넣지 않음|

6개의 독창적인 카드에 정체성·가치관·습관·성격적 모순·가상 배경을 포함한다. 평온/피곤함/슬픔/짜증/기쁨·일반/친밀/불편 관계를 구성했지만 모든 기분/관계 조합을 덮지는 않는다. multi-turn context는2원천 상황뿐이며 장기 대화 품질을 증명하지 않는다. 새 별도 평가는 작성자가 내용을 알고 있는 합성 원천 분리 평가다. 사람 블라인드/완전히 낯선 현실 질문으로 과장하지 않는다.

각 상황에 source group/license/split·category·mood·relationship·context·evidence·uncertain·feature state·현재 입력·character별 target/전략/피할 행동/claim span·검토 범위를 연결했다. `confirmed/not_found/not_checked/unavailable/fictional/user_claim/inferred`와 근거 scope를 분리한다. 저장 성공은 합성 실행 영수증이 있어야만 completion 주석을 허용하며 조회 실패/미조회/부재·인용을 성공/사건 부재로 승격할 수 없다. 여기의 영수증은 실제 운영 작업이 아니라 fixture 조건이다.

자동 검사는 구조/enum·출처 결합·span 원문 일치·상태 승격 금지·완료 영수증·원천 그룹/정확한 응답 중복·표면 near duplicate·식별자 패턴·반복 문자 경계를 검사한다. 정확/표면 near duplicate 경고0이며 **의미 중복 전체 검증·자유문장 사실 추출 정확도는 미입증**이다. Codex의 응답/주석 검토를 사람 검토 또는 검증된 AI judge 점수로 부르지 않는다. 같은 source group의 파생 응답은 같은 split에만 속한다. 학습/개발은4카드 가족을 공유하고 별도 평가는2새 가족을 추가하므로 모든 캐릭터 가족이 완전히 분리됐다는 주장도 하지 않는다.

## 토큰·손실·학습 설정

실제 로컬 토크나이저로 학습64·개발16개를 전부 export했다. 학습266~349tokens/정답23~39, 개발279~377/정답21~33이다. system·자료 JSON·기존 assistant context·현재 user를 모두 마스크하고 마지막 응답과 실제 terminator만 학습한다. 기대 전략/금지 행동/claim 주석/목표 답변은 프롬프트에 전달하지 않는다. EOS 뒤 템플릿의 newline을 허용하며 첫 검사의 '마지막 token은 turn' 가정을 실제 `<turn|>\n` 확인 뒤 교정했다. packing/padding/절단은 사용하지 않는다. 128token에 맞추기 위해 성격·근거를 삭제하지 않았다.

프롬프트는 새 연구용 구조화 카드/상태다. 실제 토크나이저 템플릿은 같지만 앱의 전체 Runtime prompt와 동일하지 않다. 최대377은 개발 정답 포함 길이이고 실제 backward의 학습 최대는349다. 512/1024/1800으로 불필요한 padding 확장은 하지 않는다. 보수적 전체 q/v 학습 계획은349/39위치에서13.900971GiB이며 최초 집계 가용14.308594GiB, 결정성 재실행 직전14.307617GiB 안에서만 로딩했다. 계획·안전 여유는 낮추지 않았다.

batch1·gradient accumulation4·rank4/alpha8/dropout0.05·AdamW·cosine/5% warmup(16step에서1step)·max grad norm1·epoch1을 고정한다. 각 accumulation window의 **정답 토큰 수로 mean**을 계산해 길이가 다른 응답을 단순 microbatch 평균으로 편향시키지 않는다. 짧은/긴 두 답변의 합친 token 평균 gradient와 같음을 회귀로 검증한다. 개발 손실은 별도 per-example mean으로 기록하며 품질 점수가 아니다.

## 체크포인트·검증 범위

optimizer boundary의 immutable 새 디렉터리에 adapter·optimizer·scheduler·CPU/CUDA RNG·Python RNG·step·data hash·설정·파일 hash manifest를 기록한다. 실패한 임시 쓰기는 자기 경로만 정리하고 이전 checkpoint는 보존한다. 파일 누락/추가/변조·다른 data/config binding을 load 전에 거절하고 torch weights_only를 사용한다. hash는 무결성 검사이지 공격자가 manifest까지 다시 쓰는 경우의 인증 서명이 아니다. 운영 모델 선택/자동 승격과 연결하지 않았다.

Toy CPU에서는 dropout을 포함한 중단/재개가 uninterrupted의 모든 학습 가중치와 bitwise 일치했고, 소형 Unified CPU·소형 NF4도 새 accumulation/저장/재생을 통과했다. 실제12B의 재개/품질 결과는 아래 최종 기록과 구분한다. 기존 테스트와 새 테스트의 이름 충돌은 마감 전에 바로잡아 기존 테스트 파일 내용을 보존했다. sandbox의 임시 directory rename 거절은 동일 오프라인 검사를 프로젝트 경로의 승인된 실행으로 확인했으며 코드의 성공 판정으로 숨기지 않는다.

## 실제 결과·후속 판정

최종 실측·회귀·Portable·보존·Git 마감은 이 절에 누적한다. 실제 Discord/다른 Windows/새 GUI/Portable GPU·장시간 GPU·사람 만족도는 별도 미검증이다.


### 편집 v2 — 원천28/응답120, 추가 학습 아님

pilot이 끝난 뒤 원본 v1 bytes/hash를 private `pilot-v1-source.json`과 Git b56d231에 보존하고 별도 v2를 편집했다. 첫 카드의 가상 배경에 현실 사용자 공동 경험의 부재를 단정하는 문구가 섞여 있었으며, 일부 가상 장소 표현의 세부 근거도 더 분명해야 했다. 현실 기억 정책은 상위 출처 경계로 분리하고 배경에는 가상 사건만 남겼다. 정원/항구/지도/산장 claim을 해당 캐릭터의 배경 anchor와 연결하며, 다른 카드의 배경을 차용하는 잘못된 주석을 거절한다. 허브차 저장 영수증의 대상과 응답 명사가 바뀌는 오류도 명시 term으로 거절한다. 이것은 주석된 anchor/entity의 일치 검사이며 자유문장 전부의 사실성 판별은 아니다.

부정된 실행 요청·미래 조건부 동의·반어적 비판·삭제 후 성공한 재조회4원천/16응답을 추가했다. v2는 train80/dev16/별도24, 학습268–384tokens/정답23–39, 개발281–394/21–33이다. 실제 토크나이저로96개 학습/개발 전체를 다시 확인했고 절단/packing/padding은 없다. 새 source hash/JSONL hash/분할을 별도로 저장했다. 최종 v2는 실제ID 없이 current_user/current_speaker/current_character/application 소유자를 구분하고, 기억 확인/성공한 저장 영수증의 동의 상태를 명시한다. 타인 소유 또는 동의 없는 확인 기억은 contract에서 거절한다. 이 계약 보강 뒤 최신 전체 회귀를 별도로 실행하며 앞선857 결과를 최신 소스로 소급하지 않는다. **이번 GPU 비교는 고정 v1의64개를 사용한 결과이며 v2의 학습/품질 PASS가 아니다.** 후속 도구는 검증한64–128개/4배수 자료를 모두 사용하고 optimizer/scheduler 길이를 실제 record 수에서 계산한다. v2라면20 optimizer step이며 이번에는 실행하지 않았다. 기존24개 별도 평가는 GPU에 넣지 않았고 최종316개도 소비하지 않았다.

### 실패 재현·결정성 조합 검증

첫12B pilot은128→256→349token backward를 통과했으나5e-5의step9에서 재개 검사가 실패했다. 이 실패 로그/step8 checkpoint를 보존하고 나머지 LR로 진행하지 않았다. 당시 재개 metric 상세를 누락한 진단 한계도 이후 expected/actual/delta 기록으로 수정했다.

같은 checkpoint를 추가 학습 튜닝 없이2번 재생한 실제 진단에서 forward loss4.4432247223·정답102tokens·LR은 일치했으나 gradient norm은5.894351/5.661798, adapter 차이 최대6.9386e-6이었다. 원래 중단 전 norm5.652140과도 달랐다. 따라서 단순 RNG 저장 누락이라고 확정하지 않았다. [PyTorch2.9 SDPA](https://docs.pytorch.org/docs/2.9/generated/torch.nn.functional.scaled_dot_product_attention.html)와 [재현성](https://docs.pytorch.org/docs/2.9/notes/randomness.html)의 비결정적 CUDA 연산 경계를 확인하고, **자체 연구 child 안에서만** CUBLAS_WORKSPACE_CONFIG=:4096:8과torch.use_deterministic_algorithms(True)를 적용했다. Windows 환경/드라이버/다른 앱/운영 설정은 바꾸지 않았다.

그 조합의 실제 재생2회는 norm5.8641657829/동일 loss·LR·token수·가중치 차이0이었다. 어느 개별 kernel이 전부의 원인인지 프로파일러로 분리한 것은 아니며 이 설정 조합에서 backward 재현성을 확보했다는 결론이다. 임계값을 완화하지 않고 새 결정성 pilot은 metric/가중치 **완전 일치**를 요구한다. 예전 비결정성 run과 새 run을 같은 baseline으로 합치지 않는다.

### 실제12B 학습률 pilot 결과 — 모두 운영 미채택

한 resident base에서 adapter를 하나씩 생성/저장/해제했고 모델 인스턴스를 병렬 로딩하지 않았다. 소형 검증1회, 최초 pilot→실패 원인 진단2조건→결정성 pilot의 각각 다른 목적에만 제한적으로 로딩했다. 최종 조건에서3LR 각각64microbatch/16유효 optimizer step(1epoch)을 완료했다. 저장step8 뒤step9의 uninterrupted 결과를 버리고 checkpoint에서 재생했으므로 물리 연산은각68microbatch/17optimizer step이다. replay 검증 비용을 숨기지 않는다. 세 후보 모두 optimizer/scheduler/RNG·재생 metric/adapter 가중치 완전 일치·기본 파라미터 version/16원소 sentinel 불변을 통과했다. 전체12B 텐서의 cryptographic 전후 비교를 했다는 뜻은 아니다.

|LR|개발16개 per-example loss|유효 visible 생성/8|생성 p50/p95초|TTFT p50/p95초|출력token p50/p95|
|---|---:|---:|---|---|---|
|no-LoRA baseline|미측정|7/8|20.196/25.690|0.297/0.344|146.5/192|
|5e-5|4.836141|7/8|21.617/28.594|0.313/0.338|129/169.65|
|1e-4|4.261781|7/8|17.258/27.491|0.305/0.333|101/167.85|
|2e-4|3.154489|8/8|7.438/20.305|0.414/0.479|39/112.05|

생성 cohort는 사전 고정한 개발2원천(소중한 물건 상실/예약 조회 실패)×4카드다. 각 조건은 max_new_tokens192/max_time30/greedy/같은 input이며 앱과 같은 EOS/end-of-turn/visible-channel 검사를 적용했다. 미완료는 유효 답변으로 세지 않고 채널 표식을 지워 허용하지 않는다. 출력 길이와 완결성 변화가 커서2e-4의 짧은 지연을 throughput/실제 Runtime 속도 향상이라고 주장하지 않는다. baseline loss가 없어 loss 감소를 baseline 대비 수치로 주장하지 않는다. 다른질문의 first/last train loss도 품질 점수로 쓰지 않는다.

Codex의 명시 근거 대조에서1e-4/dry는 실패한 조회를 '없다는 결과'로 바꿨다. 5e-5/1e-4의 장난형은 사용자 물건의 추억을1인칭으로 섞는 표현도 남았다.2e-4는 더 짧아지고 조회 실패를 올바르게 설명하는 답변도 있었지만, 물건의 의미/소중함을 확인하는 공통 공감 접근으로 수렴했다. 장난형의 '아무것도 안 뜬다'는 UI 상태를 확인된 것처럼 읽힐 수 있어 불확실로 남긴다. 애매한 표현을 억지로 확정 위반/성공으로 점수화하지 않는다. 네 캐릭터가 서로 다른 단어를 사용했다는 사실은 인격 구별 PASS가 아니다. 인격·사실성 동시 개선의 충분한 신호가 없어 **세 후보 모두 미채택**이며 rank/epoch 탐색 확대·별도/최종 평가 소비를 중단했다. AI judge 점수나 사람 만족도 PASS는 없다. `comparison-private.html`은 visible 답변만 escape한 로컬 비교 자료이며 원문/adapter는 공개·Portable에 넣지 않는다.

### 실제 자원과 안전 범위

결정성 pilot 전체820.5초. PyTorch 누적 exact peak allocated11.438510GiB/reserved11.888672GiB, OS own private peak15.161705GiB/working peak4.838169GiB였다. stage 최고66°C, 최소free VRAM2183MiB(2GiB guard 이상), RAM7.630GiB/commit18.364GiB였다.200ms 표본의 현재값과 누적 peak를 구분한다. 모델 해제/child 종료 뒤 새 CPU 운용 사전 집계에서RAM9.486GiB/commit29.727GiB·GPUfree14027MiB/41°C를 확인했다. 다른 앱이 어떤 자원을 쓰는지 조사하거나 원인으로 단정하지 않았다. 더 긴512/1024/1800token·rank8·2–3epoch 학습, 운영 LoRA 전환·새 adapter의 실제 Runtime→SDK GPU 통합은 미검증이다. 기존 SDK mock을 포함한 기능 회귀와 독립 학습 도구의 실제 GPU 결과를 합치지 않는다.

### CPU/mock 장시간 검사 — 현재 진행 중

GPU child가 모두 종료한 뒤 source39dab96의 진단 보존ON/OFF를 별도 임시 설정/SQLite/transport로 최대7200초 실행했다. 실제 Discord와 하위 소켓을 차단한다. 처음 추가한 소켓 차단이 Windows asyncio 자체 socketpair 초기화를 막는 fixture 실패를 재현했고, loop를 만든 뒤 workload 진입 전에 차단하도록 교정했다. 자체 loop의 제어 socketpair와 외부 Discord 인증을 혼동하지 않는다. 오류 주입 회귀로 workload의 connect/connect_ex/getaddrinfo 차단을 확인했다.

기존70분 run의 unsafe sample이 없으므로 그 순간의 정확한 branch는 복구할 수 없다. 이번 run은 동일 RAM3GiB/commit2GiB/own private256MiB guard를 유지하며 actual unsafe sample/reason을 먼저 보존한다. 완료/실패·자원 증가율·최종 Task/참조는 실제 종료 후 이 절에 기록한다. 현재 결과를2시간/8시간 PASS로 앞당기지 않는다.

### 현재 소스 회귀 체크포인트

최종 전체 **857검사 OK276.477초**(`full-regression.log`). 앱src는 시작e0e8e82와 동일하고 운영 no-LoRA·DB schema·권한/동의/명령 계약을 유지한다. 신뢰성 부족의 새 NLP 차단기를 운영에 연결하지 않는다. 번들83은 기존 f243675의 동일 실행 소스 근거이며 재실행했다고 쓰지 않는다. Portable 공개 문서 증분/전체hash·보존5hash·최종 staged 감사/원격 일치는 마감 후 기록한다.


최종 v2는 기분/관계의 주체도 character_mood/relationship_to_current_user로 명시한다. source/tokenizer뿐 아니라 실제 prompt hash와 compiler/마스킹 helper hash를 export에 결합해, compiler가 바뀐 오래된 export는 모델 접근0회로 거절했다. 최종 v2의 실제 최대384/정답39token·전체q/v rank4 계획은14.093231GiB다. 후속 CPU-only 계획 조회에서 가용13937MiB(13.610352GiB)로 미달했고 새 모델 로딩/추가 학습0회다. v1 후보의 품질 신호도 부족하므로 안전 여유를 깎아 v2를 강행하지 않는다. 857회귀 후 소유자/동의 결합이 추가돼 최종 소스의 전체 결과는 새 `full-final.log`로 구분한다.


소유자/동의·역할 명시·compiler 결합이 포함된 최신 전체 **859검사 OK264.058초**(`full-sealed.log`)다. 이전857/859검사는 각각 당시 단계의 근거로 보존한다. 추가 stale-compiler 오류 주입에서도 실제 모델 접근0회로 거절했다. 위 최종 v2 예산은 앞선 집계13.610352GiB와 비교한 CPU 계산이며 새로운 GPU 실행이 아니다. 더 이상의 학습 코드 변경/모델 로딩 없이 현재7200초 운용을 관측한다.


## 최종 편집 v3 — 행동 선택·긍정 근거·작업 상태 대비

실제 출력뿐 아니라 v1 정답도 일반 고민에서 공통 권고로 끝나는 경우가 많았다. 이것을 수렴의 단독 원인으로 입증한 것은 아니지만, 같은 권고의 말투 변형만 늘리는 데이터 전략은 적합하지 않다는 가설을 세웠다. v1/v2 원문/hash를 보존한 뒤 자유로운 반나절·친구의 약속 취소·추억 있는 컵의 처리·낯선 수업 선택4원천/16응답을 새로 작성했다. 휴식/외출/조건 비교/작은 책임 완료처럼 서로 다른 선택이 가능한 경우에만 최소3개의 서로 다른 선택 tag와 실제 응답 span을 요구한다. 사실/동의 경계까지 캐릭터별로 다른 결론을 강요하지 않는다. 이 검사는 **주석·원문 일치**이며 자유문장의 행동 의미를 자동으로 이해했다는 뜻이 아니다.

확인된 취미·알림 생성 영수증(전달 전)·성공한 빈 조회·유효한 최신 정정4원천/16응답도 추가했다. 모름/거절만 학습시키는 편향을 줄이는 대비 자료이며 효과를 모델에서 입증한 것은 아니다. 개인 조회 결과는 application capability와 별개의 user_query_result/current_user 범위로 둔다. 특징 지원/활성/권한과 read/store/list/create의 실제 status를 분리해, 완료 영수증과 not_requested가 동시에 존재하는 모순을 거절한다. 관련 없는 기본 기능 정보는 모델 입력에서 제외하고, 해당 근거에 연결된 feature만 보존한다. 원문/성격/근거를 절단한 것이 아니다.

최종 v3는 **36고유 상황/152조건부 응답 = 학습28상황112응답·개발4/16·별도4/24**다. 실제 토크나이저의 학습256–399tokens/정답23–44, 개발269–413/21–33이며128개 학습/개발 전체의 정답 마스크를 확인했다. v3의 새 자료/구조는 GPU에 넣거나 학습하지 않았다. 계획 VRAM은 약14.195GiB로 기록된 가용13.610GiB에도 미달하며, 허용 여유를 낮추지 않고 GPU 로딩0회다. 정확한 값은 private sealed-v3-budget.json을 따른다. 1,000–3,000개 고유 대화 목표는 여전히 미달이고, 여러 턴/기분·친밀도의 인과적 대조와 대규모 자연스러움은 미검증이다.

최종 최신 전체 **861검사 OK264.269초**(`full-v3.log`). 857/859는 각 이전 계약의 실제 근거로만 보존한다. 실제 모델 비교는 고정 v1의32생성(8입력×4조건)이며, 실패한 최초 pilot의 baseline8생성은 이에 합치지 않는다. 본 차수 총 생성 요청40회를40개의 독립 질문으로 세지 않는다. stage 집계 GPU 사용률6–94%를 관측했고 다른 프로그램별 부하/게임 FPS는 조사하지 않았다. 작은16step의5% warmup은1step이라 첫 update부터 base LR이며, 긴 warmup ramp의 효과를 검증했다고 주장하지 않는다.
