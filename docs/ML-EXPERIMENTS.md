# ML 실험 기록

갱신: 2026-10-19. 민감한 원문·응답·데이터 해시·어댑터는 `local_data/`에만 보관한다. 아래는 비식별 집계다.

## 추가 품질 단계: quality-v3 (2026-10-18)

기존 60/120단계와 정책 v2는 보존된 실험 후보이며 최종 모델이 아니다. 아래 신규 평가는 기존 개발/최종 7문항을 재사용하지 않는다. 이전 loss 표는 그 목적함수 안에서만 읽고 신규 생성 평가 순위에 섞지 않는다.

### 원인 재검증과 이번 변경

- 실제 GPU에서 합성 1토큰/6토큰 응답의 prefix 133토큰 전체 마스킹, 응답 첫 토큰·turn 종료 포함을 확인했다. 모델이 반환한 loss와 logits에서 직접 계산한 shifted cross entropy가 각각 6.43014/5.77026으로 일치했다. **마스킹이 정확하다는 것과 목표 데이터가 대화 응답에 적합하다는 것은 별개**다.
- 동일 합성 chat prefix에서 기본 대비 logit RMS 변화는 legacy-2500 0.6350, rank8-60 3.5870, rank8-120 3.5929였다. 세 어댑터가 실제 적용된다. 이 한 입력의 변화량은 품질 점수가 아니다.
- 새 경로는 chat prefix/turn 종료/`enable_thinking=False`를 맞췄지만, 학습 user 지시는 독립 문장 작성이고 추론 user 입력은 실제 질문이다. 형식 정렬만으로 `P(단독 메시지|문장 작성)`를 `P(답변|문맥·관계·질문)`로 바꿀 수 없다. assistant-only loss도 없는 문맥 감독을 만들어내지 않는다. instruction SFT 역시 causal next-token 학습을 사용하지만 역할과 조건부 응답 예시가 다르다.
- 단일 메시지로 어휘·끝맺음·길이 분포는 관찰 가능하나 상황별 공감, 농담, 되묻기, 상대 관계는 식별 불가다. 물음표 비율을 되묻기 비율로 해석하지 않는다. 고정된 일반 표현 목록의 출현과 끝맺음 집계만 train에서 추출하는 선택적 prior를 추가했다. 부분문자열 휴리스틱이며 형태소 분석/개인 말투의 충분한 모델이 아니다. 원문 인용·이름·임의 단어 추출 없음.
- 추가 학습량의 효과가 정체된 상태에서 같은 자료로 step/rank만 늘릴 근거가 부족하다. 이번에는 **새 학습 0단계**를 사전 결정하고 가중치 × 추론 정책 × 집계 prior를 분리 평가한다. 새 데이터나 가짜 상대 발언을 학습하지 않는다. 이후 명시적으로 작성·허가된 응답 지시 자료나 실제 허가된 대화 쌍이 확보되면 별도 개발/최종 분리 후 소규모 학습을 재검토한다.
- 기존 60/120단계는 학습률과 선택 표본 풀도 다르다(각 step×accumulation×2 추출 후 실제 사용). 별도 실행을 초기화하는 구조이며 순수한 step 수 단독 ablation이 아니다. 추가 생성 이득이 확인되지 않았다는 판단과 학습량의 인과 효과를 구분한다.
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

실행 보완: pilot-a는 단일 생성 호출, pilot-b는 변경한 개발 문항에서 v2/v3/prior 3슬롯 배치를 실제 시험한다. 모든 가중치에서 같은 padding 폭·슬롯 위치·디코딩 예산을 사용한다. legacy/120의 세 번째 슬롯은 v3 중복 진단이며 새 후보/독립 표본으로 세지 않는다. GPU 안전 확인 후 holdout도 같은 배치 조건으로 고정한다. 배치 shape만 달라져도 BF16/NF4 greedy 결과가 바뀔 수 있어 pilot-a와 pilot-b 사이 변화 전체를 정책 효과로 해석하지 않는다. 정책/가중치 효과는 **동일 run 안의 통제 비교**로 평가한다. 배치 응답의 seconds는 공동 wall time이므로 합산하지 않는다.

평가 편향 점검: 예비 응답에서 안전하게 기능 한계를 밝혔어도 한국어 조사 때문에 단순 거절 regex가 0이 되는 사례를 확인했다. 반대로 핵심어/정답 숫자가 포함돼도 첫 결론이 틀린 사례가 있었다. 이 규칙 신호를 안전성 합격/정확성 점수로 사용하지 않으며 원문 의미 검토와 사람 점수는 별도로 기록한다. prior의 끝부분 문자열은 명사의 일부일 수 있으므로 문법적 종결어미로 단정하지 않는다.

