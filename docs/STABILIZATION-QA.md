# 최종 안정화 검증 — 2026-10-20

시작 HEAD/원격 main은 `d7cf29a`, 작업 트리 clean·fetch 차이 0/0이었다. 이번 차수는 실제 Discord 로그인·송신·명령 동기화 없이 수행한다. 기존 운영 설정·DB·토큰·원본 가중치·LoRA는 보존한다. **사회적 청자 품질 차단이 남아 정식 릴리즈는 BLOCKED**다. 아래 과거 문서보다 이 차수의 실제 측정과 미검증 구분을 우선한다.

## 청자 판정: 형식적 안전과 실제 품질

기존 506개 회귀를 현재 시작 소스에서 다시 실행해 **506 OK / 60.676초**를 확인했다. 샌드박스 안의 첫 실행은 진행하지 못해 취소했고 별도 로그를 보존했다. 실제 실행 결과로 대체하지 않는다.

### 장시간 검사에서 재현한 별도 무응답 결함

첫 혼합 GPU 운용은 **28.406초 / 24회차에서 FAIL**했다. 두 독립 직접 요청 중 하나가 `conversation_capacity_veto`로 사라졌다. 원인은 완료된 독립 대화 기록도32개 RAM 한도에서 모두 진행 중인 것으로 취급해, 최근300초 안에는 새 직접 요청이 들어갈 공간을 확보하지 못하는 것이었다. 테스트 입력을 덜 보내거나 한도를 늘려 숨기지 않았다.

진행 task·model-switch deferred·request·pending mention을 모든 정리 경로에서 보호한다. 명확한 직접 요청이나 확인된 기존 상대의 의미 판정 후보에 한해, **완료된 캐시 이력**을 정리해32개 한도를 유지한다. 후속 후보는 의미 판정에 사용할 상위4개 실제 근거 frame도 보존한다. LRU는 RAM 정리 순서에만 쓰고 청자/합류 근거로 사용하지 않는다. 기존 상대라는 이유만으로 발언권을 주지 않으며 모호한 후보 과다·방송/타인 대상은 여전히 검증한다.

새 회귀는40개 독립 직접 질문 전부의 원본 reply와32개 상태 한도,32명 중 한 명의 오래된 보류 요청 보호, 방송 발언의 침묵을 검증한다. 중간 NameError와 단일 화자32개 흐름의 모호성을 잘못 분리한 test fixture도 실패 로그로 남겼다. 수정 뒤40초 모의 운용70개 독립 답변/중복·scope veto70건/DB lock복구·삭제 veto 등이 통과했다. 단기40초를 장시간 PASS로 간주하지 않고 새20분 GPU 혼합 검사를 시작했다.

최종 전체 회귀는 **519 OK / 78.738초**이며, 이후 변경한 Portable manifest 테스트의 추가 확인도 별도 보존한다. 기존 상태/보안 검사를 삭제하거나 기준을 완화하지 않았다.

후속 파일 감사에서는 배열/null인 config나 text_config가 `AttributeError`로 전체 탐색을 중단할 수 있었고, index의 이름과 실제 shard tensor 목록도 대조하지 않는 것을 확인했다. JSON 객체 형식·인덱스 구조·파일별 이름/중복/누락·offset 정수 타입을 검증해 불량 폴더만 사용 불가로 표시한다. 이를 포함한 최종 전체는 **523 OK / 88.356초**, 최종 모델/패키지 재검11개도 통과했다. 이전 실패와515/519 성공 기록은 삭제하지 않는다.

기존 출력 문법은 `human ... yes`처럼 타인 청자 판정과 봇 응답 허가를 동시에 제안할 수 있었다. 새 constrained grammar는 human/uncertain의 출력 허가, broadcast의 텍스트 허가를 제외한다. 최종 검증기도 유지하며 과거 acknowledgement yes/react 입력은 기존처럼 침묵으로 정규화한다. 이 변경은 확정된 수신자 경계를 중복 보호하며, **의미 판정 정확도 개선 자체를 증명하지 않는다.**

