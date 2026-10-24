# QLoRA 재개·전체 자료·캐시 준비 검증 — 2026-10-25

시작 local/main/remote `1f0deaec94ec92617d44186b050b4c2d6b309435`, clean. [이전 공개 원천/권리/편집](PUBLIC-TRAINING-DATA-QA.md)과 [릴리즈 추적표](RELEASE-CHECKLIST.md)를 확인했다. 앱src·기본 no-LoRA·운영 설정/bootstrap/두DB·기존 어댑터는 변경하지 않는다. 실제 Discord 인증/조회/Gateway/명령/송신0회, 다른 앱/게임의 목록·프로세스 내부·창·화면·입력·파일·패킷 접근0회다. 시스템 집계와 자체 실행만 계측한다. 실제 사람 만족도·다른 Windows·8시간/GPU 장시간·새 GUI는 별도 NOT VERIFIED다.

## 고정 자료와 채택 조건

376개 조건부 응답의 source hash `b67ea54ac4fc24032eb126d1e5f0aecd4c04504f004ae05197c88b0669bcb990`를 유지했다. 학습264/개발56/별도56,90원천 가족/92상황 변형이다. MIT152/CC BY224의 권리와 원천 queue/원본 카드 결합·그룹 분리·claim span·기능 상태/영수증·실제 토크나이저/컴파일러/JSONL/정답 마스크 hash를 다시 대조했다. 최종 미사용316/소비 장부는 보존하고 운영 기억·개인 대화를 학습하지 않는다.

인격은 서로 다른 관심·행동/질문·가치관, 사실성은 입력/확인 상태/시점/화자와 대조한다. 문장 길이/학습 loss/visible 비율로 품질을 대체하지 않는다. 명백한 사실/인칭 오류나 인격 개선 근거 부족은 후보 기각 사유다. 애매한 제안·비유를 실제 기능 약속으로 억지 분류하지 않는다. 개발의 동시 개선 신호가 없으면 별도/최종 평가를 소비하지 않는다. 품질 판단은 Codex의 명시 근거 검토이며 신뢰성 미달 AI judge 점수·사람 만족도 인증이 아니다. private quality-gates.json에 출력 본문을 읽기 전에 고정했다.

## 자원 재측정과 원천 가족 단위 pilot

사용자 추가 확보 뒤에도 처음 가용14.074/14.150GiB 등은 전체399/정답44token의 기존 보수적14.195160GiB 요구에 미달했다. 임계값을 낮추거나 원문을 절단하지 않았다. 별도 opt-in `--maximum-group-tokens 320`으로 **한 원천의 모든 응답/변형이 길이 기준에 맞을 때만** 선택하는 계약을 만들었다. 원본 파일/분할/전체export를 먼저 검사하고 선택·보류ID와 hash를 보고서 및 체크포인트 설정에 결합한다. 기본값은 전체 자료 사용이며 평가 자료를 curriculum에 넣거나 긴 사례를 평가로 바꾸지 않는다.

선택188응답/47가족(기존48+새 공개 원천140),76응답/19가족 보류. 실제 최대316/정답44token 계획13.739227GiB를 통과해 단일12B/NF4 frozenBF16/선택logits 경로를 실행했다. **기억·영수증 등 전용 사실성 학습 자료가 긴 보류군에 몰렸다는 편향**을 미리 기록했다. 이것은 전체264개 학습이나 광범위한 사실성 개선 검증이 아니다.

rank4/alpha8/dropout0.05, 전체텍스트 q/v88대상2,596,864학습파라미터, AdamW/base LR1e-4 하나, accumulation4,cosine/warmup5%,gradient clip1,epoch1이다.47유효optimizer step/188microbatch,step8 저장 뒤step9를 검증 재실행해 물리48update/192microbatch다. 유효 정답6,329token/물리6,465token이다. 체크포인트는 optimizer/scheduler/CPU·CUDA·Python RNG와 curriculum/data/config hash를 포함하며 metric·어댑터가중치 완전 일치했다. frozen 파라미터version/16원소sentinel 불변을 확인했다. full binary 보존은 아래 파일hash와 별도로 구분한다.

