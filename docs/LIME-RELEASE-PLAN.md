# Lime 최초 출시 계획과 변경 QA

## 2026-10-26 모드별 위험 기반 게이트

LOCAL_CHAT_READY / DISCORD_DIRECT_BETA_READY / DISCORD_AUTONOMOUS_RELEASE를 분리했다. 기본 Lime 로딩은 파일·자원·이름을 검증하고 자율 청자 probe를 실행하지 않는다. DIRECT는 입구/최종 라우팅에서 실제 선두 멘션/봇 reply를 재검사하며 자율 판별 없이 기존 SDK mock 송신·최신성·Receipt를 재사용한다. 현재 로컬 기술 시험은 가능하지만 새 실제18턴에서도 허위 공동 경험을 관측해 **세 모드의 정식 READY는 BLOCKED**다. DIRECT10상호작용은 기대6송신/4무송신·자율 판단0회로 일치했다. 실서버 실행은 Controller/UI에서 계속 잠겨 있고 자율 청자 FAIL은 local/direct 개발의 필수 게이트에서만 분리한다. 장시간은 **DEFERRED — USER REAL-WORLD TEST**이며 최종 정식 출시 필수 근거다. [위험/모드별 결과·실제 원문·재개](MODE-GATES-QA.md). 과거 FAIL/NOT VERIFIED와 기존8/8·0/4는 당시 범위로 보존한다.

검증 마감: 전체 **1,096개 OK314.942초**, Portable 자체 Python/src **200개 OK28.535초**, 비활성 Desktop 18화면(DPI100/125/150·두 창 크기)·callback 오류0. 실제 로컬18턴(모델12/Runtime6)·DIRECT10상호작용/원본12개·기대6송신/4무송신 일치·자율 판단0회. 운영5파일/원본Lime6hash 일치·합성 활성 예약0·final316 소비0. RAM 안전 중단 원인과 재실행, 실제 모델의 남은 허위 경험/조회 설명 실패를 보존했다. **RELEASE BLOCKED**, 실제 Discord 승인 전 잠금·장시간 DEFERRED 유지. 다음은 고위험 자유 생성 사실성 경계와 정상 잡담 오차단의 독립 검증이다.

## 2026-10-26 생성 예산·로컬 실행 안내·요약 경계

시작 `00cd301`. 새 책 보수 모임의 무이름 복귀는 양쪽 성공했지만, pending 설명 후보의 품질 향상은 없어 기각했다. 9108 실패·7108 근거 부족은 남는다. 새 세 조각 발언은 청자 판단 뒤 생성 예산에서 실패했으며, 실제 reply/결정 출처를 보호하면서 optional 추가 발췌2개를 제외해 1,483 native 토큰으로 실제 GPU→SDK mock 응답에 연결했다. 이전 성공 회귀13이벤트는 정상8/8·사람 오개입0/4·인용0/1 유지다.

실제 LOCAL_CHAT20턴(모델14/Runtime6)에서 허위 공동 경험·예약 약속/완료를 관측했다. 로컬의 기존 명시 명령 정책에 읽기 전용 기능 안내를 연결하고, 새10턴(모델5/Runtime5)에서 해당 질문·이름 복합·정상 잡담을 확인했다. 일반 자유 생성 전체 사실성 해결은 아니다. 모델을 호출하지 않은 안내에 이전 GPU context가 남는 진단 오류도 수정했다. 요약의 희망/제안→확정 등 좁은 충돌 검사, 보관 당시 동의 version과 조회/송신 guard의 일치, 중복 source 버전·stale fallback을 보강했다. broad 검사 후보와 회귀 오탐은 기록하고 수정했다. 신규 요약3건의 정상 의미는 유지했지만 의미 동치 전체는 NOT VERIFIED다.

