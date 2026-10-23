# 대규모 대화 평가·출처 분리 후보 — 2026-10-24

## 목표와 현재 경계

시작 main/local/remote `8c70097`, clean. 단순 문장 차이가 아니라 반응 전략·가상 인격·현실 사실성을 분리해 측정한다. 정식 릴리즈는 **BLOCKED**다. 이번 평가 도구는 운영 설정/DB/프로필/모델을 변경하지 않는다. 실제 Discord 인증·REST·Gateway·송신·명령 동기화는 금지하고 SDK HTTP mock과 구분한다. 게임/사용자 Desktop은 조사·조작·캡처하지 않는다.

현재 실행 경로의 카드·900/6000 토큰 예산·한 GPU 공정 Worker·동의·실제 원본 reply는 재설계하지 않는다. 기존702검사와 이전 GPU 기록은 당시 소스의 근거이며 이번 검사는 아래 마감 결과를 따른다. 이전 공동 카페 경험4/4 실패는 개발 회귀 자료이고 새 독립 평가가 아니다.

## 공개 자료 조사와 수집 결정

원문·라이선스 사본·출력은 `local_data/evaluation-20261024/`에만 둔다. `acquisition.json`에 고정 upstream commit, 다운로드 시각(UTC), 최종 URL, 바이트 수, SHA256, 용도와 출처를 기록한다. 재개는 기록된 해시가 일치할 때만 허용하고 원본을 덮어쓰지 않는다. 모델/토크나이저를 다운로드하지 않는다.

