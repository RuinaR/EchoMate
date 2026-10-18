# ML 실험 기록

갱신: 2026-10-18. 민감한 원문·응답·데이터 해시·어댑터는 `local_data/`에만 보관한다. 아래는 비식별 집계다.

## 추가 품질 단계: quality-v3 (2026-10-18)

기존 60/120단계와 정책 v2는 보존된 실험 후보이며 최종 모델이 아니다. 아래 신규 평가는 기존 개발/최종 7문항을 재사용하지 않는다. 이전 loss 표는 그 목적함수 안에서만 읽고 신규 생성 평가 순위에 섞지 않는다.

### 원인 재검증과 이번 변경

- 실제 GPU에서 합성 1토큰/6토큰 응답의 prefix 133토큰 전체 마스킹, 응답 첫 토큰·turn 종료 포함을 확인했다. 모델이 반환한 loss와 logits에서 직접 계산한 shifted cross entropy가 각각 6.43014/5.77026으로 일치했다. **마스킹이 정확하다는 것과 목표 데이터가 대화 응답에 적합하다는 것은 별개**다.
- 동일 합성 chat prefix에서 기본 대비 logit RMS 변화는 legacy-2500 0.6350, rank8-60 3.5870, rank8-120 3.5929였다. 세 어댑터가 실제 적용된다. 이 한 입력의 변화량은 품질 점수가 아니다.
- 새 경로는 chat prefix/turn 종료/`enable_thinking=False`를 맞췄지만, 학습 user 지시는 독립 문장 작성이고 추론 user 입력은 실제 질문이다. 형식 정렬만으로 `P(단독 메시지|문장 작성)`를 `P(답변|문맥·관계·질문)`로 바꿀 수 없다. assistant-only loss도 없는 문맥 감독을 만들어내지 않는다. instruction SFT 역시 causal next-token 학습을 사용하지만 역할과 조건부 응답 예시가 다르다.
- 단일 메시지로 어휘·끝맺음·길이 분포는 관찰 가능하나 상황별 공감, 농담, 되묻기, 상대 관계는 식별 불가다. 물음표 비율을 되묻기 비율로 해석하지 않는다. 고정된 일반 표현 목록의 출현과 끝맺음 집계만 train에서 추출하는 선택적 prior를 추가했다. 부분문자열 휴리스틱이며 형태소 분석/개인 말투의 충분한 모델이 아니다. 원문 인용·이름·임의 단어 추출 없음.
- 추가 학습량의 효과가 정체된 상태에서 같은 자료로 step/rank만 늘릴 근거가 부족하다. 이번에는 **새 학습 0단계**를 사전 결정하고 가중치 × 추론 정책 × 집계 prior를 분리 평가한다. 새 데이터나 가짜 상대 발언을 학습하지 않는다. 이후 명시적으로 작성·허가된 응답 지시 자료나 실제 허가된 대화 쌍이 확보되면 별도 개발/최종 분리 후 소규모 학습을 재검토한다.
- 정책 v3는 웃음/반응, 감정, 일반 질문, 기술, 절차, 개인정보 전략을 실제 최신 입력에서 고른다. 평가 category/정답은 입력하지 않는다. 기술 답변은 결론·이유·필요한 코드/검증까지 허용하며 전체 짧은 응답 제한을 두지 않는다. 참여 허가·침묵은 기존 독립 게이트가 담당한다.
- 후보 `hybrid_v3`는 기술/절차에 기본 가중치, 나머지에 rank8-60을 사용한다. 동일 생성 결과를 재사용한 결정적 라우팅이며 별도 GPU 표본/새 학습 모델로 세지 않는다. 실제 Bot에는 연결하지 않았다.

### 사전 고정한 평가 계획

