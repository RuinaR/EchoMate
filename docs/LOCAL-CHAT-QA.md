# LOCAL_CHAT·Direct 모드 분리와 실제 대화 QA

## 모드별 준비 판정 — 현재 우선 계약

모드별 안전/고위험 사실성 필수 게이트와 일반 품질을 분리한다. LOCAL_CHAT은 Discord 청자 검사를 요구하지 않고, DISCORD_DIRECT는 실제 구조적 호출만 처리해 자율 의미 판단을 호출하지 않는다. 일반 대화 품질과 자율 청자 실패로 두 모드의 독립 개발을 막지 않지만, 허위 완료·개인정보·권한 안내의 명백한 실패는 해당 모드 READY를 막는다. 장시간 DEFERRED는 local/direct의 한정 시험과 구분하고 최종 자율 RELEASE에서는 필수로 남긴다. 현재 실제 Discord 실행은 모든 오프라인 결과/로딩 smoke와 무관하게 잠겨 있다. [정확한 게이트·근거·구현 범위](MODE-GATES-QA.md). 아래 과거 단계의 단일 READY 표현보다 이 정책이 우선한다.

후속 의도/요약 경계·실제36이벤트와 미해결 청자: [현재 QA](RUNTIME-LAYERS-QA.md). 아래 결과는 당시 소스 범위로 보존한다.

후속 Runtime 원문 보호·명시 금지·native 예산 구현/제한: [최신 QA](LIME-GROUNDED-RUNTIME-QA.md). 기존 결과는 해당 당시 범위로 보존한다.

후속 변경: [이름·조회 상태·청자 QA](LIME-QUALITY-ITERATION-QA.md). 이전 실행 결과는 역사적 증거로 보존합니다. 장시간 검증은 이제 DEFERRED — USER REAL-WORLD TEST이며 이번 차수에 실행하지 않습니다.

시작 `3c78c94`, main/origin 일치·clean에서 시작. **RELEASE BLOCKED**. LOCAL_CHAT 사용 가능과 Discord 자율 참여 자격을 분리한다. 이 문서는 이전 Windows QA의 청자 실패→모든 로컬 생성 차단 계약을 최신 요청에 따라 대체한다.

## 실제 구현과 모드 경계

| 모드 | 실행 경로 | 자격/제한 |
|---|---|---|
| LOCAL_CHAT | LimeController → LocalChat → 기존 GGUF backend/fair queue | 고정 파일·기술 GPU·이름 검사 필수. Discord 청자 실패여도 local_ready 유지. 자격 증명 없이 별도 합성v8 DB 사용. |
| DISCORD_DIRECT | Runtime의 명시적 execution_mode | 조각 조립 뒤 구조적 선행 멘션/확인된 봇 reply만 접수. 인용/타인/불특정 발언 배제. SDK mock 전용 검증이며 현재 UI의 실제 Discord 시작 허용으로 전환하지 않음. |
| DISCORD_AUTONOMOUS | 기존 Runtime 기본 모드와 strict probe | **FAIL/BLOCKED 유지**. 기존 후속/다자/이름 호출 의미 정책·gate를 낮추지 않는다. LOCAL 성공은 이 모드의 PASS가 아니다. |

로컬 설치→이름→로딩 후 ‘로컬 채팅’에서 바로 대화한다. 최초 실행 시 테스트 fixture에 bootstrap이 없는 상태를 실제 확인했다. 로컬 생성과 합성 기능은 Discord 자격 증명을 사용하지 않는다. 실제 인증/REST/Gateway/명령 변경/송신은 미실행이다. 기존 운영 ROOT·DB는 테스트에 열거나 변경하지 않았다.

## 로컬 UI·문맥·기능