이번 단계의 상세 산출물은 `local_data/quality-v3-20261018/`에만 보관한다. 기존 217개 비공개 파일의 경로/크기/수정 시각 목록과 작업 전 변경 소스 13개를 먼저 보존했고, 이전 단계는 로컬 커밋 `e6b6f6d`로 저장했다. 기존 문서의 개인 홈 절대 경로는 비식별 입력 예시로 치환했다. GitHub push는 하지 않았다.

### 실제 예비 평가 결과와 추가 후보 결정

| 실험 ID | 실제 GPU | 개발 문항/답변 | 학습 | 시간 | 평가 구간 peak allocated |
|---|---|---|---|---|---|
| quality-v3-pilot-a | 완료 | 8건 × 실제 6조건 = 48응답, 파생 hybrid 8건 별도 | 0단계 | 1,435.1초(로딩 포함) | 7,791.4 MiB |
| quality-v3-pilot-b | 완료 | 변경 관련 5건 × 6조건 = 30응답, 파생 hybrid 5건 별도 | 0단계 | 378.1초(로딩 포함) | 8,491.7 MiB |
| quality-v3-reasoning-pilot | 완료, 품질 기준 실패 | 기술 개발 1건, base native thinking+최종 응답 2회 greedy 호출 | 0단계 | 생성 67.5초(로딩 제외) | 7,855.2 MiB |

pilot-a의 기본/rank8 v3는 v2보다 과한 공감·추가 권유·절차 반복이 늘어 실패로 기록했다. 문장 길이만 줄이라는 지시 대신 감정/반응 전략과 반복·범위 확장을 보완했다. pilot-b의 **같은 run 안**에서 기본 공감 길이 v2 94자 → v3 41자, rank8 35자 → 30자였다. 그러나 기본 절차 길이는 627자 → 860자, rank8 503자 → 561자로 늘었고 v3의 보안 지식 답변은 여전히 상한에 도달했다. 얕은 복사 문항은 기본/후보 모두 잘못된 첫 결론을 내면서 뒤에서 올바른 참조 설명을 섞었다. v3의 일괄 우위는 관찰되지 않았다. 개인 말투와 사람 선호는 미평가다.

