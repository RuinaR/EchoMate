# Lime Runtime 조회 상태·캐릭터 DB 안전성 QA

시작 main/origin `0c2c14bb5e54ba1570b83a372fff723101512e32`, clean. **Lime 단일 출시 / RELEASE BLOCKED**. 실제 기능 수정·합성 회귀·GPU 진단을 수행했으며 새 운영 모델/설정/DB 적용은 없다. 비공개 증거는 `local_data/lime-runtime-fixes-20261025/`에 보존한다.

## 실제 수정

1. 자동 기억 검색 실패가 로그만 남기고 자유 생성으로 흘러갔다. 빈 결과와 실패를 모델이 구분할 관측 정보도 없었다. 이제 pretrained Runtime은 실패 시 자체 조회 실패 응답을 보내고 자유 생성을 호출하지 않는다. **조회 장애 중에는 일반 대화도 해당 의존성을 건너뛰지 않고 실패 안내로 제한**한다. 가용성보다 미확인 기억 단정을 피하는 정책이며 장기 장애의 별도 '기억 없는 대화' UX는 미완료다.
2. 미동의 사용자의 자동 검색을 먼저 실행한 뒤 결과를 버리던 순서를 바꿨다. pretrained 경로는 허용 여부를 확인한 뒤 조회하고, await 뒤 다시 권한을 확인한다. `not_requested/not_authorized/failed/empty/found/invalidated`를 생성 문맥에 구분해 전달한다. empty는 해당 검색 범위의 빈 결과이지 사건 부재가 아니다. found도 기존 MemorySelection/행/동의/송신 최신성 검사를 유지한다. 첫 접근 검사 뒤 권한이 회복되더라도 실제 조회를 건너뛴 경우는 not_requested로 유지한다. 실제 동의 epoch가 변경되면 기존 subject guard가 생성 전에 취소한다. 상태 전달 자체로 모든 자유 생성 환각을 해결했다고 주장하지 않는다.
3. 캐릭터 DB의 marker를 모르는 구형 v7 프로그램은 namespace를 무시하고 열 수 있었다. 캐릭터 저장소는 물리 user_version8로 분리하고 legacy CompanionStore는 v7을 유지한다. namespace API의 선언 버전으로 생성/읽기 전용 복구를 일치시켰다. 실제 과거 `ba84c52` CompanionStore 소스를 격리 실행해 임시 v8 DB를 ValueError로 거절하고 행을 보존하는 것을 확인했다. 원본 v7은 읽기 전용 backup→**별도 신규 목적지**만 v8로 이관한다. 운영 이관은 미실행이다. 버전1 namespace marker/ID/기억·친밀도 격리/공통 동의·예약/원자 삭제 계약은 유지한다.

## 청자 판단 조사와 기각

