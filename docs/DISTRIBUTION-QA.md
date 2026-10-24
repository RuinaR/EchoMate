# 모델·캐릭터·일반 배포 QA — 2026-10-19

## 2026-10-24 전체 Portable 파일 감사·최신 문서 증분

실행 소스는4587355 그대로이며 연구 도구/개인 출력/초소형 어댑터를 번들에 넣지 않는다. 초기21,568개 전체 파일의크기·SHA256/membership를 읽기 검사했다. 최신 문서 증분 반영/최종 manifest와 번들65회귀·두 VBS /check의 정확한 결과는 [이번 QA](RELEASE-READINESS-QA.md)에 기록한다. /check는 파일 존재 검사이며 실제 UI 실행이 아니다. 격리 소스 UI와 번들 mock/다른 Windows/번들 GPU는 구분한다. 정식 RC/PASS는 [추적표](RELEASE-CHECKLIST.md)의 미해결 조건 때문에 승인하지 않는다.


## 2026-10-24 기본 기억 선택 보호 증분 후보

최종 실행 `701b947`/도구 `8da36a3`: 전체800검사 OK245.565초·번들52검사 OK7.474초, 공개166쌍/manifest21,568 대조·두 VBS check exit0·운영4파일 hash 동일. 앱 재시작 필요·DB 마이그레이션 없음. 실제 Discord/새 GUI/번들 GPU는 미검증이다. 공개 src/docs164파일·README/기본 프로필166쌍만 반영했고 전체 재빌드/전체 런타임 재해시는 하지 않았다. CFG/claim 추출은 앱에 활성화하지 않고 연구 도구에만 있다. 개인 출력·주석·DB·모델은 포함하지 않았다. [검증과 한계](CONSISTENCY-CLAIMS-QA.md).

## 2026-10-24 예약/카드 입력 증분 후보

실행 단계 `8af87e1`/`dec2787`: 최종788검사 OK240.115초·번들46검사 OK6.273초, 공개165쌍/manifest21,567 대조·두 VBS check exit0·운영4파일 hash 동일. 소스 사용 시 앱 재시작 필요·DB 마이그레이션 없음. 실제 Discord/새 GUI/번들 GPU 검증은 수행하지 않았다. 공개 src/docs163파일과 README/기본 프로필165쌍만 갱신했다. 전체 재빌드·전체 런타임 재해시 없이 같은 호스트 번들 Python에서 새 예약/카드 경로를 검증했으며 개인 자료·평가 원문·가중치는 포함하지 않는다. [QA와 미검증 경계](STABILITY-DIALOGUE-QA.md).

## 2026-10-24 실행·조회 근거 보호 증분 후보

최종 코드 `a5210a3`: 전체774검사 OK243.960초·번들37검사 OK5.906초, 공개164쌍/manifest21,566 대조·두 VBS check exit0·운영4파일 hash 동일. 앱 재시작 필요, DB 마이그레이션 없음. 새 GUI/번들 GPU/실제 Discord 검증으로 확대하지 않는다. 공개 src/docs162파일과 README/기본 프로필164쌍만 갱신했고 manifest21,566 membership/크기 및 공개 hash를 확인했다. 전체 런타임 재해시·전체 재빌드 없이 기존 번들 Python으로 실행·조회·원본 reply·기억 보호를 검증했다. 개인 데이터/평가 원문/가중치를 추가하지 않았다. [채택 코드와 기각 평가자·검증 범위](OPERATION-EVIDENCE-QA.md).

## 2026-10-24 v4 비교 마감 — 문서 증분 갱신

운영 src는 시작440d294와 동일하다. 공개 src/docs160파일·README/기본 프로필162쌍 hash와 manifest21,564항목 membership/크기를 대조했다. 별도 데이터 경로의 번들 카드/기억19검사 OK2.202초, 두 VBS `/check` PASS. 전체 재빌드/새 GUI/번들 GPU/다른 Windows/전체 런타임 재해시는 하지 않았다. 운영4파일 hash 동일, 개인 자료/평가 원문을 추가하지 않았다. 후보 B·C는 평가 도구에만 있고 앱에는 적용하지 않는다. [실패·실제 검증 범위](SERVICE-PERSONA-V4-QA.md).

## 2026-10-24 2단계 후보 기본 비활성 마감

공개 src/docs159파일·README/기본 프로필161쌍 hash와 manifest21,563파일 membership/크기를 대조했다. 번들22검사 OK3.042초·두 VBS `/check` PASS. 후보 모듈/Runtime 주입 경계는 포함하지만 기본None이며 UI/설정에서 활성화하지 않는다. 변경 공개 파일만 증분 반영했고 새 GUI·번들 GPU·다른 Windows·전체 인터프리터 재해시를 주장하지 않는다. 운영4파일 hash 동일·개인 자료 비포함. [실제 GPU 비교 및 기각](TWO-STAGE-GENERATION-V3-QA.md).

## 2026-10-24 레퍼런스 평가 v2 마감

운영 실행 src는 `4c4c9b2`와 동일하며 평가 도구는 앱 번들에 활성화하지 않는다. 공개 src/docs157파일·README/기본 프로필·manifest21,561 membership/크기와 공개 hash를 대조했다. 번들16검사 OK1.057초·두 VBS `/check` PASS. 문서 증분 갱신이며 전체 인터프리터 재해시/새 모델 로딩/GUI/다른 Windows 검증으로 주장하지 않는다. 운영4파일 hash 동일, 원문/가중치/개인 자료 비포함. [품질 후보 기각과 상세 범위](REFERENCE-PERSONA-V2-QA.md).

## 2026-10-24 평가 도구 마감 — 실행 소스 유지

마감: 전체714검사 OK217.451초, 마지막 국소 빈 배치 거부12검사 OK0.083초. 운영4파일 hash 동일, 공개 src/docs155+README/기본 프로필·Portable manifest21,559 대조/두 VBS check PASS. 실행 코드/운영 자료/실제 Discord 변경0회. [마감 경과](WORKLOG.md).