별도 native thinking 가설: 모델의 추론 기능이 코드 상태의 모순을 줄일 수 있는지 시험했다. [Google 공식 thinking 문서](https://ai.google.dev/gemma/docs/capabilities/thinking)와 로컬 template의 채널 구분을 확인했다. 총 512토큰 안에서 thought 최대 192개 뒤 종료 채널을 강제하고 남은 토큰으로 보이는 응답을 생성했다. private thought는 출력하지 않으며 예상 밖 channel/tool 토큰은 fail closed한다. 실제 최종 첫 결론은 맞았지만 193 thought/종료 토큰 + 319 응답 토큰을 사용하고 불필요한 대안 코드 중간에서 상한에 도달했다. 사전 성공 기준의 완결성 실패이므로 **holdout 후보에서 제외**한다. 기술 정확성을 해결했다고 쓰지 않는다. 이 경로는 진단 도구일 뿐 Bot에 연결하지 않았다.

새 후보 `selective_v3`: pilot에서 관찰한 이득을 보수적으로 적용해 실제 입력을 reaction/empathy로 판정한 경우만 rank8-60+v3, 나머지는 보존된 rank8-60+v2를 쓴다. category/정답을 라우팅하지 않는다. 동일 결과를 재사용하는 정책 조합이며 추가 GPU 표본/새 가중치가 아니다. keyword 라우터의 감정·농담 인식 한계가 있으며 일부 상황에는 v2와 완전히 같을 수 있다. 새 조합과 배치 조건은 **holdout 응답을 보기 전에** `holdout-protocol.json`으로 고정했다. 원래 문항 fingerprint/plan은 바꾸지 않았다. 최종 비교는 실제 10조건 + 파생 hybrid/selective 2조건이며 native thinking은 포함하지 않는다.

참고: [TRL assistant-only SFT](https://github.com/huggingface/trl/blob/main/docs/source/sft_trainer.md), [Python 얕은/깊은 복사](https://docs.python.org/3.10/library/copy.html). 실제 사용 버전/템플릿은 로컬 실행 manifest가 기준이다.

### 독립 평가 완료 및 선정 보류 (2026-10-19 정리)

`quality-v3-holdout-a`는 실제 GPU에서 사전 고정 26문항을 완료했다. 2026-10-18 UTC 완료, 2,482.5초(로딩 포함), 평가 구간 peak allocated 8,498.6 MiB. 실제 10조건의 평가 행 260개 중 공통 침묵 10개를 제외한 생성은 250개다. 파생 hybrid/selective 52행을 더해 저장 행은 312개이며, 이를 독립 생성 312개로 세지 않는다. legacy/120의 중복 배치 진단 50개는 모두 같은 가중치의 v3 응답과 일치했고 점수에서 제외했다. 참여 판단 2회도 별도다.

동일 정책의 가중치 간 prompt/seed/토큰 예산/배치 폭 일치 검사 통과. 아래 글자 수와 상한 도달은 품질 점수가 아니다. 25개 발화 전체의 평균으로 짧은 반응과 긴 설명이 섞여 있다. loss는 포함하지 않는다.

| 조건 | 실제 발화 | 평균 글자 | 토큰 상한 도달 |
|---|---:|---:|---:|
| 기본 + v2 | 25 | 190.8 | 0 |
| 기본 + v3 | 25 | 282.5 | 5 |
| legacy-2500 + v2 | 25 | 180.4 | 0 |
| legacy-2500 + v3 | 25 | 266.8 | 4 |
| rank8-60 + v2 | 25 | 132.8 | 0 |
| rank8-60 + v3 | 25 | 259.3 | 3 |
| rank8-120 + v2 | 25 | 128.9 | 0 |
| rank8-120 + v3 | 25 | 268.2 | 4 |
| 기본 + v3/prior | 25 | 283.0 | 5 |
| rank8-60 + v3/prior | 25 | 255.8 | 4 |
| hybrid_v3 (재사용) | 25 | 266.8 | 4 |
| selective_v3 (재사용) | 25 | 133.6 | 0 |

모든 26문항을 비블라인드 AI가 의미 검토했으며 사람 평가와 구분한다. 새 결과를 보고 정책·가중치·문항을 수정하지 않았다. 확인한 내용:

- v3의 제한적 이득: 민감정보 추출 요청에서 근거 없는 학습자료 내용 단정 대신 원칙에 따른 거절을 했다. 일부 기본/legacy 절차 답변은 별도 위치로 복원하는 검증을 명시했다. 그러나 이것만으로 개인정보 안전/전체 절차 정확성을 선언하지 않는다.
- 라우팅 실패: 농담의 계획 관련 단어가 절차 요청으로 오인돼 full-v3 6조건 모두 장문·상한 도달. 새로운 감정 표현은 keyword 공감 분기로 잡히지 않아 과잉 조언으로 확장됐다. selective는 다수 문항에서 기존 v2를 그대로 재사용하며 개인 말투의 독립 개선 증거가 없다.
- 기술 실패: 얕은 복사 상태 문항에서 실제 10조건 모두 첫 결론과 뒤의 올바른 값이 모순됐다. 별도의 다중 화자 기술 질문에서는 full-v3 6조건 모두 단순 대입과 얕은 복사를 혼동해 새 외부 리스트 생성 여부를 틀렸다. 일부 응답은 올바른 예시와 잘못된 설명을 함께 포함했다. 기본 모델에도 나타나므로 LoRA만의 문제로 단정하지 않는다. 기본값 공유 문항은 전 조건에서 원인/초기화 수정이 맞았다.
- 절차/보안: 복잡한 요청은 v2 4조건 모두 끝까지 답했지만 full-v3 6조건은 모두 상한에 도달했다. 일부 복원 검증은 파일 재열기를 복원 시험으로 취급했다. legacy-v3는 복사 도구의 해시 비교 기능을 잘못 설명했고 별도 보안 답변에서 복구 코드 공유 예외로 읽힐 수 있는 문장을 냈다. 생성 명령은 실행하지 않았다. 단순한 EOS/핵심어 검출로 놓치는 오류다.
- 산술 2건, 갱신 문맥 2건, 화자 식별 2건의 명시 답은 전 조건에서 맞았다. 정보 부재에서는 실제 과거 사실을 지어내지 않았으나 일부 v3가 근거 없는 지식 기준일/영구 기록 능력을 덧붙였다. 공통 참여 게이트는 종료된 대화에서 침묵, 명시적 기술 도움 요청에서 발화를 결정했다. 이는 가중치·정책 간 개선이나 실제 Discord 검증이 아니다.
- 스타일 prior 2조건의 정보 부재 응답에 채널/`thought` 표시가 섞였다. 별도 `h18-token-trace` GPU 재현(52.0초, peak 8,236.9 MiB)은 6개 보이는 응답 모두 원 평가와 일치했다. 기본+prior에는 생성된 channel open/close 각 1개, rank8+prior에는 close만 1개였다. `skip_special_tokens=True`만으로 최종 응답 채널이 보장되지 않는다. private raw tokens는 로컬만 보관하고 내부 내용은 문서/서비스에 노출하지 않았다. 암기된 개인정보가 노출됐다는 증거로 해석하지 않는다. 현재 평가 경로의 문제로 기록하며 운영 연결은 보류한다.
- 원문 exact/20자 겹침 힌트는 0이지만 안전 보증이 아니다. 별도 prefix-exposure GPU 진단에서 실제 rank8-60 최적화 표본 2개/기존 validation 2개에 앞 8토큰을 노출하고 4가중치로 생성한 16개 중 남은 원문 전체 복원은 0이었다. 각 가중치의 평균 연속 일치 문자는 학습 0/검증 1.5였다. 매우 작은 비대응 표본이며 검증 자료는 이미 열람됐다. 회원 추론/암기 부재/개인정보 안전을 입증하지 않는다. 해당 진단에는 별도 시간/peak 계측이 없어 수치를 주장하지 않는다.

**선정:** 새 v3/prior/hybrid/selective의 일관된 독립 품질 이득을 확인하지 못했다. 기존 rank8 q/k/v/o 60단계 + v2를 잠정 후보로 보존하며 최종 모델은 없음, production 승인 없음. 120단계의 낮은 loss/짧은 길이를 우위 근거로 쓰지 않는다. 추가 학습은 0단계이며 같은 단일 화자 자료로 무의미하게 연장하지 않는다. 기존 선정 기록을 덮어쓰지 않고 새 루트 `selection.json`에 근거와 보류를 저장했다.

사람 평가 미실시. 새 루트 `REVIEW-GUIDE.md`와 holdout-a의 블라인드 자료를 사용한다. `weights-v2`는 같은 v2에서 기본/60단계, `duration-v2`는 같은 v2에서 60/120단계, `same-policy`는 같은 v3의 기본/60단계, `same-weight`는 같은 60단계의 v2/v3, `candidate-vs-provisional`은 selective/v2 비교다. 각 26문항 전부 포함, key는 평가 후 확인. `balanced`는 후보를 회전 배정한다. 사용자 말투·반응 방식·설명 충분성은 7개 기준을 직접 평가하고 필요 시 N/A로 남긴다. 학습 문장 기계적 재현이나 통계적 유의성을 이 소수 합성 사례로 확정하지 않는다.

다음 우선순위는 블라인드 사람 평가 → 문맥/의도 라우팅과 출력 채널 처리의 별도 개발 → 허가된 실제 응답 감독 자료의 확보 가능성 검토다. 이번 holdout을 보고 고치면 해당 집합은 개발/회귀용으로 은퇴시키고 새 독립 평가를 고정한다. 상황별 개인 표현의 근거가 없는 상태에서 일반적인 친근함이나 임의의 웃음 표현을 사용자 말투로 강제하지 않는다.

재현/검토 명령(첫 두 명령은 기존 결과 읽기, 새 GPU 실행은 새 run ID만 사용):

```powershell
$env:PYTHONPATH='src'
.\.venv-gemma4\Scripts\python.exe -m unittest discover -s tests -q
Get-Content local_data/quality-v3-20261018/holdout-a/summary.md
.\.venv-gemma4\Scripts\python.exe tools/persona_quality_v3.py run --root local_data/quality-v3-20261018 --stage holdout --name holdout-reproduction-NEW --batch-policies
```

재현에는 고정 추론 코드 `b62633e`, 같은 캐시 모델/라이브러리/계획/자료가 필요하다. 다시 실행해도 새 일반화 점수가 아니다. 기존 블라인드 평점 파일은 덮어쓰지 않는다. 진단 코드 커밋 `6493f7a`는 고정 정책을 바꾸지 않는다. 마지막 검증은 217개 OK(0.935초), 도구 문법/whitespace 확인. 기술 판단의 근거: [Python copy](https://docs.python.org/3.10/library/copy.html), [Robocopy](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy), [Get-FileHash](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash?view=powershell-7), [Google backup codes](https://support.google.com/accounts/answer/1187538?hl=en). 서비스별 보안 절차 전체를 검증한 것은 아니다.

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