## 실제188응답 학습·생성 결과 — 운영 미채택

총601.157초. 첫/마지막 train loss5.130640/2.618190은 **다른 배치**의 값이라 loss 감소의 정량 비교가 아니다. 개발56개 per-example mean loss2.641438, 이 run의 baseline 개발 loss는 미측정이다. 양끝 gradient norm3.234885/3.756790이며 finite 검사·maxnorm1 clipping을 통과했다. 보고되는 step learning_rate는 scheduler 갱신 뒤의 다음 LR다.

생성은 사전 고정된 기존 핵심8+새 개발8,같은카드/입력/greedy/max_new_tokens192/max_time30/실제EOS·visible계약으로 no-LoRA16/adapter16이다. 미완료·차단channel의 원문을 잘라 정상 답변으로 세지 않는다.

|지표/16입력|no-LoRA|188응답 adapter|
|---|---:|---:|
|visible/미완료/차단channel|9/5/2|14/0/2|
|생성 p50/p95초|18.4765/24.004|3.742/6.543|
|TTFT p50/p95초|0.2815/0.301|0.289/0.332|
|출력token p50/p95|156.5/192|27.5/47.5|

출력 길이·완결성·실행 중 집계 자원 조건이 달라 throughput/Runtime속도 개선으로 주장하지 않는다. 열린 질문에서 짧은 감정 반응·수리 비유·조건 분석 등의 차이가 보이지만, 공간 변경을 아직 제안받은 상황을 이미 일어난 사건처럼 처리하고 화자의 취향을1인칭으로 섞는 오류가 남았다. 분석형의 권고가 사용자의 선택권을 제대로 다루지 않는 사례도 있다. unavailable 조회 상태를 더 분명히 구분한 좁은 개선은 있지만4개 조회 상황의 일부로 일반 사실성 PASS를 선언하지 않는다. **동시 개선의 충분한 근거가 없어 미채택**이다. 일반적인 함께 찾아보자는 제안은 실제 도구 실행 약속인지 불확실하므로 확정 위반 점수에 넣지 않았다. 별도56/최종316의 모델 입력·소비는0이다.

|188응답 run의 자원|실측|
|---|---:|
|GPU peak allocated/reserved GiB|11.052475/11.517578|
|자체 private/working-set peak GiB|14.825218/4.845543|
|최소 RAM/commit 가용 GiB|8.895416/25.593842|
|stage 최고온도/최소 freeVRAM|65°C/2,166MiB|

0.2초 recorder 표본·OS peak·PyTorch 누적 exact peak를 구분한다. 운영 모델 자동 적용·실제 Runtime→SDK GPU 통합 검증은 하지 않았다. 연구용 직접 생성과 기존 SDK mock 회귀는 별도다.

## 전체264응답 준비 실패와 상향 admission

추가 자원 및 기존 모델 종료 후 가용15,004MiB가 원래14.195160GiB를 넘었다. 보류된76개 사실/정정 자료의 복원이라는 새 커버리지 가설로, 같은 LR/rank/epoch의 원래 전체264응답 후보를 한 번 준비했다.128→256→399token 역전파 뒤 **freeVRAM2,020MiB<기존2,048MiB**로37.687초에 안전 중단했다. baseline 생성/optimizer학습/adapter품질 A/B는0이다. CUDA allocated/reserved peak11.993486/12.457031GiB,자체private15.737728GiB,최소RAM12.012947/commit30.389656GiB,stage 최고54°C였다. OOM/드라이버 오류나 품질 실패라고 부르지 않는다.

이 관측은 정적 예산이 실제 단계 준비를 보장하지 않는다는 근거다. 같은header/data/길이/rank/cache정책의 실패 증거만 받아 **기존 계획보다 높은 값으로만** admission을 보강한다. 해당 관측의15,004+(2,048−2,020)=15,032MiB는 그 실행 조건의 floor이며 다른 앱의 원인/다른PC의 필요량을 확정하지 않는다. JSON/hash는 인증 서명이 아니다. 사용자 재측정14,913/14,958/14,823MiB 등은 이 floor에 미달했고 재로딩하지 않았다. 검사 후 cache를 비워 수치만 맞추지 않았다.