실행 Python92파일이 시작 소스/기존 Portable 바이트·manifest hash와 일치한다. 출처 계약은 운영에 미채택이므로 전체 런타임 재빌드·추가 번들 GPU 로딩은 하지 않는다. 공개 문서/README와 해당 manifest 항목만 갱신한다. 개발용 평가 tools/원문/NC 자료/전체 출력/HTML/정답표/운영 설정·DB/모델·LoRA는 번들에 넣지 않는다.

두 VBS `/check` 조기 종료 PASS는 경로 확인이며 GUI/모델/Discord 시작은0회다. 새 UI 렌더/사람 조작/다른 Windows를 재검한 것으로 표시하지 않는다. 최종 공개 파일 대조는 WORKLOG와 [평가 QA](DIALOGUE-EVALUATION-QA.md)를 따른다.

## 2026-10-24 카드 공개 파일 및 번들 검사

공개 src/docs/README/기본 프로필·manifest만 갱신하며 전체 런타임 재빌드는 하지 않는다. 번들 Python·별도 데이터 홈·운영 GPU lease로 새 카드 실제 생성→SDK mock3/3·4송신을 확인했다. 모델 준비68.235초, 해제 후 allocated1KiB/reserved2MiB다. 원본 발언 전달의 마지막 수정은 이후 CPU/Runtime 검사와 전체702회귀로 검증했으므로 GPU 재검과 구분한다. 최종 파일/번들 표적/보존 수치는 [CHARACTER-CARD-QA](CHARACTER-CARD-QA.md) 마감을 따른다. 실제 Discord·다른 Windows·장시간·사람 조작을 PASS 처리하지 않는다.

## 2026-10-24 페르소나 공개 파일 갱신

마감: 전체688검사 OK221.655초, Portable 공개 src/docs149파일·manifest21,553파일 대조, 번들39검사 OK8.141초·두 VBS `/check` PASS. 운영4파일 hash 보존. 캐릭터 강한 차별성 목표 미달·실제 Discord 미검증으로 BLOCKED다.

기존 Portable 후보의 공개 src/docs/README/기본 프로필과 manifest만 갱신했다. 런타임 전체 재빌드/재다운로드/모델 포함은 하지 않았다. 번들 Python의 별도 데이터 홈에서 페르소나·UI·명령 표적39검사 OK8.141초, 두 VBS `/check` 조기 종료 PASS다. 처음 sandbox의 cscript 설정 접근 거부는 실행 성공으로 기록하지 않았고 허용된 동일 `/check` 경로로 재검했다. 실제 Discord는 시작하지 않았다.

이번 번들의 GPU 재로딩·새 프리셋 실제 사용자 클릭·다른 Windows/드라이버는 NOT VERIFIED다. 소스에서 실제 GPU를 확인한 것과 번들 표적검사를 구분한다. 최종 manifest/공개 소스 대조·운영 자료 보존과 전체 회귀 마감은 [PERSONA-QA](PERSONA-QA.md)를 따른다. 기존 일반 배포 BLOCKED와 `/동의` 비표시는 해제하지 않는다.

## 2026-10-24 명령 경로 변경

명령 계약 모듈과 조회/승인 UI가 변경돼 확정된 공개 파일만 Portable에 반영한다. 전체 런타임 재빌드나 운영 자료/모델 복사는 하지 않는다. [소스/manifest 대조와 번들 표적 검사의 마감 기록](COMMAND-RECOVERY-QA.md)을 따른다. 이전35/44검사를 이번 소스의 실행 근거로 재사용하지 않는다. 실제 Discord와 다른 Windows는 미검증이며 `/동의` 실제 비표시는 차단 사항이다.

## 2026-10-23 메모리·UI 재개

이번 실행 소스는 공통 입력과 UI/준비 단계 표시가 변경됐다. 기존 `d6bd50e` Portable 근거를 최신 실행 소스의 검증으로 재사용하지 않는다. 최종 공개 소스/문서 갱신과 번들 런타임 표적 검사는 [재개 QA 마감 기록](RESUMED-MEMORY-UX-QA.md)을 따른다. 운영 모델 선택·가중치/개인자료는 번들에 포함하지 않으며 실제 Discord/다른 Windows/설치 프로그램/자동 업데이트를 지원 완료로 선언하지 않는다.

## 2026-10-20 개발 잠정 중단 시 후보 상태

Portable `dist/EchoMate-rc-utterance`는 `d6bd50e` 실행 소스를 반영했던 기존 후보를 그대로 보존한다. 이번에는 저장소 문서만 변경했으므로 새 명령 전체 비표시 관찰/중단 안내는 번들 문서에 없고, 아래 manifest·44검사 결과는 이전 검증 기록이다. 재빌드·재검증·운영 자료 변경은 하지 않았다. 사용자의 실제 명령 정리 후 `/동의`까지 안 보인다는 보고는 미해결이며 복구/정식 릴리즈를 승인하지 않는다. BLOCKED 및 [재개 최우선 절차](AI-HANDOFF.md)를 유지한다.

최종 Portable 공개 소스 갱신 완료: manifest21,548파일, src/docs144파일 및 GPU 봉인 소스 일치, 번들 Python의 별도 저장소·숨긴 Tk·동의/명령 mock44검사 OK12.465초, 두 VBS /check PASS. 운영4파일 SHA256 보존. 이번 번들의 GPU 재로딩·실제 Discord·다른 Windows는 미검증이다. [근거](LIVE-SERVER-FIXES-QA.md).

## 2026-10-20 실서버 수정 배포 후보

이번 소스는 저장소·명령 승인·분할 호출·활성 상태·미관찰 이미지·실제 기능 설명을 수정했다. 기존 Portable 런타임을 재사용해 공개 src/docs를 한 번 갱신했다. 결과와 manifest/소스 일치·번들 검사 범위는 [통합 QA](LIVE-SERVER-FIXES-QA.md)에 기록한다. 모델/토큰/운영 DB/개인 설정은 패키지에 넣지 않았다. 다른 Windows·실제 Discord와 이번 번들의 GPU 재로딩은 NOT VERIFIED다. 정식 릴리즈 BLOCKED.