기존 판정은 청자·연결·anchor·발화행위·yes/no 조합을 한 번에 출력한다. 형식 제약은 의미 정확성을 보장하지 않는다. [llama.cpp 공식 GBNF 문서](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)와 [Lime 제공 카드](https://huggingface.co/naksyu/lime_Q6_K), 실제 내장 template을 대조했다. 내장 persona 정책/공급자 template은 임의 교체하지 않았다.

새 합성 개발8사례에서 동일 Lime/seed/생성 조건으로 작은 행동 계획과 비교했다. 4라벨 후보는 명시적 타인 멘션 오류를 줄였지만 전달문을 새 요청으로 오판하고 독백의 대상을 잘못 분류했다. 기존 response_plans 계약을 새 화자에 재사용한 후보도 전달 구분은 나아졌으나 공개 질문·독백을 human/excluded로 잘못 분류했다. 세 번째로 라벨/프롬프트를 그대로 두고 검증된 addressee ID 종류만 명시한 구조화 입력도 비교했다. 일부 사람 질문은 바로잡았지만 최초 타인 멘션의 오판을 고치지 못했다. 동일 개발8사례의 세 가설 비교이며 독립 검증으로 세지 않는다. **세 후보 모두 미채택**, 앱 classifier/엄격 probe/Runtime 참여 권한은 변경하지 않았다. 첫 human probe만 맞췄다는 이유로 채택하지 않았다. 개발 실패로 독립·최종 자료를 소비하지 않았고 같은 prompt/LR 튜닝을 반복하지 않는다. 이 실험으로 조합 출력이 유일 원인이라고 단정할 수도 없다.

## 실제 GPU → Runtime → SDK HTTP mock

고정 Lime Q6_K/b11721/2048·단일 GPU 모델·기존 resource admission으로 실행했다. strict semantic probe는 **FAIL**, capabilities_verified=false를 그대로 기록한 **진단용 구성요소 테스트**다. production startup gate를 통과한 전체 통합 인증이 아니다. 실제 Discord HTTP는 차단하고 합성 원본 조회/송신을 SDK mock으로 대체했다.

- 이름/일상 생성, 명시 기억 빈 목록, 실제 예약 생성/목록, 자연어 과거 취향 질문의 자동 검색 실패로 합계 **6송신**. 원본 reply와 SDK source 확인 모두 일치, 예약 저장1건/영수증 일치.
- 자동 검색 실패는 Runtime 문구 '조회 실패/자료 없음의 뜻이 아님'으로 송신했다. synthetic 단위 검사에서는 free text generator 호출0도 확인했다.
- 구성요소6응답 p50 **0.649초**, nearest-rank p95 **1.265초**. 생성과 결정적 기능 응답이 섞인 작은 표본으로 이전 모델 대비 속도 개선을 주장하지 않는다.
- aggregate free VRAM 최소 **7,206MiB**, RAM available 최소 **3.998GiB**, commit available 최소 **20.589GiB**, 최고 **48°C**. 자체 서버 종료/회수 확인. PyTorch allocated/reserved 측정으로 혼동하지 않는다. 두 별도 청자 pilot도 순차 종료/회수를 확인했으며 학습/다른 모델 중복 로딩은 없다.

## 검증·경계·다음 우선순위

표적 조회/상태·GGUF24개 OK4.587초, store/Runtime/legacy CRUD/기억 송신·예약68개 OK12.261초. 초기 전체994개 OK295.218초 뒤 접근 회복 경주를 추가 수정해 최종 전체를 별도로 수행한다. 최초 경합 테스트는 동의 변경 뒤 생성이 계속된다고 잘못 가정해 실패했으며, 실제로는 기존 epoch guard가 먼저 취소하는 것을 확인했다. 동의 변경 취소/접근만 회복된 미조회 상태를 분리한13검사 OK3.536초다. 최종 전체/번들/Portable 결과는 아래 마감에 추가한다. 운영 설정/bootstrap/두 DB/평가 소비 장부5hash는 실행 전후 동일, 최종316 소비0. 모델·LoRA 미변경, 토큰/개인 원문/가중치는 공개하지 않는다. 게임·다른 프로그램의 창/입력/화면·프로세스 내부·파일·패킷 조사/조작 없음.

남은 출시 차단: Lime의 의미 청자·대화 참여 판단, 자유 생성의 허위 경험/미래 기능 약속, Windows 설치/다운로드/이름/최초 controller handoff, 실제 장기 GPU·다른 Windows·마지막 별도 승인 Discord다. 기존 `/캐릭터`/`/동의` mock 계약과 fair queue/조각/reply/동의·삭제·예약 경계는 전체 회귀로 보호한다. 새 UI나30분/2시간/8시간 운용을 이번에 수행했다고 표시하지 않는다.

다음은 청자 판정의 상반된 실패(타인 멘션 vs 공개/전달/후속)를 원천 분리된 자료로 진단하고, 모델 교체·재학습·단순 prompt 반복 대신 검증 가능한 역할/행동 분리를 설계하는 것이다. 안전한 Windows 첫 활성화/installer 연결도 독립 개발 대상으로 남아 있다. 이번 조회 실패 보호는 일반 자유 텍스트의 모든 기능 약속을 결정적으로 검증하는 판별기가 아니다.

## 최종 검증 체크포인트

- 접근 회복 경주까지 반영한 최종 전체 **996개 OK279.804초**. 외부 socket 차단·프로젝트 전용 비활성 Desktop에서 GUI 포함 기존 회귀를 실행했다. 활성 사용자 Desktop 입력/캡처는 없다.
- 갱신 Portable 실제 번들 Python/번들 src **72개 OK6.921초**. 이전70개 성공은 추가 경주 수정 이전의 기록으로 별도 보존했다.
- 공개184경로 소스/문서 동기화, 민감정보·확장자·staged 전체 내용/diff 감사. Portable 전체 manifest 검사는 마감 로그에 기록한다. 실제 Portable GPU·다른 Windows·새 Lime UI·장시간 운용을 이 CPU/단기 진단으로 대체하지 않는다.
- 실제 GPU 보고서는 각각의 소스 SHA를 보존한다. 마지막 조회 실행 여부 경주 수정은 전체996/번들72에서 검증했으며 해당 추가 경주를 실제 GPU에서 다시 재현한 것은 아니다. 기존 GPU 6송신 결과를 최종 전체 제품 자격 PASS로 확대하지 않는다.