| 평가 | 결과 | 용도 |
| --- | --- | --- |
| 이전 미사용 8, 시작 정책 | 8/8 | 이번에 처음 실행; 이후 미사용 자료로 재분류하지 않음 |
| 이전 개발 44, 시작 정책 | 40/44 | 오개입 1·누락 3 |
| 지침을 순서대로 압축한 후보 | 최소 타인 청자 probe 실패 | 미채택; 실제 문항 점수 없음 |
| 발화 행위 라벨을 먼저 생성한 후보 | 36/44 | 오개입 0이나 누락 증가·상태 오류; 미채택 |
| 압축 지침 + 수신자 문법 제한 후보 | 최소 probe 실패 | 미채택 |
| 고정한 새 독립 32, 기본 지침 + 문법 제한 | **26/32** | 오개입 0·누락 5·연결 오류 1 |
| 같은 최종 정책의 개발 44 | **40/44** | 오개입 1·누락 3, 개선 주장 없음 |

독립 32는 후보 지침을 고정한 뒤 합성 이름·장터 준비 주제·사람 간 대화·보고/바깥 질문·직접 호출·맞장구·그룹 초대 등으로 작성하고 SHA-256 봉인했다. 원본은 로컬에만 보관한다. 결과 확인 뒤 해당 문항을 고쳐 점수를 올리지 않는다. 이 점수를 실제 사용자 모집단 정확도나 사람 평가로 확대하지 않는다.

주요 잔여 문제는 기존 상대의 근거 있는 우려·확인·핀잔·정정 누락, 전달문에 붙은 바깥 질문 누락, 일부 그룹 질문의 독립 대화 분리다. 개발 자료에는 제3자의 향후 계획 전달을 그룹 초대로 보는 오개입도 남는다. 시간을 기준으로 합류하거나 응답을 강제하는 우회는 넣지 않았다. 새 모델 학습·추가 GPU 분류 호출·새 사용자 ID 추정도 하지 않았다.

## 로딩 메모리: 원본과 공식 shard 복사본

Windows / RTX 4070 Ti SUPER 16GB / RAM32GB, Torch2.9.1+cu128·Transformers5.20.1·Safetensors0.8.0에서 측정했다. RAM working set, process private commit, system commit, CUDA allocator 수치는 서로 다르다.

먼저 합성 256MiB 한 파일과 64MiB 네 파일을 pread로 열었다. open 반환 뒤의 current private 증가는 거의 0이지만 OS peak private 증가는 각각 약257MiB / 65MiB였다. 현재 native pread의 선행 COW 예약은 파일별 순간 피크이며, 샘플링만으로 놓칠 수 있다.