최종 전체 **1,087개 OK 284.715초**. Portable 번들 **191개 OK 17.916초**. Portable 전체 **21,607파일 SHA256 감사 PASS**·운영5hash/원본Lime 동일·final316 소비0. 원문은 [집중 QA](SEMANTIC-FOCUS-QA.md)를 따른다. **RELEASE BLOCKED**, 장시간 **DEFERRED — USER REAL-WORLD TEST** 유지. 실제 Discord·다른 Windows·새 UI 시각 렌더링·Portable GPU는 미실행이며 운영 자료/모델/최종316을 보존한다. 다음 작업은 일반 청자 복귀·자유 생성의 허위 경험/완료·요약의 독립 의미 검증이다.

## 2026-10-25 사람 대화 경계·봇 복귀 개선

시작 `4169a81`. pending-human은 화자/채널별 마지막 확인된 사람 대상 발언 경계이며, 타이머 완화 없이 유지한다. 기존 SocialRouter/validate_social에 관계 후보 정합성·현재 입력 후치·native 최소 입력 중복 축소·실제 요청/reply 기반 이름 호출 복귀 선택·출처 버전 취소를 연결했다. 새 천가방 모임 실제 GPU→SDK mock 16상호작용(원본19개)/후보에서 응답 7/8→8/8, 사람 대상 오개입 0/4→0/4·인용1건 전송 없음. edit/철회/사람 경계 출처 삭제 뒤 생성 결과는 취소했다. 앞선 자전거 세션12건의 복귀 누락1→1도 기록하며, 과거3건 전부 해결 또는 일반 자율 참여 PASS는 아니다. 8108은 native 입력 초과를 확인했으나 7108 원본 근거 부족·9108/무이름 복귀의 의미 실패는 남는다. 자유 생성의 미래 기능 발언·요약 의미 검증·실제 Discord·다른 Windows가 남아 **RELEASE BLOCKED**. 장시간은 **DEFERRED — USER REAL-WORLD TEST**다. [실제 원인·A/B·기각·원문·재개](BOT-RETURN-QA.md).

최종 전체 **1,076개 OK 282.049초**. Portable 번들 **180개 OK 17.808초**·공개 소스/manifest **21,605파일 전체 SHA256 감사 PASS**. 운영 설정/두 DB/장부5hash와 원본 Lime hash 동일·final316 소비0. 일반 이름/예약 새 GPU 시퀀스는 기한으로 미실행이며 기존 기능 회귀와 구분한다.

## 2026-10-25 Runtime 책임·의도·요약 경계

최종 전체1,068개 OK280.928초·Portable172개 OK15.685초·전체21,603파일 감사 PASS·운영5hash/원본Lime 동일·final316 소비0. 시작c2e6ced. 기존 social/SocialDecision·권한·queue·Receipt를 유지하고 intent_router와 native context 선택을 분리했다. 현재 감정→과거 요약의 가로채기, 전달된 부탁의 실제 예약, 이름/기억 질문과 예약 응답의 선점을 수정했다. 세 능동 세션 각12이벤트에서 사람 대상 오개입은 양쪽0/6, 봇 복귀 누락은 양쪽3건으로 청자 의미 품질은 미달이다. 이름 관리자 경계/정상 예약·취소를 확인했고 자유 생성의 무근거 약속은 남았다. 요약은 검증 실패와 자료 부재를 구분하며 안전한 원문 선택으로 복귀한다. LOCAL_CHAT 명령 어댑터 회귀1건을 발견·수정했다. RELEASE BLOCKED·장시간 DEFERRED — USER REAL-WORLD TEST 유지. [실제 호출 흐름·A/B 한계·원문·재개](RUNTIME-LAYERS-QA.md).



## 2026-10-25 Runtime 원문·실행 금지·native 예산

최종 전체1,059개 OK313.159초·Portable163개 OK17.207초. 운영5hash/원본Lime 동일·final316 소비0. 시작7ba8d28. 로컬에만 적용되던 이름/조회 보호를 원본 Event 기반으로 Runtime에 연결했다. 명시적 금지를 무시하고 합성 DB에 알림을 생성하던 실제 실행 결함을 차단했으며 정상 예약·취소는 유지한다. 명확한 복합 이름 요청, 기능 안내의 잡담 가로채기, Discord 텍스트의2048 native 예산도 보완했다. 권한 문구/프레임 축소 후보는 기각했다. 능동 대화와 scripted 회귀 재생을 구분하며 일반 자율 의미 판단·자유 생성·요약 한계는 남아 RELEASE BLOCKED다. 장시간은 DEFERRED — USER REAL-WORLD TEST. [실제 원인·A/B·실패·재개](LIME-GROUNDED-RUNTIME-QA.md).


