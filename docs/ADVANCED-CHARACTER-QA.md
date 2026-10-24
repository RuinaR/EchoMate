# Advanced Character AI — 원천·SFT·고정 참조 DPO QA

2026-10-25 시작 local/main/origin `633a4f2b89c16c35a4967a933d0a3a23a415249d`, clean·fetch 일치. 최신 제품 게이트는 [RELEASE-CHECKLIST](RELEASE-CHECKLIST.md), 장기 단계/재개는 [개발 계획](ADVANCED-CHARACTER-ROADMAP.md)을 따른다. **DEVELOPMENT / RELEASE BLOCKED**. 이번 변경은 연구 도구·합성 테스트·문서이며 앱src/운영no-LoRA·설정·DB schema·송신/동의 정책은 변경하지 않았다.

## 결론과 실제 진행

공개 원천의 선택 확보·권리 상태별 혼합 참조·새 조건부80응답·편집 선호72쌍을 구축하고 **실제12B SFT와 DPO를 각각 완료**했다. 두 후보 모두 인격 차별성과 사실성의 공동 개선을 입증하지 못해 **기각**했다. 메모리·gradient·저장/재개 호환성 통과를 제품 대화 품질 PASS로 바꾸지 않았다. 운영모델/기존LoRA는 그대로이고 모든 새 adapter는 private에만 있다.

초기 aggregate free14,602MiB/40°C, RAM가용16.50GiB/commit가용44.09GiB였다. DPO 전에는 free13,390MiB/RAM8.75GiB 수준으로 호스트 여유가 변했고 다시 검사했다. 다른 앱의 종류나 프로세스를 조사하지 않았다. 실제 단일 상주 모델을 순차 실행했고 기존 GPU2GiB·RAM3GiB·commit2GiB·85°C미만 guard를 유지했다.

## 공개 원천 확보와 권리 상태

원문/다운로드 시각·최종URL·정확 bytes·SHA256·pinned revision/카드·고지는 private acquisition/research manifest에 보존했다. URL에 있는 기사나 외부 링크를 따라 수집하지 않았다. 접근제한/계정/인증 우회·유료 서비스·추가 모델 다운로드·패키지/시스템 설정 변경은 없다.

