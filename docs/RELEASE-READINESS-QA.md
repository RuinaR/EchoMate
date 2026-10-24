# 릴리즈 준비·생성 방식 비교·독립 안정화 — 2026-10-24

시작 main/local/remote `4587355590330f86c83f561121ac2f0a5db521c9`, clean. 단계 DEVELOPMENT / RELEASE BLOCKED. [요구사항 추적표](RELEASE-CHECKLIST.md)의12개 필수 영역/세부 게이트를 기준으로 진행한다. 운영4파일 hash를 `local_data/release-readiness-20261024/preserved.json`에 봉인했다. 실제 Discord 인증/명령/송신·운영 자료/모델 변경·다른 앱/게임/사용자 Desktop 조작은 하지 않는다.

## 선정한 과제·계획

1. 대화 품질이 최우선이다. 이전 문단/배치·CFG·두 단계·모델 교체를 반복하지 않고 **현재 강제 greedy와 공식 sampling의 차이**를 비교한다. [공식 generation_config](https://huggingface.co/google/gemma-4-12B-it/blob/657684f/generation_config.json)와 기존 QA 모델의 로컬 config는 do_sample=true/temperature1/top_k64/top_p.95지만 Runtime은 greedy를 강제한다. 공식값이 EchoMate의 성능 보장은 아니다. [비결정성 평가 연구](https://aclanthology.org/2025.naacl-long.211/)도 sampling이 항상 우수하지 않음을 보여주므로 두 고정 seed의 전략/사실성·비용을 함께 본다. 추가 모델/계획 호출 없이 실험 tools에서만 generate parameter를 바꾸고 RNG를 요청 범위에서 복원한다.
2. mock Runtime/실제 임시 SQLite의20분 실경과 혼합 soak를 독립 실행한다. 메시지 중복/범위·동의·삭제·예약 취소·DB 잠금·queue 기한·재시작·작업 잔류를 확인한다. 가상시간과 실제 운용/모델 품질을 혼동하지 않는다.
3. 기존 격리 Desktop 렌더러로 현재 setup/models/character/status와 팝업/DPI를 확인한다. 새 게임 입력/캡처/후킹 라이브러리는 쓰지 않는다. 실제 저장 연결은 관련 기존 이벤트 회귀와 분리 기록한다.
4. Portable의 전체 파일 SHA256/membership를 읽기 감사하고, 변경 공개 파일만 증분 반영한 뒤 번들 검사·전체 회귀·운영 hash·staged 개인정보 감사를 마친다. 다른 Windows·실제 Discord가 없으면 NOT VERIFIED/BLOCKED로 유지한다.

## 실행 결과

### 도구·검증 계약

도구 체크포인트 `67f8823`. 실행 src/기본 생성·프로필/동의/DB schema는 시작4587355와 동일하다. `sampling_diagnosis.py`/`run_sampling_release.py`는 앱에서 import하지 않는 평가 전용이다. 한 모델의 요청 범위에서 두 seed/공식값을 적용하고 RNG·generate method를 오류 시에도 복원한다. 의미/선택 판단에는 적용하지 않는다. Runtime 메시지48개(새 개발 입력4×프리셋4×greedy/두 seed)를 사전 봉인했고 best-of-N/추가 AI 채점/최종316개 소비는 없다. 닫힌 기능 안내가 모델을 우회하면 생성 호출로 세지 않는다.

`audit_portable.py`는 기존 manifest의 전체 파일 목록·크기·SHA256을 읽기 전용으로 감사한다. 이전의 공개 소스 hash/런타임 크기 검사와 달리 같은 크기의 런타임 변조도 잡는다. traversal/중복 key/대소문자 alias/Windows reparse/금지 파일을 거절하며 잘못된 manifest를 자동 수리하지 않는다. 민감 파일 이름 검사는 전체 바이너리의 개인정보 부재를 증명하는 만능 내용 검사로 확대하지 않는다. 이 배포본의 내용/의존성은 별도 기존 패키징 경계와 공개 파일 감사를 함께 따른다.

초기20분 mock soak는22.422초/20반복에서 잘못된 검사 기대 때문에 중단됐다. 서로 다른 사용자 두 답장의 원본/작성자는 맞았지만 완료 순서가 뒤바뀌었다. 큐 진입 이전 비동기 준비의 완료 순서를 고정 FIFO로 가정한 도구 오류다. `verify_stability_soak.py`는 원본 multiplicity와 원본→작성자/유형을 비교하도록 수정했으며 중복·누락·작성자 뒤바뀜·다른 Action은 계속 실패한다. 첫 helper의 `Counter(mapping)` 오용도 합성 단위 검사에서 발견해 `.keys()`로 고쳤다. 제품 결함 해결이나 큐 공정성 개선으로 세지 않는다. 초기 실패 기록을 보존하고 새 폴더에서20분을 다시 시작했다.

신규 표적8검사 OK0.070초. same-size 변조/경로/alias/유효 hash의 Settings.JSON·sampling 실패 후 RNG/메서드 복원·동시 완료의 원본 binding을 포함한다. 전체 회귀는 아래 최종 결과와 구분한다.

### 최신 UI·배포 근거

`render_isolated_ui.py --pages setup models character status` exit0. 자체 Desktop 검증 true/사용자 Desktop 캡처 false, 100/125/150%×1040/1180의30행·PNG55개(팝업 포함), callback 오류0이다. 대표150% character/models 선택/status/배경·정체성 팝업4개를 직접 이미지 확인했고 버튼 겹침/잘린 입력 영역은 보이지 않았다. 55개 전체의 심미성·실제 사용자 입력/저장·다른 화면 모두를 직접 검토한 것으로 확대하지 않는다. 운영 설정 없이 합성 snapshot/Mock Controller만 사용했으며 기존 입력→저장 회귀는 별도 전체 검사에 포함한다.

초기 Portable 전체 감사는21,568파일/4,877,370,761 bytes, missing/extra/크기·hash 불일치/금지 파일0이었다. `local_data/release-readiness-20261024/portable-before.json`은 비공개 원본 근거다. 최종 문서 증분 반영 뒤 다시 전체 감사한다. 다른 Windows·새 드라이버·번들 GPU를 검사한 결과가 아니다.

### 진행 결과와 최종 판정

GPU/20분 soak/전체 회귀/최종 Portable·보존·Git 결과는 아래에 누적한다. 이전800개 회귀와 과거 GPU/GUI 수치를 이번 재실행으로 쓰지 않는다.

### 실제 GPU 비교 — sampling 기각

기존 분할 Gemma 4 12B/NF4/no-LoRA 한 인스턴스, source4587355·도구67f8823, 두 seed20261024/20261025, temperature1/top_k64/top_p.95, 응답 상한768, 같은 입력/4프리셋/순서 교대다. 준비39.172초, 실경과424.906초. Runtime48메시지/실제 SDK HTTP mock48송신, 원본 reply48/48·중복0·pending0이다. 총53추론은 답변36+기존 출력 재작성3+이력 판별12+probe2다. `unconfirmed-past`12개는 이력 판별 뒤 같은 닫힌 안내가 나왔으므로 자유 생성의 사실성12/12나 인격 개선으로 세지 않는다. 실제 외부 HTTP는 mock/차단 상태였다.

| 조건 | 전체16메시지 E2E p50/p95초 | 2문장 요청8개 p50/p95초 | 해당8개 출력토큰 p50(재작성 포함) |
|---|---|---|---|
| greedy | 7.703 /14.301 | 7.703 /12.449 | 52.5 |
| seed20261024 | 8.704 /17.766 | 8.704 /14.774 | 61.5 |
| seed20261025 | 7.594 /16.098 | 7.594 /13.841 | 51.5 |

queue 대기 최대0초, 전체 TTFT p50은각1.140/1.141/1.156초다. 2문장 workload의 관측값은 초기10/20초 목표 안이지만 n8/조건·단일 활성 요청이므로 부하 p95/장시간 SLO 인증은 아니다. 출력 길이가 달라 sampling의 속도 개선은 주장하지 않는다. `process-dry`는 세 조건 모두 기존 재작성1회가 있었다. 추가 계획 모델/평가 모델은 없다.

개성은 열린 두 질문의 모든 출력24개를 개발자가 검토했다. 라디오 질문에서 greedy 직설형은 짐을 가져오지 말자는 선택을 했지만 sampling 두 seed는 일반적인 수리/소장 조언으로 이동했다. 과정 생략 질문도 공통적인 자원/위험 확인으로 수렴했다. 문장 변화는 있으나 두 seed에서 캐릭터별 관점의 안정적인 강화는 입증되지 않았다. 신뢰도 미달 AI judge의 점수나 임의의 블라인드 분류 정확도를 만들지 않았다. 사람이 느끼는 만족도는 NOT VERIFIED다.

미래 부탁의 공개 기능 근거는 memory=off/본인 동의false, reminders=ready였고, 임시 기억·예약은 모두0행이다. 합성 출력12개를 주체/시점/조건/실제 실행과 함께 검토했다. 명백한 미래 기억 약속은 greedy2/4·첫 seed1/4·둘째 seed2/4, 지원 중인 알림을 없음/비활성으로 설명한 것은각1/4·1/4·2/4였다. 중복을 뺀 명백한 위반 출력은각2/4·2/4·3/4다. 직설형 greedy의 조건부 미래 표현처럼 모호한 것은 실패 수에 억지로 넣지 않았다. 이것은 새 좁은 개발 질문의 수작업 판정이며 자동 한국어 판별기 정확도가 아니다. 근거/주석/출력은 비공개 JSON/HTML에 보존했다.

예: 첫 seed의 다정형은 “나도 그 의미를 잘 기억하고 있을게”, 둘째 seed의 다정형은 “부탁도 잘 기억해 둘게”라고 답했다. 분석형 첫 seed는 “알림을 예약하거나 특정 시점에 메시지를 보내는 것이 불가능”하다고 잘못 설명했다. 합성 예시이며 실제 사용자 대화가 아니다. 약속을 피한 일부 응답도 있었으나 다른 캐릭터/seed의 위반과 상쇄하지 않는다. **인격/사실성 동시 개선 불충족으로 sampling 미채택**, 앱의 greedy·기본 모델·운영 선택은 유지한다. 온도/seed를 다시 골라 점수를 맞추지 않고 최종316개도 소비하지 않았다.

실행 전 RAM 약7.2GiB/commit 여유23.8GiB/VRAM 약12.5GiB/38°C와 기존 admission을 확인했다. CUDA allocated/reserved 최대8376.1/8678.0MiB, OS process private high-water13.009GiB, 주기 샘플의 RAM/commit 최소여유6.140/12.197GiB였다. 중간 집계49°C, 종료 뒤42°C/VRAM free12927MiB를 확인했다. 샘플 시점 수치이며 전 구간 GPU 최고 온도라고 주장하지 않는다. backend.close/프로세스 정상 종료 후 모델을 해제했고 다른 앱/게임 프로세스를 조사하거나 자원을 확보하려 종료하지 않았다.

### 다른 접근의 제한적 사전 검사 — CPU 어댑터

greedy가 유일한 병목이라는 가설이 지지되지 않아 동일 prompt/sampling 조정을 중단했다. [공식 Gemma 개발자 가이드](https://developers.googleblog.com/gemma-4-12b-the-developer-guide/)의 LoRA 가능성과 [PEFT 양자화 학습 계약](https://huggingface.co/docs/peft/developer_guides/quantization)을 확인했다. 이는 이 PC의12B/Windows 학습 보장이 아니다. 설치된 torch2.9.1+cu128/Transformers5.20.1/PEFT0.21.2/bitsandbytes0.50.2, TRL미설치를 읽기 확인했다. 새 라이브러리/모델은 설치하지 않았다.

`probe_tiny_adapter.py`(e9b0d2e)는 새 무작위 Gemma4Unified 텍스트 모델21,248 parameters/LoRA448개, 합성 정수8token의 CPU1step만 검사한다. CPU 한 스레드/해당 프로세스 CUDA 비노출·offline 환경/하위 socket 차단, q/v rank2 어댑터 gradient 유한·기본 텐서 전체 불변·safetensors 저장 뒤 동일 랜덤 base에 재적용한 logits 일치를 확인했다. 출력은 새 private 하위 폴더뿐이다. loss4.10581은 API smoke 결과이지 감소량/품질 수치가 아니다. 기존 운영 모델/가중치/LoRA를 로딩하거나 바꾸지 않았다.

**CPU API roundtrip만 PASS**. 실제12B의 NF4 backward·multimodal wrapper·activation/optimizer/Windows commit 피크·학습 품질·캐릭터 전환 비용은 NOT VERIFIED다. 준비 과정에서 fp32로 바뀌는 embedding/norm과 backward 활성화가 추론보다 메모리를 늘릴 수 있으므로 현재 추론 성공만으로 학습을 시작하지 않는다. 다음 연구는 meta/크기 기반 훈련 메모리 예산과 모델 구조의 어댑터 대상부터 확인하며, 충분한 여유·독립 데이터·중단 한계를 확보할 때만 별도의 작은12B 실험을 검토한다. 최종 평가나 사용자 기억을 학습에 쓰지 않는다.

### 최종 기능 회귀·실행 오류의 구분

수정된 mock soak는 **1200.016초/1036반복 PASS(exit0)**. 독립 reply2072·중복/범위 veto2072·관계 event1036·Reaction207·digest103·철회/삭제 veto103·기억 삭제103·예약 취소69·SQLite lock 복구69·queue 만료 veto51·실제 Runtime 재시작19회다. errors/lingering_tasks는빈 목록, 종료queue0이다. 합성 의미/transport·임시 SQLite/실제 Task lifecycle이며 실제 GPU/Discord 운용이 아니다.

208개 샘플에서 main Task1/queue0, flows/states 최대32·message index 최대85였다. process handles235→244, private27,783,168→44,445,696 bytes(약26.5→42.4MiB), working set41,443,328→59,551,744 bytes였다. 샘플 thread4→5는약898초에서 증가했고 초기 thread 생성 전1/종료5다. Python executor/할당기·수집 중인 진단·상태의 영향을 분리하지 않았으므로 이 상승을 제품 누수나 무누수로 단정하지 않는다. 프로세스는 정상 종료했지만8시간/GPU/실서버 안정성은 **NOT VERIFIED**로 유지한다. 긴 run에서 plateau/소유 객체/종료 후 회수를 추가 확인해야 한다. 기존 실패 로그/첫22초/수정20분 결과를 모두 보존한다.

전체808검사 OK243.511초(exit0). `PYTHONPATH=src;tests;tools`에서 `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`로 실행했다. async debug의 느린 callback 알림은 로그에 보존했고 assertion 실패/에러는 없었다. 기능 통과를 인격/사실성 PASS로 바꾸지 않는다.

번들 Python/번들 src를 우선한65표적 검사 OK12.792초(exit0): test_memory_selection_delivery, test_reminder_freshness, test_card_field_fidelity, test_operation_grounding, test_command_sync_payload, test_command_recovery, test_ui_workflows. 첫 실행65개 중63error는 ECHOMATE_DATA_HOME과 fixture의 상대 local_data가 달라 `private_path`가 거절한 실행 환경 오류였다. 경계를 완화하거나 테스트를 삭제하지 않고 양쪽을 같은 새 격리 디렉터리로 맞춘 뒤 동일 검사를 새 로그에 실행했다. 첫 bundle.log/수정 bundle-fixed.log를 보존한다. bytecode 쓰기를 끄고 운영/번들 저장소에는 쓰지 않았다. UI workflow는 이벤트/Mock 검증이며 실제 사용자 Desktop 조작이 아니다.

두 VBS `/check` exit0은 파일 존재 검사만 한다. 일반 시작/Gateway·실제 Discord 조회/명령/메시지 송신은0이다. 운영 bootstrap·settings·companion/sent DB4파일 SHA256은 시작과 동일하며 실행 src/config diff도4587355 대비 비어 있다. 모델/LoRA/운영 프로필·선택은 바꾸지 않았다. 이번 변경은 도구/문서/합성 검사이므로 앱 재시작·DB 마이그레이션은 필요 없다.

### 재개 명령·우선순위

1. `git status --short`, `git log -3 --oneline`, 원격main·[릴리즈 추적표](RELEASE-CHECKLIST.md)와 이 QA의 실행 버전을 먼저 확인한다. 연구 도구67f8823/e9b0d2e, 운영 소스는4587355와 동일하다. 문서 마감 커밋은 `git log -1`로 확인한다.
2. 품질: 같은sampling 온도/seed·CFG·행동 prompt를 반복하지 않는다. 실제 출력/한국어 주장 주석을 개발 자료로 보존하며, 훈련 전 구조·fp32 전환/activation/optimizer/취소의 메모리 예산부터 검증한다. 작은CPU API 통과만으로12B 학습을 강행하거나 LoRA를 운영 기본으로 바꾸지 않는다. 새로운 원천 확인 자료와 두 품질 축을 사전에 고정한다. 미사용316개는 계속 봉인한다.
3. 안정성: 이번20분 mock과 별개로 실경과8시간/GPU 주기 부하/종료·재시작·누수 확인이 필요하다. 세션 밖 무한 실행이나 자동 재시작을 만들지 않았다. 다른 Windows의 초기 설치/업데이트·실제 사용자 UI는 별도 환경에서 확인한다.
4. 재현: GPU는 `tools/run_sampling_release.py --model <검증된분할복사본> --output <새local_data하위>`, CPU API는 `tools/probe_tiny_adapter.py --output <새local_data하위>`, soak는 `tools/verify_stability_soak.py --seconds 1200 --output <새local_data하위>`, full hash는 `tools/audit_portable.py --root dist/EchoMate-rc-utterance --output <새local_data하위JSON>`이다. 각 새 실행 전에 자원/목적/새 검증 가치를 확인하고 성공한 동일 조건을 이유 없이 반복하지 않는다.
5. 실제 Discord는 최후반이다. `/동의` 비표시는 미해결/원인 미확정. 필요한 시점에 인증 읽기 조회·명령 변경·메시지 송신 계획과 승인을 각각 분리한다. 이번에는 승인 요청이나 실제 API 실행을 하지 않는다. 사회적 오개입/누락/연결 실패도 그대로 릴리즈 차단이다.


## 마감 판정·증거 위치

공개src/docs166파일+README/기본 프로필168쌍만 증분 동기화했다. 최종manifest21,570파일의 membership/크기·전체SHA256을 읽기 감사하여 missing/extra/불일치/금지 파일0을 확인한다(`portable-final.json`). 전체 재빌드·모델/평가 도구/개인 출력/어댑터 동봉은 하지 않는다. 이전 runtime의 크기만 확인한 결과와 이번 전체 rehash를 구분한다. 패키지 이름rc는 정식RC 상태 인증이 아니다.

비공개 원본 경로는 `local_data/release-readiness-20261024/`이다. preserved/after4파일hash, gpu의 seal/results/annotations/aggregates/summary/report.html, 초기soak와soak-fixed의summary/progress, ui/report·PNG, full-regression/bundle와bundle-fixed 로그, tiny-adapter/report, portable-before/final JSON을 보존했다. 원문/실제 생성 전체 출력·DB/진단·초소형 adapter는 GitHub/Portable에 포함하지 않는다. 공개 변경은 tools/합성tests/문서만 명시 stage하고 토큰·실사용자ID·개인 경로·허용되지 않은 확장자와 diff를 검토한다. 운영4파일hash 동일/실행src/config 불변이다.

최종 상태는 **DEVELOPMENT / RELEASE BLOCKED**. 이번에 제품 대화 품질이 개선됐다고 주장하지 않는다. sampling의 효과 부족을 실제 동일 조건으로 확인하고 기각했으며, 전체 패키지 무결성 감사와 올바른 soak 검증 계약·현재 UI/기능 근거를 보강했다. 인격 수렴/일반 기억·기능 약속/한국어 판별 신뢰성/사회적 의미 판단은FAIL, 실제 Discord와다른 Windows는BLOCKED,8시간 운용/넓은 부하·사용자 만족도는NOT VERIFIED다. 현재12B 학습이나 모델 교체는 적용하지 않았다. 남은 문제는 외부 승인만의 문제가 아니며, Discord 승인 이전에도 품질 연구·장기/배포 검증이 필요하다. 무한 백그라운드 실행·다른 앱 조사/창/입력/캡처·시스템 설정 변경은0이다.