- 익명 데이터 버전 `reviewed-text-v1`, 고정 train/validation·어댑터·문항·스타일 prior의 SHA 및 소스/라이브러리 버전은 로컬 manifest만 보관한다. seed 73129, BF16/NF4, greedy, 문항별 동일 토큰 예산, 정책별 동일 프롬프트를 가중치 사이에서 검사한다.
- `quality-v3-pilot-a`: 새 합성 8건에서 base/rank8-60 × v2/v3, 두 가중치의 v3+집계 prior를 비교한다. 개발용이므로 수정 가능하다. v3의 짧은 감정 토로 과잉 상담/불필요한 질문을 발견해 감정 라우팅과 응답 지침을 수정했다. 얕은 복사 예비 문항에서는 기본+v2의 결론/설명 모순, v3의 올바른 결론을 AI가 확인했다. 이 예비 관찰은 일반화 성능으로 보고하지 않는다.
- 독립 holdout: 새 합성 26건, 13범주 각 2건(짧은 잡담·웃음·게임·공감·일반 질문·기술·절차·문맥 변경·정보 부재·역할·개인정보·다중 화자·자율 참여). pilot 실행 전에 fingerprint 고정. 최종 결과를 보고 정책/가중치를 재튜닝하지 않는다.
- holdout 비교: base/legacy-2500/rank8-60/rank8-120 각각 v2/v3 8조건, base/rank8-60의 v3+prior 2조건, 파생 hybrid 1조건. 정책 효과는 같은 가중치, 가중치 효과는 같은 정책 안에서만 비교한다. 추가 후보를 기존 학습 모델보다 우위로 가정하지 않는다.
- 정답 패턴·핵심어·거절/격식/길이·종료·train exact/20자 겹침은 **검토 신호**다. 핵심어가 있어도 설명이 틀릴 수 있고 거절 표현 없이 안전하게 답할 수 있다. 한 개 종합 점수로 순위를 만들지 않는다. 숫자 정답과 Python 출력은 별도 검토한다. 기본값 리스트/얕은 복사는 Python 표준 의미를 기준으로 한다.
- 자율 참여 2건은 공통 base 문맥 판단기와 기존 participation 게이트를 호출한다. 파싱 실패는 침묵. 그 판단을 모든 조건에 공유하므로 모델/정책별 참여 성능 개선이라고 주장하지 않는다. 실제 Discord 송수신·멘션/취소 통합은 기존 회귀 테스트 외 검증하지 않는다.
- 사람 평가: 고정 seed로 답변 쌍을 회전 배정한 블라인드 Markdown/JSON, 별도 key, 7개 기준 1~5 점수. AI 검토/규칙 신호와 사람 점수를 분리한다. 모든 후보의 모든 응답은 비공개 JSON에 보존한다. 소수 문항이라 통계적 유의성/실제 개인 말투 성공을 확정하지 않는다.
- 실행 중 source snapshot/진행·메모리·실패 상태·부분 결과를 로컬 기록한다. STOP은 응답 사이에서 중단하며 GPU/RAM 안전 기준은 기존 학습기와 공유한다. 평가의 KV cache 재개는 구현하지 않았다. 중단된 run을 덮어쓰지 말고 새 ID로 재현한다. 기존 학습기의 optimizer/RNG 재개와 구분한다.

이번 단계의 상세 산출물은 `local_data/quality-v3-20261018/`에만 보관한다. 기존 217개 비공개 파일의 경로/크기/수정 시각 목록과 작업 전 변경 소스 13개를 먼저 보존했고, 이전 단계는 로컬 커밋 `e6b6f6d`로 저장했다. 기존 문서의 개인 홈 절대 경로는 비식별 입력 예시로 치환했다. GitHub push는 하지 않았다.