## 2026-10-25 품질 우선 후속 작업

장시간 GPU30분/Runtime2시간/8시간/누수 목적 반복 재시작은 **DEFERRED — USER REAL-WORLD TEST**다. 이번 차수에서는 실행하지 않는다. 짧은 취소·종료·재로딩·데이터 변경 경합은 유지한다. 다른 Windows와 실제 Discord의 별도 검증/승인 조건은 유지하며 장시간 미실행을 PASS로 바꾸지 않는다.

현재 변경과 실제 원문·채택/기각 근거는 [이름·조회 상태 및 청자 후속 QA](LIME-QUALITY-ITERATION-QA.md)를 따른다. LOCAL_CHAT·명시 호출·자율 참여는 따로 판정하고 자율 청자와 일반 자유 생성 사실성은 계속 차단 항목이다.


### LOCAL_CHAT 마감 근거와 다음 작업

실제 능동10턴과 별도 scripted100회 연속 생성(장기50 포함), 기억20·예약20·인칭20·일상30 시나리오를 구분해 기록했다. 모델의 이전 이름 수용·근거 없는 조회/미래 약속은 남아 있어 RELEASE BLOCKED다. 실제 stream 취소·기억 삭제 경합·재시작 stale 세션 거절을 확인했다. 긴 문맥 native 사전 계산을 같은 선택 메시지 기준32초→약1.4초로 줄였으며 생성 속도 개선과 구분한다. 현재 세션 중복 모델 소유와 외부 고정 파일 가져오기도 보호했다. 최종 결과·실패 로그·Portable·정확한 재개는 [LOCAL-CHAT-QA](LOCAL-CHAT-QA.md)를 따른다.

우선순위: (1) 원천 분리 사회적 시퀀스로 DISCORD_AUTONOMOUS의 오개입/누락 개선, (2) 기존 receipt 기반 기능 경로와 자유 생성의 거짓 약속 구분, (3) 이름 유도·긴 대화 사실성, (4) 다른 Windows 검증. 장시간 운용은 DEFERRED — USER REAL-WORLD TEST. 실제 Discord는 마지막 별도 승인이다. 재학습·새 모델 탐색으로 범위를 확장하지 않는다.

## 2026-10-25 LOCAL_CHAT 분리·실제 대화 검증 — RELEASE BLOCKED

청자 자격 실패가 로컬 채팅까지 막던 결합을 분리했다. 파일/자원/이름 기술 검사를 통과하면 LOCAL_CHAT을 사용하며 Discord 자율 참여는 계속 BLOCKED다. 로컬 채팅 UI·합성v8 저장소·명시 기능/영수증·native 토큰 예산·저장 세션의 삭제/철회 재생성 방어를 연결했다. 실제 능동10턴과 별도 scripted 기억/예약/일상/장기 대화를 수행했지만 자유 생성 사실성은 미해결이다. 제한 Direct GPU→SDK mock7이벤트/의도한4reply·오류0은 자율 참여의 PASS가 아니다. [검증 범위·실패·원문 위치·재개](LOCAL-CHAT-QA.md).


## 2026-10-25 Lime Windows 설치·이름·GPU 준비 연결 — RELEASE BLOCKED

시작 `32cf372`. 기본 실행을 Lime 앱으로 연결하고 고정 출처 다운로드/가져오기·전체 파일 검증·취소/복구·이름 저장/rollback·별도v8 저장소와 기존 InstanceLease를 통합했다. 과거 앱은 명시적 legacy 실행으로 보존한다. 실제 기존 모델 설치28.219초·GPU 준비3.672초/유나 이름 확인 후 **strict 청자 검증 FAIL→안전 해제·Discord 시작 차단**을 확인했다. 최소freeVRAM7,132MiB/RAM5.49GiB/commit20.185GiB, 최고48°C. 운영 자료/실제 Discord는 건드리지 않았다.

