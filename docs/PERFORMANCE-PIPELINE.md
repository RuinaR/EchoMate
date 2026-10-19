# 전체 응답 파이프라인 계측

Trace는 실제 Discord on_message에서 넘기는 monotonic 수신 시점부터 모의/실제 전송 완료까지 기록한다. scope_check, member_resolution, conversation_candidates, conversation_wait, social, assessment, memory_lookup, summary, research, action, text, output_check, sending을 분리한다. permissions/catalog/discord_send 하위 span과 전처리 총계는 겹칠 수 있으므로 더해서 E2E를 만들지 않는다. 선택된 작업에만 UI 상세를 표시한다. 생성은 단일 GPU 공정 큐를 공유한다.

각 모델 호출은 queue_seconds(대기), worker_seconds(전처리 포함 실제 worker), preparation/tokenization, 첫 stopping callback(TTFT 근사), 전체 생성 토큰/초, 종료 토큰, RAM/VRAM을 기록한다. 첫 callback은 동기화한 GPU 첫 토큰/Discord 사용자 표시 시간이 아니다. load_seconds/switch_seconds는 모델 단계의 별도 값이다. summarize는 성공 전송 E2E 평균/p50/p90/p95, 모든 결과 건수, queue/TTFT/tokens/sec/RAM/VRAM과 재생성을 구분한다. 모델 초기 로딩과 warm 생성, 침묵과 성공 답변 지연을 혼합하지 않는다. 원문/토큰/비공개 추론은 로그에 쓰지 않는다.

이번 실GPU 청자 재검은46문항45/46, 평균1.158초/p501.562초/p952.043초, 의미 물리 작업33개, peak allocated8059.6MiB였다. 이는 분류+고정 합성 전송이며 전체 답변 속도가 아니다. 앞선 같은46문항40/46·오개입3·누락3 대비 정확도는 개선됐지만 하드웨어 부하가 달라 지연 개선을 주장하지 않는다. 당시 한 건의 명시적 제외 표현을 잘못 받았고 이후 검증기에 제외 근거를 추가했다. 이 추가와 공식 no-LoRA 로더의 실제 GPU 독립 평가는 아직 수행하지 못했다.

실제 생성용 동일9문항(3질문×3반복) legacy PEFT wrapper+base vs no-LoRA base A/B, 네 캐릭터×세 질문 비교 프로토콜을 준비했다. 그러나 Windows commit 부족1455가 모델 열기에서 발생해 **실행 완료하지 못했다**. 수신→최종 답변 p50/p95·TTFT·tokens/sec의 새 비교 수치는 N/A이며 과거 다른 질문의6초/30초를 대신 넣지 않는다. 검색/요약/모델 전환의 최신 GPU 지연도 N/A다.

긴 구조화 선택지 토큰화의 bounded4-entry cache 후보는 구현했으나 기본OFF다. `--cache-choices`로만 시험한다. 동일 GPU A/B가 없으므로 자동 활성화하지 않았다. 중복 문맥 재사용 후보도 미채택했다. max_new_tokens/종료 조건/attention/KV cache/기술 설명 분량을 임의로 줄이지 않았다. 현재 가장 명확한 제약은 가중치 로딩을 막는 호스트 메모리이며 프로그램 종료/시스템 page file 변경으로 우회하지 않았다.

재현(개발자): 기존 GPU 작업 종료와 운영 잠금·자원 여유를 확인한 뒤 PYTHONPATH=src;tools에서 verify_social_gpu.py의 --protocol/--output/--official-base/--cache-choices를 사용한다. 새 output을 쓰며 원본 결과를 덮지 않는다. protocol/소스 hash·실제 가중치·동일 디코딩·seed·warmup을 보존한다. 합성 transport의 E2E에는 실제 Discord 네트워크 지연이 없다.
