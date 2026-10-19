# 전체 응답 파이프라인 계측

## 2026-10-20 최종 안정화 — 최신

마감: **523회귀 OK58.467초**, 실제20분 혼합 운용1912 mock 답변·GPU10/10·worker0, source 및 Portable의 실제 shard 로딩/모델 선택·미리보기 PASS. 최종 shard peak12.92GiB(최초13.01), 원본31.35GiB. 운영 자료 보존·독립 청자26/32로 **릴리즈 BLOCKED**. 실제 Discord/다른 Windows/Maple/24시간/사람 말투 평가는 NOT VERIFIED. 상세·소스/패키지·Git 마감은 STABILIZATION-QA를 우선한다.

최신 cold loader 비교에서 원본/공식 shard 복사본 load25.016/25.485초, OS peak private31.35/13.01GiB였다. 로딩 속도 개선으로 주장하지 않는다. 현재 최종 GPU suite는 직접 호출→mock 전송, 캐릭터 기술 설명, 분류 token-choice cache A/B, 공정 큐/전환, sparse GPU 혼합 운용을 구분한다. 완료한 수치만 링크 문서의 마감에 기록하며 실제 Discord network 지연은 포함하지 않는다.

상세 근거·실패·미검증·재현·마감: [최종 안정화 QA](STABILIZATION-QA.md). 아래 이전 차수의 숫자는 당시 기록이다.


## 2026-10-19 재개 — 실제 생성과 같은 GPU A/B (최신)

기본 no-LoRA 로딩·최소 추론을 통과했다. 초기 backend load25.969초, Windows process peak commit31.35GiB/working set4.81GiB, 반복 로딩 peak 약32.6GiB. 기존 weight+2GiB는 부족해 실측 준비비용 reserve10GiB+margin2GiB로 보강했다. 모델 해제 뒤 cuBLAS workspace가 큰 split segment를 붙들어 남은 PyTorch reserved 약6.99GiB를, worker 종료 후 안전한 workspace 정리로2MiB까지 줄였다. 다른 Torch 버전은 capability 검사하며 미검증이다.

같은 GPU·가중치·캐릭터·입력·디코딩에서 bare/disabled-PEFT를 교차하고 질문별 warmup pair를 제외했다. 각9회, E2E p50 **4.047/4.234초**, p95 **4.715/4.797초**, TTFT 근사 p50 .531/.547초, 생성 전체 tokens/sec p50 8.314/8.172. 출력9쌍 동일·재생성0. 표본이 작아 통계적으로 확정된 속도 개선은 아니다. LoRA 스타일 효과 비교도 아니다.

별도 직접 호출9/9은 E2E p50 4.218/p95 4.865초, text stage p50 4.203/p95 4.846초, idle queue0, mock sending p95 .016초였다. 실제 Discord 네트워크/최초 로딩은 제외, TTFT는 첫 callback의 wall-time 근사다. stage0은 시계 해상도 아래일 수 있다. 기존 분류만1~2초/서로 다른 질문6초·30초와 혼합하지 않는다. 캐릭터12문항 p95 24.881초는 기술 설명이 포함돼 짧은 잡담과 동일 조건 비교가 아니다.

실제 공정 큐·생성 중 전환/실패 복구·Portable GPU 미리보기는 통과했다. 다만 사회적 청자 평가의 오개입/누락과 다른 Windows·장시간 안정성은 남아 **릴리즈 BLOCKED**. 전체506 OK55.636초. [계측·원본·재현](RESUMED-GPU-QA.md)을 우선하며 아래 N/A·GPU 중단 기록은 과거다.

## 2026-10-19 f1c0ec6 후속 — 로딩 병목과 측정 경계

Windows1455를 native pread의 선행 전체 COW 매핑까지 추적했다. 합성파일64/256MiB 각2회와512MiB1회에서 거의 파일 크기만큼 순간 commit 예약을 확인했다. 50ms system commit 표본과 OS process peak/private·working set을 함께 기록한다. 순간 매핑은 open 반환 후 사라져 current RAM만 보면 놓칠 수 있다. [상세 원인·수치·재현](LOADER-MEMORY-QA.md).

no-LoRA import private1432.73MiB, PEFT import 포함1546.89MiB; 이는 import 비용이며 실제 모델 load peak가 아니다. 실제 모델22.28GiB, 사전 guard24.28GiB에 비해 여유13.37GiB로 GPU 시작 전에 차단했다. 같은 조건의 GPU 재시도는 하지 않았다. +2GiB는 provisional admission margin이며 전체 NF4 피크 보장은 아니다. 같은 guard를 import와 processor 준비 후 재검사한다. 개발용 full profiler는 registry/import/processor/model init·native safe_open/NF4 convert/최소 추론/unload 단계와 이미 초기화된 CUDA allocator를 관찰하도록 준비했지만 후반부는 실행하지 못했다.