전체1,018개 OK301.405초·번들94개 OK8.705초·격리 UI100/125/150%·표적58개 통과. 운영/장부5hash·원본 Lime hash 동일. 새 앱의 정상 실사용·청자/일반 자유 생성 사실성·장시간/다른 Windows는 미완료다. **실사용 테스트 준비 완료가 아니다.** [구현·실측·검증 한계·재개](LIME-WINDOWS-APP-QA.md).


## 2026-10-25 Lime 조회 실패·저장소 downgrade 보호 — RELEASE BLOCKED

기준 `0c2c14b`. 자동 기억 검색 실패의 자유 생성 fallthrough를 Runtime 실패 응답으로 막고, 미동의 자동 조회를 생략하며 실패/빈 결과/실제 항목 상태를 분리했다. 캐릭터 DB는v8, legacy는v7로 유지해 marker를 모르는 과거 구현의 접근을 거부한다. 임시 사본/읽기 전용 복구·실제 과거 코드 거부를 확인했고 운영 DB는 변경하지 않았다.

실제 Lime 진단→SDK mock6송신/원본reply·예약영수증을 확인했지만 semantic gate FAIL을 유지했다. 작은 행동 계획2후보는 다른 유형 회귀로 기각했다. UI/장기/실서버 검증은 미완료이며 Yaho/기획자는 출시 필수가 아니다. [실제 수정·GPU·회귀·보존·다음 과제](LIME-RUNTIME-SAFETY-QA.md).

## 확정 계약