|원천|원본 근거/권리 상태|이번 활용|
|---|---|---|
|[Topical-Chat](https://github.com/alexa/Topical-Chat/tree/7c939229cbcf6f55f6977b341a5a2f2fe982d53f)|[DATALICENSE](https://github.com/alexa/Topical-Chat/blob/7c939229cbcf6f55f6977b341a5a2f2fe982d53f/DATALICENSE) CDLA-Sharing1.0, 코드 라이선스와 별개. 제3자 wiki/WaPo 고지 함께 확보|train60,771,967bytes/8,628대화, audio/전체 repo 미수집. 600원천가족 editorial queue, 자동 학습정답 승인0|
|[LongMemEval cleaned](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned)|공식 repo/카드 MIT, revision98d7416…|oracle15,388,478bytes/500문항만 확보. 장기 평가 원천으로 보류, 학습/모델입력0. 큰s/m 전체는 받지 않음|
|[BeyondDialogue](https://github.com/yuyouyu32/BeyondDialogue/tree/c994140ca7aaf660f8bcbc5b0c00cab6fcc23c57)|라이선스 파일 미표기, UNSPECIFIED 유지|공개 CESRP1,803,773bytes/500문항 확보, 혼합 로컬 연구 참조. 원문을 SFT target으로 복사하지 않음|
|[CharacterBench](https://github.com/thu-coai/CharacterBench/tree/66c113cf3c011697d4c232de6beabb7797a9a380)|원 repo 라이선스 미표기. 동명 다른 프로젝트의 Apache를 적용하지 않음|behavior-consistency human 한 파일3,561,000bytes/250문항 확보. 이름/프로필·원문·점수를 정답으로 복제하지 않음|
|[PersonaGym](https://github.com/vsamuel2003/PersonaGym/tree/536f705e610289c38d84e083fcea6ea5093d3a25)|repo MIT, 원천·모델 출력/평가 신뢰성은 별도|고정 metadata/README/license·파일 크기 확인. 전체 질문/모델/외부 API 실행0|
|[ConvAI2/PersonaChat](https://github.com/facebookresearch/ParlAI/tree/a29567f7ce76992fd1f03c51ba9e3b155a37ea51/parlai/tasks/convai2)|공식 데이터 CC BY4.0. 미러에 license 없다는 이유로 원본 조건이 사라지지 않음|기존 BST 원천 분리 유지, 새 공식 license 확인. 별도 전체 재다운로드/미러 학습0|
|[Blended Skill Talk](https://github.com/facebookresearch/ParlAI/tree/a29567f7ce76992fd1f03c51ba9e3b155a37ea51/parlai/tasks/blended_skill_talk)|데이터 CC BY4.0, 코드 MIT와 구분|이전1,838후보/1,773component/가족 격리를 보존. 새 데이터로 중복 계수하지 않음|
|[Wizard of Wikipedia](https://github.com/facebookresearch/ParlAI/tree/a29567f7ce76992fd1f03c51ba9e3b155a37ea51/parlai/tasks/wizard_of_wikipedia)|공식 데이터 CC BY4.0 LICENSE_DOCUMENTATION 확인; 출처/변경 고지와 제3자 자료 구분|license와 build 구조 검토. 기존BST seed와 겹치는 원문을 새 독립 학습으로 받지 않음|
|[EmpatheticDialogues 원본](https://github.com/facebookresearch/EmpatheticDialogues/blob/9649114c71e1af32189a3973b3598dc311297560/LICENSE)|원본 NC4.0과 [ParlAI task](https://github.com/facebookresearch/ParlAI/blob/a29567f7ce76992fd1f03c51ba9e3b155a37ea51/parlai/tasks/empathetic_dialogues/LICENSE_DOCUMENTATION)의 BY4.0 표시 충돌|이번 학습 제외. 느슨한 표기만 선택하지 않으며 기존ED seed 제외를 유지|
|[KorEmpatheticDialogues](https://huggingface.co/datasets/passing2961/KorEmpatheticDialogues), [KoED](https://github.com/KUNLP/KoED/tree/de9fe3c5c3e5d48ab82812b75560a44b55c06272)|각 카드/README의 CC BY-NC4.0, ED 파생 관계 유지|카드/원천 조건 확보. 새 한국어 raw 학습0|
|[DailyDialog](https://github.com/facebookresearch/ParlAI/tree/a29567f7ce76992fd1f03c51ba9e3b155a37ea51/parlai/tasks/dailydialog)|원천 NC-SA 경계·미러 license 미표기를 구분|공식 task/원천 조사, 이번 학습 제외|
|[LoCoMo](https://github.com/snap-research/locomo/blob/main/LICENSE.txt)|기존 NC 경계 유지|이전 자료 보존, 이번 새 학습0|
|[Multi-Session Chat](https://github.com/facebookresearch/ParlAI/tree/a29567f7ce76992fd1f03c51ba9e3b155a37ea51/parlai/tasks/msc)|코드 MIT와 데이터 조건을 동일시하지 않음|공식 build 구조/원천 관계 검토, raw 승인0|
|[KoDialogBench](https://github.com/sb-jang/kodialogbench/tree/36a6ba95a4bb325e189d258e377487d22c9ec5b7)|repo MIT와 AI Hub/ED/DailyDialog 등 개별 원천·번역 조건 구분|README/metadata/license 확인. 혼합 원천 전체를 MIT학습 자료로 승격하지 않음|
|[UltraFeedback binarized](https://huggingface.co/datasets/HuggingFaceH4/ultrafeedback_binarized/tree/3949bf5f8c17c394422ccfab0c31ea9c20bdeb85)|카드 MIT, prompt 구성 원천/모델 생성 선호의 신뢰성은 별도|공식 카드/버전만 확보. 원래 AI 점수·pair를 EchoMate 정답으로 자동 승인하지 않음|

Topical archive SHA256 `39a079d8464ea5f44f0fd78dbc85fd4eed96303347cbf4f9301f823e3c0f437f`, LongMem oracle `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`, Beyond `21a5b6c7e26a13f242a29746922411c937ece52ff45c33bfd762081ae85b4435`, CharacterBench `243f1692c336df199e0e2bb0ccbc38cf2de16db203cd3b82ed1426846f822c91`. 정확한 다운로드 시각/크기와 고지는 private acquisition.json을 따른다.

## 혼합 참조와 실제 정답의 구분

사용자의 추가 지시로 **라이선스 미표기 자료도 혼합 로컬 연구에 포함**했다. 미표기 자료를 자동제외하거나 자유이용 라이선스로 재명명하지 않는다. 다만 명시 NC·제3자 권리·개인정보·보호 대사 대량 복제·접근 제한·원문 외부 공개 경계는 유지한다. unknown 자료의 자동 raw-target 승인과 재배포 승인은 여전히0이며, 이는 이번 편집/개인정보/내용 검토 단계이지 사용자의 혼합 연구 승인을 다시 요구하는 절차가 아니다.

Topical은 기사URL/대화 정규화 hash 기반 family에서 한 대화씩 선택했다. 8,628중 개인정보/길이 경고10개를 제외한2,488가족에서600개를 고정했다(train483/dev50/별도67). 패턴 screen은 이름·간접식별·의미 중복의 완전 부재를 보장하지 않는다. shared article을 다른 split에 넣지 않고 원문URL을 직접 열지 않는다.

혼합 index는 Topical600+Beyond500+CharacterBench250=**1,350 source pointers/842가족**이다. 같은 정규화 캐릭터 이름241가족을 분리하지 않도록 보강했다. Beyond의 공통 system prompt를 실제 사건 식별자로 쓸 수 없고 중·영/인물 교차도 검증되지 않아500문항을 보수적으로 한 가족에 유지했다. 따라서842를 의미적으로 독립인 상황 수로 인증하지 않는다. 기존 Topical 분할을 보존하고 충돌을 거절한다. 미사용 index v1/v2도 보존했고 v3가 최신이다. 기존 EchoMate final316/소비장부는 그대로다.

## 새로운 SFT와 선호 자료

외부 원문을 번역해 채우지 않고 기존 독창적4카드의 새로운20사건·80응답(train64/dev16)을 개별 작성했다. 조회 미실행/실패/빈 성공/실제 항목, 동의 철회, 타인 저장 발언 인용, 조건부 제안, 화자/시점 정정, 조언으로 요청 전환, 불편 뒤 장난 중단, 공정함/정직함/자긍심 등을 넣었다. 기존376·이전80·기존 adapter·평가 원문은 수정하지 않았다.

source/split/claim span/근거/기능 상태/영수증/마스크 계약80/80과 새·기존 자료 표면 near 중복 경고0을 확인했다. **이는 자연어 의미·자연스러움·실제 인격 품질 PASS가 아니다.** 기분은20상황 중 평온15/짜증1/슬픔1/피곤함1/기쁨2, 관계 일반13/친밀4/불편1/처음1/거리1이라 여전히 불균형하다. 네 캐릭터는 각20응답이며 shy/curious는 이번 실제학습 대상이 아니다.

실제 Gemma tokenizer/template로 train275–399token/target28–41, dev287–384/target29–43을 보존했다. 마지막 assistant completion만 loss, system/user/과거 assistant와 padding은 제외한다. 실제 padding/packing/절단은 사용하지 않았다. 정답·strategy 주석은 입력에 넣지 않는다.

같은 source/card/evidence의80선호 후보 중 공정함/자긍심의 단일 우열이 모호한8쌍을 제외해 **72쌍(train56/dev16)**을 구성했다. 이유는 사실/기능 상태·화자/시점·현재 의도·관계 경계·인격에 연결하고 issue span을 실제 rejected 문장에 묶었다. 정확한 source family/split은 SFT에서 상속하며 독립/최종을 preference training으로 relabel하지 않는다. train은14사건의56캐릭터 pair다. 전체 rejected는18고유 문장이 네 캐릭터에 반복되므로72독립 상황이라고 부르지 않는다. human preference validation은 NOT VERIFIED, AI judge 승인0이다.

추가 사용자 지시 뒤에는 Topical의 감정 분류·Beyond의 감정/관계/성격/스타일 분류 **축**을 참고한8개 새 독창적 사건/32응답(train24/dev8)을 별도 초안으로 작성했다. 외부 질문·정답·이름·줄거리·프로필·대사를 쓰지 않았고 원문 SFT 파생 승인으로 세지 않는다. 자체 응답은 원본 synthetic MIT, 참조 자료는 CDLA/UNSPECIFIED 라벨과 hash를 그대로 남긴다. 실제 tokenizer/template로 추가32개의 정답 mask·완전 입력도 확인했다(train274–345/dev최대342token). 현재두pilot에는 중간 삽입하지 않았으며 이32개는 미학습이다. 새 원문에서 실제 사건 정답을 수천 개 확보한 단계와 구분한다.

편집 사후 감사에서는 피곤함2target에 구현/설정 설명처럼 들리는 표현을 발견했다. 고정 자료를 뒤늦게 덮어쓰지 않고 새 버전에서 제외/재작성할 과제로 남겼다. 두 응답 모두 품질이 낮은 pair를 제외해야 하며, schema 통과만으로 자연스러움이 승인됐다고 하지 않는다. 이번 1,000–3,000목표는 **미달**이다.

## SFT 실제 실행

rank4/alpha8/dropout0.05, text q/v88모듈·2,596,864trainable, NF4/doublequant/BF16/frozenembedding, 선택 logits·non-reentrant train checkpoint·cache hygiene를 재사용했다. AdamW1e-4·batch1/accum4·clip1·cosine warmup5%·1epoch, 16유효update(재생 포함17물리update)다. 새로운 자료에서 한 설정만 실행했고 LR탐색을 반복하지 않았다.

고정20입력(새dev16+이미소비된 query실패4)×no-LoRA/이전264/새SFT=60생성이다. CE4.696719→3.944231, step8저장→복원→step9 metric/가중치 exact. 그러나 gentle의 확인되지 않은 좌석 선호 기억, playful의 미래 기억 약속, dry의 사건 부재 단정, 일반 공감/질문 수렴, analytical query의 blocked channel이 남았다. **후보 기각**, 새 독립56/final316 소비0. 모델 한계와 자료 부족의 단독 원인까지 확정하지 않는다.

## DPO 설계·공식 근거·호환성

[DPO 논문](https://arxiv.org/abs/2305.18290), [TRL DPO](https://huggingface.co/docs/trl/dpo_trainer), [ORPO](https://huggingface.co/docs/trl/orpo_trainer), [KTO](https://huggingface.co/docs/trl/kto_trainer)를 검토했다. TRL은 설치돼 있지 않으며 **TRL DPOTrainer/Windows 전체 API 통과로 주장하지 않는다.** 안정된 기존 optimizer/checkpoint/양자화 경로에 논문 목적함수를 구현한 별도 연구 도구다. ORPO는 reference-free 대안이지만 목적함수 변경까지 동시에 탐색하지 않았다. KTO는 unpaired label/기준 분포 설계가 별도로 필요해 이번 pair pilot에 무조건 도입하지 않았다.

completion causal log probability는 길이 평균이 아닌 **합**이다. chosen/rejected 양쪽 prompt를 모두 mask하고 EOS를 포함한다. DPO는 beta0.1의 logistic loss를 사용한다. 초기 **SFT adapter가 활성화된 고정 모델**로72쌍의 reference logps를 한번 계산한 뒤 data/pair/modelheader/tokenizer/version/초기adapter hash에 결합했다. adapter를 끈 원본 no-LoRA를 SFT reference로 잘못 쓰지 않으며, 변화하는 policy로 ref를 갱신하지 않는다. ref model을 별도로 로딩하지 않는다.

policy chosen/rejected의 train-mode no-grad 값과 RNG를 먼저 얻은 뒤 각 forward를 같은 RNG로 재생해 chain-rule coefficient로 순차 backward한다. 한 graph만 유지하며 dropout 재생 값이 다르면 중단한다. 1pair당4policy forward로 계산량을 교환하고, gradient accumulation은 pair 평균으로 계산한다. 각 live graph/단계에 guard를 적용하고 optimizer 전에 finitegradient/clip을 확인한다. 참고 scalars/체크포인트에 원문이나 운영 상태를 넣지 않는다.

CPU와 tinyNF4에서 두 graph 방식 대비 loss·전체 gradient 최대 차이0, optimizer/scheduler/CPU·CUDA·Python RNG 재생 metric·adapterweights exact를 확인했다. 처음 tiny CPU는 NF4 전용 준비 함수 오사용으로 중단했고, 다음 시도는 JSON tuple/list 계약 불일치로 중단했다. 각각 수정·새 출력 폴더에서 재검증했으며 실패 기록을 보존했다.

첫 NF4 tiny는 double_quant=False였고 실제12B는 기존검증 double_quant=True였다. 그 구성을 동일하다고 소급하지 않는다. 실제12B에서도 모든 policy 재계산과 checkpoint 재생은 통과했으나, 이후 **double_quant=True까지 같은 추가 tiny 증거**를 실행해 차이0/exact를 확인했다. 최종 preflight는 해당 양자화 필드·정확한 라이브러리 버전·진짜 boolean 증거와 proof hash를 요구하도록 강화했다. 실제 body는 같고 추가 guard·진행상태·오류 증거를 보강한 뒤 전체 회귀를 수행했다. 동일12B 성공 학습을 이유 없이 반복하지 않았다.

## 실제 DPO 결과

새SFT를 읽기 전용 초기 adapter/reference로 사용해56pair/14유효update(재생 포함15물리update), beta0.1/AdamW5e-6/accum4/clip1/cosine warmup5%/1epoch를 실행했다. SFT보다 작은 보수적 첫 preference step이며 최적 LR라고 주장하지 않는다. 초기 SFT reference가 고정돼 초기 eval DPO 기준은 ln2≈0.693147이다. 개발 DPOloss0.699440으로 일반화 개선 신호도 없었다. CE와 DPO loss를 같은 척도로 비교하지 않는다.

동일20입력×no-LoRA/초기SFT/DPO=60생성에서 playful의 실행 없는 기억 약속, query오류의 없음 취급, analytical blocked channel, 일반 공감/질문 수렴이 남았다. DPO visible18/incomplete1/blocked1, 초기SFT19/blocked1이다. 출력 제한·호스트 변화를 함께 기록하고 불완결을 유효 답변으로 세지 않는다. **공동 인격/사실성 개선 불충족으로 기각**했으며 데이터/step/rank 확대·독립/최종소비·운영적용0이다.

## 실행 범위와 다음 작업

새 adapter의 실제 Runtime→SDK HTTP mock **GPU 통합**·장기 기억 DB 통합·새5–100턴 평가·새GUI/PortableGPU/다른Windows/8시간 운용은 NOT VERIFIED다. 짧은 개발 게이트를 통과하지 못한 후보의 평가 규모를 무조건 늘리지 않았다. 기존 기능/SDK mock 회귀와 standalone 학습·생성은 구분한다. 실제 Discord 인증/REST/Gateway/명령/송신0, 게임/다른 앱의 목록·창·화면·입력·내부/파일/네트워크 접근0이다.

다음은 혼합 큐의 **사건 단위 실제 편집**과 최소한의 대조 쌍 품질 검토다. 특히 현재 네 카드/정답이 정직·배려 같은 공통 규범을 반복해 실제 판단 대조가 약할 가능성은 남은 가설이다. 같은 사실에 대해 관계 유지/새로운 시도/검증 가능한 계획/책임 경계의 우선순위가 충돌하는 상황을 만들고, 두 답변 모두 사실적으로 옳지만 한쪽만 카드의 판단을 따르는 hard pair를 검토한다. 기존 behavior_contrast/choice/span 계약과 카드 교환 통제를 재사용하되, 주석 자체를 실제 persona 성공으로 간주하지 않는다. 불확실 상태와 화자·현재 요청 전환·인격 전략을 다른 원천에서도 다루고, metadata 설명 같은 target과 모호한/반복 pair를 보완해야 한다. 32초안도 이 검토를 거친 새 버전으로만 확대한다. 같은 소규모 자료의 LR/rank/epoch 조정이나 검증되지 않은 AI judge 승인을 반복하지 않는다. 장기 상태는 기존 Store/Receipt/fresh/동의 scope를 재사용하는 설계부터 임시 저장소에서 확인한다. 상세 재개는 로드맵과 private checkpoint.json을 따른다.

## 실제 자원·성능 측정

|실제 실행|SFT64|DPO56pair|
|---|---:|---:|
|경과 초|813.453|1165.360|
|계획 GiB(기존2GiB안전 포함)|12.632122|12.641543|
|GPU allocated 피크 GiB|8.814240|7.650050|
|GPU reserved 피크 GiB|8.904297|7.808594|
|own private commit OS 피크 GiB|12.970592|13.042362|
|own working-set OS 피크 GiB|4.838333|4.847286|
|표본 최소 RAM가용 GiB|5.419708|4.336742|
|표본 최소 commit가용 GiB|21.884598|22.263439|
|단계 최소 freeVRAM MiB|4403|4335|
|단계 최고온도°C|66|64|

SFT399token/target41, DPO400token/target43이다. 단계 free/온도와0.2초 recorder 표본은 continuous worst-case 보장이 아니며, PyTorch peak가 드라이버·다른 GPU 사용 전체를 포함하지 않는다. SFT 피크에는 별도128token checkpoint ON/OFF 비교가 포함되고 DPO에는 그 비교가 없어 **이 표만으로 DPO가 SFT보다 메모리 효율이 좋다고 주장하지 않는다.** 단일 graph 방식의 정확성은 별도 tiny gradient/replay 비교로 확인했다. host 여유 변화와 own process 사용량도 혼동하지 않는다.

|동일 cohort20, arm|p50/p95초|TTFT p50초|출력token p50|visible/incomplete/blocked|
|---|---:|---:|---:|---|
|SFT run no-LoRA|14.704 / 26.821|0.329|103.0|17/2/1|
|기존264|4.125 / 5.315|0.336|25.0|19/0/1|
|새 SFT|11.946 / 23.214|0.344|72.0|19/0/1|
|DPO run no-LoRA|14.696 / 26.424|0.328|103.0|17/2/1|
|초기 SFT|11.836 / 23.195|0.343|72.0|19/0/1|
|새 DPO|12.688 / 28.091|0.343|75.5|18/1/1|

모든 arm은 logits_to_keep1·greedy·max192·max_time30·같은 tokenizer/prompt/cohort다. 출력 길이·불완결·호스트 부하와 arm 순서가 달라 raw latency를 throughput 개선이나 Runtime SLO 통과로 해석하지 않는다. 두 run 합계120 generate 요청이며 model 내부 token forward나 checkpoint 재계산의 수와 다르다. DPO는 재생 포함60pair의 policy240forward, reference72pair의144forward를 사용한다. 참조 사전 계산은 학습 데이터나 validation을 추가 gradient 학습으로 바꾸지 않는다.

## 회귀·보존·Portable·Public 마감

연구 코드/합성테스트 **1813a17**, 전체 **929검사 OK260.722초**. Windows loopback 이외 socket connect/DNS를 거절한 기존 wrapper로 실행했고 실제 SDK mock·기존 동의/기억/예약/명령/취소 기능을 보호했다. 함수 단위/초소형/NF4/실제12B 결과를 구분한다. standalone adapter 시험을 Runtime GPU 통합 PASS로 승격하지 않는다. 추가 패키지 설치나 시스템 설정 변경은 없다.

작업 전후 운영설정/bootstrap/두DB/최종 소비장부 **5SHA256 동일**, 기존 모델12shard 전체SHA256 동일, tokenizer/config4파일·이전264 adapter2파일·DPO 초기SFT adapter2파일·원본376/new80 자료 hash 동일을 확인했다. 새/기존 독립56·기존최종316의 모델입력0이다. LongMemEval500·미표기 외부750도 이번 Gemma 학습/생성 입력0이며 private 원문·참조 연구와 모델 소비를 구분한다. 모든 weight/adapter/정답/생성/진단/HTML은 private에만 있다.

Portable은 앱src 변경 없이 공개 docs/README만 증분 반영한다. 공개src/docs·README/기본프로필 **176쌍**, manifest **21,578파일**의 목록/크기/전체SHA256·금지파일 경계를 감사한다. 실제 결과는 private portable-final.json/portable-public-pairs.json에 남긴다. 이전 번들83검사는 동일 앱src의 과거 근거이며 이번 새 실행으로 세지 않는다. 다른 Windows/새GUI/Portable GPU/장시간8h/실제Discord는 NOT VERIFIED/BLOCKED다.

커밋 전 명시 staged 파일/전체내용/diff·민감정보 패턴·링크를 감사한다. 공개 대상은 코드·합성 계약 테스트·비식별 문서뿐이다. 코드 commit 다음 문서commit이 최종 HEAD이며 main push 후 local/origin 일치와 clean을 확인한다. 세션 종료 전에 private checkpoint.json에 최종HEAD/실행 source hash·기각/미검증·다음 source-family 편집 과제를 남긴다. GPU 자식은 종료하고 자동 재시작/heartbeat/무제한 재시도는 만들지 않는다. **정식 RELEASE BLOCKED 유지.**