**이번 새 기본 모델의 E2E p50/p95, TTFT, tokens/sec, queue 지연, 로딩/전환 시간, VRAM 피크, 취소·재생성률, 실제 GPU 다중 사용자 처리량은 N/A**다. 모델이 준비되지 않아 응답을 생성하지 못한 admission 시간을 정상 응답 지연으로 혼합하지 않는다. 사회적 판정/캐릭터/전체 파이프라인 GPU A/B도 미완료다. 최종500개 단위·모의 회귀 OK60.204초는 정확한 GPU 지연 측정이나 실사용 품질 검증을 대체하지 않는다.

Trace는 실제 Discord on_message에서 넘기는 monotonic 수신 시점부터 모의/실제 전송 완료까지 기록한다. scope_check, member_resolution, conversation_candidates, conversation_wait, social, assessment, memory_lookup, summary, research, action, text, output_check, sending을 분리한다. permissions/catalog/discord_send 하위 span과 전처리 총계는 겹칠 수 있으므로 더해서 E2E를 만들지 않는다. 선택된 작업에만 UI 상세를 표시한다. 생성은 단일 GPU 공정 큐를 공유한다.

각 모델 호출은 queue_seconds(대기), worker_seconds(전처리 포함 실제 worker), preparation/tokenization, 첫 stopping callback(TTFT 근사), 전체 생성 토큰/초, 종료 토큰, RAM/VRAM을 기록한다. 첫 callback은 동기화한 GPU 첫 토큰/Discord 사용자 표시 시간이 아니다. load_seconds/switch_seconds는 모델 단계의 별도 값이다. summarize는 성공 전송 E2E 평균/p50/p90/p95, 모든 결과 건수, queue/TTFT/tokens/sec/RAM/VRAM과 재생성을 구분한다. 모델 초기 로딩과 warm 생성, 침묵과 성공 답변 지연을 혼합하지 않는다. 원문/토큰/비공개 추론은 로그에 쓰지 않는다.

이번 실GPU 청자 재검은46문항45/46, 평균1.158초/p501.562초/p952.043초, 의미 물리 작업33개, peak allocated8059.6MiB였다. 이는 분류+고정 합성 전송이며 전체 답변 속도가 아니다. 앞선 같은46문항40/46·오개입3·누락3 대비 정확도는 개선됐지만 하드웨어 부하가 달라 지연 개선을 주장하지 않는다. 당시 한 건의 명시적 제외 표현을 잘못 받았고 이후 검증기에 제외 근거를 추가했다. 이 추가와 공식 no-LoRA 로더의 실제 GPU 독립 평가는 아직 수행하지 못했다.

실제 생성용 동일9문항(3질문×3반복) legacy PEFT wrapper+base vs no-LoRA base A/B, 네 캐릭터×세 질문 비교 프로토콜을 준비했다. 그러나 Windows commit 부족1455가 모델 열기에서 발생해 **실행 완료하지 못했다**. 수신→최종 답변 p50/p95·TTFT·tokens/sec의 새 비교 수치는 N/A이며 과거 다른 질문의6초/30초를 대신 넣지 않는다. 검색/요약/모델 전환의 최신 GPU 지연도 N/A다.

긴 구조화 선택지 토큰화의 bounded4-entry cache 후보는 구현했으나 기본OFF다. `--cache-choices`로만 시험한다. 동일 GPU A/B가 없으므로 자동 활성화하지 않았다. 중복 문맥 재사용 후보도 미채택했다. max_new_tokens/종료 조건/attention/KV cache/기술 설명 분량을 임의로 줄이지 않았다. 현재 가장 명확한 제약은 가중치 로딩을 막는 호스트 메모리이며 프로그램 종료/시스템 page file 변경으로 우회하지 않았다.

재현(개발자): 기존 GPU 작업 종료와 운영 잠금·자원 여유를 확인한 뒤 PYTHONPATH=src;tools에서 verify_social_gpu.py의 --protocol/--output/--official-base/--cache-choices를 사용한다. 새 output을 쓰며 원본 결과를 덮지 않는다. protocol/소스 hash·실제 가중치·동일 디코딩·seed·warmup을 보존한다. 합성 transport의 E2E에는 실제 Discord 네트워크 지연이 없다.
