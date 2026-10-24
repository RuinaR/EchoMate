# 공개 원천 확보·조건부 정답 편집 — 2026-10-25

후속 실제188/전체264응답 학습·캐시 후보·품질 미채택은 [재개 QA](QLORA-RESUME-QA.md)를 따른다. 아래의 로딩0회는 이전 차수 당시 자원 미달 기록이다.

시작 local/main/remote `8a348d42ba0e6a3c0933514daa82686486b1269f`, clean. RELEASE BLOCKED. 실행 앱src·운영 no-LoRA·프로필·DB schema·큐·동의·송신 경로는 변경하지 않았다. 실제 Discord 인증/조회/Gateway/명령/송신0회다. 다른 프로그램의 목록/창/화면/입력/내부/네트워크는 조사·조작하지 않았다. 시스템 집계와 자체 테스트만 읽었다.

## 우선순위와 기존 결과의 구분

이전 [3LR pilot](DATASET-QLORA-QA.md)은 v1의64개 학습 응답을 사용했다. 마지막 공개 v4의104개는 **학습하지 않은 자료**였다. 이번에도 loss나 이전349token 학습 성공을 품질 근거로 재사용하지 않는다. 먼저 공개 원천의 별도 확보·권리/평가 원천 배제·한국어 편집·정답 마스크를 고정하고, 한 학습률의 제한 pilot 가능성을 검사했다. 운영 모델을 자동 교체하지 않는다.

## 실제 다운로드와 권리 판단