- 기존 다크 앱의 채팅 화면: 여러 턴 목록, 검증 전 스트리밍, 취소, 초기화, 명시적 저장/불러오기, 합성 A/B·채널1/2, 긴 글 줄바꿈·스크롤·선택 복사, 오류/생성 상태. Enter 전송/Shift+Enter 줄바꿈, 중복 Enter 대기 작업 방지. 승인된 비활성 Desktop의 자체 HWND만 검사한다.
- Stream observer/token budget은 task-local ContextVar이고 기존 공정 큐가 request context를 복사한다. 다른 사용자 작업이나 Discord 출력에 provisional token을 보내지 않는다. 취소/실패/재작성 때 임시 스트림을 지우고 최종 검증 답변만 대화 이력에 확정한다.
- Native `/apply-template`→`/tokenize`로 실제 입력 길이를 검사한다. context2048, 출력384+margin64 유지. 필수 정책·정체성·현재 입력·검증 근거를 자르지 않고 오래된 완전한 user/assistant 쌍만 제외한다. 제외 개수를 UI에 표시하며 요약을 사실로 승격하지 않는다. 필수 자료만으로 예산을 넘으면 명시적으로 거절한다. [공식 server API](https://github.com/ggml-org/llama.cpp/blob/b11721/tools/server/README.md); 실제 고정 엔진에서 API 사용 검증.
- 로컬 저장소는 별도 `lime/local-chat/synthetic.sqlite3`, v8 CharacterStores의 Lime namespace다. 합성 사용자/채널만 허용한다. 공통 동의·예약과 캐릭터별 기억·관계 API를 재사용한다. 일반 문장은 상태를 변경하지 않는다. 명시적 `/동의`, `/기억`, `/친밀도`, `/알림`만 실행한다. 자연어 전체 기능 의도 파악을 완성했다고 주장하지 않는다.
- 기능 완료 응답은 기존 handle_request/Receipt/ReadReceipt의 DB commit·현재성 검증을 사용한다. 미실행/실패/불확실을 구분한다. 기억 자동 조회 실패는 고정 실패 안내로 종료하며 빈 결과로 바꾸지 않는다. 로컬에서는 허용된 최근 기억3개와 정확한 선택 최신성 계약을 사용한다.
- 발견·수정: 목록 영수증을 검색 선택에 적용해 정상 결과를 stale로 거부하던 연결을 MemorySelection으로 수정. 기능 명령 뒤 대화 이력을 비울 때 잃던 실행 근거는 내용 없는 typed receipt 상태만 다음 생성에 제공하며, 현재 유효할 때만 포함/재검증한다. **이 연결 수정만으로 모델 자유 생성의 사실성 개선이 입증된 것은 아니다.**
- 삭제·철회·정정 후 이전 채널 이력을 폐기한다. 저장 세션은 schema2·persisted state version·합성 DB evidence signature를 검증한다. 과거 role/system 주입·잘못된 scope/짝·과도한 크기를 거부한다. 저장 이후 데이터가 달라지면 재시작 후에도 stale 세션을 불러오지 않는다. 원본을 자동 삭제하거나 낮은 검증으로 복구하지 않는다.
- 로컬 예약은 자체 inbox에만 표시하며 DB claim 뒤 사용자의 명시적 알림 확인으로 finish한다. worker에서 inbox 생성 전에 delivered를 기록하지 않는다. 이 delivered는 로컬 합성 전달이지 Discord 네트워크 전달이 아니다. 전송 exactly-once를 일반화하지 않는다.
- Tk 정리 중 executor GC에서 Tcl 인터프리터가 소멸하는 실패를 재현했다. 로컬 위젯/변수의 UI thread 정리와 Canvas/SelectionList app callback 순환 참조 제거로 수정했다.

## 실제 대화와 평가 방법

원문은 ignored `local_data/lime-local-chat-20261025/`의 command-response·scenario·bridge 보고서에만 보관한다. 모델/DB/원문/캡처/체크포인트는 Public 커밋하지 않는다. 기존 최종316/소비 장부는 사용하지 않는다.

직전 답변을 Codex가 읽고 다음 말을 선택한 **10턴 능동 대화**를 수행했다. 게임 실수의 감정→조언 거부→농담→이름 말장난 오해→정정→없는 공동 경험 유도→권한 확인→현재 문맥 회상→저장/예약 미실행 확인으로 이어졌다. 대화 의미 검토는 Codex의 원문 검토이며 독립 사람 평가가 아니다.

나머지 대화는 별도로 명시한 scripted 개발 시나리오다. 이것을 모두 Codex가 한 턴씩 능동 선택한 대화 또는 독립 holdout으로 부르지 않는다. 기억20·기능20·인칭/시점20·일상30은 최초 실행에서 처리 완료했다. 긴50 시나리오는 첫 실행20회 성공 뒤 서버 중단으로 멈췄다. 첫 서버 중단의 정확한 원인은 당시 기록되지 않아 자원 부족으로 단정하지 않는다. 그 뒤 같은 상태의 실패 요청을 반복한 비공개 도구를 수정해 첫 실패에서 멈추도록 했다.

영수증 연결 수정 후 기억20/기능20 재검증을 완료했다. 긴50 재검증은40회 성공 뒤 예약이 실제 로컬 발화해 예약 대기 영수증이 무효가 된 응답을 올바르게 폐기했다. 이것을50회 연속 성공으로 계산하지 않는다. 이 실패 경로·실제 알림 표시·DB 상태 변화는 별도 기록한다.

## 확인된 품질 한계

- 사용자 지정 이름은 실제 대화에서 유지했지만, 말장난을 과도하게 설명하고 무단 조회를 준비하는 듯한 미래 발언을 생성했다. 실제 조회/상태 변경은 없었다.
- 검증된 ‘좋아하는 음료’를 ‘최근 마신 음료’로 확장하거나, 친구의 예약 발언을 자신의 과거 오해로 표현하는 오류가 있었다. 저장/정정/삭제·예약 DB는 모델 발언과 독립적으로 유지됐다.
- 영수증 문맥을 보강해도 삭제 상태에 대한 일반론/추측이 남았다. 자연스러움·캐릭터 매력·거짓 약속이 전반적으로 해결됐다고 주장하지 않는다. 프롬프트 반복 조정/학습·모델 교체는 하지 않았다.
- 실제 Direct GPU→SDK mock7이벤트: 의도한4응답,3침묵, 원본reply4개 일치, Runtime 오류0. 선행 멘션/직접 reply의 제한 범위이며 자율 후속/다자 의미 판단 통과가 아니다.

## 검증과 남은 게이트

중간 표적72개 OK12.393초, 중간 전체 CPU/mock1,032개 OK292.885초(CUDA 차단, 비활성 Desktop/외부 socket·DNS 차단). 중간1,032개 OK305.488초 및 초기 실패 로그도 보존했다. 검사 수를 합산해 성과로 세지 않는다. GPU 반복 관측은 실제 경과·호출 수·freeVRAM·RAM·commit·온도·소유 서버 private/parent handle을 분리한다. private 증가를 캐시 또는 누수로 단정하지 않는다. 2/8시간·다른 Windows는 미검증이다.

운영 설정/bootstrap/두 DB/평가 장부와 원본 모델을 보존한다. 실제 Discord 전 단계는 계속 별도 승인 대상이다. 최우선 남은 작업은 자율 청자 판단, 자유 생성의 거짓 조회/기능 약속, 긴 대화 사실성, 메모리 증가 원인·장기 안정성 및 Portable 실환경이다. **실사용 테스트 준비 완료/RELEASE PASS가 아니다.**


## 후속 실제 GPU 검증과 발견한 결함

`latest-implementation/report.json`에서 장기50·인칭20·일상30을 이어 **100회 실제 모델 생성**을 완료했다. 이 중 장기50이 포함되므로 별도100과50으로 합산하지 않는다. 실제 Controller partial 상태166회를 관측했다. 앞의 능동10턴과 달리 이100회는 scripted 개발 평가다. 49번째에는 서린을 인식했지만 69번째에는 사용자 유도에 따라 이전 이름 하루를 받아들였고99번째에는 서린으로 돌아왔다. **이름의 강한 다중 턴 일관성 FAIL**이다.

그 뒤 최초 token 대기20초 초과를 조사했다. 긴 문맥에서 완전한 과거 쌍을 하나씩 제거하며 매번 native tokenization을 반복하던 비용이었다. LOCAL_CHAT에 한해 보호된 system/현재 입력을 보존하고 최근 완전 쌍 suffix를 bounded 탐색하며 모든 채택 입력을 실제 tokenizer로 재검사한다. BPE 단조성이나 최대 이력 보존을 증명했다고 주장하지 않는다.

같은 상주 모델·동일100턴 fixture의 linear→bounded→bounded→linear 비교에서 선택된 메시지가 정확히 동일했다(input1585·제외89쌍). 사전 계산만32.156/32.062초에서1.344/1.406초, native count90회에서9회였다. **생성 속도/전체 지연의 동일 배율 개선이 아니다.** `final-controls/report.json`에 원문과 순서를 보존했다.

이후 실제 짧은 문맥 stream0.422초 뒤 취소, future 취소·native idle 확인, 생성 중 기억 삭제로 답변 폐기, 저장 세션의 삭제 후·재시작 후 재사용 거부, 서린 설정 유지·재시작 시 모델 비상주를 확인했다. 의도적 Windows terminate의 owned server exit1과 모델 참조 해제를 기록했으며 crash라고 해석하지 않는다. 로딩3.125초, 최소freeVRAM9744MiB/RAM6.953GiB/commit21.987GiB, 최고47°C였다.

별도 periodic run은 실제 상주1934.953초(약32분15초), 주기적 호출77회 뒤 정상 정리했다. 최소freeVRAM9180MiB/RAM3.833GiB/commit18.081GiB, 최고54°C, 소유 native private 최대9.155GiB였다. 연속 GPU compute 또는 사람 대화100턴을 뜻하지 않는다. native private가 증가 후 관측 후반부에서 비슷한 범위였지만 allocator/cache/누수 원인은 확정하지 않았다. **이32분은 이전 linear 버전이며 마지막 bounded 최종 소스의30분 인증이 아니다.** 2/8시간은 미검증이다.

일부 실패/취소만 반복해도 UI rows가 즉시200개 이하가 되도록 고쳤다. 취소된 기능 worker는 정리까지 기다리며 성공/rollback을 추측하지 않는다. 저장된 텍스트의 위조 notification ID는 실행 가능한 확인 권한으로 복원하지 않는다. Tk UI는 최종 알림 확인 버튼 포함9개 화면(100/125/150%)을 별도 비활성 Desktop에서 자체 HWND만 렌더링·검토했다.

데이터 폴더별 file lock만으로는 소스/Portable가 각각 모델을 소유할 수 있어, 현재 Windows 세션의 EchoMate 전용 lifetime named Event를 함께 사용한다. 다른 앱/프로세스 목록을 조사하지 않는다. 외부 원본 모델 가져오기는 고정 hash·크기·별도 복사 원칙을 유지하면서 잘못된 DATA_HOME 읽기 제한을 수정했다. symlink/reparse leaf는 거부한다. 이 변경의 단위·경계 검사도 수행한다.

실패 기록: 이전 전체1,037개에서 기존 publish-lock 테스트가 예상2회 대신3회 rename을 관측했다. 기대값/제품 retry는 변경하지 않았다. 이후 연구용 checkpoint 포함 표적92개21.196초 OK. 최신 전체·Portable 결과는 아래 마감 기록을 따른다. 이전 실패 로그는 삭제하지 않았다.


100회 scripted 대화의 Controller 경과 중앙값6.133초/p95 28.109초/최대33.266초는 **linear 사전 계산을 포함한 해당 실행** 수치다. bounded 최종 소스에서100회를 같은 조건으로 재실행하지 않았으므로 전체 p95 개선 수치로 바꾸지 않는다. 최종 실제 stream 첫 partial0.422초는 별도 짧은 문맥 사례이며 일반 TTFT SLO 인증이 아니다.


## 최종 CPU·UI·번들 검사

- 최신 소스 전체 **1,041개 OK286.074초**(wrapper290.796초), 외부 socket/DNS 차단·CPU/mock·검증된 비활성 Desktop. 실행: `PYTHONPATH=src;tools;tests` 설정 후 `.venv-gemma4/Scripts/python.exe local_data/lime-local-chat-20261025/run_regression_current.py`(Windows 격리 Desktop 생성 권한 필요). 기존 성공/실패 증거와 별도 파일이다.
- 최신 표적92개 OK21.196초. Portable 자체 Python·번들 source 경로 assertion·별도 합성 데이터 홈·외부 network 차단: **117개 OK12.391초**. CPU/UI/mock 결과이며 GPU 실행과 분리한다.
- 최종 `rendered-local-ack/` 9개100/125/150% 자체 HWND 렌더를 확인했다. 실제 Return 위젯 이벤트 검사도 별도 수행했다. 이 화면 fixture의 partial은 합성 표시이며 실제 streaming 증거166회와 구분한다.
- 운영 설정/bootstrap/두 DB/최종 소비 장부5개 SHA256 동일, 원본 Lime SHA256 동일, final316 소비0. 운영 자료를 새 로컬 테스트 DB에 이관하지 않았다.

## 재개 절차

루트 `EchoMate.vbs` 또는 `dist/EchoMate-rc-utterance/EchoMate.vbs`에서 설치/이름/기술 검사 후 로컬 채팅을 연다. 다운로드와 가져오기는 UI의 사용 조건 확인이 필요하다. 테스트 기록은 별도 합성 DB이며 `/도움말`과 사용 안내를 따른다. 원문 증거는 `local_data/lime-local-chat-20261025/`에만 있다.

코드 변경 후 표적 검사는 `run_targeted_ownership.py`, 전체는 위 wrapper다. 기존 출력 파일을 덮어쓰지 않도록 새로운 실행명·로그 경로를 사용한다. GPU 반복 도구는 각자 비공개 output 디렉터리의 `exist_ok=False`로 과거 결과 덮어쓰기를 막는다. 같은 resident 모델을 중복 실행하지 말고 자원 admission을 그대로 따른다. 다음 개발은 신규 사회적 시퀀스의 원인 분석과 자유 생성 사실성/이름의 독립 실패 재현부터 시작한다. 최종 holdout은 소비하지 않는다.


Portable 실제 GPU: 번들 Python/소스 assertion과 별도 `ECHOMATE_DATA_HOME`의 bootstrap 없는 상태에서 외부 고정 GGUF/공식ZIP 가져오기·검증→새봄 이름→실제 생성3회와 합성 명령2회→partial 관측/취소→정리를 수행했다. 실제 no-LoRA Lime만 상주, stage `local_ready`, social_qualified=false다. 최초 보고서의 `model_released=false`는 종료된 Popen 참조를 증거 보존하는 기존 설계에 대해 `process is None`을 잘못 검사한 **계측 결함**이었다. 원본 보고서는 보존하고 실제 owned exit code·model=None·활성 generation 없음·child Job 해제로 재검증한다. 이를 숨기거나 원본 수치를 덮어쓰지 않는다. `bundle-gpu/` 및 후속 `bundle-gpu-reclamation/` 보고서를 구분한다.

최초 Portable GPU 로딩3.875초, 최소freeVRAM9750MiB/RAM5.849GiB/commit21.697GiB, 최고47°C. 작업 전후 aggregate freeVRAM13798MiB가 같았지만 다른 앱 변동이 있으므로 이것만으로 자원 회수 증거로 삼지 않는다. 같은 호스트의 새 데이터 홈/import 검사이며 외부 네트워크 최초 다운로드·다른 Windows·최종30분 GPU를 검증한 것이 아니다.


후속 Portable 해제 검사 완료: 실제 소유 server exit1(의도적 terminate), model 참조 해제·활성 generation0·child Job 해제 모두 확인, closed=true. 종료된 process 참조 보존은 설계대로다. 최초 계측 실패와 후속 수정 검증을 모두 보존한다.

Portable 전체 **21,596파일 / 4,877,906,755bytes**의 membership·전체 SHA256·금지 파일 감사 PASS. 이후 이 QA 등 최종 공개 문서만 동기화하고 manifest 문서 delta를 별도 검증한다. 번들 모델/토큰/DB 포함0, 다른 Windows 검증은 NOT VERIFIED다. 검증된 공개 파일25개 staged 내용·diff 감사에서 금지 확장자/토큰/개인 경로/개인 키 패턴0을 확인했다. 실제 Discord 요청0이며 Release는 계속 BLOCKED다.