|자료|확인 근거·조건|이번 취급|
|---|---|---|
|Blended Skill Talk|[ParlAI 데이터 문서](https://github.com/facebookresearch/ParlAI/blob/a29567f7ce76992fd1f03c51ba9e3b155a37ea51/parlai/tasks/blended_skill_talk/README.md), 별도 LICENSE_DOCUMENTATION CC BY4.0. 프레임워크 MIT와 구분|공식 archive의 공개 SHA256 확인. 약36MiB 전체 archive가 최소 공식 묶음이어서48MiB 상한으로 수집하고 약17MiB train JSON만 메모리에서 읽음. archive 경로 추출/실행 없음|
|PersonaChat / ConvAI2|[공식 ConvAI2 문서](https://github.com/facebookresearch/ParlAI/blob/a29567f7ce76992fd1f03c51ba9e3b155a37ea51/parlai/tasks/convai2/README.md)는 CC4.0 BY. 원래 PersonaChat task README에는 같은 명시가 없어 모든 미러에 확대하지 않음|원본/미러 추가 수집 없음. BST의 ConvAI2 seed 계열을 개발에만 사용|
|EmpatheticDialogues|[원 저작자 LICENSE](https://github.com/facebookresearch/EmpatheticDialogues/blob/main/LICENSE) CC BY-NC4.0|원본 추가 수집 없음. KoED와의 파생 관계 때문에 ED seed의 BST1,620개를 이번 corpus에서 제외|
|KoED|[공식 README](https://github.com/KUNLP/KoED/blob/de9fe3c5c3e5d48ab82812b75560a44b55c06272/README.md) CC BY-NC4.0, ED의 단순 번역이 아닌 문화적 재구성|1,360대화 원본 약2.83MiB 수집, 한국어320개를 최종 전용으로 봉인. 비상업 연구 평가용, 상업/배포/학습 사용 근거로 삼지 않음|
|LoCoMo|[공식 LICENSE](https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/LICENSE.txt)는 저장소에 CC BY-NC4.0. 코드 MIT라고 가정하지 않음|약2.68MiB 자료 수집. 코드 복사 없음. 10원천 대화에서 최대3세션씩30개 프로토콜, 영어8~12개 화자 턴|
|WildChat|[공식 데이터 카드](https://huggingface.co/datasets/allenai/WildChat) ODC-BY. redacted flag를 비식별화 보장으로 해석하지 않음|공개 카드만 조사. 실제 사용자 원문·잔존 개인정보의 표본 검토 체계가 충분하지 않아 이번 원문 수집/생성에서는 제외|
|한국어 AI Hub|[공감형 대화 자료 안내](https://aihub.or.kr/aihubdata/data/view.do?currMenu=115&dataSetSn=71305&topMenu=100)|로그인·이용정책·개별 접근 조건이 필요하므로 원문 미수집. 별도 조건 없는 공개 원문이라고 표시하지 않음|

라이선스가 다른 원문을 EchoMate MIT로 재배포하거나 Portable에 넣지 않는다. NC 자료가 포함된 합성/평가 산출물도 기본적으로 로컬 연구용이다. AI Hub의 다른 연속 감정 대화와 번역 미러는 접근/파생 조건이 확정되지 않아 채택하지 않았다.

## 자료 규모·분할과 품질 감사

공개 자료 시나리오 **1,650개**: 개발200(BST ConvAI2 seed), 표준1,130(BST WoW1,100+LoCoMo30), 최종320(KoED). 영어1,330/한국어320이며, 여기에 직접 작성한 한국어 개발21개를 별도로 제공한다. 표준 공통 입력100개 이상을 네 프로필에 재사용할 수 있으나 실제 GPU에서100개씩 모두 실행했다는 뜻은 아니다.

BST30개는4~8턴, LoCoMo30개는8~12턴 프로토콜이다. 전자를 장시간/장기 기억30개 검증으로 부르지 않는다. LoCoMo도30독립 인물이 아니라10개 원천 대화의30세션이다. 수십 세션을 잇는 장기 기억 품질 목표는 아직 미달이다. 한국어 개발/표준 다양성도 영어 분량과 같은 수준이 아니다.

원천 대화 그룹을 보존한다. KoED의 영어/Korean 대역과 그 원천 ED 계열은 최종 영역 밖에서 사용하지 않는다. 같은 원천 그룹의 다른 턴·정규화 동일 발언·80자 연속 복사 구간이 개발/표준/최종을 넘으면 거부한다. 의미·번역 누수를 완전히 검출한 것은 아니다. 임베딩이나 외부 모델을 내려받지 않았고, 의미가 유사한 일반 상황은 사람 표본 검토가 필요하다.

개발/표준30개 표본을 직접 검토했다. 대명사·앞선 발언을 생략한 짧은 원문이 있어 처음에는 첫 문장만 추출하던 도구를 수정했다. BST의 두 선행 인간 발언을 별도 가상 출처로 보존하며 EchoMate의 실제 assistant 이력으로 넣지 않는다. 출처의 인물 설정도 현재 캐릭터 카드로 대체하지 않는다. 이는 가상 상황 반응 평가이며 실제 Discord 이벤트 평가가 아니다. LoCoMo 사람 턴을 생성 답변과 이어 재생하면 원래 상대의 말이 생략돼 부자연스러울 수 있어 별도 한계로 기록한다.

이메일·긴 전화번호·URL·credential 형태·Discord 멘션을 탐지하면 해당 사례를 제외한다. 개인정보가 없다고 인증하는 도구가 아니며 이름·사건의 실제 식별성은 완전히 검증하지 못했다. 최종 원문은 개발자가 표본을 들여다보는 대신 봉인/소비 장부로 접근을 기록한다.

## 실행 및 평가 계약

`prepare_dialogue_evaluation.py acquire/build` → 원문 해시 검증/원천 분리/최종 봉인 → `run_dialogue_evaluation.py` → 개별 비공개 JSON/HTML/블라인드 묶음 → `review_dialogue_evaluation.py` 순서다. 산출물 경로는 프로젝트 `local_data`의 하위로 제한한다. HTML은 텍스트를 escape하며 외부 요청·script를 CSP로 금지한다.

기존 `echomate_studio.persona_dataset`은 별도 권리/개인정보 검토가 필요한 과거 원문 스타일 학습용이며, 이번 공개 대화의 라이선스·선행 대화·원천 가족/봉인 계약과 다르다. 이를 자동 학습 자료로 연결하지 않았다. 실제 생성은 기존 `LocalBackend`/`InstanceLease`/`MemoryRecorder`/모델 validator와 Worker를 그대로 재사용하고 새 대화 Runtime이나 모델 로더를 만들지 않았다. 모델 사전학습에 공개 자료가 들어갔는지는 확인하지 못하므로 최종 독립성은 이번 개발 반복에서의 미사용을 뜻한다.

- **Fast:** CPU 계약 검사·캐시된 출력 재검토·근거 ID 대조·사람의 블라인드 투표/원자 주장 주석 수입. 키워드 flag가 없다고 사실성 PASS로 하지 않는다.
- **Standard:** 사례 수·시간이 제한된 실제 Gemma 생성. 동일 모델/파라미터/프로필과 실제 chat-template prompt hash, 선택된 lore/example ID, token/TTFT/큐·worker 시간과 메모리를 기록한다.
- **Deep:** `--long`에서 실제 생성 답변을 다음 턴에 넣고 원래 인간 답변을 정답처럼 재사용하지 않는다. 작은 배치로 운영하며 전체 자료를 매 수정마다 재실행하지 않는다.
- **Final:** 후보 source/출처 계약 해시 고정 후 최종 파일 hash 확인. 사례 ID를 생성 전에 소비 장부에 기록하며 실패·중단도 미사용으로 되돌리지 않는다. 한 번 본 자료의 재사용은 개발 회귀다. 소비 후 corpus 재빌드도 거부한다.

캐시 식별자는 사례/맥락/정답/프로필/실행 source/모델 설정/생성 설정/평가 버전을 포함한다. GPU 응답 자동 재사용은 하지 않으며 Fast는 보존된 응답의 재분석이다. 모델 config/tokenizer 설정/index hash와 라이브러리 버전을 기록하지만 매 평가마다 수십 GiB 가중치 전체를 다시 hash하지 않으므로 가중치 전체의 새로운 무결성 인증은 아니다.

### 평가자의 한계

개발자 재현 순서: 프로젝트 Python 환경과 `PYTHONPATH=src;tests;tools`에서 `prepare_dialogue_evaluation.py acquire --root local_data/<새 평가>` → 같은 root의 `build` → `freeze`를 실행한다. 이미 소비한 root/candidate seal을 덮어쓰지 않는다. 생성 도구는 `--suite standard --limit 4 --phase baseline --output local_data/<새 실행> --model <기존 검증 모델 폴더>`로 작은 배치를 먼저 실행한다. Final/paired campaign은 추가로 `--candidate-seal local_data/<새 평가>/candidate-freeze.json`을 지정한다. 실제 source가 고정되지 않았거나 품질 실패가 남았으면 Final을 반복 소모하지 않는다. 로컬 결과 재검은 `review_dialogue_evaluation.py --run local_data/<실행>`이며 사람의16응답 HTML 투표를 저장한 뒤 같은 도구의 `--votes <local_data 안의 투표 파일>`로 점수를 대조할 수 있다. 기본 경로 밖 corpus를 쓰면 생성 도구의 `--corpus`도 해당 `corpus` 디렉터리로 지정한다.

원자 주장 검사기는 합성 사실 ID/value 및 `current/dialogue/consented_memory/card/lore/general/unverified/none` 출처를 대조한다. 동의 기억은 본인·서버·동의가 맞아야 하고 가상 lore는 현실 공동 경험의 근거가 될 수 없다. 자연어 전체에서 자동으로 모든 주장을 추출하거나 일반 지식을 판정하는 시스템은 아니다. 미주석 응답은 REQUIRES_CLAIM_REVIEW로 남긴다. 욕설 단어만으로 실패 처리하지 않고 불편 중지 맥락은 따로 검토한다.

블라인드 파일은 응답과 임의 ID만 포함한다. 정답 profile/case/phase는 별도 key다. 직접 이름/배경 고유명/명시적 캐릭터 유형을 드러낸 응답은 구별 평가에서 제외하고 제외 수를 기록한다. 4인 균형 기준25%,70%는 도전 목표다. 혼동행렬·macro recall·Wilson95% 구간을 보고하며 작은 표본의 높은 점수를 사람 평가 증명으로 쓰지 않는다.

상주 Gemma를 활용하는 선택형 보조 분류는 두 번의 라벨 순서를 바꿔 안정성을 측정하고 쉬운 수작업4응답으로 교정한다. 같은 생성 모델 평가의 자기 선호 편향, 작은 교정 자료의 한계를 기록한다. 이 분류는 자연스러움·정확성·상황에 맞는 독설의 종합 품질 평가가 아니다. [LLM-as-a-judge 연구](https://arxiv.org/abs/2306.05685)의 순서/길이/자기 선호 문제와 [FActScore](https://arxiv.org/abs/2305.14251)의 원자 사실·근거 구분을 설계에 참고했고 논문의 성능을 이 도구의 성능으로 인용하지 않는다.

## 이번 baseline 및 후보

64응답 baseline: 텍스트44응답/실제 생성45회(재작성1), 물리적 공동 경험 한계 안내20응답은 GPU0회. 생성 응답 p50/p95 **6.805/22.396초**, TTFT **0.734/0.790초**, 준비37.281초. 해제 후 allocated1KiB/reserved2MiB. 문장 길이가 달라 이전 소수 짧은 QA와 인과적 속도 비교를 하지 않는다.

핵심 실패:

1. **없는 취향/저장 성공:** 기억에 없다고 명시한 요청에도 음식 취향을 지어내거나 기억하겠다고 약속했다. 직접 생성 계층 검사이므로 Runtime의 별도 기능 안내가 똑같이 실패했다고 단정하지 않는다.
2. **예시 출처 혼동:** 장보기 실수 질문에 기존 예시의 탄 빵 사건으로 답했다. 사소한 표현 차이가 아니라 현재 사건을 바꾼 사실 오류다.
3. **스타일 수렴:** 위로/간접 우려/인용 질문에서 비슷한 접근이 많다. 사용자가 위로를 원할 때 캐릭터 차별성만 위해 공감을 억제하지 않는다.
4. **가상 설정의 확장:** 명시되지 않은 가상 사건을 덧붙이는 경우가 있다. 가상 창작과 카드 모순, 현실 공동 경험 조작을 같은 종류로 합산하지 않는다.

후보 `dialogue_evidence_candidate.py`는 평가 도구에만 존재한다. 현재 주장/검색된 기억/가상 카드/다른 상황 예시/assistant 이력/미확인 저장을 분리한 짧은 출처 계약을 기존 생성에 넣는다. 추가 분류/GPU 모델/DB/검색 기능을 만들지 않으며 출력 문장을 강제하지 않는다. `not_retrieved`는 검색하지 않았다는 상태일 뿐, 기능 없음이나 기억 전체 부재를 뜻하지 않는다. 원본 정책·카드·사용자 발언은 보존한다.

독립 자료를 열기 전에 후보와 채택 기준을 고정했다. 없는 개인 사실/저장 약속이 남거나 가상 lore/스타일이 무너지거나 감당하기 어려운 지연이면 운영 코드에 채택하지 않는다. 무조건 거절·침묵·추가 GPU 검증으로 메우지 않는다. 운영 Runtime으로 승격하려면 실제 조회 성공/빈 결과/실패/철회 상태의 전달과 최신성 검증도 필요하다.

## 마감 결과

실제 실행 결과와 채택/기각, 전체 회귀·운영 해시·Portable·Git 마감은 아래 누적한다. 위 자료 규모와 도구 구현만으로 목표 대화 품질을 PASS 처리하지 않는다.

### 비교 실패 후 다음 접근의 비용

|대안|예상 이득|비용·채택 전 조건|
|---|---|---|
|현재 후보처럼 출처 계약을 생성 입력에 추가|예시 사건과 현재 사건 분리를 도울 가능성|추가 GPU 호출0회지만 입력 토큰/답변 길이가 늘 수 있음. 실제 생성이 계약을 따르는지 확인해야 하며 설명 자체는 검증기가 아님|
|기존 개인 기억 조회의 확정 결과와 비사실적 캐릭터 반응을 분리|검색 실패/빈 결과/동의 철회 상태를 사실로 유지|기존 `handle_request`를 재사용하는 최소 확장이 우선. 모호한 질문의 분류와 문맥 최신성, 자연스러움 검증이 필요하고 모든 기억 질문을 고정 거절로 바꾸면 안 됨|
|근거 ID가 있는 원자 주장 계획과 자유로운 표현을 분리|없는 개인 사실을 ID 검증에서 차단 가능|한국어 주장 추출/계획 누락의 정확도 미검증. 호출을 나누면 추가 큐/TTFT/토큰 비용, 한 호출로 합치면 출력 계약 부담. 자유 텍스트가 계획을 위반하는지도 별도 검증 필요|
|캐릭터별 합성 선호/무근거 거부 대조 자료와 LoRA|말투보다 반응 전략을 학습할 가능성|평가자 교정·사람 구별 평가·동의 없는 원문 제외가 먼저. 가변 배경/개인 기억을 가중치에 넣지 않음. 과적합·기본 정확성 손실·어댑터/큐 수명주기 비용을 함께 평가|

[Gemma4 공식 개요](https://ai.google.dev/gemma/docs/core.md)는 fine-tuning 메모리가 추론보다 훨씬 크고 framework/batch/PEFT에 의존한다고 설명한다. [12B 공식 개발 안내](https://developers.googleblog.com/gemma-4-12b-the-developer-guide/)의16GB 로컬 실행 설명을 Windows16GB의 안전한 학습 보장으로 해석하지 않는다. [PEFT quantization 안내](https://huggingface.co/docs/peft/developer_guides/quantization)의 k-bit 준비와 NF4/LoRA 경로는 참고 가능한 방법이지 이 PC에서 검증한 학습 결과가 아니다.

현재 torch2.9.1+cu128/Transformers5.20.1/PEFT0.21.2/bitsandbytes0.50.2/Safetensors0.8.0을 확인했다. 라이브러리 설치/추가 모델 다운로드/학습/어댑터 기본 적용은 하지 않았다. 12B의 단순4bit 가중치 크기만으로 activation·gradient·optimizer·Windows commit 피크를 계산할 수 없어 실제16GB 학습 가능 여부는 **NOT VERIFIED**다. 이번 결과로 LoRA가 더 낫다고 결론 내리지 않는다. 동일 프롬프트의 무한 재작성보다 평가 자료와 사람 근거, 출처 검증이 가능한 구조를 다음 작업으로 삼는다.