## 2026-10-20 완성형 차례 후보 — 소스/오프라인 검증 / BLOCKED

기존 `dist/EchoMate-rc-utterance`의 공개 src/문서만 한 번 갱신했다(4.542GiB/21,546파일). 모델·LoRA·토큰·운영 DB와 번들 Python/의존성은 변경하지 않았다. 실행 소스85파일은 GPU 봉인 소스와 같고 manifest21,546개 파일 목록·공개146개 해시는 일치했다. 금지 파일0건·운영4파일 해시 보존을 확인했다. 번들 Python에서 별도 데이터 폴더로 발언·숨긴 Tk·오프라인·저장/취소54검사 OK16.722초, 창을 띄우지 않는 VBS /check PASS. 사용자 화면 조작이나 실제 Discord 동작은 아니다.

실제 GPU는 현재 체크아웃에서 한 상주 모델로 새 고정7시퀀스7/7·11SDK mock송신을 확인했다. 이번에는 Portable에서 GPU 가중치를 다시 로딩하지 않는다. 기존 번들 로더/캐릭터 미리보기 GPU 성공 기록을 보존하며, 실행 경로 바이트 일치와 이번 CPU/UI 검사를 별도로 보고한다. 실제 친구 서버·사용자 화면·다른 Windows·장시간 사용은 NOT VERIFIED, 정식 릴리즈 BLOCKED다.

## 2026-10-20 분할 발언·교차 화자 통합 — 사용자 검증 후보 / BLOCKED

새 후보 `dist/EchoMate-rc-utterance`를 한 번 전체 빌드했다(4.542GiB/21,546파일). 이후 발견한 마지막 Runtime 수정은 해당 공개 소스 파일만 반영했다. 소스85파일을 체크아웃과 대조하고 문서/README·manifest를 최종 갱신한다. 모델·토큰·DB·LoRA는 포함하지 않는다.

번들 Python의42개 검사 OK9.128초: 숨긴 Tk의 슬라이더/선택/저장·취소·오류·프로필·오프라인 초기 설정·DPAPI·재시작/SQLite·발언 시퀀스. 처음에는 cwd가 별도 private_path 경계 밖이라38개가 차단됐고, 정책을 낮추지 않고 격리 작업 폴더로 수정했다. VBS /check는 창을 열지 않는 분기로 정상 종료했다.

번들 GPU는 수정 회귀1/1+새5/5, 최종 Runtime에서 지연 보충1/1+새 의미3/3. Controller 미리보기·취소도 PASS·관계/기억/요약 저장0·pending0·종료 Worker0. 로딩/프로브 시간38.281초·최종65.843초는 별도 시스템 자원 조건이며 성능 향상으로 비교하지 않는다. 최신 loader 프로세스 private peak 약13.0GiB·해제 allocated1KiB/reserved2MiB.

운영4파일은 해시 일치, schema7은 임시 DB에서만 검증했다. 새 DB를 연 뒤 구형6코드로 되돌리는 경로는 지원 완료가 아니다. 애매한 완결형 조각·동일 화자의 암묵적 복수 흐름과 기존 넓은 사회적 판단 실패는 해결을 보장하지 않는다. 실제 Discord·사용자 화면·다른 Windows·새 소스의 장시간 실사용은 NOT VERIFIED이며 정식 릴리즈 BLOCKED다. 설치 프로그램·자동 업데이트·다른 Windows 지원은 추가 인증이 아니다. [실행 계약·경계·검증](MULTI-MESSAGE-UTTERANCES.md).

최종 패키지 감사에서21,546개 manifest SHA-256과 src85파일의 체크아웃 일치를 확인했고 비공개 파일 포함0건이었다. 마지막 문서 변경은 해당 문서의 manifest 해시만 갱신했으며 런타임을 다시 빌드하지 않았다.

## 2026-10-20 소스 고정 후 갱신 계획 — 아직 미실행

읽기 전용 실물 점검에서 현재 Portable src83파일은 자체manifest와 일치했다. 그러나 저장소 src84파일 대비 누락1·내용 차이4이며 manifest에는 source HEAD 필드가 없다. 최신 소스 반영/현재 Git HEAD의 패키지라고 표시하지 않는다. 이번에는 전체 재빌드·사용자 UI 실행·다른 Windows 시험을 하지 않았다. [사회적 품질 차단](SOCIAL-EVIDENCE-QA.md)은 별도로 남는다.

갱신은 운영 src를 확정하고 해당 HEAD의 회귀를 마친 뒤 한 번 진행한다.

1. Git HEAD·미커밋 상태·소스/공개 문서 범위를 확정하고 기존 패키지는 보존한다. 운영 데이터/모델/토큰을 복사하지 않는다.
2. 검증된 Python에서 `tools/build_portable.py --output dist/EchoMate-rc-<확정HEAD>`로 **존재하지 않는 새 버전 폴더**를 만든다. 도구는 Windows·12GiB 여유를 요구하며 이미 존재하는 출력에는 덮어쓰지 않는다. 이는 개발자 절차이며 일반 사용자에게 명령어 입력을 요구하는 설치 흐름이 아니다.
3. 번들 실제 src의 파일 집합과 SHA-256을 확정 소스와 대조한다. manifest의 files 해시와 실물도 대조하고, manifest SHA-256·원본 Git HEAD·시험 환경은 별도 비공개 QA 기록에 함께 묶는다. 현재 schema1 manifest에 없는 HEAD 필드를 있다고 가정하지 않는다.
4. refresh-public은 파일을 덧씌우는 경로로 삭제된 소스를 자동으로 완전히 동기화하는 보장이 없다. 기존 폴더를 갱신한다면 오래된 파일까지 포함한 집합 대조가 필요하며, 불일치 상태로 배포하지 않는다. 현재 계획은 새 폴더 빌드를 우선한다.
5. 번들 Python으로 별도 빈 검증 저장소·Discord HTTP mock을 사용해 최초 설정/DPAPI·모델 발견·로컬 미리보기·저장/재시작/종료를 확인한다. 실제 Bot Token/운영 DB를 복제하지 않고 GPU 여유·동시 로딩 방지를 확인한다.
6. 모델·LoRA·DB·인증정보·개인 설정·원문 로그 미포함을 검사한다. 사용자는 준비된 [10~15분 오프라인 확인](USER-MANUAL-QA.md)으로 가독성/파일 선택/키보드 사용을 직접 확인할 수 있다. 실제 Discord/깨끗한 다른 Windows/장시간 운용은 별도 승인·환경이 필요하며 미검증을 PASS로 바꾸지 않는다.