`tools/prepare_sharded_model.py`는 **선택적으로 실행하는 로컬 QA 복제 도구**다. 원본을 읽기 전용으로 열고 [공식 Hub 분할 API](https://huggingface.co/docs/huggingface_hub/package_reference/serialization)와 Safetensors 저장/읽기를 사용한다. 한 번에 최대2GiB 그룹만 물질화하며 저장 후 원본과 모든 텐서의 SHA-256·shape를 비교한다. 원본 덮어쓰기·하드링크 수정·다운로드·운영 모델 자동 선택은 하지 않는다. 추가 디스크 약22.28GiB가 필요하고 공간 부족/기존 출력 폴더는 사전 거부한다. 생성 중 중단된 폴더를 정상 모델로 승격하지 않는다.

실제 복사본: **677개 텐서 모두 일치, 12 shards, 최대 shard 2147118104 bytes**. 최초 시도의 HF blob 확장자 검사 오류는 파일 작성 전에 발생했고 수정 후 재실행했다. 원본·복사본을 서로 다른 새 프로세스에서 차례로 로딩했다. 기존 보수적인 34.28GiB admission을 양쪽 모두 통과한 뒤 측정했으며, 안전 기준을 먼저 낮춰 성공시킨 결과가 아니다.

| 실제 측정 | 원본 단일 파일 | 같은 텐서의 shard 복사본 |
| --- | ---: | ---: |
| process OS peak private commit | **31.35GiB** | **13.01GiB** |
| process peak working set | 4.81GiB | 4.81GiB |
| CUDA peak allocated | 7.21GiB | 7.21GiB |
| backend 로딩 구간 | 25.016초 | 25.485초 |
| 최소 추론·수신자 probe | PASS | PASS |
| 동일 두 질문의 greedy 출력 | 두 쌍 모두 일치 | 두 쌍 모두 일치 |

단일 비교이며 로딩 속도 향상·전반적인 품질 동등성의 통계 검증은 아니다. byte 단위 텐서 일치는 모든 원본 가중치 값이 보존됐다는 근거다. 서로 다른 프로세스의 GPU 최고 메모리에는 해당 합성 출력만 포함된다.

새 admission은 **측정한 config hash·2GiB 이하 shards·20~24GiB 총 크기·Windows·동일 세 라이브러리 버전**일 때만 `최대 shard + 준비12GiB + margin2GiB`, 이 복사본에서는 약16GiB다. 관측 peak13.01GiB보다 여유를 둔다. 원본 단일 파일은 기존 약34.28GiB를 유지한다. 미측정 config/버전/크기는 총 가중치+기존 준비 reserve로 되돌아간다. RAM/VRAM/온도 안전 기준은 바꾸지 않았다. 이 값은 admission estimate이며 모든 PC에서의 성공 보장이 아니다.

system commit의 OS peak는 **부팅 이후 최고치**로 명명했다. 검사 구간의 global peak로 오해하면 안 된다. 50ms sample과 process OS peak를 함께 보존하며 process handle 수도 계측한다. cuBLAS workspace 정리는 이전 worker-drain 경계를 유지한다.

메이플 실행·조작·종료나 페이지 파일 변경은 하지 않았다. 실제 게임과 병행한 안정성·지연은 **NOT VERIFIED**다. 상주 후에도 컨텍스트·생성에 추가 VRAM이 필요하고 전환은 다시 host 메모리를 요구한다. 로딩 완료가 이후 모든 자원 상황의 안전을 보장하지 않는다.

## 캐릭터·성능·운용 검증 상태

캐릭터 energy/calmness/honesty/exclamation/emoji/humor는 기존 두세 구간 대신 다섯 행동 구간(0~14 / 15~39 / 40~64 / 65~84 / 85~100)으로 컴파일한다. 정체성·기분·성별·저장 프로필 값은 덮어쓰지 않는다. 슬라이더101개 값마다 지각상 다른 목소리를 보장하지 않으며 UI에 다섯 단계임을 안내한다. 사실성·필수 설명·보안·참여 권한을 바꾸지 않는다. 실제 네 프로필 생성과 사람 말투 평가는 별도로 기록한다.

전체 지연은 직접 호출 GPU 생성→송신 mock, 청자 분류만 수행한 경로, 기술 설명을 구분한다. 캐시 A/B는 같은 resident 모델·동일 packet·디코딩·counterbalanced 순서·warmup 제외로 수행하며, CPU token-choice 재사용과 모델 계산 속도를 혼동하지 않는다. 추가 집계는 검증 완료 후 이 문서에 누적한다.

실제 기본 no-LoRA의 직접 호출9/9은 수신→송신 mock **평균3.233초 / p50 3.234 / p90 3.731 / p95 3.756초**였다. TTFT는 첫 callback 기준 근사 p50 .500/p95 .516초, 전체 생성 tokens/sec p50 8.914, idle queue p50/p95 0, text stage p50 3.188/p95 3.716초로 생성이 지배했다. output check와 mock sending의 p95는 각각 .016초, 재생성0. Windows monotonic 해상도 아래 stage0을 비용0으로 해석하지 않는다. 이전 차수의4초대 수치와는 캐릭터 지침 등이 달라 동일 조건 속도 개선율로 비교하지 않는다. 의미 분류만 한23 GPU 호출을 포함한 독립32의 판단 지연 p50 1.211/p95 1.469초도 전체 생성 지연과 합산한 대표값이 아니다.

token-choice cache A/B는3개 동일 packet×5회 교차 반복, warmup6호출 제외, 각15회다. 판정15쌍 일치, cache OFF p50/p95 **1.203/1.396초**, ON **1.219/1.380초**로 사전 median 개선 기준을 충족하지 못했다. **캐시는 기본 OFF 유지**이며 큰 추론 속도 개선으로 보고하지 않는다.

네 프로필×동일 세 질문은12/12 mock 전송·재생성0, 같은 질문의 프로필별 출력은 모두 달랐다. 존댓말은3/3 존댓말 끝맺음, 장난스러운 프로필은 짧은 두 답변에 느낌표가1개씩 있었다. 기술 답변 길이는 차분418/장난400/담백485/존대480자로 관찰됐지만 길이가 품질 점수는 아니다. 이모지는12개 모두 없었으므로 해당 축의 효과는 입증하지 못했다. 여러 축을 함께 바꾼 비교이며 개별 slider 인과 효과·기분 전 종류·자연스러움의 사람 평가는 별도다. 새 블라인드 응답/키/빈 평가지를 로컬에 보존했다.

실제 GPU 공정 큐와 같은 가중치의 다른 경로 reload/실패 주입 후 실제 복원·설정 미저장·생성 중 전환·원본901/902 재개도 PASS했다. 전체 전환 시나리오98.812초는 단일 load 시간으로 쓰지 않는다. 신규 용량 검사는 합성 완료 이력32개 뒤 **실제 GPU 답변1건**을 원본3100에 전송하면서 상태32개 한도를 유지했다. 이 검사의32개 초기 답변은 mock fixture이며33개 모두 GPU 생성했다고 보고하지 않는다.

`tools/verify_stability_soak.py`는 합성 Discord transport·임시 SQLite·공정 scheduler로 직접 요청/원본 reply/중복/범위 차단/실제 반응 action/동의 철회·삭제·오래된 작업 veto/DB lock·복구/예약 취소/기한 만료/재시작을 혼합한다. optional GPU probe는 같은 상주 backend를 빌리며 mock producer를 잠시 멈추고 약120초 간격으로 실행한다. 다른 12B 모델을 동시에 로딩하지 않는다. 소요 시간·횟수·task/thread/handle/메모리·큐·재시작 결과를 비공개 산출물로 남긴다. 짧은 smoke 실패(중복 입력 및 thread allowlist fixture 오류)도 보존했다.

첫20분 시도는 위 용량 결함으로28초에 실패했고 보존했다. 두 번째는 mock transport가 결과 목록을 비운 뒤 봇 메시지 ID를 재사용하고 Reaction에도 새 메시지 ID를 반환하는 fixture 결함을 발견해 INTERRUPTED로 중단했다. 운영 프로그램을 종료한 것이 아니며 해당 부분 실행을 장시간 PASS로 계산하지 않는다. 고유 ID/Reaction None/중단된 실행의 FAIL 기록 회귀를 추가한 새 도구로 다시20분 검사를 완료했다. 아래 실제 결과만 PASS로 인정한다. 두10분 runtime 세션 사이 재시작은 별도 항목이고24시간 한 세션 운용 인증이 아니다. 웹/네트워크 전체 동작이나 실제 Discord 검증을 이 도구의 범위로 과장하지 않는다.

## 재현·보존·릴리즈 경계

원본 결과와 source snapshot·명령·실패 로그·봉인은 `local_data/stabilization-20261020/`에 보관한다. 모델 복사본과 출력·DB는 Git에 포함하지 않는다. GPU 실행 전 운영 instance lease·자원을 확인한다. CPU regression은 `PYTHONPATH=src;tests;tools`에서 `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`. GPU/복제/soak 도구는 각 `--help`를 따르고 항상 새 private output을 사용한다.

Portable source/runtime hash·실제 새 저장소·숨긴 Tk·DPAPI·설정 복원·GPU 미리보기는 이번 최종 소스에서도 다시 확인한다. 깨끗한 다른 Windows VM/드라이버/다른 GPU·일반 사용자 화면·실제 Discord·Maple 병행·24시간 운용·설치 프로그램·자동 업데이트는 제공/검증되지 않았다. 새 후보 패키지 생성이나 회귀 성공만으로 정식 릴리즈 PASS를 선언하지 않는다.


## 최종 마감 결과 — 2026-10-20

- **실제 경과1200.422초**,956회차, 독립 mock 답변1912건과 중복/scope veto1912건, 관계 이벤트956건, Unicode 반응191건, 요약/동의 철회·삭제/오래된 기억 veto95회씩, 예약 취소·SQLite lock복구63회씩, 기한 만료47회, runtime 재시작1회, **동일 상주 GPU 대표 요청10/10**. 이 수치는 임의의 실제 사용자 대화 정확도나 실제 Discord 성공률이 아니다.
- 종료 pending task0·queue0, asyncio 종료 후 작업용 thread0. Python thread 수2가 남는 프로세스 종료 직전 관측을 모두 worker 누수라고 부르지 않는다. 상태 최대32개, 각 샘플의 mock queue0. 모델은20분 내내 하나만 상주했다.
- sampled process private 11820670976→11835932672 bytes(**+14.55MiB**), working set 약+15.25MiB, handle531→537(범위531~540), Python threads5→6, 관측 tasks1. 마지막5분 private+1.97MiB·handle537→537이었다. 작은 CPU 증가도 숨기지 않으며 장시간 누수 부재를 인증하지 않는다.
- CUDA allocated7687894528/reserved8640266240 bytes가 모든5초 표본에서 동일했다. 모델 종료 후 PyTorch allocated1024/reserved2097152 bytes, 작업용 worker0을 확인했다. 이 값은 driver context 전체의 크기가 아니다. 실제24시간·게임과 병행·외부 네트워크·Gateway 실운용 검증은 아니다. 일부 CPU 회귀·패키지 hashing을 별도 프로세스에서 병행했고, 동일 조건 성능 A/B는 그 전에 따로 완료했다.
- 최종 source의 shard admission17179503640 bytes(약16GiB)에서 실제 재로딩/최소 probe가 PASS, private OS peak**12.92GiB**, working set4.81GiB·CUDA peak allocated7.21GiB, backend load25.016초였다. 원본 비교의 두 응답과 다시 일치했다. 단일 원본 admission을 낮추지 않았다.
- Portable 번들 Python3.10.11/discord.py2.7.1/Torch2.9.1+cu128/Transformers5.20.1, 시스템 Python 없는PATH·새DATA_HOME·숨긴Tk로 최초 설정/DPAPI/프로필/로컬 모델 발견을 확인했다. 별도 Controller 재시작에서 수정한 프로필과 합성 기억1건을 그대로 읽었다. readiness를 settings까지만 기다린 첫 보존 도구의 AttributeError는 시험 도구 오류로 보존하고 companion 준비까지 기다린 재검이 PASS했다.
- 최종 Portable GPU 검사는 **실제 shard 폴더 등록→모델 준비/probe→설정 저장→해제→실제 로컬 미리보기→종료→설정 복원**을 완료했다. source의 약16GiB 프로필을 사용하며 동시에 두 모델을 올리지 않았다. preview 관계/기억/예약 갱신0, Discord 접속false. 모델 선택 validation과 preview가 각각 로딩하므로 한 번의 로딩 시간으로 합산하지 않는다.
- 최종 전체 회귀 **523 OK58.467초**(이전523 OK86.839/88.356초도 보존). source 검사·SDK HTTP mock·임시 SQLite·격리Tk DPI/키보드·GPU·현재 호스트 Portable 검증을 구분한다. 사용자 화면을 마우스/키보드로 조작하지 않았다.

| 릴리즈 영역 | 판정 |
| --- | --- |
| 원본 no-LoRA 로딩 / shard 실제 메모리 절감·동일 텐서 | PASS, 이 호스트/명시 버전 한정 |
| 대화 이력 용량·요청 보존·전체 회귀 | PASS, 모의 및 대표GPU |
| 20분 혼합 운용·종료 | PASS, 제한된20분 및 두10분 runtime; 장시간 누수 인증 아님 |
| 캐릭터 생성/말투 proxy | 구현·GPU 생성 PASS, 사람 품질/개별 축 인과 효과 NOT VERIFIED |
| 최종 독립 청자32 | **FAIL26/32**; 누락5·연결1, 개발44에는 오개입도 남음 |
| 현재 호스트 Portable 설치 경로·모델 선택·미리보기 | PASS, 격리 검사 |
| 다른 Windows/다른 GPU·driver/깨끗한VM/실제 Discord/Maple 병행/24시간 | **NOT VERIFIED** |
| 설치 프로그램·자동 업데이트 | 미구현 |
| 전체 정식 릴리즈 | **BLOCKED** |

다음 우선순위는 독립32를 개발 자료로 소모하지 않고 남은 의미 판정의 일반화·사람 검토를 개선하는 것이다. 활동 수준/시간으로 답변을 강제하거나 예문별 예외로 점수를 맞추지 않는다. 이후 별도 허가/환경이 있을 때 다른 Windows·실제 Discord·긴 실사용을 확인한다. 이번에는 추가 접속 승인을 요청하거나 실제 서버에 접근하지 않았다.


## 공개 산출물·보존 감사

최종 검토에서 Hub splitter가 max_shard_size보다 큰 개별 텐서를 별도 shard로 허용한다는 예외도 확인했다. 복제 도구는 그런 입력을 메모리 상한 초과로 **파일 생성 전 거부**하도록 명시하고 tiny fixture로 검증했다. 이번 공식 원본의 최대 텐서는 해당 상한 이내였고 이미 생성한677개 값의 검증 결과는 유효하다. 앱 로딩·원본 모델은 수정하지 않았다.

Portable 최종 전체 streaming manifest 생성 뒤 **4.59GiB / 24757파일**, source81/docs43 byte·공개 hash 일치, manifest 누락/크기 차이0, 모델·DB·설정·비공개 파일0건을 확인했다. 서명 bootstrap/settings·운영 companion/sent DB 네 파일의 시작/종료 SHA-256도 모두 동일하다. 원본 base weights는 Hub ETag와 실제 전체 SHA-256이 일치했다. 완전히 resolve한 Xet 저장 식별자를 내용SHA로 오인한 첫 감사는 수정했으며 가중치 변경이나 재다운로드를 하지 않았다.

공개38파일의 실제 운영 secret/ID 리터럴·개인 절대 경로·깨진 문서 링크·index/worktree 차이0, staged diff/check를 확인했다. source commit과 마감 문서 commit 및 최종 clean/push는 후속 마감 절과 git log를 따른다. 원본 비공개 산출물·가중치 복사본·Portable 런타임은 GitHub에 올리지 않았다.


최종 구현 commit **94c87fc** (시작d7cf29a). 최종 전체523 OK58.467초·공개38파일 stage검사0건·운영4파일hash동일·원본weights Hub ETag 일치. Portable4.59GiB/24757파일 source81/docs43 byte·manifest 공개hash 일치/비공개 파일0. 정식 릴리즈 BLOCKED, 코드·후보만 보존한다. 최신 문서 마감 commit은 git log를 확인한다. 실제 Discord 접속·사용자 데스크톱/게임 조작 금지는 유지한다.
