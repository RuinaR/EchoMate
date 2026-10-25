# Lime Runtime 원문·실행 금지·토큰 예산 QA

시작 main/origin `7ba8d28`, clean. Lime 단일 모델, LOCAL_CHAT 유지, 실제 Discord 미실행. 장시간 GPU/Runtime/누수 반복 재시작은 계속 **DEFERRED — USER REAL-WORLD TEST**다.

## 재현과 채택한 수정

1. **이름/조회 보호 경로의 실제 Runtime 연결 누락.** 기존 backend.text는 마지막 user 메시지를 보았지만 Discord Runtime은 실제 발언 뒤에 청자 메타데이터를 붙인다. 따라서 로컬 성공이 Discord 경로의 같은 보호를 뜻하지 않았다. GGUF의 동기 `grounded_reply(text,lookup)`를 공통화하고 Runtime이 원본 Event.content·실제 조회 상태로 호출한다. 기존 기능 영수증 응답을 덮어쓰지 않으며 원본/동의/송신 최신성 검사는 그대로 유지한다. 메타데이터가 붙은 Runtime 재현 테스트에서 자유 생성 fallthrough가 사라졌다.
2. **명시적 실행 금지를 무시한 실제 DB 예약.** 가정·예시라는 설명과 예약하지 말라는 명확한 금지가 있어도 keyword 기반 handle_request가 알림을 생성했다. 예약/등록/저장/삭제 등 명시적 금지 표현은 실제 기능 실행 전에 원문 중 비인용 부분에서 검사하고, 모호한 충돌 요청은 이번 변경을 실행하지 않은 상태로 설명한다. 출력 금칙어 필터가 아니라 실행 권한 경계다. 정상 예약·취소·기존 Receipt 경주는 유지한다. 일반 제안·모든 조건문·과거 전달을 완전하게 이해하는 NLP 판별기라는 뜻은 아니다. 이중 인용 payload 저장은 기존 safe_subject_text가 거부하는 별도 정책이며 이를 완화하지 않았다. 처음 신규 테스트의 인용 허용 가정이 잘못된 것을 실제 응답으로 확인하고 기존 계약에 맞춰 수정했으며 기존 테스트 기준은 낮추지 않았다.
3. **한정된 복합 이름 요청.** 모든 절이 기존 명확한 자기 이름 문법으로 해석될 때만 여러 절을 결합한다. 더 긴 검증 문장이 같은 이름 사실을 포함하면 중복 앞 문장을 조립하지 않는다. 다른 질문·해석 불가능한 제안·인용·조건을 버리지 않고 기존 자유 대화 경로에 남긴다. 저장 이름·NameVersion을 일반 대화로 변경하지 않는다. 임의 서문/혼합 잡담의 이름 오류는 여전히 남는다.
4. **기능 안내가 실제 잡담 질문을 가로챔.** 앞 문장에서 동의 상태를 인정한 뒤 음악/퍼즐에 관한 한 개의 명시적 질문을 해도 동의 안내문만 반환했다. 그 하나의 명시적 질문 범위를 검사하되 생략된 기능 술어(사진 뒤 볼 수 있는지 묻기)는 기존 문맥 처리를 유지한다. 모든 무구두점·복합 의도 의미 판단을 해결한 것은 아니다.
5. **Discord 텍스트 생성의 native 예산 누락.** 실제 엔진 로그에서2057입력토큰이 고정2048을 넘은 오류를 확인했다. 기존 LOCAL_CHAT만 native 토큰 검사를 했다. 새 Runtime 텍스트 경로는 실제 tokenizer로 policy·기능 근거·현재 Event·알려진 reply 원문을 보존하고 완전한 오래된 교환 묶음만 제외한다. 생략 상태도 입력에 표시·계산한다. 고정2048/출력384/margin64와 자원 하한을 바꾸지 않았다. 필수 자료만으로 넘으면 명시적으로 거부한다. 선택은 bounded suffix heuristic이며 토큰 단조성·최대 이력 보존을 주장하지 않는다. 의미 classifier/summary의 모든 호출까지 예산을 보증한 것은 아니다. [고정 llama.cpp server API](https://github.com/ggml-org/llama.cpp/blob/b11721/tools/server/README.md)의 apply-template/tokenize를 그대로 사용한다.

## 실제 Lime·Runtime·SDK mock A/B

단일 상주 모델을 같은 설정/프롬프트/생성 조건에서 이전 Runtime과 새 Runtime에 순서대로 사용했다. 별도 합성 v8 DB와 SDK MemoryHTTP를 사용하며 실제 토큰·운영 DB는 쓰지 않았다. 원문은 ignored `local_data/lime-grounded-runtime-20261025/`에만 보관한다.

첫 능동 세션11이벤트에서 실제 응답을 읽고 감정→조언 거부→타인 전환→다른 사용자 질문→이름→과거 경험→제안/조건→실행 금지로 다음 발화를 정했다. 기존 경로는 근거 없는 공동 경험을 주장했고 새 경로는 미동의·미조회를 구분했다. 같은 원본reply를 유지했다. 명확한 복합 이름 질문도 기존 경로의 대화 중 이름 변경 수용과 새 경로의 관리자 설정 경계를 구분했다. 임의 서문이 추가된 이름 질문은 양쪽 모두 잘못 답했다.

후속 `verify` 세션은 실제 금지된 예약의 DB 생성 전/후를 비교했다. before는 예약1건, after는0건이며 두 경로 모두 Runtime 예외0이었다. 관리자 권한 설명 추가 후보3개와 타인 프레임을 줄인 청자 후보6개도 작은 고정 비교로 검사했으나 미채택했다. 이름 후보는 대화 중 별명 변경을 여전히 허용하는 답을 했고, 프레임 후보는 맞장구를 응답으로 바꾸는 회귀가 있었다. 운영 prompt/classifier/probe는 그 후보로 바꾸지 않았다.

마지막 음악 주제의 능동12이벤트는 타인 간 발언2건을 제외한 응답을 별도로 기록했다. 기능 안내가 잡담을 가로채는 문제와 native 입력 초과/요약 TypeError도 숨기지 않았다. 이 마지막 능동 실행 before/after에 각각 실패가 있었으며 전부 성공으로 세지 않는다. 생성되지 않은 대기 요청은 턴 수에 포함하지 않는다. 의미·매력·자연스러움 검토는 Codex의 검토이며 사람 평가가 아니다.

그 뒤 문맥 예산 수정 후 **동일12이벤트를 한 번 scripted 회귀 재생**했다. 이는 새 독립·능동 평가가 아니다. 해당 실행 before/after 모두 Runtime 예외0, 두 사람 간 발언은 침묵, 대상 응답10건과 원본reply가 맞았다. 마지막 after 입력1594토큰·오래된7교환 제외·최종reply6111 송신을 확인했다. before가 이번에 예외0이었다는 결과와 이전 실행의2057토큰 오류는 모두 보존하며 실패율 개선의 통계적 근거로 과장하지 않는다. shared engine.last_context는 비생성 이벤트에서 직전 값을 유지하므로 그 필드를 각 이벤트의 새로운 측정으로 해석하지 않는다.

## 한계와 다음 작업

자율 의미 청자 qualification은 계속 실패/BLOCKED다. 일반 평서형 공동 경험 유도, 무금지 조건/인용의 실행 의도, 임의 서문이 섞인 이름 요구, 자유 생성의 기능 약속/보존 정책 설명은 미완료다. 요약 경로 TypeError와 의미/요약 native 예산도 별도 원인 확인이 남는다. 현재 입력이 명확하지 않다고 모든 상황에서 침묵시키지 않았으며, 신규 일반 참여를 허용하거나 모델 gate를 낮추지 않았다. **실사용 테스트 준비 완료·RELEASE PASS가 아니다.**

이번 UI 레이아웃 변경은 없으며 격리 위젯 회귀/Portable 결과와 실제 시각 렌더링을 구분한다. 다른 Windows·실제 Discord는 미검증/승인 전, 장시간은 사용자 실사용으로 이관한다. 운영 자료/원본모델/소비 장부는 보존한다. 정확한 최신 테스트/Portable 마감은 아래 기록을 따른다.


## 마감 검증과 재개

- 최종 소스 전체 회귀 **1,059개 OK / 313.159초**. 별도 비활성 Desktop을 검증한 CPU/mock 실행이며 실제 Discord는 하위 외부 네트워크까지 차단했다. 긴 안정성 시험이 아니다.
- Portable 자체 Python과 번들 src import 경로를 확인한 **163개 OK / 17.207초**. 격리 Tk 위젯·DPI/페이지 상태·취소·종료를 포함하며 새 시각 디자인 검사나 다른 Windows 인증이 아니다. UI 소스 변경은 없다.
- native 예산 수정 후 실제 GPU scripted12이벤트에서 최소 free VRAM **8,412MiB**, 시스템 RAM 여유 **8,760,762,368bytes**, commit 여유 **32,762,146,816bytes**, 최고 온도 **62°C**. 단일 Lime 인스턴스 종료 확인. 이전/이후의 전체 요청 구성이 같지 않아 속도 향상을 주장하지 않는다. 응답별 지연은 비공개 원문 보고서에 보존했으며 이번 수정의 통제된 p50/p95·TTFT 비교는 NOT VERIFIED다.
- 운영 설정·bootstrap·companion/sent DB·평가 장부 **5개 SHA256 동일**, 원본 Lime SHA256 동일. 최종316사례 소비0. 실험 fixture의 남은 예약1건만 취소했고 운영 자료는 수정하지 않았다.
- Portable 산출물은 기존 `dist/EchoMate-rc-utterance`의 공개 파일을 갱신한다. 모델/토큰/DB는 포함하지 않는다. 전체 manifest 21,600개 / 4,877,970,141bytes의 전체 SHA256·membership·금지파일 감사 PASS(누락/추가/불일치/금지0). staged 공개20파일 전체 내용·diff 감사도 검출0이며 비공개 원문/DB/모델은 stage하지 않았다. 최종 문서 마감만 delta 동기화하고 변경 hash·전체 공개 src/docs 일치를 다시 확인한다.

비공개 증거: `local_data/lime-grounded-runtime-20261025/` 아래 `bridge-report.json`(능동11), `verify/bridge-report.json`(능동7 및 별도 후보실험), `final-dialogue/bridge-report.json`(능동12), `budget-replay/report.json`(동일12 scripted 재생), `full-regression-final.log`, `regression-final.json`, `bundle-tests.log`, `preserved-after.json`. 이 파일들과 원문·DB·모델은 공개 커밋 대상이 아니다.

다음 세션은 최신 main·이 문서와 AI-HANDOFF를 먼저 확인하고 **summary TypeError의 실패 스택과 실제 호출 시그니처**부터 최소 재현한다. 이후 일반 의미 청자/혼합 이름 서문/비명시적 기능 의도의 원천 분리 실패를 각각 좁힌다. 이번에 기각한 권한 문구 추가와 타인 프레임 축소를 근거 없이 반복하지 않는다. native 텍스트 예산의 성공을 classifier/summary 예산으로 확대하지 않는다.

표적 명령: 프로젝트 Python으로 `-m unittest test_runtime_context_budget test_character_runtime test_identity_contract test_lookup_inquiries test_operation_grounding` (`PYTHONPATH=src;tools;tests`). asyncio/격리 Tk는 검증된 프로젝트 전용 비활성 Desktop runner와 외부 네트워크 차단을 사용한다. 자원 admission 통과 후에만 단일 GPU를 로딩하며 장시간 soak는 실행하지 않는다. 운영 설정을 로딩한 실제 Discord 실행은 승인 전 금지다.