사회적 품질 게이트를 통과하지 않은 빌드는 사용자 검증 후보일 수 있어도 정식 릴리즈 PASS가 아니다.

## 2026-10-20 정밀 판단·UI 동작 후속 — 최신 / BLOCKED

시작 `a7ae298`, 구현 `548d0c6`. 전체 **575검사 OK75.691초**, 숨긴 Tk 렌더420조합 및 엄격한 SDK HTTP mock 디스패치209건을 확인했다. 초기 검사 경계 누락은 성공 결과에서 폐기했다. [정밀 사회적 QA](PRECISION-SOCIAL-QA.md)와 [실제 UI 동작표](UI-ACTION-QA.md)를 현재 기준으로 삼으며, 아래 이전 차수의 수치는 당시 기록이다.

새32 최초24→25/32, 별도 새16 직접 관계9→13/16이다. 수정 후32 재검27/32는 독립 성능이 아니다. 누락·관계 오류가 남아 정식 릴리즈 **BLOCKED**다. [오프라인 사용자 확인](USER-MANUAL-QA.md)은 준비했지만 아직 사람이 수행하지 않았다. 실제 계정/Gateway/송신·다른 Windows·24시간·사람 말투 평가는 NOT VERIFIED다.

최종 소스548d0c6로 공개 파일을 갱신한 Portable은24,767파일·4.590GiB이다. 모델/개인 자료는 포함하지 않는다. 새 `EchoMate-Check.vbs`는 별도 manual-check 저장소와 실제 Discord 차단을 제공한다. 최종 실제 GPU/빈 설치/새 프로세스 복원 검사는 아래 마감 절에서 별도로 기록하며, 단순 패키지 생성으로 성공을 선언하지 않는다.


## 2026-10-20 최종 후속 QA — GPU 허용 후 / BLOCKED

시작 HEAD `3829408`, 최종 앱 소스 `868f156`. 최종 문서 커밋은 Git 기록을 확인한다. 아래 초기 감사·GPU 보류 기록은 당시 경과이며 현재 결과는 이 절과 [상세 QA](SOCIAL-UI-QA.md)를 우선한다.

- 전체 회귀 **547개 OK63.119초**. 실제 숨긴 Tk 10화면·두 Canvas 크기·배율3종·7상태의420조합에서 활성 클릭/버튼/목록 텍스트 이탈0·callback 오류0. 렌더 p50/p95 **4.609/66.888ms**. 모든 팝업·파일 선택·사람의 시각 검토를 전수 PASS한 것은 아니다.
- 실제 GPU의 새16문항 최초 평가 **12/16**(누락3·연결오류1), 이전24·76문항은 개발 자료이며 **19/24·66/76**. 직접 호출 관계 전용의 별도 좁은8문항은 기존6/8→8/8, 오개입0. 이를 일반 청자 성능으로 확대하지 않는다. 비질문형 후속 누락과 개발 자료의 타인 대상 오개입이 남아 **정식 릴리즈 BLOCKED**다.
- 같은 입력·상주 가중치의 직접 연결 분류32회/조건에서 p50/p95 **1.4187/1.6264→0.6179/0.8195초**. 전체 수신→mock 송신9건은 **3.719/4.291초**, TTFT 근사0.609/0.635초, 중앙 생성속도7.724tokens/s. 큐 대기0·재생성0이며 긴 설명/검색/포화 경로 전체를 대표하지 않는다.
- 혼합 운용183.859초 실패를 보존하고 반응만 완료된 세션의 회수 누락을 수정했다. 수정 후 **600.188초·497반복·mock 답변994·반응99·GPU probe5/5**, 오류/잔류 Task0. commit 증분2.898MiB, GPU allocated/reserved 일정, 종료 후 worker0. 10분 대표 검사이며24시간 인증이 아니다.
- 최종868f156 Portable 실제 GPU에서 암호화 최초 설정·모델 선택/probe·미리보기·재시작 복원 PASS. 로딩 중 숨긴 미리보기 창 닫기 후24.813초에 안전 정리, allocated1KiB/reserved2MiB·worker0·관계/기억/예약 쓰기0. [배포 검사](DISTRIBUTION-QA.md)의 동일 호스트/샌드박스 제약을 따른다.
- 운영 설정·토큰·관계/기억/예약 DB·가중치·LoRA는 보존한다. 실제 Discord 접속/송신, 다른 Windows/GPU, 메이플 병행, 사람의 캐릭터 평가,24시간 실사용은 **NOT VERIFIED**다. 비공개 근거는 `local_data/social-ui-qa-20261020/`에만 둔다.


## 2026-10-20 사회적 대화·UI 후속 감사 — 진행 범위 / BLOCKED

시작/원격 `3829408` clean을 확인했다. 기준선523검사 OK60.304초, 수정 뒤 **527검사 OK59.774초**다. 명확한 실제 봇 멘션과 타인 멘션이 함께 있을 때 선택적인 그룹 연결 분류가 실패해도 독립 요청을 보존한다. 불확실한 이름 언급에 응답 권한을 새로 부여하거나 추측으로 그룹을 병합하지 않는다. 청자 PROMPT·활동/시간 정책·GPU 안전 기준은 변경하지 않았다.