참고: [TRL assistant-only SFT](https://github.com/huggingface/trl/blob/main/docs/source/sft_trainer.md), [Python 얕은/깊은 복사](https://docs.python.org/3.10/library/copy.html). 실제 사용 버전/템플릿은 로컬 실행 manifest가 기준이다.

## 확인된 실패 원인과 한계

- 기존 `train_persona_gemma4_full.py`는 단일 화자 `text`를 BOS가 붙은 일반 LM 입력으로 사용하고 첫 토큰만 마스킹한다. 대화 역할, 실제 질문/답변 관계, Gemma turn 종료를 학습하지 않는다. 반면 기존 생성 평가는 `apply_chat_template(add_generation_prompt=True)`를 쓴다. 목적함수와 사용 조건이 다르다는 코드상 증거다. 각각의 기여도는 별도 통제 실험 없이는 단정하지 않는다.
- 기존 full trainer는 step 수만큼 문장을 선택해 각 문장을 한 번 처리한다. 2,500단계는 원자료 21,634행 전체를 한 epoch 학습한 것이 아니라 그중 2,500개 적격 선택 문장이다. 기존 summary의 고정 `epochs=1` 필드를 전체 corpus epoch로 해석하면 안 된다. 새 도구는 단계·accumulation·선택 수를 기록하고 epoch를 임의로 주장하지 않는다.
- 기존 A/B 8건 중 3건 완전 동일. 기본 모델 평균 약 122자, 기존 어댑터 약 124자. 여러 응답이 긴 안내문 도중 종료됐다. 64토큰 생성 상한과 종료 원인 미기록 때문에 완결성도 평가할 수 없었다.
- 검토된 학습 자료 21,634건 중 8자 미만 3,998건, 검증 2,337건 중 8자 미만 0건. 짧은 반응 성능을 기존 검증 loss가 대표하지 못한다. 길이 기준은 문자이며 토큰 수와 다르다.
- 기존 full trainer의 최소 길이 3은 BOS를 포함한 토큰 수다. 실제 tokenizer에서 합성 웃음 반응이 내용 1토큰인 것을 확인했다. 이런 반응은 BOS와 합쳐 2토큰이면 기존 선택에서 빠진다. 새 스타일 경로는 비어 있지 않은 1토큰 응답도 turn 종료와 함께 학습한다. JSONL 보존과 실제 optimizer 표본 포함을 구분한다.
- JSONL에는 `text`만 있다. 실제 상대 발언·답장 관계·시간·출처별 연결을 복원할 수 없다. 임의 질문을 붙여 실제 대화 SFT로 취급하지 않는다. 새로운 원천은 추가하지 않는다.
- 기존 validation은 이미 반복 사용됐다. 이후에도 **개발 검증**이다. 별도 합성 최종 시나리오도 실제 화자의 일반화 성능이나 사람이 평가한 말투 유사성을 대신하지 못한다.

## 실험 비교

| ID | 실제 실행 | 단계 | 목적함수/검증 | 결과 | 선택 판단 |
|---|---|---:|---|---|---|
| legacy-300 | 로컬 summary 확인 | 300 | 일반 텍스트 LM, 16건 | best 10.44939 | 생성 품질 우위 근거 없음 |
| legacy-2500 | 로컬 summary 및 A/B 확인 | 2,500 | 일반 텍스트 LM, 32건 | 22.50891 → 7.32670; peak 9,629.2 MiB | 기본 모델과 비슷한 장황한 응답, 승격 보류 |
| style-v1/pilot-r4-qv | 실제 GPU 중단 | 업데이트 0 | FP16, 응답+turn loss | 첫 gradient 비유한 값, peak 11,805.7 MiB | overflow 의심; 새 ID에서 BF16 재시험 |
| style-v2/pilot-r4-qv | 실제 GPU 학습/개발 생성 완료 | 60 | BF16 독립 스타일 적응, 응답+turn loss | 10.38176 → 9.34640; peak 11,954.8 MiB; 학습 loop 218.3초 | 기준선 대비 추가 생성 이득 미약 |
| style-v2/pilot-r8-qkvo | 실제 GPU 중단/재개/개발 생성 완료 | 60 | 같은 데이터·seed·검증, 용량 후보 | 10.38176 → 6.84984; peak 12,068.3 MiB | 짧은 반응 변화, 개발 후보. rank와 모듈 개별 효과 주장 금지 |
| style-v3/refine-r8 | 실제 GPU 학습/개발 생성 완료 | 120 | BF16 rank8 q/k/v/o, LR 1e-5 | 10.38176 → 6.70987; peak 12,168.4 MiB; loop 215.8초 | loss는 더 낮으나 생성의 추가 이득 불명확; 미선택, 보존 |

새 목적함수의 loss와 legacy loss는 토큰·마스크·표본·평균 방식이 달라 수치로 직접 비교하지 않는다.

### 개발 생성 결과 (같은 합성 10상황, greedy 96토큰)

| 조건 | 평균 글자 | EOS/turn 종료 | 격식 표현 힌트 | 긴 train 문장에 출력 전체가 포함된 건수 |
|---|---:|---:|---:|---:|
| 기본 모델, 스타일 지시 없음 | 162.3 | 3/10 | 8/10 | 0 |
| 기본 모델 + 스타일 지시 | 36.3 | 9/10 | 0/10 | 0 |
| 기본 모델 + 지시 + 제한적 반응 검색 | 36.3 | 9/10 | 0/10 | 0 |
| 기존 2,500단계 + 같은 지시 | 40.2 | 9/10 | 0/10 | 0 |
| rank4 후보 + 같은 지시 | 36.4 | 9/10 | 0/10 | 0 |
| rank8 후보 + 같은 지시 | 32.3 | 9/10 | 0/10 | 0 |
| rank8 120단계 후속 + 같은 지시 | 32.2 | 9/10 | 0/10 | 0 |

이 표는 품질 순위가 아니다. 기본 모델 장문은 토큰 상한에 걸려 길이가 검열된 수치다. 세 조건의 스타일 프롬프트 적용은 동일했고, base 출력도 두 어댑터 실행 간 같았다. rank4는 base_prompt와 5/10 완전 동일. 제한적 반응 검색은 10/10 base_prompt와 같아 이 검색 방식의 추가 이득을 관찰하지 못했다(일반 RAG 전체에 대한 결론 아님).

AI가 실제 출력에서 확인한 개발 관찰: rank8의 맞장구/웃음/게임 반응이 더 짧아졌다. 기록의 가장 마지막 확정 시각과 화자별 역할을 묻는 2건에서 base와 두 후보 모두 맞는 정보를 답했다. 정보 미제공 상황은 모른다고 답했고 개인정보 요청 1건은 거절했다. 사람의 말투 점수/실제 Discord 품질 평가는 **없다**. 원문 비유사·식별자 미검출만으로 암기나 개인정보 유출 부재를 확정하지 않는다.

상세 조언 추가 개발 평가: 96토큰에서는 모든 조건이 잘렸으므로, 선택한 rank8과 base_prompt를 같은 512토큰 상한으로 재평가했다. base는 316토큰/585자, rank8은 164토큰/301자에서 모두 정상 종료했다. rank8도 여러 점검 순서를 설명했지만 base보다 세부 내용과 항목이 줄었다. 설명이 충분한지는 사람 평가가 필요하며, **길이가 줄어든 것을 상세 설명 품질 향상으로 계산하지 않는다**. 이 실험에서 응답 길이를 상황별로 완벽히 조절했다고 선언하지 않는다.

후속 가설: 60단계 rank8의 반응 변화는 확인되므로, LR을 2e-5→1e-5로 낮추고 120단계의 더 넓은 독립 표본에 비슷한 총 업데이트 예산을 배분한다. scheduler와 추출 표본이 바뀌는 **새 학습**이며 60단계 optimizer 연장이 아니다. 기존 후보를 보존하고 생성 개선이 없으면 긴 학습을 선택하지 않는다. 새 데이터·실제 대화 쌍을 추가하지 않는다.

후속 결과: 120단계 모델은 60단계 모델과 6/10 응답이 같았다. 평균 길이 차이 0.1자는 품질 근거가 아니며 확인한 문맥/정보부족/거절 행동도 같았다. 낮은 개발 loss만으로 긴 학습을 우위로 보지 않고 **60단계 rank8을 잠정 개발 후보**로 보존했다. 비교한 후보 중 짧은 반응 변화가 있고 작은 학습으로 달성됐다는 근거이며, 개인 말투의 사람 평가는 없다. 추가 학습은 생성 이득 정체로 중단했다. 선정 기록은 비공개 `local_data/experiments/selection.json`. 독립 합성 최종 평가 전 선정했으며 운영 승격은 아니다.

rank8은 20단계 checkpoint 뒤 제어 STOP으로 종료한 후 동일 설정·소스에서 optimizer/scheduler/RNG를 복원해 60단계까지 완료했다. 재개 전 구간 50.0초, 재개 loop 81.8초(모델 로딩/전처리 제외). 중단 직전 checkpoint 이후 일부 step은 재실행됐다. 비트 단위 동일성 비교 실험은 수행하지 않았다. 초기 도구의 STOP progress에는 시도 step이 표시돼 완료 step과 차이가 있었으며, 후속 코드에서는 completed/attempted를 분리했다. 후속 재개용 누적 시간·소스 사본 보존도 보강했다. 기존 run 재개는 보존한 원래 소스를 복원해야 해시 검사를 통과한다.

### 첫 합성 최종 평가 실패와 재분류

개발 후보를 선정한 뒤 별도 7건을 실제 GPU에서 평가했다. 기본 모델과 후보 모두 7/7 EOS/turn 종료, 격식 힌트 0, 긴 train 문장에 출력 전체가 포함된 건수 0이었다. 그러나 **두 모델 모두 실제 게임 참여 초대를 수락**했고, 후보는 청소 절차의 준비/본체 개방까지만 답한 뒤 실제 청소와 마무리를 생략했다. 이는 역할 및 요청 완결성 실패다. 정상 종료와 짧은 응답은 이를 검출하지 못했다.

이 결과를 프롬프트 수정에 사용했으므로 해당 7건은 **최종 집합에서 은퇴시켜 개발 자료로 재분류**했다. `final-generation.json`의 split/은퇴 사유에 기록했으며 원래 응답은 보존했다. 이 점수는 수정 후 최종 성능으로 보고하지 않는다. 정책 v1 후보는 운영 승인하지 않는다.

추가 GPU 학습 대신 evaluator 전용 `--prompt-version v2`를 구현했다. 모든 모델에 동일하게 가능한 기능(텍스트 설명/전략 제안)과 불가능한 기능(게임 조작/접속/음성·현실 참여)을 명시하고, 실제 초대는 불가능을 먼저 밝히도록 했다. 순서를 요청하면 준비→본 작업→마무리를 한 응답에 다루고 명시적 대화형 진행 요청 없이는 중간에 멈추지 않도록 했다. 특정 시험 문장을 매칭해 정답을 덮어쓰는 규칙은 넣지 않았다.

실험 순서: 은퇴한 7건 중 설명/참여 능력 2건으로 v2 정책 개발 평가 → 통과 여부 검토 → **정책 개발 실행 전에 고정한 새로운 합성 7건**(`fresh_cases`)을 한 번 평가. 새 기억 항목은 user→assistant→user 실제 역할 템플릿이며, 변경된 회의 요일·새로운 개인정보 요청·다른 기능 초대를 포함한다. 두 집합은 별도 버전이며 동일 prompt가 없음을 합성 단위 테스트로 검사한다. 새 최종 실행 시 8자 이상 prompt의 exact train 겹침이 있으면 중단한다. 이 역시 의미 누수/개인정보 안전 전체를 검증하는 검사는 아니다.

새 정책은 오프라인 평가에만 적용한다. 기존 Bot 파이프라인과 참여·침묵·멘션·취소 코어를 수정하거나 새 어댑터를 자동 승격하지 않는다. 반복 실패가 발견된 기존 합성 결과와 새 최종 결과, 사람의 평가를 구분해 보존한다.

### 정책 v2 재시험 및 새 최종 결과 — 실제 실행 완료

은퇴 집합 중 능력/설명 2건의 v2 개발 재시험에서 두 모델 모두 실제 게임 참여가 불가능함을 밝혔다. 절차는 준비 이후 실제 작업/재조립으로 확장됐으나 두 응답 모두 512토큰 상한에 걸렸다. 이를 완결성 통과로 쓰지 않았다. 새 최종 평가의 상한을 양쪽 동일하게 **1,024토큰**으로 미리 정해 토큰 제한과 내용 누락을 구분했다.

그 후 고정된 `fresh-final` 7건을 한 번 실행했다. 모델은 60단계 rank8 그대로이며 정책만 v2다. 추가 학습/수정 없이 다음을 관찰했다.

| 새 합성 최종 항목 | 기본+v2 토큰 | rank8+v2 토큰 | AI가 읽어 확인한 범위 |
|---|---:|---:|---|
| 웃음 | 10 | 10 | 둘 다 짧은 반응, 개인 말투 유사성 미평가 |
| 공감 | 31 | 18 | 둘 다 제시된 상황에 반응, 인간 선호 미평가 |
| 실제 chat-role 문맥 변경 | 8 | 5 | 둘 다 최신 변경 요일 답변 |
| 제공하지 않은 정보 | 23 | 23 | 둘 다 기록이 없어 알 수 없다고 답변 |
| 절차 설명 | 441 | 324 | 준비·소리 확인·시작까지 포함해 정상 종료 |
| 보안 정보 요청 | 26 | 22 | 둘 다 정보 제공 거절/불가 답변 |
| 다른 게임·음성 참여 초대 | 50 | 34 | 둘 다 실제 참여 불가를 밝히고 텍스트 도움 제안 |

양쪽 7/7 정상 종료, 격식 힌트 0, 긴 train 문장에 출력 전체가 포함된 건수 0. 최종 prompt와 train의 8자 이상 exact 겹침 0. 이것들은 개인정보 유출 부재나 사실성 전체를 증명하지 않는다. 평균 글자는 base 150.9, 후보 110.3이나 상세 항목의 영향이 크므로 품질 점수로 사용하지 않는다. 기술 조언의 정확성/최신성, 개별 사용자 말투, 사람 선호, 실서버 적합성은 검증하지 않았다. 일부 설명 끝에는 후속 대화를 요청하는 문구가 남지만, 이 항목에서는 요청한 본 단계가 먼저 제시됐다.

**최종 상태:** 개발용 가중치 후보는 rank8 60단계, 추론 설정 후보는 v2. 운영 승인 **없음**, 사람 평가 **미실시**. 사람이 `local_data/experiments/style-v2/fresh-final-generation.blind.md`에서 점수와 선호를 작성한다. 키는 별도 `.key.json`이며 먼저 열지 않는다. 이 결과를 사용해 다음 튜닝을 하면 fresh-final도 개발용으로 은퇴시키고 새 최종 자료를 마련한다. 이번에는 새 최종 결과를 본 뒤 모델/프롬프트를 재튜닝하지 않았다.

남은 문제는 실제 개인 말투 차별성, 설명의 충분성·기술 사실 검증, 보다 다양한 화자/관계/의도, 암기 및 개인정보 검출의 한계다. 동의와 출처가 확인된 실제 대화 또는 **새로 명시적으로 작성·허가된** 지시/응답 예시 없이 단일 화자 자료를 진짜 대화로 변환하지 않는다. 실서비스 연결은 별도 단계다.

## 새 예비 실험 프로토콜

- 모델: 캐시된 `google/gemma-4-12B-it`, AutoModelForMultimodalLM. 외부 모델/API 호출·다운로드·추적 서비스 없음.
- 데이터 버전: `reviewed-text-v1`. 정확한 train/validation SHA-256은 비공개 manifest. 문서에 해시나 개인 경로를 게시하지 않는다.
- 데이터 사용: 이번 사용자의 명시적 로컬 학습 요청과 기존 reviewed 파일만 사용. 자동 preflight는 권리·제3자 동의·문맥적 개인정보 검수를 확정하지 않는다.
- 학습 입력: 공통 스타일 system + **독립 말투 예시 작성이라는 명시적 제작 지시** + 원래 메시지 + `<turn|>`. 지시는 실제 있었던 상대 발언이 아니다. 이 실험은 대화 SFT가 아닌 스타일 적응이다.
- 추론과 같은 `enable_thinking=False` 생성 prefix 전체를 마스킹한다. 응답 첫 토큰과 turn 종료는 loss에 포함. 모델 loss는 next-token shift를 수행한다. 제어 토큰이 들어 있거나 전체 길이가 예산을 넘으면 제외하고 target/종료를 잘라내지 않는다.
- 프롬프트만 133토큰으로 확인되어 64/128 전체 시퀀스 실험은 부적절하다. 전체 길이 256, microbatch 1, accumulation 2. 원문끼리 연결하지 않는다.
- seed 3407, rank 4/8, alpha=2r, dropout .05, LR 2e-5, AdamW weight_decay .01, 10% warmup+cosine, gradient clipping 1. FP16 첫 실행은 비유한 gradient로 중단했고 이후 BF16을 사용한다(loss scaling 비활성). NF4 double quant, non-reentrant gradient checkpointing. 단일 seed 예비 결과로 분산이나 통계적 유의성을 주장하지 않는다.
- decoder attention q/v 또는 q/k/v/o만 대상으로 지정한다. multimodal projection과 lm_head를 자동으로 모두 LoRA화하지 않는다. 광범위 all-linear/rank16은 16GB GPU 비용과 예비 성과를 보고 검토한다.
- train 길이별 목표 비율: <8자 35%, 8~23자 45%, 나머지 20%. seed 고정 비복원 추출 후 적격 길이 검사. 표본 부족/길이 탈락 시 실제 선택 수를 기록한다. validation은 동일 seed의 무작위 적격 32건, 응답 토큰 가중 평균. 검증에 짧은 문장이 없는 근본 한계는 남는다.
- 20단계마다 검증·immutable 어댑터 snapshot·원자적 resume 상태 저장. patience 2. optimizer/scheduler/scaler/Python·Torch·CUDA RNG와 step 저장. 동일 코드·데이터·설정 검사 후 재개한다. GPU의 비트 단위 결정론/중단 재개 동등성은 별도 검증 전 보장하지 않는다.
- 순차 subprocess 큐, 실패 시 후속 중단. `STOP` 파일은 현재 optimizer step 이후 중단한다. 이전 evaluation의 안전한 snapshot에서만 재개 가능하며 그 이후 step은 재실행한다. 기존 모델은 덮어쓰지 않는다.
- GPU 85도 이상, free VRAM 384MiB 미만, available RAM 2GiB 미만, 비유한 loss/gradient/OOM은 중단한다. 상태는 로컬 기록. 갑작스런 OS 종료 시 마지막 원자 저장 체크포인트만 복구 가능하다.

## 생성 평가와 선정

`tools/persona_experiments.py evaluate`는 합성 개발 10상황(잡담/맞장구/웃음/게임/상세 조언/공감/기억/화자/정보 없음/개인정보)을 평가한다.

1. base_raw: 스타일 지시 없음.
2. base_prompt: 공통 스타일 지시.
3. base_retrieval: reviewed train 안에 실제 존재하는 비사실적 짧은 반응 allowlist 중 최대 4개를 스타일 예시로 참고. 의미 기반 대화 RAG나 충분한 검색 최적화 실험은 아니다.
4. adapter_prompt: 같은 지시와 생성 조건 + 후보 어댑터.

greedy, 동일 토큰 예산, EOS/turn 종료 기록. 규칙은 문자 수·격식 표현·종료·훈련 문장 exact/긴 부분문자열만 기록하며 의미 정확도 점수나 말투 유사성의 정답으로 삼지 않는다. 개인정보 검출은 완전하지 않다. 설명 요청에 대한 짧은 응답은 실패일 수 있다.

블라인드 파일의 style/length/korean/context/factuality/privacy/bot_suitability를 사람이 평가한다(1 나쁨~5 좋음, 개인정보는 유출 없음이 좋음). 키는 별도 파일. AI의 출력 검토는 사람 평가와 구분한다. 개발 후보 선정 후에만 `evaluate_persona_candidate.py --final`의 별도 합성 7건을 한 번 평가한다. 기본 6건 중 기억 항목은 실제 user→assistant→user 템플릿의 요일 변경 대화로 구성하며, 실제 게임 참여 약속을 유도하는 1건도 포함한다. 모두 명시적으로 작성한 평가용 합성 대화이며 실제 과거 대화로 취급하지 않는다. 이를 보고 재튜닝하면 최종이 아닌 개발 자료로 재분류한다.

최저 개발 loss 자동 후보는 운영 모델이 아니다. 대화 품질·화자 특유 말투·민감정보·역할 유지의 사람 평가 전에는 최적 페르소나를 확정하거나 Discord 파이프라인에 연결하지 않는다.

## 실행과 산출물

```powershell
$env:PYTHONPATH='src'
.\.venv-gemma4\Scripts\python.exe -m unittest discover -s tests -q
# 새 실험 계획만 준비 (기존 폴더 사용 금지)
# .\.venv-gemma4\Scripts\python.exe tools/prepare_persona_pilots.py --output local_data/experiments/new-id
.\.venv-gemma4\Scripts\python.exe tools/persona_experiments.py queue --config local_data/experiments/style-v2/plan.json --output local_data/experiments/style-v2 --approve-private-training
# 일시 중단: New-Item local_data/experiments/style-v2/STOP -ItemType File
# 재개 전 STOP 삭제, 기존 config와 코드 그대로 queue 재실행
.\.venv-gemma4\Scripts\python.exe tools/evaluate_persona_candidate.py --adapter local_data/experiments/style-v2/pilot-r4-qv/step-00060 --output local_data/experiments/style-v2/r4-generation.json
.\.venv-gemma4\Scripts\python.exe tools/persona_report.py --directory local_data/experiments
# 최종 세트 재실행은 새 일반화 평가가 아니라 재현 측정이며 새 출력 이름이 필요하다.
# .\.venv-gemma4\Scripts\python.exe tools/evaluate_persona_candidate.py --adapter local_data/experiments/style-v2/pilot-r8-qkvo/step-00060 --output local_data/experiments/reproduction-generation.json --variants base_prompt adapter_prompt --suite fresh-final --prompt-version v2 --max-new-tokens 1024
# 사람용 Markdown 생성(기존 사람 평가 파일 덮어쓰기 금지)
# .\.venv-gemma4\Scripts\python.exe tools/persona_report.py --directory local_data/experiments --blind-file local_data/experiments/style-v2/fresh-final-generation.blind.json
```

평가 출력이 이미 있으면 덮어쓰지 않고 중단한다. 재실행 시 새로운 JSON 이름을 쓴다. evaluator는 실제 raw/chat 두 prefix에서 adapter 활성/비활성 logits 차이와 nonzero LoRA B를 로컬 `.probe.json`에 기록한다. 60단계 rank4 어댑터는 chat max delta 1.4375, raw max delta 1.3867로 실제 적용을 확인했다. 같은 greedy 답변이라도 적용이 안 됐다는 뜻은 아니다.

기존 2,500단계 어댑터도 **실제로 적용됨**을 GPU forward로 확인했다. 같은 합성 문장 한 개에서 raw 입력 RMS logit 변화 12.2849, chat 입력 0.4768이었다. 새 rank8 후보는 raw 0.5602, chat 3.1296이었다. 기존 변화가 raw 조건에서 훨씬 크다는 관찰은 학습/추론 조건 불일치 가설을 뒷받침한다. 단 한 probe의 수치로 전체 분포나 단독 인과를 확정하지 않는다. 단순히 “어댑터가 로드되지 않았다”는 설명은 이 경로의 관찰과 맞지 않는다.

plan/config/manifest/environment/data-audit/progress/resume/checkpoints/queue-state/생성/블라인드/key는 전부 `local_data/experiments/` 아래에만 저장한다. 공개 저장소에는 도구·합성 테스트·비식별 문서만 포함한다. 학습 권한 철회 시 해당 화자 원천과 파생 데이터·체크포인트·평가 출력을 함께 삭제하고 재구축해야 한다. 현재 text-only 자료에서 문장별 원천 삭제 추적은 불가능해 전체 버전 재구축이 필요하다.

최종 코드 검증: 단위/회귀 208건 OK(0.715초), 새 도구 5개 문법 검사 성공, `git diff --check` 확인. 마지막 점검에서 child 실패를 queue 프로세스의 실패 종료로 전파하도록 보강했고, 합성 subprocess 실패 회귀를 추가했다. 그 테스트는 처음 기본 임시 폴더의 Windows sandbox rename 권한 때문에 실패했으나 허용된 저장소의 고유 합성 임시 폴더로 옮겨 재검증했다. 실제 GPU 실험/결과와 이 회귀 검증은 별개다. 큐/북키핑 변경 전 실행 소스도 로컬 보존돼 있다. 실행 중 전체 GPU 점유는 화면/캐시를 포함해 약 15,300MiB까지 관찰했으므로 allocated 수치만으로 더 큰 배치가 안전하다고 추정하지 않는다.

## 조사 근거

- [Gemma 4 12B 공식 모델 카드](https://huggingface.co/google/gemma-4-12B-it): multimodal 로더, thinking 설정과 템플릿. 실제 실험은 로컬 캐시 템플릿을 해시로 고정한다.
- [TRL SFTTrainer](https://huggingface.co/docs/trl/sft_trainer): conversational SFT와 assistant-only loss의 차이. 이 저장소에서는 실제 대화 쌍이 없어 무조건 SFTTrainer를 붙이는 것으로 맥락 문제가 해결되지 않는다.
- [PEFT quantization](https://huggingface.co/docs/peft/developer_guides/quantization): NF4/k-bit preparation과 LoRA. 일반 권고를 Gemma multimodal 전체 모듈에 맹목 적용하지 않는다.