시작 HEAD `246424320592a20a1ecaba19bb072d49555bafad`, main/origin 일치·clean에서 시작했다. 최초 정식 제품은 **Lime 단일 모델**이다. 기본 출처 [naksyu/lime_Q6_K](https://huggingface.co/naksyu/lime_Q6_K), 기본 이름 라임, 사용자 이름 변경 지원이다. Yaho/여성 IT 기획자는 확장 카탈로그에 남는 미지원·추후 제공 후보이며 출시 조건에서 제외한다. 라이선스/가중치 문제를 해결했다고 주장하거나 READY로 표시하지 않는다.

카탈로그의 `DEFAULT_CHARACTER_ID`, `RELEASE_CHARACTER_IDS`, `default_character()`, `product_characters()`로 제품 기본 목록을 명시했다. `discover()`는 전체 확장 카탈로그를 보존한다. 자동 설치/로딩/동의/운영 설정 변경은 없다. 이 정책의 '출시 대상'은 실제 READY라는 뜻이 아니다. 기존 이름 파일에 유나 등이 저장돼 있으면 기본값 라임으로 덮어쓰지 않는다.

## 사용자 흐름과 출시 범위

1. **모델 설치**: Lime만 기본 표시. 고정 revision/file/hash·라이선스·용량·자원 요구·실제 설치 상태 안내. 다운로드 진행/중단/재개·손상 파일 거부, 부분 파일을 설치 완료로 표시하지 않음.
2. **이름 설정**: 기본 라임. per-CharacterId 저장, 생성 정체성 override, 이름 변경 version/epoch와 stale 응답 차단. Discord 프로필 변경과 구분.
3. **모델 로딩**: 단일 backend/InstanceLease, 기존 2GiB GPU 여유/host admission, 취소/drain/unload/reclaim 후 reload. 기술 로딩과 의미/품질 Ready를 구분. 실패 시 실행 차단·원인·재시도 안내.
4. **Discord 설정**: 개인 Bot/허용 채널·스레드/최소 권한과 동의 안내. 실제 인증/조회/등록/송신은 현재 별도 승인 전 금지.
5. **실행**: 여러 사용자 I/O는 비동기, GPU는 검증된 공정 큐. 본인별 동의·캐릭터별 기억/친밀도, 공통 예약, 메시지 조각·reply·수정/삭제/철회·송신 최신성 유지.

학습·성격 카드 편집은 새 주요 흐름에서 제외한다. 기존 운영·레거시 자료는 삭제하지 않는다. 미래 모델은 사용자가 실행할 수 없는 기본 선택지로 나열하지 않는다. 필요할 때만 정확한 미지원 사유를 별도 안내한다. **현재 Windows 앱의 설치·이름·로딩 흐름은 연결됐다.** 실제 이름 검증 후 청자 gate 실패로 실행은 차단된다. 정상 실사용/장시간/실서버 완료로 과장하지 않는다.

## 최우선 실행 순서

| 순서 | 목표/현재 차단 | 완료 기준 |
|---|---|---|
| 1 | Lime 청자 판단 FAIL 원인 분리 | 원천 분리 직접 호출/후속/사람 간 대화/다자 시퀀스, 오개입·누락·reply 독립 측정. 모델 gate 우회 금지. |
| 2 | Runtime 기능 상태·영수증 보호 확대 | 조회 안 함/실패/빈 목록/항목/저장·예약 성공/취소를 구분. 자유 생성 약속을 실행 성공으로 기록하지 않음. 새 상태·부정/조건/인용 확인. |
| 3 | Windows Lime 첫 activation/installer | 임시 DB/lease에서 모델 설치→이름→load→Discord 설정→실행과 실패·취소·재시작 복구 연결. 운영 migration 별도 승인. |
| 4 | 이름/기억·관계·예약/병렬 통합 | 실제 GPU→SDK HTTP mock, 여러 사용자·채널·스레드/조각/reply/철회/epoch를 긴 시퀀스로 확인. |
| 5 | 장시간·Portable | 단계적30분GPU/2시간/가능시8시간, 실제 첫 설치·업데이트·다른 Windows는 수행 범위만 기록. |
| 6 | 마지막 실제 Discord | 다른 필수 게이트 통과 뒤 읽기/명령 변경/송신 각각 별도 실행 계획·승인. |

단일 Lime이 로딩된다는 이유로 RELEASE PASS가 되지 않는다. [최신 요구사항 추적표](RELEASE-CHECKLIST.md)의 Lime 필수 품질/라이선스·개인정보·UI·성능·배포·실제 Discord를 모두 충족해야 한다. Yaho/기획자 확보·학습 연구는 이 경로의 선행 조건이 아니다.

## 이번 변경 검증 범위

모델 카탈로그·이름·manager/Runtime/store/명령/GGUF mock 표적 **57개 OK6.978초**. 실제 이름 파일 보존·기본 목록 Lime 하나·미래 두 후보 metadata/blocker 유지 검사를 포함한다. 제품 범위 추가와 문서 정리이며 생성/학습/DB schema/GUI 위젯 코드는 변경하지 않았다. 새 GPU/실제 UI/장기/실제 Discord를 실행하지 않았고 과거 988개 전체 회귀를 이번 소스의 신규 전체 실행으로 세지 않는다.

운영 설정/DB·모델/LoRA·최종316자료를 변경하지 않는다. 새 가중치 다운로드나 다른 앱·게임의 창·화면·입력·프로세스 내부 조사는 없다. 공개 코드/합성 테스트/비식별 문서만 커밋한다. Portable 동기화/최종 보존·공개 감사 결과는 마감 항목에 기록한다. **RELEASE BLOCKED**, 이유는 위 Lime 필수 항목이다.

## 검증 마감

Portable 실제 번들 Python·번들 src를 확인한 표적 **66개 OK4.745초**. 공개183경로 소스/문서 동기화·manifest 갱신을 완료했다. 운영 설정/bootstrap/두 DB/평가 소비 장부5개 SHA256이 기존 기준과 같으며 모델/LoRA를 쓰지 않았다. 공개16개 staged 경로·전체 내용·diff/확장자·민감정보 패턴을 검사해 검출0이다. 새 GPU·GUI·전체 회귀를 실행하지 않았고 이 변경에 필요한 catalog/이름/manager/store/Runtime/명령 표적과 번들 검사를 수행했다. Portable 전체21,586파일의 membership/size/SHA256 감사 PASS, 누락·추가·불일치·금지 파일0. 이 마감 기록 동기화 뒤 최종 manifest도 재검사한다. 실제 Portable GPU/다른 Windows/새 UI 검증은 아니다.