기억 목록의 이전 query/kind 결과·삭제된 선택/버튼 대상과 실제 선택 표시를 수정했다. 캐릭터 편집의 두 요청을 save_apply로 통합하여 프로필 저장 실패 후 설정만 적용되는 경로를 차단했다. 임시 저장소 실패/성공 및 실제 withdrawn Tk 회귀를 추가했다. 모델 화면은 분할 가중치·GiB·파일 검사와 GPU 준비를 구분한다.

실제 Tk 10화면×두 크기×DPI3종 상당60조합에서 활성 클릭 영역 창 밖 이탈0건. render+idle p50 22.474/p95 113.906ms(단일 혼합 분포·속도 향상 주장 없음). **전체 버튼·팝업의 기능 연결 전수 PASS는 아니다.** [기능 연결 감사](UI-FUNCTIONAL-AUDIT.md)와 [공식 UX 참고](UX-REVIEW.md)를 확인한다.

이전32·44문항은 이제 개발/회귀 자료다. 새로운 합성 독립24문항을 봉인했지만 **미평가**다. 지속적인 외부 GPU 사용률 약19~20%가 관측되어 경쟁 부하를 만들지 않고 실제 GPU/새 E2E/새 Portable GPU 검사를 보류했다. 이전26/32·40/44의 누락/연결/오개입은 해결됐다고 주장하지 않는다. 이번 소스로 기존 Portable GPU 결과를 재사용하지 않는다. 실제 Discord·사용자 데스크톱 입력·다른 Windows·24시간 실사용은 미검증이다.

비공개 근거는 `local_data/social-ui-qa-20261020/`. 운영 DB·설정·토큰·원본 가중치·LoRA를 수정하거나 삭제하지 않았다. 정식 릴리즈 **BLOCKED**를 유지한다. 다음 우선순위는 GPU 경쟁이 없는 조건에서 봉인24 최초 평가, 남은 의미 오류 개선·새 독립 재평가, 팝업/비동기/종료의 UI 전수 검증 및 최종 Portable 재검증이다. Git 마감과 패키지 정합성은 최신 작업 로그를 확인한다.


최종 구현 commit **94c87fc** (시작d7cf29a). 최종 전체523 OK58.467초·공개38파일 stage검사0건·운영4파일hash동일·원본weights Hub ETag 일치. Portable4.59GiB/24757파일 source81/docs43 byte·manifest 공개hash 일치/비공개 파일0. 정식 릴리즈 BLOCKED, 코드·후보만 보존한다. 최신 문서 마감 commit은 git log를 확인한다. 실제 Discord 접속·사용자 데스크톱/게임 조작 금지는 유지한다.


## 2026-10-20 최종 안정화 — 최신

마감: **523회귀 OK58.467초**, 실제20분 혼합 운용1912 mock 답변·GPU10/10·worker0, source 및 Portable의 실제 shard 로딩/모델 선택·미리보기 PASS. 최종 shard peak12.92GiB(최초13.01), 원본31.35GiB. 운영 자료 보존·독립 청자26/32로 **릴리즈 BLOCKED**. 실제 Discord/다른 Windows/Maple/24시간/사람 말투 평가는 NOT VERIFIED. 상세·소스/패키지·Git 마감은 STABILIZATION-QA를 우선한다.

이번 후보도 **BLOCKED**다. 메모리 부족만 남은 원인으로 설명하지 않는다. 공식 shard QA 복사본은 실제 peak commit 감소를 보였으나 독립 청자32의 누락5/연결1과 개발44의 오개입1/누락3이 남는다. Portable에는 원본/복사본 가중치·사용자 자료를 넣지 않으며 최종 source byte/hash 및 격리 실행 결과를 링크 문서에 누적한다. 다른 Windows/설치형/자동 업데이트 인증은 없다.

상세 근거·실패·미검증·재현·마감: [최종 안정화 QA](STABILIZATION-QA.md). 아래 이전 차수의 숫자는 당시 기록이다.


## 263eedc 후속 — GPU·Portable 재개 (최신)

메모리 여유 확보 후 공식 no-LoRA 로딩/최소 추론, 네 캐릭터12생성, 전체 응답9/9, 교차 A/B18/18(출력9쌍 동일), 실제 전환·실패 복구·생성 중 두 요청 보존, 최종 네 요청 공정 큐, **Portable 실제 모델 로딩·숨긴 Tk 미리보기**를 완료했다. 전체 **506 OK55.636초**. 초기 메모리 부족만을 현재 차단 사유로 쓰지 않는다.

실측으로 기존 weight+2GiB가 부족함을 확인해 준비 reserve10GiB+margin2GiB(공식 단일22.28GiB 기준 시작34.28GiB)로 보강하고 이미 사용한 process commit을 중복 계산하지 않는다. cuBLAS workspace가 큰 segment를 붙든 문제를 수정해 생성·전환 후 PyTorch reserved 약6.99GiB→2MiB를 실제 확인했다. no-LoRA/disabled-PEFT E2E p50 4.047/4.234초, p95 4.715/4.797초(n9씩, 큰 개선 주장 없음).

**정식 릴리즈 BLOCKED**: 추가 청자12 최초 평가는11/12(누락1), 이전44 개발 재검40/44(오개입1·누락3). 추가 의미 후보는 최소 수신자 probe 실패로 폐기했다. 캐릭터 사람 평가·다른 Windows/드라이버·장시간 실사용·실제 Discord는 NOT VERIFIED. 다른 PC가 제공되지 않아 현재 호스트의 격리 PATH/저장소 검사로 대체 성공을 선언하지 않는다.

구체적 단계/실패/수치/재현과 비공개 파일 목록은 [재개 GPU QA](RESUMED-GPU-QA.md). 아래490/500·GPU 미실행·Portable weights=false 기록은 과거 상태다. 최종 패키지·보존·공개 감사는 마감 절에 누적한다.

