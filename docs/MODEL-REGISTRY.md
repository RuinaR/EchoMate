# 로컬 모델 레지스트리

## 2026-10-23 원본·분할 선택과 추가 메모리 조사

이번 읽기 전용 확인에서 운영 `base`는 HF 캐시 원본이었고 분할 QA 복사본은 자동 선택되지 않았다. UI도 **원본 기본 모델**과 발견한 분할 폴더를 구분한다. 기존 분할 GPU 로딩 private commit 피크13.015GiB/26.157초를 재현했지만 더 낮은 안전한 경로를 입증하지 못했다. Windows pread와 NF4 순차 변환은 이미 라이브러리 기본 동작이며 작은 shard는1.875GiB 최대 텐서의 하한을 받는다. admission/원본/운영 모델은 그대로다. [상세 계측과 기각 근거](RESUMED-MEMORY-UX-QA.md).

## 2026-10-20 최종 안정화 — 최신

마감: **523회귀 OK58.467초**, 실제20분 혼합 운용1912 mock 답변·GPU10/10·worker0, source 및 Portable의 실제 shard 로딩/모델 선택·미리보기 PASS. 최종 shard peak12.92GiB(최초13.01), 원본31.35GiB. 운영 자료 보존·독립 청자26/32로 **릴리즈 BLOCKED**. 실제 Discord/다른 Windows/Maple/24시간/사람 말투 평가는 NOT VERIFIED. 상세·소스/패키지·Git 마감은 STABILIZATION-QA를 우선한다.

검증한 공식12B config hash·20~24GiB 총 크기·2GiB 이하 shards에서만 측정 메모리 프로필을 부여한다. Windows와 Torch2.9.1/Transformers5.20.1/Safetensors0.8.0이 모두 일치할 때 largest shard+준비12GiB+기존 margin2GiB(이번 약16GiB)를 사용한다. 그 외에는 총 가중치+기존10GiB 준비+2GiB로 보수적으로 복귀한다. 원본 단일 파일34.28GiB admission·RAM/VRAM/온도 기준은 유지한다. 별도 검증 복사본은 자동 기본 선택하지 않는다.

상세 근거·실패·미검증·재현·마감: [최종 안정화 QA](STABILIZATION-QA.md). 아래 이전 차수의 숫자는 당시 기록이다.


공식 기본은 google/gemma-4-12B-it 하나다. base/persona/adult 이전 설정은 서명 확인 후 base로 읽고 원본 파일은 자동으로 다시 쓰지 않는다. 다음 소유자 저장 때 새 스키마로 서명한다. 기존 LoRA·실험·가중치는 보존하며 기본 로더는 PEFT를 요구하거나 로딩하지 않는다. 명시적 adapter 인자는 과거 로컬 비교 도구만을 위한 호환 경계다.

model_registry.py가 기본 models 폴더, 소유자 지정 최대8루트, 공식 HF 캐시 snapshot을 읽기 전용 탐색한다. 루트128항목/캐시16snapshot 제한으로 무제한 재귀·다운로드를 피한다. 전체 모델 목록을 스크롤/키보드로 선택하고 위치·형식·크기·검사 사유를 본다. 모델 ID는 경로 hash이며 권한이나 내용 무결성 hash는 아니다. 파일 이동/제거는 재검색·적용 시 다시 검사한다.

지원 후보는 Gemma4 Unified Transformers, Safetensors, tokenizer.json, 채팅 템플릿을 갖춘 모델이다. config/인덱스 크기, shard 경로/존재, Safetensors 헤더/offset/파일 크기, 아키텍처·큰 크기·사전 양자화·auto_map 요구를 검사한다. pickle/remote Python 코드를 실행하지 않으며 from_pretrained는 local_files_only/trust_remote_code=False다. 이는 전체 tensor hash나 한국어·요약 품질 인증이 아니다. 헤더만 정상인 파일도 실제 로딩에서 실패할 수 있다.

GGUF는 별도 엔진이 없어 사용 불가, PEFT LoRA는 기본 모델 일치·독립 품질·메모리 전환이 아직 검증되지 않아 사용 불가다. 다른 Gemma 크기/아키텍처/사전 양자화는 지원하지 않는다. 모델 추론과 판단은 한 인스턴스를 공유하며 향후 판단 모델 분리는 ID 계층에서 확장할 수 있다. 중복 GPU 모델은 로딩하지 않는다.

적용은 파일 재검→runtime 보류·기존 GPU 작업 종료→기존 모델 해제→새 로딩→최소 출력 및 타인 청자 분류 probe→설정 확정 순이다. 누락/크기 불일치 가중치 로딩은 거절한다. 실패 시 기존 ID를 다시 로딩·검증하고 복구 실패 시 안전 정지한다. 이전 설정은 성공 전에 확정하지 않는다. 같은 실제 경로를 고르면 중복 로딩을 피한다. 봇 OFF에서도 준비 검증 후 적용하며 임시 backend를 종료한다. 최소 probe는 상태/구조화 청자 한 사례 검사이며 한국어/행동/요약 전 기능 인증이 아니다. 별도 실제 품질 평가는 [배포 QA](DISTRIBUTION-QA.md)의 미완료 항목이다.

Windows1455 후 실제 전체 로딩을 계측해 파일 크기+2GiB만으로 부족함을 확인했다. 관측한 준비 private 약9.03GiB를 바탕으로 준비 reserve10GiB+margin2GiB를 쓰며 import/processor/같은 backend 재로딩에서 이미 사용한 commit을 중복 계산하지 않는다. 공식 단일 원본의 시작 estimate는 약34.28GiB, RAM3GiB 하한이며 성공 보장/일반 최소 사양이 아니다. 작업이 배출된 모델 해제 시 capability 확인한 Torch cuBLAS workspace도 정리한다. 시스템 page file을 바꾸거나 다른 앱을 종료하지 않는다. CPU-only 미지원, VRAM10GB 안내는 추정치이며 context/드라이버에 따라 달라진다. 네트워크 모델 다운로드/대체 GGUF 엔진은 추가하지 않았다. [실제 로딩·전환·복구·미리보기](RESUMED-GPU-QA.md).

[공식 모델 카드와 라이선스](https://huggingface.co/google/gemma-4-12B-it)는 Apache2.0으로 표시돼 있다. 실제 다운로드 파일의 라이선스/접근 조건을 확인해야 한다. 패키지에는 모델을 넣지 않는다. 이전 Gemma 모델 약관을 Gemma4에 그대로 적용하지 않는다.