## 별도 캐시 후보 — 동일 자료/학습 설정, 계산 전만 정리

직전 peak allocated와reserved 차이를 근거로 단계 사이 유휴 캐시의 영향을 가설로 삼았다. [PyTorch2.9 empty_cache](https://docs.pytorch.org/docs/2.9/generated/torch.cuda.memory.empty_cache.html)는 점유되지 않은 캐시를 반환하며 일부 단편화에 도움을 줄 수 있다고 설명한다. 모델에 필요한 활성 메모리를 줄이는 기능으로 해석하지 않는다. 새 `--cache-hygiene`는 **다음 smoke/backward 또는 optimizer window 전에** synchronize/공개empty_cache만 호출하고 활성 allocated 불변을 검사한다. 별도 기본OFF 연구 옵션이며 앱 Worker/추론/전역 allocator·드라이버 설정은 바꾸지 않는다. private cuBLAS hook을 이 새 단계 정리에 사용하지 않는다.

작은 실제 NF4의 gradient·저장/재개 metric/가중치 완전 일치와 활성 할당량 유지3회를 먼저 확인했다(peak reserved22MiB). 이는 단편화 절감이나12B품질의 증명이 아니다. cache정책을 checkpoint 설정에 결합하고 다른정책의 실패floor를 같은workload 증거로 사용하면 거절한다. 동일 전체264/399token/정답44,LR1e-4의 새 후보에서만 준비·학습·개발 비교를 실행한다. **각 계산 후의 같은2GiB guard 이전에 정리하지 않으며**, 기준 미달이면 다시 중단한다. 새 후보의 실측/최종 판정은 아래 최종 절을 따른다.

## 독립 보강 자료와 남은 검증

현재376개를 실험 도중 수정하지 않고 새 원본MIT4가족/8조건/32응답을 private next-contrast-draft.json에 작성했다. 축제 문구의 기쁨/피곤함, 가까운 관계의 놀림/불편 표현, 친밀도와 무관한 타인 기억 저장 권한, 듣기에서 조언으로 바뀌는 후속 발언이다. 가족 단위 train24/dev8,같은 입력의 대조2쌍은 같은분할에 유지한다. 엄격주석/권한/마스크 계약은 통과했지만 Codex 편집 초안이며 사람/검증된judge의 품질 인증이 아니다. 실제토큰은train274–378/정답28–42,dev314–366/31–41이고 절단/packing/padding은 없다. 이번 어떤 GPU 학습/선택에도 넣지 않았다. 기분·관계/여러턴·다자/장기 일반화가 해결됐다는 주장도 하지 않는다.

비공개 root는 local_data/qlora-resume-20261025다. checkpoint.json의 phase/own session/source/datahash,원본mask/실행source 스냅샷,각 run/report/log/짝지은HTML/명시 근거 검토를 보존한다. raw/incomplete channel은 HTML에 표시하지 않고 escape/CSP 처리한다. 원문/어댑터/새정답/개인 경로/진단은 공개 및Portable에 넣지 않는다. 최종 결과와 재개는 아래 마감 기록을 우선한다.


## 전체264응답 캐시 후보의 최종 기록

새 cache 정책의 사전 가용은15,020MiB/42°C였다. 이전 실패floor15,032MiB는 이전 allocator 정책에만 결합된 관측이다. 새 정책도 원래14.195160GiB 계획과 동일한 단계후2GiB 기준을 모두 적용했다.399token 직전 reserved11,284,774,912→7,872,708,608bytes를 반환했고 active allocated7,756,875,264bytes는 불변이었다. 실제399token 계산 뒤 freeVRAM2,266MiB로 통과했다. 검사 뒤의 정리로 실패를 숨기지 않았다.

전체264응답/66원천 상황·66유효 update(1epoch)/264microbatch를 **739.031초**에 완료했다. 저장/재개 검증 때문에 물리67update/268microbatch,유효 정답8,572token/물리8,706token이다. LR1e-4/rank4/alpha8/dropout0.05/qv/accum4/clip1은 그대로이며 warmup은ceil(66×5%)=4step이다. checkpoint optimizer/scheduler/RNG metric·가중치 완전 일치 및 frozen version/sentinel 불변을 통과했다. public cache 호출70회의 전후 active allocated 불변을 확인했다. 이전188run이나 새32초안과 섞어 학습하지 않았다.

|지표/16입력|전체 후보의 no-LoRA|전체264 adapter|
|---|---:|---:|
|개발56 mean loss|5.216509|2.449784|
|visible/미완료/차단channel|9/5/2|14/0/2|
|생성 p50/p95초|22.7265/30.07025|5.2265/8.96925|
|TTFT p50/p95초|0.2815/0.39025|0.273/0.363|
|출력token p50/p95|156.5/192|31.5/64|

첫/마지막train loss5.630237/2.467793은 다른 배치의 값이다. 동일 개발 손실 감소는 확인했지만 실제 응답의 사실성·매력 점수는 아니다. 두 run baseline16개 중14개는 tokenwise 동일했고2개는 동일prefix의 미완료 길이만 달랐다(192→191,192→183). max_time 경계와 출력 길이/자원 조건을 기록하며 다른run baseline을 재사용하거나 모델 throughput 개선으로 해석하지 않는다.

|전체 cache run의 자원|실측|
|---|---:|
|GPU peak allocated/reserved GiB|11.985758/12.181641|
|자체 private/working-set peak GiB|15.462215/4.845005|
|이번 recorder의 최대 시스템commit 사용 GiB|36.464008|
|최소 가용RAM/commit GiB|16.158081/32.724529|
|최고 stage온도/최소 stage freeVRAM|67°C/2,266MiB|

이전 cache미정리 준비의reserved peak12.457031GiB보다 낮았고 새399token 준비·전체66step이 같은guard를 통과했다. 호스트 집계 조건도 조금 달랐으므로 차이 전부를 유일한 원인이나 다른PC 보장으로 확대하지 않는다. **이 호스트의 연구 경로에서 계산 전 유휴 cache 정리가 검증된 것**이며 앱기본정책을 변경한 것은 아니다. 이후에도 사전추정은 상한 보장이 아니고 각 단계의 실제guard가 필요하다.

### 품질 판정과 원인 범위

전체 후보도 **운영 미채택**이다. 조회실패로는 목록이 비어 있는지 알 수 없는데 비어 있지 않다고 단정하는 응답이 남았다. 방 꾸미기의 시점/화자 혼동도 재현됐고, 분실물에 대한 부자연스러운 부정/긍정 결합·과도한 의인화가 나타났다. 일부 분석형의 권고는 사용자의 선택권을 충분히 다루지 못했다. 의인화나 거친 농담 자체를 금지/사실 위반으로 세지 않으며, 여기서는 부정/긍정 모순과 시점/화자 오류를 따로 검토했다. 같은사실의 다른표현이나 길이 감소를 인격 성공으로 세지 않는다. 미래 안내 표현이 실제 기능 실행 약속인지 불분명한 경우는 확정 위반에 넣지 않았다. 채널차단2개도 남아 있으며 raw channel을 잘라 허용하지 않는다.

추가로 정답의 operation/status 조합을 사례 단위로 집계했다. 현재train에는 memory/read/store·reminder/create는 있으나 **reminder/list/failed와reminder/list/success는 각각0상황**이고 개발에는 각각1상황이 있다. 새입력에서의 일반화가 필요하지만, 기존 자료에 모든핵심 기능 상태가 골고루 들어갔다고 주장할 수 없다. 누락을 단독 원인으로 입증한 것은 아니다. 다음은 단순LR/rank/epoch 증가보다 **기능별 조회 안함/실패/성공한 빈조회/확인된 항목을 구별하는 원천 분리 대조 자료**의 균형을 보강하는 것이다. 실패한 개발문항은 이후독립정답으로 재사용하지 않는다.

개발의 명확한 오류 때문에 독립56/최종316 모델 입력은0이며, 학습·생성·독립 품질 향상을 모두완료했다고 보고하지 않는다. 실제 Runtime→SDK의 새adapter 통합도 보류한다. 기존 source/SDK mock은 최종회귀로 보호한다. 두 실제 학습 후보188/264는 private에만 보존하고 기본 Gemma/no-LoRA를 유지한다.


## 최종 회귀·보존·Portable·재개

연구/검토 도구·합성테스트 **e6fef4c**,최신 전체 **890검사 OK251.922초**(private full-final.log). 이전885검사 OK250.240초는 cache정리/coverage보강 전 단계 근거다. 최종 뒤의 문서/링크 감사는 별도로 수행한다. 앱src는 시작1f0deae와 같고 모델/명령/동의/기억/예약/송신/큐 정책을 바꾸지 않았다. 실제 SDK HTTP mock 기능 회귀를 새 어댑터의 GPU Runtime 통합 PASS로 확대하지 않는다. 이전 번들83검사 근거는 같은 앱src의 과거 실행으로 유지했으며 이번에 새로 실행하지 않았다.

운영 설정/bootstrap/두DB/기존final 소비장부 **5개SHA256 동일**(preserved-final.json). 사용한12개 model shard는 첫 전체준비 전과 모든 전체후보 종료 후의 SHA256이 모두동일했다(model-shards-final.json). 이 파일hash 기준점은188후보 뒤에 잡았으므로 전체차수 최초부터의 모델binary hash 보장으로 소급하지 않는다.188에서는 frozen version/sentinel과 adapter-only 저장 경로를 검증했다. 기존 원본 단일파일/개인LoRA는 변경하지 않았다. GPU작업과own session은 모두종료했고 종료뒤집계는free14,324MiB/42°C였다. 집계변동을 다른앱의원인으로조사/단정하거나 신규probe의allocated0을과거프로세스의0이라고주장하지 않는다.

Portable은 공개 src/docs171파일·README/기본프로필 포함 **173쌍**,manifest **21,575파일**의 목록/크기/전체SHA256·금지파일 경계를 감사한다(private portable-final-verified.json). 실행src가 같아 문서만 증분 반영하며 불필요한 재빌드는 하지 않는다. 새 연구도구/정답/원문/adapter/로그/HTML은 번들에 넣지 않는다. 새 GUI·실제 Portable GPU·깨끗한 다른 Windows·8시간·실제 Discord는 NOT VERIFIED/BLOCKED로 유지한다. 공개 staged 목록/내용/민감정보 패턴/링크를 검토한 소스·합성테스트·비식별문서만 일반 main push한다. 마지막 문서commit과최종HEAD는 main/최종보고로식별하며 amend/강제push를하지않는다.

private checkpoint.json/evaluation-usage.json은188/264학습과각32생성·개발손실·미소비독립/최종·미학습32초안을분리한다. 재현이필요하면새출력경로와기존로컬모델·고정source/export를지정하고tiny-cache-proof/report.json·기존결정성proof·--learning-rates 0.0001·--cache-hygiene를사용한다. 옵션구문은run_persona_pilot.py --help와private실제명령을따른다. 원문/설정/카드를잘라예산에맞추거나직전실패를그대로무한재시도하지않는다. 연구기본값은cache정리OFF이고현재앱의기본모델도no-LoRA다.

현재 **DEVELOPMENT / RELEASE BLOCKED**다. 다음우선순위는1)학습/개발의기능·operation·조회결과/동의/영수증커버리지분포를근거로원천분리대조정답보강,2)인칭/시점/논리모순과행동차이를공통안내문편향없이편집검토,3)새32조건부초안의추가검토/통합후새질문으로검증이다. 개발실패문항을새독립평가로재사용하지않는다. 불충분한품질을더큰rank/epoch/추가LLM호출로덮지않는다. 인격수렴·일반허위기억/기능약속·한국어주장추출·사회적판단·실제동의명령접근·실사용/배포·장기게이트는해결됐다고선언하지않는다.