2026-10-20 마감 구현 **cbe2c77**: Portable4.59GiB/24,756파일, source81/docs42 byte·공개 manifest hash동일. 운영4파일 hash동일·평가 봉인4개 유효, 공개20파일 민감 리터럴/개인 경로/깨진 링크0건, 패키지 가중치/DB/운영 설정0건. 생성된 bundle/src bytecode만 제거했다. 12문항은 이후 개발 자료가 되어 최종 일반화 점수로 쓰지 않는다. 별도8을 고정 commit으로 시도했지만 host 여유27.07GiB<34.28GiB로 로딩 전 차단했고 재시도하지 않았다. 이8·깨끗한 다른 Windows·장시간·실제 Discord는 미검증이며 릴리즈 BLOCKED다. 이미 완료한 GPU/Portable 성공 범위는 그대로 유효하다.

## f1c0ec6 후속 — Windows 1455 메모리 감사 (최신)

시작 main/HEAD/원격 `f1c0ec6`, clean·fetch 차이0/0. 기존490검사 OK61.101초, 최종 **500검사 OK60.204초**. 추가10검사는 실제 Windows counter 단위·admission/재검사·실패 traceback 정리·Torch 미import cleanup·안전한 UI 오류 숫자를 검증한다. 기존 사회적 라우팅/공정 큐/동의·DB·UI 전체 모의 회귀를 포함한다.

1455는 PEFT 이전 native Safetensors 열기였다. **pread도 헤더 처리 전 전체 COW 매핑**하는 버전 동작과 일치한다. 실제 Windows 합성64/256MiB 각2회·512MiB1회에서 순간 process commit 증가64.13/256.50/513.01MiB를 확인했다. mmap256MiB는 피크513.01MiB로 더 컸다. no-LoRA import private1432.73MiB, 기존 PEFT import 포함1546.89MiB. LoRA 제거가 base 로딩 메모리를 늘렸다는 증거는 없다. [원인·측정·안전 기준·재현](LOADER-MEMORY-QA.md).

실제 단일 원본22.28GiB / guard24.28GiB / 여유 commit13.37GiB로 **사전 차단**, GPU 모델 로딩 시도0회. +2GiB를 보장된 전체 피크로 인정하지 않고 기존 기준을 유지한 채 import/processor 이후 재검사한다. 로딩 실패 시 frame locals/processor/부분 모델 참조 정리, cleanup의 불필요한 Torch import 방지, 소유자 UI의 안전한 실제 여유/기준 표시를 구현했다.

NF4/실제 모델 초기화 피크, 기본 no-LoRA 최소 추론, 독립 청자20, 캐릭터12, E2E A/B9, 최신 실제 GPU 전환/공정 큐, Portable 실모델·미리보기는 **BLOCKED 또는 NOT VERIFIED**다. 깨끗한 다른 Windows/장시간 운영/실제 Discord도 NOT VERIFIED. 아래 과거 성공 수치를 이번 GPU 검증으로 재사용하지 않는다. 전체 릴리즈 **BLOCKED**를 유지한다.

마감 구현 커밋 **338af1f**. Portable 후보 `dist/EchoMate-rc-model-character` 4.59GiB/24,767파일의 공개 소스를 갱신했다. 프로젝트와 번들 source81파일의 집합·전체 bytes·source manifest hash가 일치했다. 번들 Python3.10.11/Torch2.9.1+cu128/Transformers5.20.1/discord.py2.7.1, 시스템 Python 없는 PATH·새 DATA_HOME·빈 HF cache·숨긴 Tk에서 최초 설정/DPAPI 암호화/프로필 저장/설정 복원/종료를 재검증했다. Discord 연결false, 가중치 로딩false, 빈 cache 모델 발견0은 예상 결과다. 실제 모델 로딩/미리보기/다른 Windows 성공으로 해석하지 않는다.

운영 settings/bootstrap/companion/sent 네 파일 hash동일, 미사용 독립20 protocol seal유효. 공개12파일 staged 검사에서 비공개 경로/실제 bootstrap 민감 리터럴/개인 경로/깨진 문서 링크0건, diff check 통과. 패키지의 가중치·사용자 DB·운영 설정0건. 원본·집계·검사 로그는 `local_data/loader-qa-20261019/`에 보존하며 Git/배포에서 제외했다. 소스/문서 최종 커밋은 `git log`를 확인한다. 공개 릴리즈 파일 업로드/정식 릴리즈 승인은 하지 않는다.

시작 main/HEAD5249fd2, 원격 main fetch0/0, 초기 clean. 운영 설정/bootstrap/companion/sent 네 파일 hash와 소스 기준선을 비공개 local_data/distribution-qa-20261019에 보존했다. 실제 Discord 로그인·조회·동기화·송신/사용자 데스크톱 마우스·키보드 조작은 하지 않는다.

## 구현

- 기본 모델 base 하나, 기존 persona/adult 서명 설정의 읽기 마이그레이션, 기본 PEFT 의존 제거. 가중치/어댑터 파일은 보존.
- ModelRegistry/Validator: 로컬 폴더/HF 캐시 탐색·헤더/인덱스·tokenizer/template·architecture 검사, GGUF/LoRA는 미지원 이유 표시. 새 모델은 안전 전환·최소 probe 후 확정, 실패 복구/대기 원본 재검증.
- 독립 캐릭터 프로필 schema/enum compiler·서명 저장·목록·편집/복제/삭제/복원·가져오기/내보내기, 기존 기분/성별/활동 보존, GPU 큐 기반 오프라인 미리보기.
- 새 설치 GUI 토큰 마스킹·Windows DPAPI, allowlist 기본 차단, 자동 네트워크 없음. source local_data와 Portable AppData 분리.
- 청자 이름 후보의 무공백 호격/2인칭 증거·보고/인용 구분, 맞장구와 종료/평가 분리, 확인된 상대에게 명시적으로 제외된 초대 거부. 시간/활동으로 청자를 확정하지 않음.
- 단계 계측/RAM·VRAM 분포, 속도 후보 기본OFF. [전체 지연](PERFORMANCE-PIPELINE.md).

## 실제 수행과 한계