- [BST 공식 task](https://github.com/facebookresearch/ParlAI/blob/a29567f7ce76992fd1f03c51ba9e3b155a37ea51/parlai/tasks/blended_skill_talk/README.md), [데이터 라이선스](https://github.com/facebookresearch/ParlAI/blob/a29567f7ce76992fd1f03c51ba9e3b155a37ea51/parlai/tasks/blended_skill_talk/LICENSE_DOCUMENTATION), [공식 build/hash](https://github.com/facebookresearch/ParlAI/blob/a29567f7ce76992fd1f03c51ba9e3b155a37ea51/parlai/tasks/blended_skill_talk/build.py)를 대조했다. 코드 MIT와 데이터 CC BY4.0은 별개다. CC BY의 상업적 이용·가공 허용에는 출처/변경 고지 등의 조건이 있으며 제3자 권리·개인정보까지 면제하지 않는다.
- 고정 ParlAI revision `a29567f7ce76992fd1f03c51ba9e3b155a37ea51`. 공식 [archive](https://parl.ai/downloads/blended_skill_talk/blended_skill_talk.tar.gz) 38,101,408bytes, SHA256 `5fbed0068ee89e2d43b93c3ecb341e784617033efa5e8e911a219d4eda6134a6`, BST v1.5. 라이선스18,658bytes/SHA256 `f5b745ef98087f531e719ee8ca6a96809444573ecc7173c6fa68eaad39b3cc3f`. 새 다운로드 시각은2026-10-25 01:24 KST(archive UTC2026-10-24T16:24:50.989936)다. 이전 평가 archive를 학습으로 전환하지 않고 공식 원천을 새 비공개 폴더에 받았다.
- HTTPS·최대48MiB·45초timeout·공개 checksum을 사용하며 정확히 하나의20MiB 이하 regular train.json만 메모리에서 읽는다. tar 경로를 디스크에 추출하거나 실행하지 않는다. 다운로드 원문·attribution·해시·최종URL은 private acquisition.json에 남겼다.
- [ConvAI2](https://github.com/facebookresearch/ParlAI/blob/main/parlai/tasks/convai2/README.md)는 공식 CC4.0 BY 표기만 확인했다. 모든 PersonaChat 미러의 권리로 확대하지 않았고 별도 미러를 받지 않았다. BST의 ConvAI2/WoW 계열만 후보로 사용한다.
- [EmpatheticDialogues](https://github.com/facebookresearch/EmpatheticDialogues/blob/main/LICENSE), [LoCoMo](https://github.com/snap-research/locomo/blob/main/LICENSE.txt), [KoED](https://github.com/KUNLP/KoED)의 NC 경계를 유지해 이번 학습에서 제외했다. BST 안의 ED seed1,620개도 보수적으로 제외했다. [AI Hub](https://aihub.or.kr/)는 계정·개별 조건을 우회하지 않았고 새 한국어 원문을 확보했다고 주장하지 않는다. 한국어 target은 원본 대사 번역 대신 상황을 검토한 새 편집이다. 다양한 한국어 공개 원천의 확보는 아직 부족하다.

## 기존 평가와의 분리

기존 개발200/표준1,130의 메타데이터만 읽고 seal/hash를 대조했다. BST1,300개 원천의 persona+seed 가족과 어느 seed라도 공유하는 대화를 **전이적으로** 제외했다. 다른 상대와 재등장한 seed를 새 대화로 세지 않는다. 신규 후보도 연결된 seed component 전체가 같은 분할에 속하도록 SHA 기반으로 배정했다. final.json은 열지 않았고 최종 미사용316/소비 장부는 그대로다. 메타데이터 seal의 final hash를 읽는 것과 final 원문을 소비하는 것은 구분한다.

공개 train4,819개에서 ED1,620·기존 평가/공유 seed1,355·개인정보/길이 screen6을 제외해 **1,838개 원천 후보/1,773 component**를 확보했다. 후보 분할은 학습1,450/개발193/별도195다. 이 숫자는 학습 응답이나 품질 승인 수가 아니다. 이메일/전화/URL/인증 형태 등의 보수적 패턴 검사일 뿐 완전 비식별 인증은 아니다. 이름·간접 식별성과 의미/번역 중복의 완전한 부재도 입증하지 못했다.

## 실제 정답 편집과 품질 범위

56개 새 원천에서 **224개 새 응답**을 개별 작성했다. 원천의 갈등·취미·직업·취향 등의 상황을 한국어로 재구성하고4개의 기존 독창적 카드에 각각 판단/반응을 작성했다. 원본 답변을 정답으로 복사하거나 같은 문장에 말끝만 바꾸는 생성 스크립트는 없다. 원천 index/component/대화 hash/가공 고지를 각 사례에 연결하고 파생 자료의 CC BY를 MIT로 바꾸지 않는다. 정답 TSV/전체 JSON/원문/HTML은 모두 local_data에만 보관한다. Codex가 작성·검토했으며 사람 검토나 신뢰성 미달 AI judge 합격으로 부르지 않는다.

|분할|기존 v4 응답|새 응답|합계 응답/상황 변형|
|---|---:|---:|---:|
|학습|104|160|264/66|
|개발|24|32|56/14|
|별도 평가|24|32|56/12|
|합계|152|224|376/92|

전체90원천 가족/92상황 변형이다. 같은 상황의4캐릭터를4독립 대화로 세지 않는다. 새 자료의 기준 출처는 CC BY224응답, 기존 MIT152응답은 그대로다. 별도 평가는 작성자가 알고 있는 합성/원천 분리 자료이며 인간 블라인드가 아니다. 이번에는 새/기존 별도 자료를 모델에 넣지 않았다. 개발은 기존 소비를 유지하며 새 개발 원천을 다시 final이라고 부르지 않는다. 최종 holdout316개도 미소비다.

상황별 우선 관심은 선택권·부담, 작은 실험·비유, 전제·조건, 책임·경계처럼 다르게 작성했다. 실수 정정은 실제 합성 이력에 연결했다. 미확인 공동 여행/강아지 이름은 not_checked, 제공된 카드에 없는 토핑/반려견은 카드 범위 not_found로 주석했다. 이를 현실 사건 부재나 실제 조회/저장 성공으로 승격하지 않는다. 기존 영수증·동의·정정/삭제 주석도 보존한다. 추측/농담을 실제 완료 보고로 표시하지 않는다.

현재 audit는 source/split/대화 hash 결합·카드/원본 보존·라이선스·정확/표면 near 중복·claim span/근거/영수증·반복 표현·정답 마스크를 검사한다. 원천/분할 충돌과 표면 near 경고0,4회 이상 같은 첫 문장0이다. 전부의 자유문장 사실을 추출한 것은 아니며, 주장 주석 누락·의미 중복·공통 반응 수렴은 여전히 수동 근거 검토가 필요하다. 자동 결과를 완전한 데이터 품질 PASS로 쓰지 않는다.

1,000–3,000응답 목표는 미달이다. 특히92상황 중 평온88, 그외4이고 관계는 일반89/동의된 친밀2/불편1이라 **기분·관계 불균형이 크다**. 새 기분·관계의 인과적 대조를 검증했다고 주장하지 않는다. 새 합성 이력2개와 기존 이력만으로 장기 대화/다자 Discord 품질도 증명하지 못한다. 추가 복제보다 이 빈 영역의 원천·정답 편집이 다음 데이터 과제다.

## 토크나이저·pilot 계약·실제 자원 차단

실제 기존 Gemma 토크나이저로 학습264/개발56의 전체320개를 export했다. 학습256–399token(p50 300/p95 383), 정답23–44; 개발264–413(p50 297/p95 387), 정답21–41. 역할·마지막 assistant completion/terminator만 loss, 과거 assistant/user/system/padding 손실 제외를 확인했다. packing/padding/절단을 하지 않았다. 원천/target/전략/주석을 현재 입력으로 누출하지 않는다. 실제 템플릿의 generation block 부재 때문에 [TRL assistant-only](https://huggingface.co/docs/trl/sft_trainer)를 가정하거나 라이브러리를 교체하지 않았다.

새 default는 rank4/alpha8/dropout0.05·LR1e-4 하나·accum4·cosine/warmup5%·maxnorm1·epoch1이다. 최적값이라는 주장이 아니라 이전 세LR을 무작정 반복하지 않기 위한 제한 pilot이다. bounded runner는 전체264개를66유효 optimizer step으로 처리하도록 계약하고 기존128개 상한에서 조용히 잘라 쓰지 않는다. 비교 입력은 기존 핵심8응답+신규 개발8응답을 생성 전에 고정한다. 별도/최종 자료는 사용하지 않는다. 파일/컴파일러/토크나이저 hash와 원천 queue/원본 카드 binding을 모델 접근 전에 확인한다.

실제 새 admission: 가용 VRAM13,247MiB(**12.936523GiB**) < 보수적399/44token 요구 **14.195160GiB**. 온도55°C, 가용RAM 약10.42GiB, commit약30.45GiB. static 단계 `BLOCKED_STATIC_VRAM`, **model_load_attempts=0**이다. GPU 학습/추론/새 adapter 생성0이며 새 loss/gradient/TTFT/생성 p50/p95·품질 A/B 값은 없다. 파라미터/긴 사례/안전 여유를 줄여 강행하거나 다른 프로그램을 종료하지 않았다.512/768/1024/1800token도 실행하지 않았다. 이 차단을 학습 성공이나 후보 기각 품질 판정으로 혼동하지 않는다.

## 검증·마감·재개

표적 소스/마스크28검사 OK0.340초. 후속37검사에서는 Windows 임시 checkpoint directory rename WinError5가1건 발생했다. 동일 실패 케이스를 격리한1검사 OK1.504초로 범위를 좁혔으며 원인을 확정하거나 숨기지 않는다. 이전 체크포인트는 보존됐고 기대값/저장 원자성/안전 기준을 낮추지 않았다. 최종 전체 회귀/Portable/운영 보존/Git 마감은 아래에 누적한다.

비공개 재개 루트는 `local_data/public-training-20261025/`. acquisition/source-summary/prior-binding/editorial-summary/conditional/tokenized/pilot12b/report/checkpoint를 따른다. `editorial-private.html`은 escape/CSP 처리한 로컬 target 비교표이며 원문 대화·외부 script/request를 넣지 않았다. 데이터·체크포인트·로그는 공개/Portable에 넣지 않는다. 실행src가 동일하므로 새 GUI·새 Portable GPU·다른 Windows·새 장시간 GPU/8시간 운용은 NOT VERIFIED다. 이전2시간 mock은 당시 source 범위 근거로 유지한다.

다음: 현재376응답의 의미/인칭/행동 차이를 추가 검토하고 기분·관계/여러 턴·다자 원천을 보강한다. 현재 자료는 기준 pilot의 후보이며 대규모 정답 보증이 아니다. 안전한 새 자원 여유가 있을 때만 동일 데이터/해시/고정 비교 입력의 LR1e-4 pilot을 재개한다. 신호가 부족하면 rank/epoch/학습률 탐색을 확대하지 않는다. 실제 학습·개발 생성의 동시 개선 전에는 별도평가와316개를 소비하지 않는다. 인격 수렴·허위 기억/기능 약속·사회적 판단·실제 `/동의`·배포/장기 검증의 필수 게이트를 유지하므로 **RELEASE BLOCKED**다.


### 최종 검증과 실행 명령

최신 연구 소스 **c507567**에서 전체 **875검사 OK281.831초**(private full-regression.log). 초기 표적 rename 실패가 최종 전체에서 재현되지 않았다는 뜻이며 근본 원인 해결로 확대하지 않는다. 기존 SDK HTTP mock의 기능 회귀는 포함되지만 이번 새 어댑터의 실제GPU→Runtime→SDK 통합은 미실행이다. 새 UI/8시간/다른Windows/GPU 해제 측정도 수행하지 않았다. 이전2시간 검사나 번들83개 결과를 이번 새 실행으로 부르지 않는다.

공개 실행src는 시작8a348d4와 동일하다. Portable은 문서만 증분 반영하고 공개 src/docs170파일·README/기본프로필 포함 **172쌍**, manifest **21,574파일**의 전체SHA256/목록/크기/금지파일 감사를 수행한다(private portable-final.json). 새 연구 도구·원천/정답/HTML/adapter는 번들에 넣지 않는다. 운영설정/bootstrap/두DB/기존final소비장부 **5개SHA256 동일**(preserved-final.json). 기존 모델/LoRA는 변경하지 않았으며 전체 모델binary 전후hash를 새로 인증한 것은 아니다. 공개 staged 내용/목록/민감정보 패턴·링크를 검토한 소스·합성테스트·비식별 문서만 일반 main push한다. 마지막 문서 commit은 최종 main HEAD와 보고로 식별한다.

PowerShell의 PYTHONPATH는 src;tools;tests, Python은 기존 .venv-gemma4다. 도구의 --help와 private checkpoint.json을 먼저 대조한다.

- 공식 자료: tools/acquire_training_situations.py --root local_data/<새루트> --prior-corpus local_data/evaluation-20261024/corpus. 기존 acquisition은 덮어쓰지 않는다.
- 정답: 새루트의 authored.tsv를 원천별로 직접 편집·검토한 뒤 tools/curate_training_situations.py --root local_data/<새루트> --original tests/fixtures/persona_evidence_pilot.json. 공개 코드만으로 private 정답을 자동 재생성한다고 주장하지 않는다.
- 마스크: tools/persona_dataset.py --source local_data/<새루트>/conditional.json --model <기존검증모델> --output local_data/<새루트>/<새export>.
- 제한 pilot: tools/run_persona_pilot.py의 model/source/export/output/tiny-proof/replay-proof에 고정 자료와 기존 증거를 지정하고 --learning-rates 0.0001 --source-queue local_data/<새루트>/source-queue.json --original-source tests/fixtures/persona_evidence_pilot.json. 현재 예산에서는 실행하지 않는다. 기존 pilot12b를 덮어쓰지 않고 새 출력 경로와 새 자원 검사로 재개한다.
- 회귀: python -m unittest discover -s tests -q. 동일 소스의 성공 검사를 이유 없이 반복하지 않는다.