최종 마감: **전체490 OK58.325초** (`final-regression.log`). 추가한 청자 제외/인용 회귀의 누락 import 오류도 수정 후 전체를 다시 실행했다. 이후 첫 설정 전 시작 버튼 비활성화는 UI/Controller 검사로 별도 확인한다. 이전489는 그 전 중간 수치다. 실제 GPU 성공과 단위/모의 성공을 혼합하지 않는다.

마지막 UI/레지스트리/Controller12검사 OK4.855초. 최종 번들에서도 별도 DATA_HOME의 첫 실행/합성 DPAPI/프로필 저장/재읽기/안전 종료를 다시 통과했다(`portable-publish-check.json`). VBS /check는 앱을 열지 않고0으로 종료했다. 제한 셸에서 WSH 설정 접근 거부가 있었으나 호스트 권한의 같은 무실행 검사에서는 통과했다. 일반 사용자 더블클릭·실제 Discord·GPU 가중치 로딩을 성공으로 추가 해석하지 않는다.

| 검사 | 결과/구분 |
| --- | --- |
| 시작 전체 회귀 | 475 OK58.633초 |
| 분리 중간 전체 회귀 | 483 OK61.215초; 이후 마감 결과는 아래 절 |
| Controller/프로필/모델/격리 Tk 중간 | 57 OK13.683초; 새 공통 프로필 속성·계측 변경 후 전체 재검 필요 |
| 실제 로컬 GPU 이전 실패46문항 | 45/46, 오개입1·누락0·흐름 오류0; 약22GiB 파일의4bit NF4와 기존 adapter를 로딩하고 base 분류 사용 |
| 최종 독립20문항 | 해시 고정 후 새 no-LoRA 로더 실행 시 Windows1455로 시작 실패. 완료/성공 점수 없음 |
| 캐릭터 실제 생성12문항 | 프로토콜 준비, 미실행 |
| 동일 전체 파이프라인 A/B9문항 | 프로토콜 준비, 미실행 |
| Portable 생성 | runtime+공개 소스 약5GiB, 모델/개인 자료 제외. manifest와 로컬 폴더 산출물 |
| Portable 독립 실행 | 설치 Python 경로를 제외하고 번들 Python3.10.11·Torch2.9.1+cu128·Transformers5.20.1·discord.py2.7.1·bitsandbytes import, CUDA 가용성, 실제 Controller/숨긴 Tk, Gemma 클래스·빈 캐시 탐색 확인 |
| Portable 최초 설정·저장·복원 | 별도 DATA_HOME/빈 HF cache에서 합성 토큰 DPAPI 등록→프로필 저장/적용→모델 재검색→안전 종료→서명 설정 재읽기 통과. 실제 토큰 검증/서버 목록/가중치 로딩은 제외 |
| 깨끗한 Windows VM / 설치 프로그램 | 미검증 / 미구현 |
| 실제 Discord / 장시간 사용자 품질 | 미검증 |

GPU 최초46은 새 코드 개발 통제이며 새 독립 성적이 아니다. 마지막 명시적 제외1건에 대한 결정적 검증은 추가했지만 최종 GPU 재검을 대신하지 않는다. 여러 활동/시간·다중 대화/FIFO/원본/공정 큐·개인정보는 기존 모의 테스트를 재실행한다. 고정 문자열 예외나 맞장구 일괄 삭제로 결과를 맞추지 않는다.

Windows 오류는 weight safe_open에서1455, 이후 관측 여유 RAM약6.4~6.7GiB/commit약10~12GiB였다. 실제 대형 로딩 재시도를 중단하고 RAM/commit 사전 검사를 추가했다. 다른 프로세스 종료/시스템 설정 변경/운영 DB 변경은 하지 않았다. 따라서 새 기본 모델 성공·실제 전환 복구·캐릭터 효과·생성 p50/p95를 검증했다고 주장할 수 없다.

Portable 첫 실행은 라이브러리 내부 models 폴더를 사용자 모델 폴더와 혼동한 복사 필터 때문에 Transformers import가 실패했다. 필터를 수정해 누락된 라이브러리를 복원했고 두 번째 독립 실행은 통과했다. 이 실행은 동일 호스트에서 PATH/PYTHONHOME/빈 HF cache/별도 DATA_HOME을 사용한 검사이며 드라이버/시스템 DLL까지 없는 깨끗한 VM과 같지 않다. 전체 폴더를 유지해야 하고 소스 갱신 후 manifest를 재계산한다.

## 릴리즈 판정

공개 구현 커밋 **826a816**. 커밋 전 공개66파일 staged 경로/실제 토큰·키·개인 ID 리터럴/개인 경로/문서 링크 검사0건, diff --check 통과, 원격main과 시작HEAD 차이0/0이었다. 운영4파일 hash동일. 비공개 실행 산출물은 local_data/distribution-qa-20261019, Portable은 dist/EchoMate-rc-model-character에만 있다. 두 경로 모두 Git 비추적이며 Release 자산 업로드 없음. 후속 마감 문서 커밋은 최신 git log를 확인한다.

최종 전체 회귀 `publication-tests.log`: **489 OK61.667초**. 그 뒤 모델 준비와 종료가 함께 실패해도 준비 표시를 해제하는 finally를 보강했고 Controller 관련12검사 OK4.959초, 관련30검사 OK8.480초를 확인했다. 개발 중 문자 인코딩/모듈 경로 도구 오류, 구형 모델 버튼/정책·오류 문구 기대값 불일치, 초기 캐릭터 문자열 연결·목록 setter 인자 오류는 수정해 재검했다. 미실행 코루틴 경고도 오류로 다뤘다. 수치만 늘리는 성공 기준이 아니다.

소유자의 명시 선택으로 EchoMate 소스에 MIT를 적용했다. Python/패키지/CUDA/모델 라이선스를 MIT로 재지정하지 않는다. Portable 후보4.59GiB·약24700파일을 생성했지만 GitHub Release 자산으로 업로드하지 않았다. 운영4파일 hash4/4 동일, 패키지 내 가중치/비공개 DB·token/key/jsonl 파일0을 확인했다. 공개 staged 민감정보 검사와 최종 커밋은 마감 절에 기록한다.

**BLOCKED / 검증 후보**. 새 기본 모델의 GPU 로딩·독립 청자/캐릭터/전체 지연 검증, 새 로컬 모델의 실제 구조화/요약 품질, 깨끗한 Windows 첫 실행·업데이트·장시간 QA가 남았다. 코드·모의 통과와 일반 사용자 배포 승인을 구분한다. 자동 모델 다운로드·GGUF 엔진·CPU-only·설치 프로그램·자동 업데이트는 구현하지 않았고 개인 LoRA를 배포하지 않는다.

개발 재현: PYTHONPATH=src;tests 후 가상환경 python -m unittest discover -s tests -q. 모델 비교는 verify_social_gpu.py. 배포 빌드는 tools/build_portable.py --output dist/새버전폴더, 공개 파일 갱신은 --refresh-public. 격리 런타임 검사는 echomate_bot.distribution_check이며 가중치/Discord에 연결하지 않는다. 일반 사용자는 이 명령 대신 GUI를 사용한다.

## 이번 최종 Portable 검사 환경

공개 소스868f156를 기존 번들에 갱신하고 전체24,761파일·4.590GiB manifest를 다시 계산했다. 모델 가중치와 운영 자료는 포함하지 않았다. PATH는 번들 런타임과 Windows 시스템 경로로 제한하고, 별도 데이터 폴더·오프라인 Hugging Face·Discord login/start 금지 mock을 사용한다. 설치/미리보기 중 원문은 비공개 폴더에만 쓴다.

첫 재검사는 모델 로딩 전에8초 초기화 timeout이 났다. 별도 초기화 probe의 스택이 Windows asyncio 내부 socketpair의 accept에서 멈춘 것을 확인했다. 샌드박스 밖의 검토된 동일 검사에서는 초기화가 진행됐다. 따라서 초기 실패는 보존하며 이를 앱의 GPU 실패나 깨끗한 Windows 실행 증거로 바꾸지 않는다. 샌드박스의 네트워크/프로세스 제약 밖 검사는 실제 Discord 접속 허용이 아니다.

### 최종 실행 결과

검토된 실행에서 868f156 공개 소스가 번들에서 import됨을 assert했다. 번들 Python3.10.11, discord.py2.7.1, Torch2.9.1+cu128, Transformers5.20.1에서 신규 DPAPI 토큰/서명 설정·프로필 저장·검증된 shard 모델 선택·최소 probe·한국어 미리보기·재시작 설정 복원이 통과했다. 실제 Discord는 연결하지 않았다.

동일 번들에서 실제 숨긴 Tk 미리보기 생성 버튼 바인딩을 실행하고 GPU 로딩 중 창을 닫았다. 요청별 취소와 실제 모델 해제 후24.813초에 완료했으며 allocated1KiB/reserved2MiB, 종료 후 worker0, companion 데이터 쓰기0이었다. 취소는 현재의 비중단 모델 로딩을 안전하게 drain한 뒤 종료한다. 창을 닫으면 즉시 GPU 로딩이 물리 중단된다는 의미가 아니다.

최종 소스/문서 파일 해시와 manifest를 재정합한다. 전체 패키지 실행 성공은 이 호스트의 격리 런타임 검사에 한하며 깨끗한 다른 Windows 설치 검증이 아니다. 사회적 청자 및 UI 전수 실행 미완료로 정식 릴리즈는 BLOCKED다.

## 2026-10-20 Portable 최종 사용자 흐름 — 소스548d0c6

최종 번들 Python·자체 숨긴 Tk·새 빈 검증 저장소에서 GUI 최초 설정(DPAPI/서명), 가상 서버/채널, 실제 분할 모델 선택/probe, 현재 캐릭터 파일 내보내기/새 항목 가져오기, 실제 GPU 미리보기와 로딩 중 닫기, 새 프로세스 복원을 확인했다. 첫 흐름87.140초·첫 UI0.406초, 재시작0.437초·첫 UI0.390초였다. 실제 Discord는 강제 차단했고 외부 HTTP0·관계/기억/예약 쓰기0·종료 worker0이었다.

로딩 중 취소는26.063초 후 정리됐고 GPU allocated1KiB/reserved2MiB였다. 안전한 로딩 구간을 즉시 물리 중단하지 않는다. Tk 검사 펌프 최대 간격1.937초가 있어 완전 무정지 UI라고 인증하지 않는다. 같은 호스트의 격리 저장소 검증이며 다른 Windows/깨끗한 VM/native 사용자 조작은 NOT VERIFIED다.

공개 Portable은24,767파일·4.590GiB이며 모델·개인 DB·토큰은 제외한다. 최종 source/docs 바이트 및 전체 파일 manifest는 별도 package audit로 대조한다. 소스와 Portable의 일반/오프라인 VBS 4진입점 /check는 앱/봇을 시작하지 않고 통과했다. 공개 다운로드 릴리즈는 만들지 않고 후보를 로컬에만 둔다.
## 2026-10-24 모델/시스템 진단 후 증분 반영

운영 기본은 Gemma이고 Qwen 평가 사본·평가 데이터/출력·tools·운영 DB/설정/토큰은 Portable에 넣지 않는다. 공개 런타임3모듈과 문서만 반영하며 기존 Python/의존성 전체 재빌드는 하지 않는다. 번들 Python의 별도 CWD/local_data에서 기억·동의·송신32검사 OK13.400초. 첫 시도의 경로 불일치25오류는 보호 규칙을 완화하지 않고 격리 경로를 바로잡아 해결했다. 실제 GUI/GPU 미리보기·다른 Windows·사용자 조작은 이번에 재검하지 않았다. 최종 공개 파일/manifest/VBS 대조는 [진단 마감](MODEL-SYSTEM-DIAGNOSIS-QA.md)을 따른다.
