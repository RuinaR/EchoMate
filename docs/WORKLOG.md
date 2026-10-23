# 작업 로그

## 2026-10-24 캐릭터 페르소나·현재 성격 조회

마감: 전체688검사 OK221.655초, Portable 공개 src/docs149파일·manifest21,553파일 대조, 번들39검사 OK8.141초·두 VBS `/check` PASS. 운영4파일 hash 보존. 캐릭터 강한 차별성 목표 미달·실제 Discord 미검증으로 BLOCKED다.

시작601c572 clean. 표현 위주 성격 지침의 충돌, preview/Runtime 기분 차이, 동의 없는 관계의 임의50을 수정했다. v2 반응 방식·제한된 정체성 데이터·v1 서명 호환·네 프리셋과 미저장 미리보기/동일 모델 비교를 구현했다. 소유자 ID 전용 ephemeral `/성격`과 `/동의`의 두 명령 계약·새 검토 fingerprint를 반영했다. 운영 자료/모델은 변경하지 않았다.

기존 프롬프트12와 최종 후보32 GPU 응답을 같은 모델에서 비교했지만 네 방향 차별성은 미달이다. 추가 예시 후보36응답은 새 평가의 모욕성 출력 때문에 제거했고 실패 근거는 비공개로 보존했다. 반복 튜닝은 멈추며 사람이 판단하는 캐릭터 수용 기준과 자료 구축 검토를 후속으로 남긴다. 최종 핵심 생성5모듈은 첫 GPU 봉인과 일치한다. 실제 Discord0회, 소스 SDK2/2·3송신, 격리 UI12화면+6모달·43디스패치, 번들39표적검사 확인. 전체 회귀와 Portable 공개 파일/보존 마감은 [PERSONA-QA](PERSONA-QA.md). `/동의` 미해결·사회적 품질 때문에 릴리즈 BLOCKED다.

## 2026-10-24 — 명령 복구 준비·실사용 안정화

- 시작 main/local/remote09a785e clean. 사용자 응답은 오프라인만. 운영 audit 부재/pending false만 읽기 전용 확인했으며 원격 비표시 원인은 미확정.
- SDK2.7.1 `[0]` 접근 배열 손실과 이름만으로 확인하던 검증의 한계를 재현. SDK HTTP 원본 범위 보존·fingerprint 강화, 전역 확인 전에 서버별 삭제하지 않도록 수정. 오류/취소 단계·HTTP 코드와 새 승인 경계를 유지.
- 목록 조회/변경 승인 UI 분리·안전한403/404 안내. 격리6화면+팝업 시각 확인/응답 화면16디스패치 PASS. 초기 SDK·화면 변수·테스트 인코딩 실패 기록을 보존하고 표적 수정/재검.
- 기존 분할 Gemma 단일 상주 모델로 새6시퀀스6/6, 실제 생성→SDK mock11송신/Runtime15호출, pending0. 넓은 의미 오류를 해소했다고 하지 않고 안정적인 의미 코드를 유지. 게임/다른 앱 조작·실제 Discord는0회.
- 전체 회귀·Portable·자료 보존·최종 Git 근거와 다음 승인은 [명령 복구 QA](COMMAND-RECOVERY-QA.md)에 마감 기록. 정식 릴리즈 BLOCKED 유지.

## 2026-10-23 — 메모리 계측·Windows UI 입력 수명주기 재개

- 시작 main/local/remote `046ed12` clean. 사용자 재개 지시로 잠정 중단 해제. 운영 선택은 원본 `base`; 자동 전환하지 않음.
- 기존 분할 GPU 준비26.157초/private high-water13.015GiB. allocator warmup 계측 추가, Windows pread·NF4 순차 변환은 기존 라이브러리 동작임을 확인. 추가 절감 미입증으로 계산/안전 기준 유지.
- 공통 release/Space/드래그 취소·Future 중복 잠금·idle redraw 생략. 초기 설정·모델 빈 상태·고배율 캐릭터/진행/응답/관계 겹침 수정. 실제 비활성 Desktop의 owned HWND만 렌더.
- SDK sync를 실제 직렬화하고 HTTP만 mock하는 검사를 추가. 원격 `/동의` 문제는 미확정으로 유지. 처음 UI 색상/누름 전용 테스트 실패와 미연결 명령 차단을 구분해 보존.
- 검사 명령·수치·실패·Portable·데이터 보존 및 다음 승인 경계는 [재개 통합 QA](RESUMED-MEMORY-UX-QA.md)에 누적. 실제 Discord와 운영 자료 변경 없음. 정식 릴리즈 BLOCKED.

## 2026-10-20 잠정 중단 인수인계 — 문서만 변경

시작 main/로컬·원격 `d6bd50e` clean. 사용자의 실제 Discord 명령 정리 후 `/동의` 포함 모든 명령 비표시 관찰을 미해결로 기록했다. 현재 install/review/apply/setup_hook 및 설치된 SDK sync의 전역/서버 분기와 기존 QA를 읽기 전용 점검했다. 명령 정리 검사는 fetch/sync AsyncMock의 흐름 검사이며 실제 등록/표시 증거가 아님을 명확히 했다. 당시 실행 버전·Application·원격 목록/응답은 확인하지 않았고 원인을 단정하지 않았다.

읽기 전용 인증 조회 승인과 실제 변경 승인을 분리한 복구 절차, 사회적 판단 차단, Portable/번들 문서 상태를 AI-HANDOFF/CURRENT-STATUS 등에 기록했다. 운영 자료/Discord 상태 변경·추가 기능·테스트/GPU/Portable 재빌드는 하지 않았다. 문서 diff/링크/포함 목록 검토 후 문서만 커밋·푸시하고, 사용자 재개 요청 전까지 EchoMate 추가 작업을 중단한다.

최종 Portable 공개 소스 갱신 완료: manifest21,548파일, src/docs144파일 및 GPU 봉인 소스 일치, 번들 Python의 별도 저장소·숨긴 Tk·동의/명령 mock44검사 OK12.465초, 두 VBS /check PASS. 운영4파일 SHA256 보존. 이번 번들의 GPU 재로딩·실제 Discord·다른 Windows는 미검증이다. [근거](LIVE-SERVER-FIXES-QA.md).

최종 기능 질문 오분류(일반 의견의 ‘가능’ 표현을 가로챔)를 실제 GPU 내용 검토로 발견해 수정했다. 첫 독립 자료는 회귀로 전환하고 새4시퀀스를 고정했다. 최종 전체662검사 OK209.577초 및 최종 GPU 결과는 [통합 QA](LIVE-SERVER-FIXES-QA.md)를 참조한다. 명령 부분 실패 pending 유지 검사도 추가했다.

## 2026-10-20 실서버 결함과 실제 기능 설명 통합

`74e1c9a`에서 시작. 구형 CommandNotFound의 저장소 실패 오표시, 별도 CompanionStore 초기화/잠금 오류 고정, 단독 이름 후속의 근거 손실, 짧은 반응의 조기 확정, 완료 Task 활성 잔존, 이미지 OFF 첨부/앞 조각 자료 손실을 수정했다. 읽기 전용 capabilities와 최신성 검사, 소유자 명령 목록 검토/승인/실제 재조회 계약, 가명 진단을 추가했다.

최초661 회귀에서 실패5/오류1을 보존했다. 단독 호출의 연결 근거가 의미 판단을 우회하던 후보를 바로잡고, 바뀐 실패 안내·승인 계약의 검사/실제 Controller fixture를 갱신했다. 관련55검사 OK35.805초 후 최종 전체661검사 OK208.037초. 운영 DB는 읽기 전용/비공개 복사본으로만 조사했다. [최종 GPU/Portable 근거와 남은 한계](LIVE-SERVER-FIXES-QA.md). 실제 Discord 연결·운영 자료 변경은 하지 않았다.

## 2026-10-20 탈퇴 서버의 가입 목록 잔존 수정

설정·DB·소유자 서버 ID와 가입 서버 목록을 합치던 표시 오류를 수정했다. 전체 로컬 서버 자료는 보존하고, 대화할 곳의 가입 목록에는 현재 Gateway 가입 정보(연결 중) 또는 마지막 조회 inventory(오프라인)에 있는 서버만 표시한다. 숨겨진 서버 선택/채널 선택을 정리하며 관계·기억 관리의 로컬 자료 접근은 유지한다. 실제 Discord 연결 없이 숨긴 Tk/임시 DB UI19검사 OK8.588초. GPU/전체 회귀는 국소 UI 수정으로 반복하지 않았다. Portable에도 해당 공개 파일만 반영했다. 실제 서버명/탈퇴 여부를 이번에 새로 조회한 것은 아니다.

## 2026-10-20 완성형 연속 반응 — 최신 / 사용자 검증 후보·BLOCKED

시작/원격 `77841f0` clean/main. 문장 완결과 대화 차례 확정을 분리했다. 실제 reply·확인된 청자/현재 직접 상대·명확한 진행 요청 보충/호칭 초대에만 완성형0.3초 대기를 허용하며 미완성0.8초·첫 조각부터최대4초를 유지한다. 완성형 직접 요청/근거 없는 일반 발언은 일괄 지연하지 않는다. 후보 결합이 봇 응답 자격·대화 연결을 확정하지 않는다.

전체 회귀 **639개 OK164.355초**(추가9개). 새 GPU 고정 시퀀스 **7/7**(동일 상주 모델 A/B1개+나머지 최초6개), 실제 생성→discord.py SDK HTTP mock **11송신**. 11조각·3화자 교차·사람 청자·독립 호출·생성 중 완성형 보충에서 기대한 원본/연결/응답 범위를 확인했다. 대상 오개입·누락·연결/원본 reply 오류·중복 송신은 이 세트에서0, 각 시퀀스 종료 pending0이다. 의미 호출은3회로 이 자료가 넓은 의미 품질을 대표하지는 않는다.

좁은 동일 모델 비교에서 이전 조립 방식은 한 후속 차례를 의미 판단4회·후속 답변3회로 처리했고, 후보는4원본을 판단1회·후속 답변1회로 보존했다. 혼합11송신 수신→SDK mock p50/p95 **8.844/16.6175초**, 마지막 조각 기준 **8.828/16.6095초**. GPU 실제 호출15회(의미3·텍스트12, 그중 생성 중 보충으로취소1), 매 조각별 재생성은 없다. 서로 다른 전체 코호트의 속도 개선으로 비교하지 않는다.

예산을 넘는 보충 대기가 앞선 작업까지 무효화해 원본을 잃을 수 있던 경로를 수정했다. 구성 실제 멘션 ID를 합집합 보존하고 SDK의 같은 전송 내 원본/Reaction 대상 재조회를 제거했다. GPU 세트29구성 원본→29조회, 별도 SDK11원본+중간 Reaction도11조회다. 최신 권한·작성자·채널·본문·수정/삭제·개인정보 검사는 유지했다.

Portable `dist/EchoMate-rc-utterance`의 공개 소스를 한 번 갱신했다. 번들 Python의 발언·숨긴 Tk·오프라인·저장/취소54검사 OK16.722초, 창을 띄우지 않는 VBS /check PASS. src85파일이 GPU 봉인 소스와 같고 manifest21,546개 파일 목록·공개146개 해시가 일치하며 운영4파일 해시가 보존됨을 확인했다. 이번 Portable 경로의 GPU 재로딩은 하지 않았고 동일한 최신 소스의 실제 GPU 검사와 이전 번들 GPU 성공을 구분한다.

문맥 없는 완성형 첫 조각, 기한 뒤 조각, 같은 화자의 암묵적 복수 흐름/청자 전환과 기존 Gemma 정정·우려·농담·전달문 질문 실패는 해결 보장이 없다. 실제 Discord·친구 서버·사용자 화면·다른 Windows·장시간 실사용은 NOT VERIFIED이며 정식 릴리즈 BLOCKED다. [정책과 한계](MULTI-MESSAGE-UTTERANCES.md), [별도 승인 후 서버 시험 준비](USER-MANUAL-QA.md).

조사 결과: 기존 `unfinished()`는 끝 기호에서 즉시완료, 열린 버퍼도 완성형 다음 조각에서 즉시확정했다. Pending의 문장 힌트와 차례 후보 근거/타이머를 분리하고 Runtime에서 메타데이터와 확인된 대화 상태만 후보로 공급했다. 초기 새 검사에서 legacy 주입 backend에 확인된 direct_peer가 없던 fixture와 즉시 완료를 전제한 대기/재연결 검사를 실제 사회적 backend·발언 확정 계약으로 수정했다. 누적 예산 검사에서 실제 작업 유실을 찾아 수정했으며 단언을 완화하지 않았다.

명령: `PYTHONPATH=src;tests;tools`, `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`. 관련48검사 OK15.540초 후 최종 전체639검사를 한 번 실행했다. GPU 도구 `verify_utterance_gpu.py --sdk-mock`은 실제 SDK 객체/직렬화와 fail-closed HTTP mock을 사용하며 프로토콜·응답·trace는 비공개 `local_data/turn-20261020/`에만 둔다. 비교는 이전 assembler만 교체하고 같은 현재 Runtime과 상주 가중치를 사용했다. 최초 래퍼 참조 오류는 모델 로딩 전에 수정했다. 독립 평가 후 자료를 개발 회귀로 전환하며 그 결과를 보고 분류 프롬프트를 조정하지 않았다.

## 2026-10-20 분할 발언·교차 화자 통합 — 사용자 검증 후보 / BLOCKED

시작/원격 `e9f4230` clean. 기존 SUPPLEMENT/30초/작업별 cancel을 감사하고 Raw Event/논리 뷰·bounded wait·전체 원본 검증·독립 세그먼트를 통합했다. 초반 전체616검사에서 실패 누적과 SDK 대기 계약2건을 재현/수정했다. 최초 GPU7시퀀스6/7은 방식 조사 보충이 조기 확정되어 2회 답했으며 문법 경계 수정과 회귀로 보존했다. 별도38개 Portable 검사 실패는 테스트 작업 폴더가 private_path 경계 밖인 하네스 오류였고 경계를 완화하지 않고 격리 cwd를 바로잡았다.

전체 회귀 **630개 OK141.186초**. 신규 발언 시퀀스 회귀24개, 새 Portable의 번들 Python·숨긴 Tk·오프라인 경로42개 OK9.128초. 최초 GPU7시퀀스6/7의 조기 확정·중복 답변을 수정하고, 해당 회귀1/1·새 시퀀스5/5·새 의미 시퀀스3/3·지연 보충1/1을 확인했다. 미사용 자료는 평가 후 회귀 자료로 전환한다. 최종 명령: `PYTHONPATH=src;tests;tools`, `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`. GPU 도구는 `tools/verify_utterance_gpu.py`, 프로토콜·응답·Trace는 비공개 `local_data/utterance-20261020/`다.

새 Portable 한 번 빌드(4.542GiB/21,546파일), 최종 Runtime 반영·VBS /check·번들 UI/모델/미리보기·취소 확인. 모델 프로브와 미리보기는 Runtime 응답 측정에서 제외한다. 운영4파일 해시 보존. 애매한 완결형 조각·동일 화자의 암묵적 복수 흐름과 기존 넓은 사회적 판단 실패는 해결을 보장하지 않는다. 실제 Discord·사용자 화면·다른 Windows·새 소스의 장시간 실사용은 NOT VERIFIED이며 정식 릴리즈 BLOCKED다. [실행 계약·경계·검증](MULTI-MESSAGE-UTTERANCES.md).

최종 패키지 감사에서21,546개 manifest SHA-256과 src85파일의 체크아웃 일치를 확인했고 비공개 파일 포함0건이었다. 마지막 문서 변경은 해당 문서의 manifest 해시만 갱신했으며 런타임을 다시 빌드하지 않았다.

## 2026-10-20 응답 적격성·연결 분리 — 후보 기각·QA 계약 수정

시작 `c947358` clean. 실제 GPU의 동일116개 개발 문항은 기존104/116·누락8·연결3, 단일 분리85/116·누락25·연결5, 두 단계82/116·누락30·연결3이었다. 오개입/추론 오류0, Worker88/88/96. 첫 적격성에서 no를 잘못 골랐고 모든 분리 구조/모델 용량의 한계로 일반화하지 않는다. 후보를 튜닝·채택하지 않았고 새 고정40개/실제 생성 확대는 하지 않았다. 원본/코드/해시는 `local_data/social-factorization-20261020/`에 보존했다.

종료 처리를 하지 않아도 침묵만 맞으면 통과할 수 있는 QA 빈틈을 확인해 expected_evidence/expected_state_effect의 실제 마지막 Trace 검증과 contract_failures를 추가했다. 관련8개 OK, 전체 **606개 OK84.697초** (`PYTHONPATH=src;tests;tools`, `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`). 후보 비공개 계약5개 OK는 제품 회귀 수에 합산하지 않는다. src/운영 파일4개 해시 보존·GPU 종료1KiB/2MiB/Worker0. Portable 실제manifest/src 비교는83대84파일·누락1·차이4, 소스HEAD 필드 없음. 재빌드하지 않고 갱신 절차를 정리했다. [최신 상세](SOCIAL-EVIDENCE-QA.md). 실제 Discord·다른 앱 조작·다운로드·학습·시스템 변경 없음, 릴리즈 BLOCKED.

## 2026-10-20 현재 발언·역할 표현 비교 — 후보 기각

시작 `763a544` clean. 현재 발언을 역할별 이력의 마지막 user로 분리하는 후보를 실제 기존 Gemma4 no-LoRA·NF4 한 모델에서 비교했다. 새 고정32건28/32→32/32, 개발36건33/36→35/36이나, 넓은 재사용116건은104/116→106/116·오개입0→1·연결3→8로 악화돼 철회했다. 이전32 재검도 누락 대신 연결1건이 남았다. 좁은 점수만으로 채택하지 않았다. 종료 상태1건의 과거 영구 종료 기대/현재 휴지 계약 차이도 숨기지 않고 원본 실패를 보존했다.

후보 연결 검사66개 OK 후 후보 코드·검사를 비공개 사본으로 보존하고 실행 변경을 철회했다. 복원된 전체 소스 SHA-256 일치와 전체602개 OK75.907초를 확인했다. 명령은 `PYTHONPATH=src;tests;tools`, `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`. 합성 GPU/실제 생성과 자원·운영 파일 해시는 `local_data/speech-roles-20261020/`, 공개 비식별 결과는 [현재 발언·역할 QA](SPEECH-ROLE-QA.md). 운영 파일4/4 보존·GPU 종료 Worker0. 실제 Discord·다른 앱 입력·모델 다운로드·시스템 설정 변경 없음. Portable 재빌드 없음, 정식 릴리즈 BLOCKED. 다음은 응답 자격과 연결 근거 분리 대안의 비용/품질 비교다.

## 2026-10-20 대화 근거 감사 — 최신 / BLOCKED

시작 `5de1c27` clean. 긴 보충 문맥에서도 실제 봇 답변·원본 reply를 제한된 창과 토큰 축약에 보존하고, 마지막 수신자를 보존된 실제 reply 부모에서 구한다. 짧은 정정·전달문 실패에는 정보가 이미 충분했으며 그 의미 판단 문제를 해결했다고 주장하지 않는다.

사전 고정한 새32문항은 기존/최종 모두29/32(오개입0·누락3·연결0), Worker28회였다. 두 후보 탐색은 같은 입력의 개발36에서 엄격33/36→28/36·백엔드 예외7건으로 기각했고, 효과 없던 호칭 검색 가설도 철회했다. 그룹 종료·다른 수신자 pending 보존은 실제 GPU3회로 PASS, 실제 생성→모의 전송2/2. 오류 침묵을 정답으로 세던 QA 집계도 수정했다. 최종 전체602개 OK74.830초, 운영 파일 해시4/4 일치. 상세·한계는 [대화 근거 QA](SOCIAL-EVIDENCE-QA.md). 실제 Discord/데스크톱 조작은 없고 Portable은 최신 소스 미반영이다. 정식 릴리즈 BLOCKED를 유지한다.


## 2026-10-20 사회적 후속 대화·종료 상태 — 최신 / BLOCKED

시작 `dae8473` clean. 실제 봇 답변을 후보 검색 근거에 포함하고, 모델의 종료 추정은 작업 취소·즉시 확정 종료와 분리했다. 단순 전달문은 임의의 첫 peer에 연결하지 않는다. 명시적 종료·타인 청자·범위·원본 reply 검증은 유지한다.

최종 전체 회귀590개 OK73.203초. 새 미사용 GPU12문항11/12(오개입0·누락1·연결0), 종료 연쇄1/2→2/2, 실제 생성→모의 송신6/6. 개발 자료의 누락을 줄인 의미 계획 후보는 새24문항에서22/24→21/24로 악화되어 철회했다. 실험의 점수·속도를 최종 제품 성과로 주장하지 않는다. 최종 유지 코드의 GPU 결과·실패 단계·미검증 범위는 [후속 대화 QA](PRAGMATIC-CONTINUITY-QA.md)를 따른다. 실제 Discord·데스크톱 입력·운영 자료 변경은 없으며 기존 Portable은 이번 수정 미반영이다. 의미적 누락·연결 오류가 남아 정식 릴리즈는 BLOCKED다.


## 2026-10-20 입력·인터랙션 정비 — 최신 UI / 전체 릴리즈 BLOCKED

시작 d7490b1 clean. 표현 고급 설정의 4개 수치는 슬라이더/값/의미, 잡담 길이·비속어는 실제 정책에 맞는 2개 선택 그룹으로 바꿨다. 캐릭터/친밀도/기억·호칭/만료·알림/파일 작업의 유한 값도 명시적 컨트롤로 정리했다. hover·누름·포커스·선택·비활성·삭제·저장 중을 구분하고 실제 저장 실패 시 입력을 보존한다.

전체584 OK72.338초, 동적209 PASS(하위 HTTP0·소스 일치), 숨긴 Tk420조합 PASS. 전체 렌더 p50/p95 3.902/59.706→5.219/65.578ms로 추가 비용을 기록했고 속도 향상을 주장하지 않는다. hover는 이전/현재 항목만 칠해500회에서 재렌더/항목 누적0, p50/p95 0.033/0.040ms였다. 새 GPU/실제 Discord·사용자 데스크톱 입력은 없다. 기존 사회적 판단의 누락·연결 오류와 사용자 화면 미검증은 남아 정식 릴리즈 BLOCKED다.

Portable 번들 Python/실제 번들 UI에서도32검사 OK9.791초(자체 숨긴 Tk·임시 자료·모의 GPU/Gateway)를 확인했다. 실제 사용자 화면과 다른 Windows는 미검증이다.

[입력·상태 규칙](UI-COMPONENT-GUIDELINES.md) · [검증·실패·한계](UI-INTERACTION-GUIDE.md). 이전 수치와 실패 기록은 아래에 보존한다.

## 2026-10-20 정밀 판단·UI 동작 후속 — 최신 / BLOCKED

시작 `a7ae298`, 구현 `548d0c6`. 전체 **575검사 OK75.691초**, 숨긴 Tk 렌더420조합 및 엄격한 SDK HTTP mock 디스패치209건을 확인했다. 초기 검사 경계 누락은 성공 결과에서 폐기했다. [정밀 사회적 QA](PRECISION-SOCIAL-QA.md)와 [실제 UI 동작표](UI-ACTION-QA.md)를 현재 기준으로 삼으며, 아래 이전 차수의 수치는 당시 기록이다.

새32 최초24→25/32, 별도 새16 직접 관계9→13/16이다. 수정 후32 재검27/32는 독립 성능이 아니다. 누락·관계 오류가 남아 정식 릴리즈 **BLOCKED**다. [오프라인 사용자 확인](USER-MANUAL-QA.md)은 준비했지만 아직 사람이 수행하지 않았다. 실제 계정/Gateway/송신·다른 Windows·24시간·사람 말투 평가는 NOT VERIFIED다.

변경: response_plans/inference/runtime/social의 유한 계획·출처 후보·진단, desktop/desktop_ui/companion_ui의 Future 적용 결과·선택 문맥 보호·오류 재배치, user_check와 EchoMate-Check.vbs, 합성 UI/계약 회귀·SDK HTTP mock 도구. 실제 SQLite 잠금·요약 삭제/비부활·DPAPI 최초 설정·파일 I/O·취소·시작 연타를 검증했다.

실행: 전체 unittest574 OK61.334초, renderer420 PASS, dispatcher209 PASS(하위 HTTP0). 실제 GPU 관계/생성 A/B·공정 큐·모델 실패 복구·600.141초 혼합 운용 PASS는 각각 정밀 QA의 한정된 범위다. 허용되지 않은 가짜 토큰 인증2건과 일시적인 자체 창 표시라는 검사 실수를 기록·폐기하고 HTTP/Tk 차단을 보강했다. 운영4파일 hash는 보존 검사를 별도로 수행한다.


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


## 2026-10-20 최종 안정화 (시작 d7cf29a)

마감: **523회귀 OK58.467초**, 실제20분 혼합 운용1912 mock 답변·GPU10/10·worker0, source 및 Portable의 실제 shard 로딩/모델 선택·미리보기 PASS. 최종 shard peak12.92GiB(최초13.01), 원본31.35GiB. 운영 자료 보존·독립 청자26/32로 **릴리즈 BLOCKED**. 실제 Discord/다른 Windows/Maple/24시간/사람 말투 평가는 NOT VERIFIED. 상세·소스/패키지·Git 마감은 STABILIZATION-QA를 우선한다.

변경 파일: runtime/desktop/distribution_check/model_registry/loader_memory/inference/social/character_profiles/desktop_ui, prepare_sharded_model/verify_loader_memory/verify_resumed_release_gpu/verify_stability_soak/build_portable와 관련 회귀·문서. 재현: PYTHONPATH=src;tests;tools, `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`; GPU는 `tools/verify_resumed_release_gpu.py --capacity --fairness --soak-seconds 1200 --output <새 local_data 경로>`, native 로더는 `tools/verify_loader_memory.py --mode full --model-path <검증한 shard 폴더> --output <새 local_data JSON>`. 실제 Discord 접속 없이 현재 호스트에서만 수행했다.

Git/main clean0/0·506회귀 OK60.676초를 다시 확인했다. social 문법의 타인/불확실 청자와 출력 허가 모순을 제거하고 legacy acknowledgement 침묵 정규화는 보존했다. 후보 지침/act-first는 품질 실패로 미채택했다. 새 독립32는26/32·개발44는40/44로 BLOCKED를 유지한다.

model_registry/loader_memory/inference와 공식 shard 복제·계측 도구: 원본677 tensor를 hash/shape 검증한12 shard 복사본을 별도 local_data에 만들고 원본과 cold process A/B로 private peak31.35→13.01GiB·두 출력 일치를 확인했다. 단일 원본 guard는 유지하고 측정 config/버전의 shard profile만 별도 reserve를 적용한다. 시스템 설정·다른 앱·운영 모델 선택은 변경하지 않았다.

character_profiles/desktop_ui의 여섯 표현 축을 다섯 구간으로 세분화했다. verify_stability_soak/verify_resumed_release_gpu는 혼합 SQLite/공정 큐/실제 원본 reply·중복/삭제 veto/재시작·sparse GPU20분 검증을 기록한다. build_portable은 큰 파일 전체 read 대신 streaming SHA-256을 사용하고 검증한 bundle/src 내부 생성 bytecode만 정리한다. 실패 로그와 상세 실행/최종 회귀·Portable/보존/commit은 [안정화 QA](STABILIZATION-QA.md)에 누적한다.


## 2026-10-19 메모리 확보 후 실제 GPU·Portable 재개

- 시작/원격263eedc clean0/0, 사용자 추가 자원 확보 후 실제 GPU 검증. 초기 로딩PASS 뒤 host 여유 감소로 admission 차단1회, 기준을 낮추지 않고 자원 확보 후 재개했다. Discord 로그인/송신/명령 sync/사용자 데스크톱 조작 없음.
- `inference.py`, `loader_memory.py`, `processes.py`: pre-open 약9.03GiB/peak31.35GiB와 반복32.6GiB 계측에 따라 준비 reserve10GiB+margin2GiB·최초 private 기준 재사용. 생성 후 cuBLAS workspace의 segment pin을 재현/수정, 실제 모델 생성·전환 해제 reserved 약6.99GiB→2MiB. 미초기화 CUDA cleanup 없음·원래 로딩 오류 보존/안전 비활성.
- `naming.py`, `social.py`: 현재 간접 발화 요청과 과거 보고 구분, 명사화 인용은 semantic 후보, 바깥 질문·평가 의도 지침. 현재 요청을 보고로 오인한 전체9요청6/9 문제는 수정 후9/9. 최종 새12문항11/12, 이전44 개발40/44로 품질 차단 유지. 추가 합성 예시 후보는 최소 human 수신자 probe 실패로 폐기, 최종 미사용8은 평가하지 않았다.
- `verify_resumed_release_gpu.py`: 한 resident 모델·원본/trace/source hash 보존, 캐릭터12생성, 같은 GPU·디코딩의 교차 bare/disabled-PEFT A/B18성공/출력9쌍 동일, 워밍업6제외. p50 4.047/4.234초·p95 4.715/4.797초(n9씩), 통계적 큰 개선 주장 없음. 공정 큐 네 요청 순서/원본/중복0, 실제 reload/실패복구·생성 중 모델 전환901/902 보존 통과.
- `distribution_check.py`: opt-in 실제 GPU 로컬 미리보기, Discord 강제 차단·격리 저장소. 검사 자체의 중복 lease/초기 비동기 속성 조회 오류를 고친 v3에서 번들 Python·시스템Python 없는PATH·숨긴Tk·모델발견/실제로드/미리보기/DPAPI/저장·복원·종료 통과, 관계·기억·알림 생성 없음.
- 새 메모리/정리/보고문 회귀 포함 전체 **506 OK55.636초** (`PYTHONPATH=src;tests;tools`, `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`). 중간502는 test fixture 가변 참조 오류로 실패했으며 수정 후 전체 재실행했다. 모든 실패 로그는 보존했다.
- 비공개 `local_data/resumed-qa-20261019/`에 측정/응답/프로토콜/봉인/캐릭터 블라인드(사람평가 미실시) 보존. 공개에는 비식별 요약만 기록. [전체 재개 QA](RESUMED-GPU-QA.md). 사회적 정확도·다른Windows/드라이버·장시간·실제Discord 미검증으로 정식 릴리즈 BLOCKED. 최종 package/source/hash·운영 자료 보존·공개 감사/commit은 마감 절에 이어 기록한다.

### 2026-10-20 마감

구현 cbe2c77。공개20파일 staged diff/check·실제 bootstrap 민감리터럴·개인경로·문서링크 검사0, 운영4파일hash동일·평가봉인4개유효. `build_portable.py --refresh-public` 재빌드 후 bundle/src의 생성 bytecode만 절대경로를 확인해 정리, 4.59GiB/24,756파일. source81/docs42 byte/공개manifest hash일치·가중치/DB/운영설정0건. 이후 문서 commit은 git log 확인. 원본/수정/실패/폐기 후보/평가 scope를 RESUMED-GPU-QA에 누적했다.

별도 미사용8을 고정 commit으로 마지막 검사하려 했으나 host commit 여유27.07GiB<34.28GiB로 로딩 전 차단, GPU 시작/재시도 없음. 12문항은 이후 개발 기준에 편입되어 최종 일반화 점수로 쓰지 않는다. 완료한 GPU/Portable 성공과 남은 독립8/사람/다른Windows/장시간 미검증을 구분했다. 정식 릴리즈는 계속 BLOCKED다.

## 2026-10-19 f1c0ec6 후속 — Windows1455 원인·메모리 안전성

- 시작/원격 main f1c0ec6 clean0/0, 기존490 전체 OK61.101초. 기존 성공 소스와 실패 traceback/설치 라이브러리·공식 소스를 비교했다.
- 변경: `loader_memory.py`, `processes.py`, `inference.py`, `desktop.py`, `verify_loader_memory.py`, `test_loader_memory.py` 및 최신 인수인계/상태/배포·성능/LOADER-MEMORY-QA 문서. Windows system commit과 process private/peak·RAM을 분리, import/processor 후 admission 재검사, 실패 frame 참조·processor/cache 해제, 사전 차단 cleanup에서 Torch 미import 유지, GUI 숫자 안내.
- Safetensors0.8.0 pread도 선행 전체 COW 매핑. 실제 CPU 합성64/256MiB 각2회·512MiB1회 순간 commit64.13/256.50/513.01MiB; mmap256MiB513.01MiB. import private no-LoRA1432.73MiB vs PEFT 포함1546.89MiB. NF4/전체 모델 피크와 구분했다.
- 실제 원본22.28GiB / guard24.28GiB / 당시 여유13.37GiB로 차단, GPU 모델 load 시도0회. 기존 +2GiB를 보장값으로 쓰지 않고 유지했다. 사용자 프로그램 종료/page file 변경/모델 변경·삭제/Discord 접속 없음.
- 테스트: PYTHONPATH=src;tests에서 `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`, 최종 **500 OK60.204초**. 새10검사는 counter·admission·재검사·실패 수명·안전 UI를 검증한다. CPU 계측은 `tools/verify_loader_memory.py`, 비공개 `local_data/loader-qa-20261019/`에 원본 보존.
- 미확인: 새 기본 GPU 로딩·실제 초기화/NF4/해제 피크·독립 청자/캐릭터/전체 E2E/실GPU 공정 큐·Portable 실모델·다른 Windows·실제 Discord. 릴리즈 BLOCKED 유지.
- 마감 구현338af1f: `tools/build_portable.py --refresh-public --output dist/EchoMate-rc-model-character` 성공, 4.59GiB/24,767파일. source81파일 byte/manifest 일치, 가중치/사용자DB/설정0건. 번들Python·격리PATH/새DATA_HOME/빈HFcache에서 `-m echomate_bot.distribution_check` 실제 숨긴Tk/최초설정/DPAPI/프로필저장/설정복원/종료 성공, Discordfalse·weightsfalse. 운영4파일 hash동일·미사용독립20seal유효. 공개12파일 staged diff/check·실제민감리터럴·개인경로·문서링크 검사0건. 상세 로그/보고서 비공개 보존, 이후 문서 commit은 git log 확인.

## 2026-10-19 모델·캐릭터 분리 및 일반 배포 — 최신 기준

시작 HEAD/원격5249fd2·clean을 확인했다. 공식 기본 Gemma4 12B 하나와 독립 캐릭터를 사용하며 기존 persona/adult 고정 UI·기본 LoRA 의존을 제거한다. 이전 서명 설정은 검증 후 base로 읽고 기존 가중치/자료는 삭제하지 않는다. 성인 유머는 별도 기본OFF 정책이다. 로컬 모델/HF 캐시 탐색·호환성 검사·전환/복구, 프로필 서명 저장·편집·미리보기, GUI 첫 설정/Windows DPAPI와 Portable 런타임을 구현했다. 기존 개인정보 동의/기억/관계/요약/알림/검색/공정 큐/Unicode 반응/원본 reply를 유지한다.

청자 무공백 호격·2인칭/맞장구를 분리한 GPU 개발 재검45/46, 오개입1·누락0이었다. 추가 제외 근거를 검증기에 넣었지만 공식 no-LoRA 로더의 독립20문항은 Windows commit 부족1455로 실행을 마치지 못했다. 실제 캐릭터 생성/전체 지연 A/B·깨끗한 Windows VM·실제 Discord는 미검증이며 전체 릴리즈는 **BLOCKED**다. 이전 세 모델 QA와 숫자를 최신 구조의 성공으로 재사용하지 않는다. 사용자 데스크톱/실제 Discord 접속을 수행하지 않았다.

[모델](MODEL-REGISTRY.md) · [캐릭터](CHARACTER-PROFILES.md) · [설치](USER-INSTALLATION.md) · [배포 QA·실패·마감](DISTRIBUTION-QA.md) · [전체 지연](PERFORMANCE-PIPELINE.md). 아래 이전 차수보다 이 절을 우선한다.

구현 커밋826a816, 시작5249fd2. 공개66파일·staged diff/민감 리터럴/개인 경로/문서 링크 검사0건, 원격main 충돌0/0 확인 후 커밋했다. 비공개 자료와 Portable 런타임은 Git에 포함하지 않았다. 최종 인수인계 문서 커밋은 git log로 확인한다.

변경 파일은 settings/inference/character/adult_policy/model_registry/character_profiles/paths/onboarding/desktop/UI/processes/runtime/social/members/telemetry와 공개 샘플·Portable 빌더·관련 회귀다. 최종 전체490 OK58.325초. GPU 개발46문항45/46 이후 별도20독립평가는 Windows1455로 시작 실패했다. resource commit 사전 차단을 추가하고 실행 중인 다른 앱을 종료하지 않았다. 세 고정 모델 회귀 행렬은 기본 모델+서로 다른 세 캐릭터로 바꿨고 구형 슬롯은 서명 마이그레이션 검사에만 남긴다. 캐릭터12/성능A/B9는 준비만 했다. Portable 라이브러리 폴더 누락은 수정 후 격리 import와 실제 Controller 최초 설정·저장·종료·복원 통과, 깨끗한 VM/실제 Discord는 미검증이다. MIT는 사용자 허가로 적용했고 제3자 라이선스는 유지한다. 운영4파일·가중치를 보존하고 릴리즈 차단을 유지한다.

## 2026-10-19 사회적 청자·대화 상대 — 현재 기준

기준3cc53eb/main과 원격 일치/초기 clean을 확인했다. sessions/runtime의 최신 세션 선택·새 화자 단일 후보·bare-call 합류·verify_target group 재승격을 추적했다. social.py와 공통 assess_social, 후보 임시 상태/확정 상대/사람 간 순서·완료 sibling 정리, 실제 멘션의 청자/화제 분리, 보고된 호출 보류, 구조화 진단·UI를 구현했다. 변경 모듈은 runtime/sessions/inference/members/naming/telemetry/desktop/desktop_ui, 관련 테스트와 verify_social_gpu/SDK mock 프로토콜이다. 기존 기능과 운영4파일을 보존한다. 검사 명령/개발 실패/미사용 결과/실제 GPU/미검증/최종 커밋은 SOCIAL-ROUTING-QA에 누적한다.

[설계와 경계](SOCIAL-ROUTING.md) · [검증·실패·재현](SOCIAL-ROUTING-QA.md). 아래 이전 차수 기록보다 이 절을 우선한다.

최종: 전체475 OK54.507초. 실제 SDK HTTP mock의 공백 없는 멘션→후속→reaction과 pending 인간 보충 발언의 기존 봇 요청 취소/병합 방지를 추가했다. 실제 GPU 공정 큐 세 모드3/3, 결합 회귀128/132. 마지막 소형 현재 상대 분류는46문항 오개입6으로 거부했고 원본 경로로 복원했다. 복원 통제46문항40/46(오개입3/누락3)으로 잔여 결함을 확인해 릴리즈 PASS를 차단했다. 새 통제10문항의 실패4건을 숨기지 않으며 무공백 타인 호칭·이름+2인칭·맞장구·간접 평가를 다음 과제로 남긴다. 실패 로그·운영 자료 모두 보존, 실서버 연결 없음.

공개30파일 감사 후 구현 커밋6dd3ba2를 생성했다. 민감 경로/실제 토큰·개인 ID 리터럴/개인 절대 경로/깨진 문서 링크0, 운영4파일 hash동일. 후속 문서 커밋은 최신 git log를 확인한다. 릴리즈 차단을 유지하며 GitHub에는 공개 변경만 반영한다.

## 2026-10-19 — 후속 릴리즈 안정화·무상한·공개 검색·다중 턴 요약

구현 커밋 ab22ec3, 기준0ddb4df. 공개50파일/민감정보 검토0건, 최종452 OK46.601초. 후속 인수인계 문서 커밋은 git log로 확인한다.

기준0ddb4df/main과 원격 일치/초기 clean을 확인했다. 최신 사용자 지시로 AGENTS의 과거 일일 상한 요구보다 무상한을 우선하고 Ledger/설정/Runtime/UI/도구/테스트에서 차단 조건을 제거했다. 이전 운영 기록은 지우지 않았다.

주요 변경 파일: ledger/settings/runtime/telemetry, safe_web/web_research/inference/structured, summary_store/summarization/companion_store/privacy/consent_ui, reaction_requests/discord_app/output_policy/processes, desktop/desktop_ui/companion_ui. 테스트는 test_followup_release 및 기존 개인정보/SDK/병렬/UI/자원 회귀를 갱신했다. 실제 GPU 재현 도구 verify_followup_gpu/verify_followup_runtime_gpu를 추가했다. 마지막 감사에서 자동 요약의 동일 버전 반복·봇 OFF 생성·백그라운드 자원 실패 안전 정지 누락을 수정했고 해당14검사 OK8.673초였다. 구체 원인·실패·비교 수치와 전체 수정 범위는 [후속 QA](FOLLOWUP-RELEASE-QA.md)에 기록한다.

명령: PYTHONPATH=src;tests 후 `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`. 기준436 OK, 최종452 OK46.601초. 신규 GPU 독립18/18·버스트18/18·기존 실패12/12·저장 요약 조회6/6, 모델 전환/실패 복귀/알림 병행 확인. 숨긴 Tk3스케일/임시 SQLite/HTTP·Discord SDK mock으로 검사했다. 공개 위키 조회2.703초 성공, 뉴스2회 시간 초과를 숨기지 않는다. 초기 내부 JSON 파싱/분류/주제어 실패와 첫 독립 backend 실패도 비공개 로그로 보존했다.

운영 설정/bootstrap/companion/sent4파일을 해시로 보존하고 모델·어댑터·서명 키·개인 자료를 수정하지 않았다. 실제 Discord 접속/명령 동기화/송신·사용자 컴퓨터 조작 없음. 전체 실사용 NOT VERIFIED이며 새 가중치 선정/학습은 하지 않았다. 최종 전체 검사·공개 staged 검토·커밋은 후속 QA 마지막 절에 기록한다.

최신 구현·검증 커밋: **99761cc**. 후속 인수인계 문서 커밋은 `git log -1 --oneline`로 확인한다.

## 2026-10-19 — 단일 개인정보 동의·Windows 관리 통합·릴리즈 후보 감사

공개47파일 staged 검토: 비공개 추적0·실제 bootstrap 민감 리터럴0·개인 경로0·문서 상대 링크 오류0, `git diff --cached --check` 통과. 운영4파일 해시 동일. 최신 구현 커밋은 후속 문서 기록을 참고한다.

시작 main/d1b2d6a, fetch한 origin/main과0/0, 기존 미커밋 변경 없음. README/정의/구조/인수인계/로그·기존 구현/비공개 진단을 확인했다. private 운영4파일의 작업 전후 SHA256 동일, 가중치/기존 실험은 보존했다. 실제 Discord 연결/송신/명령 동기화·사용자 화면 조작 없음.

변경: privacy/consent_ui 추가, CompanionStore 스키마5·독립 본인 동의/개인 발췌·철회/삭제/쓰기 경합 처리. discord_app 관리자 명령 제거와 단일 /동의/다음 연결 승인 동기화, sticker 송신/UI 제거, settings 서명 후 보존 마이그레이션. desktop/desktop_ui/companion_ui의 OFF 조회·동의 상태·조회 경합·작업 상세·한도/진단/캐시 관리·쉬운 한국어 안내. runtime/action/inference/character 공통 코드·URL 경계, reaction_requests의 실제 Unicode 실행·일시 실패 복구, 한도 사전 차단, 의미 라우터의 공유/타인 구분. scheduler/telemetry 실제 큐 상세. research는 기존 aiohttp를 사용하는 기본 OFF 공식 버전5주제 조회이며 범용 검색으로 주장하지 않는다. __main__의 잔존 /echo 안내 제거. 새 평가 도구 verify_release_gpu/verify_release_pipeline_gpu와 회귀 검사를 추가했다.

진단 근거: 운영 성공 전송100/한도100, 마지막 요청이 생성 후 rate veto였다. 임의 상한 해제/ledger 삭제 없이 GPU 이전 검사와 이유·사용량·소유자 앱 변경을 제공했다. 관계 DB의 구본인 동의0건도 확인해 UI 갱신 장애와 동의상 정상 침묵을 구분했다. 세부 개인정보 원문은 공개하지 않는다.

검증 명령: PYTHONPATH=src .venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q. 최종 tests-publish.log **436검사 OK39.186초**. GPU 연속18/18·중복0, 공통 실행18/18, 기존 실패 순서12/12. 독립 생성 old/new18쌍은 코드9→0, 제한된 개념 문자열6/6 양쪽, 새 정책은 일부 더 느려 엔진 개선으로 보고하지 않는다. 모의 API·격리 SQLite·숨긴 Tk DPI 및 실제 공개 공식 API5/5를 구별했다. 초기 실패/수정/수치/전체 재현은 RELEASE-QA 최신 절, 전체 기능 연결 감사는 RELEASE-CANDIDATE, 본인 안내는 PRIVACY-COMMANDS에 기록했다.

남음: 실제 명령 등록/삭제·원격 Discord 송수신/통신 장애·실제 사용자 Windows 조작·장시간 GPU/RAM·사람 블라인드 품질 미검증. 범용 검색/추상적 다자 요약 미구현. 전체 릴리즈는 NOT VERIFIED이며 새 학습/모델 승격은 없다. 공개 소스·비식별 문서만 검토 후 커밋한다. 원본은 local_data/release-qa-20261019/에 보관한다.

## 2026-10-19 — 서버 구성원 호칭·청자 근거 계층

구현·검증 커밋 **e5cf00f**. 공개26파일 staged 검사: 비공개 파일·실제 bootstrap 민감 값·개인 경로 포함0, 문서 상대 링크 오류0, diff check 통과. 후속 문서 커밋에 실제 구현 해시를 기록한다. 비공개 평가·DB·설정·어댑터는 제외했다.

기준5697cbd의 깨끗한 작업 트리에서 README/정의/구조/인수인계/로그와 기존 이름·라우팅·세션·Runtime·SDK·관계 저장소를 확인했다. 기존382검사 OK29.361초를 기준선으로 보존했다. 사용자 지시대로 실제 Discord 연결/송신/사용자 수동 QA는 하지 않았다.

변경 파일: members/member_aliases 추가, runtime/discord_app/dialogue_intent/companion_store/desktop/companion_ui 통합, 관련 SDK·호칭·저장소·UI 회귀, verify_members_gpu 평가 도구, MEMBER-ADDRESSING 및 관련 문서. 봇 이름 호출과 구성원 후보를 분리하고 실제 화자/청자/멘션/답장/참조 후보를 역할별로 전달한다. 생산 경로의 중복된 일반 호격 추측을 제거하고 기존 의미 모델을 필요한 곳에만 사용한다. 새로운 모델/경량 분류기/학습은 추가하지 않았다.

채널별 별명 후보와 ID 근거는 스키마4로 저장하고, 소유자가 기존 사람과 관계 화면에서 확인/수정/삭제한다. 본인 동의 없는 자동 축적/후보 자동 확정/추정 ID 기반 기억·친밀도·타인 알림은 하지 않는다. 제한 캐시·닉네임 갱신·삭제/편집 근거 철회·탈퇴/접근 검증·재시작 시 승인 별명 대상만 조회를 추가했다. 타인으로 대상이 바뀌면 활성 lease만 정리해 자연스러운 후속 문맥은 보존한다.

테스트: `PYTHONPATH=src .venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q` 최종407검사 OK30.964초(tests-publish.log; 이전 전체 회귀36.310초도 보존). 실제 discord.py 파서/SQLite/Windows 숨긴 Tk DPI 회귀를 포함하며 네트워크는 모의 경계다. 초기 조사 분리 결함과 검사 기대값 오류는 원인을 수정하고 실패 기록도 남겼다.

GPU: verify_members_gpu로 이전 Runtime/분류 프롬프트와 동일 가중치·합성 문맥·greedy를 교대 비교했다. 개발용12×3, 별도 독립12×3 모두 각9/12→12/12; 최종 타인 오인3→0/필요한7응답 누락0. 의미 호출9→6/텍스트 호출10→7이다. 프롬프트/출력 길이는 달라 생성 자체 속도 향상을 주장하지 않는다. verify_direct_bursts 최신18/18·중복0, 최종 코드의 타인 침묵/활성0/후속 복귀/다른 화자 호출12/12. 실제 GPU·모의 Discord이며 실제 API 성공이 아니다.

보존된 기존 무응답4단계의 실제 GPU 회귀도3모드12/12·원본 reply/공유 흐름 유지로 확인했다. 최종 연속성 GPU 소스 해시와 현재 bot 소스 차이0. v3 별명 테이블 부재→v4 생성/기억 보존의 엄밀한 추가 저장소5검사도 OK0.237초다.

비공개 `local_data/member-qa-20261019/`에 평가 원문·응답·소스 스냅샷·지연·DB 이행·운영 설정 해시 보존 결과를 둔다. 기존 운영 settings/bootstrap 해시가 유지됨을 확인했다. 가중치·기존 비공개 데이터/실험은 덮어쓰지 않았다. 공개 집계/한계는 RELEASE-QA와 MEMBER-ADDRESSING에 기록했다. 다음 우선순위는 모호한 호칭의 새 독립 사례와 제한된 실제 회원 이벤트 전달 검증이며, 현재 사용자 지시 없이 실서버 QA를 재개하지 않는다.


추가 짧은 반복 부하 검사: 실제 단일 ThreadPoolExecutor에 32.157초/115묶음/2300요청을 투입했다. 정상1955·의도취소345·예기치 않은 오류0, 최대 동시 워커1, 종료 후 실행/대기0·asyncio task 증가0이다. SDK/GPU/원격 서버는 사용하지 않은 큐·취소·종료 검사이며 장시간 RAM/GPU 누수나24시간 안정성을 입증하지 않는다. 원본 스크립트·결과는 private short_soak.py/short-soak.json에 보존했다.


구현·회귀/GPU·SDK 모의 검증 기록 커밋 **6b369e6**. 공개34파일 staged 검사: bootstrap 민감값·개인 경로·가중치/DB/데이터 파일 포함0, 문서 상대 링크 오류0, diff check 통과. 후속 문서 커밋에 구현 해시와 최신 모의 전용 범위를 기록한다.


## 2026-10-19 — 의미 중심 참여·명확한 호칭·기분 표현 개선

기능 구현·실제 GPU/모의 검증 커밋: **a854d0a**. 최신 인수인계 문서 커밋은 `git log -1 --oneline`로 확인한다.

[SEMANTIC-ROUTING](SEMANTIC-ROUTING.md)를 먼저 읽는다. 기준66d0b02. 실제 Discord 연결/송신은 하지 않으며 사용자 수동 QA를 요청하지 않는다. 기존 다중 대화·단일 GPU·친밀도·기억/알림·소유자 설정과 원본 reply는 유지한다.

올바른 호칭도 후보 판정 뒤 모델의 veto에 사라질 수 있고, 기존 후속/신규 화자 경로가 일부 문장부호·연결 표현에 의존함을 확인했다. 기존 진단으로 사용자 보고 당시 개별 메시지의 수신 여부는 확정하지 못했다. Gateway/Runtime 수신과 이름·후속·큐·생성·송신 이유를 원문 없이 분리하고 앱 진행 상황에 최근 판단을 표시한다.

등록된 명확한 호출은 결정적 초대로 처리한다. 나머지는 발화행위/대상/연결/반응 가치의 구조화 의미 판단으로 분리하고 실제 화자·답장 근거를 제공한다. 새로운 화자는 후보 비교 후 승인됐을 때만 실제 문맥을 합친다. 진행 중 요청은 보존/FIFO를 유지한다. 모든 앱 모드는 같은 런타임과 기본 모델 참여 판정을 쓴다.

기분은 프롬프트에 전달되던 기존 단순 지시를 첫 반응·어휘·문장 리듬으로 구체화했다. 기술 설명/민감한 상황에서는 연출보다 정보와 배려를 우선한다. 출력 채널 보호를 유지하며 알려진 채널 혼입/자모 표현은 최대 한 번만 새로 생성한다. 검사에 재실패한 답변은 보내지 않는다.

최종 단위/통합 회귀: **382검사 OK34.115초**, 명령 `PYTHONPATH=src .venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`(tests-final-4.log). 실제 SQLite·모의 SDK·숨긴 Tk DPI 회귀를 포함하며 실제 사용자 화면 조작은 하지 않았다.

실제 GPU: 단계4의20사례×3모드=60/60(새8표현을3모드 반복;24개 독립 문장이 아님), 문장부호 비교6쌍의 응답/침묵 일치. 이후 전체 발언 순서 재현에서3인칭 평가 누락을 추가 발견해 수정했고, 최종 audience 시험에서 장문 문맥→핀잔→새 참가자 호칭2회→평가12/12·원본 대상 오류0·공유 대화 ID 유지, 제3자 정보/인용/타인 멘션/종료 등의 분리6사례×3모드=18/18을 확인했다. 최종 코드의1/2/5초·큐 대기·보충/중복 GPU 회귀18/18, 중복 송신0이다. 원래 실패 당시 실제 Gateway 수신을 복구한 것은 아니다.

기분 비교는 동일 질문/가중치/greedy의7기분×3모드 old/new21쌍이다. 서로 다른 출력 수는 기본5→7/개인5→6/성인정책3→7, 유효 출력은 양쪽21/21. 채널 보호 후 재생성은 old1/new4회였다. 출력 차이는 기분의 정확한 전달/자연스러움이나 사람 평가를 뜻하지 않는다. 평온·신남·피곤함의 기술 설명은3모드9/9 정상 종료와 제한된 핵심 사실 문자열을 확인했다. 이 설명들은약10~35초로 여전히 느리며 속도 향상을 주장하지 않는다.

검증 원본은 local_data/semantic-qa-20261019/에만 보관한다. 초기 GPU1의 오판·채널 guard 중단, GPU2/3의 제3자/반응 오판, 첫 sequence의 마지막 평가 누락9/12도 보존한다. 처음 새 표현 집합의 실패를 보고 수정했으므로 그 집합은 개발 자료로 취급하며 최종 일반화 성능으로 보고하지 않는다. 전체 실사용 릴리즈/사람 블라인드 말투/장기 안정성은 **NOT VERIFIED**다. 실제 Discord 접속/송신·사용자 수동 QA·새 학습/모델 승격은 없다.

## 2026-10-19 — 사용자 조작 없는 모의 검증으로 범위 확정

사용자 최신 지시로 실제 Discord 테스트 채널·스레드 접속/송신과 사용자 수동 QA 요청을 중단하는 범위를 확정했다. 이번 다중 대화 작업의 실서버 송신은 없으며 과거 알림 성공 기록은 유지한다. 영향: test_discord_simulator.py, 인수인계/상태/Discord·앱·검증 문서. 과거 시험 안내보다 최신 범위를 우선하도록 표시했다.

실제 SDK 객체·메시지 파싱·답장 직렬화·운영 수신/런타임을 사용하고 HTTP 경계만 메모리로 대체했다. 외부 HTTP 요청을 AssertionError로 차단한다. 4검사 OK0.372초: 원본 reply·nonce·멘션 억제, 차단 채널/봇 입력, 스레드 권한·기본 스티커/반응, 삭제 원본/권한 실패. Windows 제한 환경의 첫 비동기 실행 대기는 해당 QA 프로세스만 종료하고 sdk-simulator-1/2 로그를 보존했다. 실제 Gateway/전달/서버 rate-limit 성공을 주장하지 않는다. 최종 전체 회귀는 `PYTHONPATH=src .venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`: 366검사 OK25.682초(final-tests-6.log).

## 2026-10-19 — 다중 대화 순차 구현 후 릴리즈 감사

기준 HEAD eaf1d1e, clean main, 기존 private1234파일 inventory를 기록하고 전체328검사 OK18.002초로 시작했다. 영향: 새 sessions/scheduler, runtime/inference/discord_app/DialogueState/desktop·진행 UI/routing, companion_store schema3·동의/UI안내, 테스트/실제 GPU QA 도구/문서.

1단계: 실제 reply/화자별 흐름 분리·보충 병합/독립 질문 FIFO·원본 고정 reply와 source hash, 공정한 GPU admission/aging/deadline/취소·용량/입력 수신 분리. 다른 대화의 취소·모델/재연결 보류 누락·일반 오류 전역 전파·Windows 조기 타이머 발언 누락을 수정했다. 사용자 최신 지시로 전역 자율 차단을 폐기하고 실제 활성/휴지·범위별 cooldown·부하 보정을 적용했다. 같은 작성자1/2/5초의 별개 요청은 보존하고 원문 완전 중복만 억제한다.

2단계: 요구 추적/24문서 내부링크 감사(깨진 상대링크0), SQLite flow 격리·기존 보존 schema3·다른 구성원 자동 동의, Gateway/모델 실패·원본 편집·권한·DB잠금/rollback/backup·종료와 숨긴 Tk100/125/150% QA. 초기 import 오류로 멈춘 이 저장소의 QA 프로세스만 정리했고 실패 로그/중단 GPU 버전을 보존했다. group-1 기본 후속 누락은 실제 공유 주제 근거 경로로 보강하고 다른값 group-2로 재시험했다.

명령 `$env:PYTHONPATH='src'`; `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`: 최종366검사 OK25.682초. GPU 도구 verify_parallel_gpu/verify_direct_bursts/verify_shared_group_gpu/verify_parallel_lifecycle_gpu는 한 번에 하나씩 실행했다. 중첩 기준9/18→변경18/18, 동일작성자18/18, 회상12/12, 공유후속 보강 후12대상/변경값 유지, 생성중 모델전환2원본 보존/실패후GPU복구/GPU중모의알림 약15ms. 단일 산술5쌍은 동일 프롬프트/답변이나 표본이 작고 이후 가드가 더해져 전체속도 개선을 확정하지 않는다.

실제 Discord 다중 계정은 사용자가 ‘이번에는 로컬 GPU·모의 검증만’을 선택해 미실행. 실제 Windows 사용자 조작/장시간 soak/실제망 장애·인적 품질 평가는 미확인. 전체릴리즈 NOT VERIFIED, 모델승격 보류. 컴퓨터 조작 자동화·클라우드·새학습·미디어 확장 없음. private 원본/스냅샷은 local_data/parallel-qa-20261019/. 단계별 실제 결과와 한계는 PARALLEL-CONVERSATIONS/RELEASE-QA 최신 절 참조.

## 2026-10-19 — 세 요구 순차 통합·GPU/실제 예약 검증

기준 f2539f9에서 비공개 기존1104파일 inventory를 보존하고 common character/context/relations → SQLite 선택 기억·UTC/서버 시간대 만료 → 본인 자연어 예약·독립 scheduler 순서로 구현했다. 영향: companion/store/ui/context/memory_context/routing/temporal 신규, runtime/discord_app/desktop/settings/naming/inference/DialogueState/telemetry 및 테스트·QA 도구·문서. 자동 기억 OFF, 소유자/HMAC/allowlist·이전 모델/미디어 제약 유지. 새 GPU 학습 없음.

개발 GPU 초기 실패 원인(첫 이름 호출 누락/일반 시간 질문 오예약/직접 공감 veto)을 분석 수정했다. Windows ledger connection 미종료와 예약 편집/선점 stale 본문 경쟁도 수정했다. 별도 트랜잭션 최신 row와 processing 편집 거부, 취소·원본 삭제 tombstone, opt-out cutoff, 만료 조회 배제/보존 정리를 구현했다.

검증 명령 `$env:PYTHONPATH='src'`; `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`: 최종328개 OK20.504초. 숨긴 Tk DPI1.33/2.0/최소창, 실제 SQLite200예약·재시작·DST·개인격리·삭제 부활, 모의 Discord 권한·nonce·본인 멘션·GPU busy 포함. 도구 verify_companion.py/verify_companion_release.py는 실제 GPU+합성 transport다. 개발72턴은 모든 턴 응답/완벽한20턴 기억을 보장하지 않았고 기본2/개인1개 추가 누락을 기록했다. 이름 독립36사례 기대 일치, 기억 재시작 A/B0/3→3/3. 경로 A/B는 출력 불일치로 속도 개선율 산출 금지.

사용자가 실제 테스트 채널1분 알림을 허용했다. live-1은 채널 불일치 수신0 후 정리, live-2에서 소유자 요청1/확인1/알림1·GPU 실행 중 예정+1.936초(API1.312초). 사용자가 한 번 도착을 확인했다. 다른 범위8이벤트 차단, 원래 설정 불변. QA 전용 signed 설정/DB만 쓰고 Gateway/GPU를 정리했다. 실제 Windows 사용자 조작/장시간 soak/사람 블라인드 말투 평가는 미완료이며 자동 화면 조작은 하지 않았다.

private 원본: local_data/companion-qa-20261019/. 상세 설계·표·한계·재현은 COMPANION-MEMORY-REMINDERS.md. 공개 파일만 staged 검토 후 커밋하며 모델 승격은 보류한다.

## 2026-10-19 — 세 모델 선택·공통 성별·지속 대화 QA

기능·평가 기록 커밋: `ad7b903`. 소스/합성 테스트/비식별 문서30개만 포함했다. staged 비공개 파일0, bootstrap 값/개인 경로/토큰 패턴 검출0. 기존701파일 모두 존재하고 runtime.lock 외700파일 크기/mtime를 보존했다. GPU 평가 프로세스 정상 종료도 확인했다.

자동 판정 추가 검토: 정상166응답 전부 만점이었으나, 같은 판정기의 사전 고정 대조6개 중 기대 기준 일치는3개(부정 대조 검출2/5)였다. 따라서 자동 점수는 모델 선정/품질 동등성 근거에서 제외한다. GGUF 승격은 보류하고 사람 블라인드 평가를 남긴다. 세부 결과는 ADULT-MODE-QA를 따른다.

- 의도: 기존 개인 LoRA/기본 모델을 보존하고 성인 유머 선택지와 공통 성별을 기존 Canvas 화면에 추가한다. GGUF 품질이 충분하지 않으면 기본 Gemma 4+정책을 유지하며 새 학습/멀티모달 확장은 하지 않는다.
- 변경: settings/character/adult_policy, desktop/desktop_ui, discord_app/runtime/inference/processes. 성별 서명 마이그레이션, 소유자 검사, 모델 준비 상태/취소/실패 시 이전 선택 유지, 전환 중 최신 이벤트 보류, 전송 직전 NSFW REST 재검사, 의미 기반 지속 대화를 구현했다. 시간은 문맥 보관에만 사용한다.
- 평가 도구: adult_qa_cases/evaluate_adult_models/gguf_probe/verify_adult_conversation/judge_adult_holdout. 새 합성60문항을 개발36/블라인드24로 분리하고 프롬프트 고정 후 독립 평가한다. 로컬 judge는 자동 판정이며 사람 승인이 아니다. 응답/키/원시 수치는 local_data 내부에만 저장한다.
- 후보: 공식 고정 revision과 파일 SHA 확인 후 Q4_K_M 두 파일 및 llama.cpp b11721 CUDA12.4 엔진만 다운로드했다. 카드 라이선스 표기가 다른 점을 기록했다. GGUF에 개인 PEFT를 결합하지 않고 GPU 모델은 순차 실행했다.
- 발견/수정: 초기 큰 컨텍스트의 VRAM 안전 중단, HTTP 스트림 연결 재사용 오류, mmap의 호스트 RAM 안전 중단, 평가 스냅샷/들여쓰기/표준 모듈 이름 충돌을 구분해 기록했다. load-mode none/no-host/작은 배치/EOF 소비 후 GGUF 개발144회 정상 종료했다. Transformers 종료 후 같은 프로세스의 잔여 CUDA 메모리도 확인해 엔진별 자식 프로세스/lease를 순차 실행하고 불완전 평가를 성공으로 종료하지 않게 했다. Tk 지연 GC의 다른 스레드 정리 크래시는 UI destroy와 테스트의 명시적 자원 해제로 수정했다. 실패/부분 결과와 기존 private701파일을 보존한다.
- 검증: PYTHONPATH=src, `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q` → 기준280개 OK, 변경 후290개 OK(12.762초), 엔진 프로세스 격리/실패 시 다음 모델 차단 회귀 포함 최종292개 OK(13.418초). gender/HMAC/소유자/연령 게이트/취소/모델 준비 실패/경쟁 상태/대화 지속/숨긴 Tk DPI 경계 회귀를 포함한다. 화면·마우스·키보드 자동 조작은 하지 않았다.
- GPU 상세 결과·한계·선정 근거는 [ADULT-MODE-QA](ADULT-MODE-QA.md)의 최신 절을 따른다. 동일768 토큰 평가와 초기192/384 토큰 개발 결과를 합쳐 순위를 매기지 않는다. GGUF 속도는 NF4와 엔진·양자화도 달라 가중치 효과만으로 해석하지 않는다.
- 미확인: 사용자가 성인 연령 제한 테스트 채널이 없다고 답해 이번 범위는 GPU·모의 이벤트까지 진행한다. 실제 사용자 Windows 화면 상호작용, 새 코드의 실제 Discord 송수신, 사람 블라인드 평가, 장시간 soak, GGUF 생산 hot-swap. 단위/합성/GPU 시험만으로 실사용 품질을 승인하지 않는다.

## 2026-10-19 — 시작·응답 중 콘솔 깜빡임 수정

- 시작 Git clean/9cce121. 응답 중 주기적인 nvidia-smi 상태 조회가 pythonw에서 자식 콘솔을 생성할 수 있음을 확인했다. stdout 수집만으로 창이 숨겨지지 않던 경로다.
- 변경: processes.background_options의 Windows CREATE_NO_WINDOW를 inference.health와 초기 setup의 whoami/icacls에 적용. 조회 timeout/실패 전파/온도·VRAM·RAM 보호 검사는 유지했다. 개인정보를 담을 수 있는 stderr는 직접 콘솔에 내보내지 않는다.
- EchoMate.vbs 추가: 개인 경로/키 없이 저장소 기준 pythonw 직접 실행, 창 표시0, cmd/PowerShell 미사용. /check는 앱/대화상자를 열지 않는 WSH 검증. .cmd는 호환 유지하며 배치 자체의 첫 콘솔을 피하려면 vbs로 시작하도록 README/앱/테스트/인수인계/상태/아키텍처/RELEASE-QA 문서 갱신.
- 검증: `PYTHONPATH=src`, `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q` **280개 OK(8.445초)**. 실제 Windows Python 자식 GetConsoleWindow=0와 출력 수집 확인, 실제 cscript VBS /check 종료0, GPU 과열·조회 timeout 회귀 통과. `LocalBackend.health()` 실제 GPU 조회 OK. compileall/diff --check 통과. private 로그 local_data/release-qa-20261019/tests-console-final.log와 console-health.log.
- 미확인: 사용자가 기존 앱을 닫고 새 vbs로 시작했을 때 실제 화면의 깜빡임이 사라졌는지의 수동 관찰. 화면·마우스·키보드 자동 조작과 실제 Discord 송신/추가 학습은 하지 않았다. 토큰/모델/개인 설정 변경 없음.

> 최신 사용자 설정: 컴퓨터 화면·마우스·키보드 자동 조작을 사용하지 않는다. 전역 권한을 변경한 것이 아니며 파일 수정·명령 기반 검증만 이어간다.

## 2026-10-19 — 릴리즈 계측·종료 정리·활동 목록·서버별 호칭

- 보존: 시작 HEAD fdf4c46/clean. 기존 private684파일 size/mtime 보존 목록과 기준260테스트 OK(7.269초)를 local_data/release-qa-20261019에 기록. 이전 미커밋 안정화 변경은 덮어쓰지 않고 이어 작업했다. 실제 모델/체크포인트/서명 설정을 새 값으로 임의 변경하지 않았다.
- 수정 파일: telemetry/inference/runtime/discord_app/desktop/desktop_ui/__main__/settings/character 및 새 naming.py. 원문 없는 단계 계측과 숫자 진단, executor context 전파, 저장 실패와 무관한 종료 정리, lifecycle 직렬화, 단일 scope 저장, 미저장 초안/키보드/드래그/배치, 실행 중 활동 목록 필터와 전체 보기, 소유자의 서버별 이름 및 자기 닉네임 동기화, 호격 후보 후 의미 판단을 구현했다.
- GPU: verify_release_performance.py, 상황별 warmup1 + A/B각5회(총22) 완료. TF32 이득 없어 미적용. 잡담 A/B p50 4.968/5.141, 기술36.204/36.282초. 모델 학습/승격/시각 실험 활성화 없음. TTFT는 host callback 근사, Windows monotonic 해상도 한계 명시. 개인 생성은 공개하지 않음.
- 회귀: 267개 OK(안정화 단계), 호칭/격리/차단/상속 필터/닉네임 mock 추가 후274개 OK(7.662초). 명령 `$env:PYTHONPATH='src'; .venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`, compileall. 테스트 수를 실사용 품질로 간주하지 않는다.
- 실제 UI: computer-use로 창 열기/선택/미저장 표시/성격 화면 관찰. 물리 Escape 중단 보고로 종료/나머지 조작 미완료, 재시도도 중단됨. 이후 최신 이름/필터는 합성 Tk 테스트만 확인. 서버/채널 이름이 담긴 스크린샷은 공개하지 않았다.
- 미확인: 새 닉네임/호칭의 실제 Discord 송수신, 다중 화자 품질, 실제 비소유자 계정/기본 스티커/재연결/장시간 QA. RELEASE-QA에 분리 기록. 앱 재시작과 TESTING-DISCORD-APP의 최신 절을 사용자 검증 순서로 제공한다.
- 문서: AI-HANDOFF/CURRENT-STATUS/ARCHITECTURE/DISCORD-BOT/DESKTOP-UI/TESTING-DISCORD-APP/ML-EXPERIMENTS/RELEASE-QA에 현재 구현·검증 경계를 기록. 최신 커밋은 git log -1로 확인한다.

## 2026-10-19 — 누적 변경 문서 반영·커밋 재확인

- 요청: 지금까지의 변경사항을 문서에도 반영하고 커밋.
- 확인: 구현 `76b2ccc`/`f366aab`와 누적 문서 `eac9463`이 이미 로컬에 보존돼 있었고 작업 트리는 깨끗했다. 다크 GUI/5개 화면, 등록 미디어 제거, 기본 에셋 전용·실험 분석 OFF, 문맥 지속/원래 질문 reply, 지연 측정·실패 실험, 실제 QA 미확인 범위와 사용자 테스트 안내가 기록돼 있음을 확인했다.
- 보완: README에서 사용자 테스트/인수인계 진입 경로를 연결하고, PROJECT-DEFINITION의 과거 상태를 별도 이력으로 표시했다. AI-HANDOFF에 구현·문서 기준 커밋과 읽는 순서를 명시했다. 과거 계획과 현재 구현을 혼동하지 않게 했다.
- 검증: 문서 내부 링크와 `git diff --check`, 변경 파일 범위 및 private 자료 미추적 여부 확인. 문서만 수정했으므로 GPU/Discord/전체 테스트는 재실행하지 않았다. 기존 최종260개 통과(9.002초) 기록을 그대로 유지한다. 앱은 실행하지 않았으며 비공개 자료/토큰/가중치를 커밋하거나 GitHub로 push하지 않는다.

## 2026-10-19 — 최종 UX 문구·실행 흐름·직접 답장 지연 개선

- 사용자가 앱을 닫았다고 알리며 직관적인 문구/UX로 정리, 응답 지연 개선 포함 작업 종료 후 테스트 방법 제공. 이후 앱을 다시 열지 않았다. 최신 소스 커밋 `f366aab`(앞선 다크/에셋 제거 `76b2ccc`), 문서 최종 커밋은 `git log -1`로 확인하며 GitHub push는 없다.
- UI: 대화할 곳/응답 방식/성격과 기분/진행 상황/실험 기능 5화면. 채널 미선택 저장 차단, 준비 중/실행 중 중복 시작 차단, 봇 켜기와 응답 허용 연결, 일시정지와 종료 구분, 초/분/% 단위, 긴 목록 이름 말줄임, 빈 상태와 저장 실패 안내, 부모 채널에서만 스레드 적용, 반응 기능 OFF 안내. Canvas 버튼 Tab/Enter 포커스도 보완했다.
- 문맥/지연: 실제 이력에 연결된 Discord 봇 답장도 명시적 요청으로 처리해 끼어들기 판단을 생략한다. 나머지 무멘션 대화는 의미 판단 유지. 작성 중 표시는 별도 비동기 작업으로 갱신하고 완료/취소 시 종료한다. 부분 텍스트는 전송하지 않는다. GUI의 응답 일시정지는 현재 생성만 취소하고 기존 문맥은 보존하며 멈춘 동안 메시지는 받지 않는다. 봇 끄기는 모델/연결/이력을 정리하고 enabled=false를 저장한다.
- 실제 GPU: gpu-explicit-reply-2의 합성 멘션6.593초/직접 후속 답장3.969초, 각1호출/모의 TEXT1건. 앞선ID1은 합성 후속 시각을 실제 봇 답변보다 과거로 지정해 후속이 ingest에서 거절된 도구 오류였다. 0초를 개선으로 세지 않고 파일을 보존한 뒤 올바른 시간 순서/seed2026의 새ID2로 재시험했다. 단일 짧은 문항이며 실제 Discord 지연/일반 품질 보장은 아니다.
- 검증: 전체260개 OK(9.002초), 5화면 렌더링/설정/재개 시 중복 모델 방지/종료 저장/직접 답장/입력 표시 수명/원래 reply 대상/기존 회귀 포함. 최신 명령은 `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q`, 로그는 local_data/discord-integration-20261019/ux-tests-release.log. compileall도 실행했다. GPU/실제 네트워크/합성 테스트를 구분한다.
- 인수인계: TESTING-DISCORD-APP에 실행·멘션·무멘션·지연 원래 질문 reply·기본 에셋·실험 OFF/ON·중지·미허용 채널 검증 순서를 작성했다. AI-HANDOFF/CURRENT-STATUS/ARCHITECTURE/DISCORD-BOT/DESKTOP-UI/ML-EXPERIMENTS/README를 갱신한다. 새 UI 사용자 조작, 실제 최신 typing/reply/기본 스티커 송신 및 장기 QA는 남아 있다. 기존 rank8-60 잠정 모델 보존, 추가 학습/운영 승격/외부 클라우드/유료 API 없음.

## 2026-10-19 — 최신 사용자 변경: 다크 UI·기본 에셋 전용·원래 질문 답장

- 요청: 등록 미디어 제거, 커스텀/기타 이미지 분석은 실험 옵션 하나로 기본 OFF, 정상 인식/송신은 Unicode/Discord 기본 스티커, 초대 서버 채널·스레드 목록 UI, 직접 그린 세련된 다크 스타일, 추가 지연 개선, 늦은 응답의 원래 질문 reply.
- 구현: `desktop_ui.py` Canvas 목록/선택/스크롤/버튼/토글/칩과 4개 페이지. 모델 로딩 전 REST 메타데이터 조회, 초대 서버 전체 표시/활성 스레드/Ctrl 다중 선택/독립 채팅·반응 규칙. 기존 컨트롤 UI는 교체했다. Obsidian/LM Studio 공식 안내의 사이드바·로딩 상태 구분을 참고하고 자산/코드/앱을 복제·설치하지 않았다(DESKTOP-UI 참조).
- 제거: media.py와 media_add/media 명령 및 파일 송신 경로 삭제. 구 MEDIA/TEXT_MEDIA 제안은 최종 검증에서 거절한다. 기존 private 파일은 보존했다. 관련 폐기 기능 테스트를 제거/거절 회귀로 대체했으며 원래 217개 테스트는 유지한다. 공식 StandardSticker만 전송, 커스텀 반응 금지, 실험 분석 ON도 송신을 확대하지 않는다. HMAC 인증 후 asset_policy=2 마이그레이션으로 과거 vision=true를 계승하지 않는다.
- 속도: 명시적 멘션의 끼어들기 판단을 생략해 TEXT 1회 생성. 무멘션 의미 판단/안전 실행기는 유지한다. GPU fast-3 잡담 6.125초/1호출, 기술 후속37.891초/2호출. 앞선 단일 출력과 달라 보편 개선/품질 향상으로 선언하지 않는다. 긴 출력 지연은 남아 있다. CPU thread8/4 교차 생성14.359/14.500/14.438/14.468초(모두86토큰)로 이득 없어 변경하지 않았다.
- 답장: 원래 미응답 멘션 ID와 최신 문맥 이벤트 ID를 분리한다. SDK fetch_message/reply 대상은 원래 ID, 취소·중복 예약은 최신 상태로 검증한다. 텍스트가 항상 reply이므로 지연 시에도 대상이 연결된다. 원래 대상 삭제 시 안전 실패한다.
- 검증: 전체259개 OK(7.035초), compileall. Canvas 합성 창 시각/선택·저장/소유자·범위/마이그레이션/제거 명령/기본 에셋 제한/원래 reply 대상 회귀. 공식 Bot REST로14팩/362기본 스티커, 초대2서버의57채널(음성/카테고리 포함 raw 수)/36활성 스레드 메타데이터 조회 확인. 실제 본문 수집/송신 없이 수행했다. 최신 다크 앱은 GPU 미로딩/봇 정지 상태로 열었다. 새 UI 사용자 조작과 새 실제 답장·기본 스티커 송신은 미확인이다.
- 산출물/보호: local_data/discord-integration-20261019의 fast-3/threads-1/테스트/메타데이터 QA/합성 UI 확인 파일. 실제 토큰/owner/guild ID와 공개 대상 대조, private 파일 Git 미추적 확인 후 소스·비식별 문서만 로컬 커밋. GitHub push 없음. 상세 모델 품질 승격 없음/추가 학습0단계. 후속은 AI-HANDOFF 첫 절과 DESKTOP-UI/DISCORD-BOT을 읽는다.

## 2026-10-19 — 사용자 지연 지적 대응: Windows GUI와 문맥 지속

- 요청: 느린 응답 개선, 채팅/이모지의 활동 서버·채널·스레드와 기분/활동 빈도를 GUI로 관리, 처리 상태 표시, 멘션 없는 참여·지속.
- 보존: 기존 로컬 수정/217개 private 실험 파일과 어댑터/평가를 덮어쓰지 않았다. 모델 학습/승격 없음. 기존 설정 서명을 검증 후 읽고, 기존 mention/reaction/silent/autonomous 범위는 명시적 GUI 저장 전 그대로 유지한다.
- 변경: `desktop.py`, `instance.py`, `EchoMate.cmd`, GUI 시작 스크립트, `settings.py` 선택적 독립 반응 범위, `inference.py` compact 참여+지속 판단, `runtime.py` TEXT planner 생략/단계 상태/완료 시간/후속 2초 간격, `character.py` 상황별 길이 지침. 실제 발언/이벤트 메타데이터 분리와 embed 억제/프레임 디코드 offloop 등 앞선 미커밋 수정도 보존했다. `test_bot_desktop.py`, 통합 테스트와 `verify_bot_latency.py` 추가.
- 검증: `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests -q` 258개 OK(9.471초); `compileall` 성공. Tk 위젯·범위 저장·비허용 서버/설정 거절·중복 프로세스 잠금, 합성 창 캡처 후 시각 확인. 합성 GPU에서 이미지 32.7→20.7초, 잡담 10.985→5.859초, 기술 후속 84.437→79.500초. 개념 질문 중복 억제 별도 지침은 28.797초. 표본/출력/지침 차이를 ML-EXPERIMENTS에 명시했으며 보편 성능/품질 향상으로 선언하지 않는다.
- 실제 Discord: 이전 세션 TEXT 6건/REACTION 1건 성공. 해당 세션을 안전 종료/GPU 해제 후 GUI를 열어 기존 허용 테스트 서버 Gateway 연결 확인. 자동 범위 확대 없음. 새 GUI 조작과 무멘션 대화의 실사용 결과는 사용자 확인 대기이며 모의 테스트로 대신하지 않는다.
- 비공개 산출물: `local_data/discord-integration-20261019/`의 fast GPU 결과/소스 사본/테스트 로그/합성 GUI 캡처. 운영 GUI 상태는 `local_data/bot/desktop-status.json`, 성능은 종료 시 `desktop-performance.json`. 토큰/본문/에셋 원문을 공개 문서에 포함하지 않는다.
- 미확인: 반복 성능 분포·사람의 말투/정확성 평가, 등록 미디어/GIF/서버 에셋 실사용 전체 QA, 비소유자 실계정/네트워크 재연결/장시간 운영. 모델은 기존 rank8-60 잠정 후보 유지. 소스·비식별 문서만 로컬 커밋하며 push하지 않는다.

## 2026-10-18 — Phase 0 초기화
- 요청: GitHub `RuinaR/EchoMate` 초기 구조, 프로젝트 정의, AI 작업 지침, 인수인계 문서화.
- 결정: 최초 대상 사용자 본인/단일 화자 메시지. 로컬 Ollama. 지정 스레드. 확장형 페르소나.
- 추가: README, AGENTS, docs/PROJECT-DEFINITION, ARCHITECTURE, DATA-GOVERNANCE, ROADMAP, AI-HANDOFF, WORKLOG, .gitignore, 소스/테스트 placeholder.
- 테스트: 없음 (실행 코드 미구현).
- 남은 이슈: Discord 데이터 패키지 미수령, 사용 권한 검토, Discord 봇 앱/토큰 미생성, 성능 검증 미수행.

## 2026-10-18 — 참고 프로젝트 조사 및 설계 확장
- 검토: Disclone, discord-inference-bot, Archimedes, discord-persona-bot, MarkBot, DiscordChatExporter 공개 문서.
- 생성: docs/REFERENCE-PROJECTS.md, docs/DATA-ACQUISITION-OPTIONS.md.
- 수정: ROADMAP, AI-HANDOFF에 스트리밍·메모리 TTL·성능 통계·관리자 제어·데이터 import 검증·원자적 페르소나 전환·자율 응답 취소 설계 반영.
- 규정: 사용자 토큰 자동화·무허가 AI 학습을 구현하지 않음.
- 검증: 문서 기반 검토만 수행. 실제 소스 코드 통합·봇 동작 테스트는 미실시.

## 2026-10-18 — 관계별 개인화 추가 및 DiscordChatExporter 경로 검토
- 관계별 스타일 설정 요구에 따라 docs/RELATIONSHIP-PERSONALIZATION.md 추가, 프로젝트 정의/로드맵/인수인계 갱신.
- Discord 공식 self-bot 금지, 개발자 정책 §16 관계 프로파일링 금지와 §21 AI 학습 허가 요건 재확인.
- 권장: 공식 봇 계정 사용, 수동 관계 선호 설정. 별도 일반 계정으로 제한을 우회하는 방식은 지원하지 않음.
- 검증: 문서 갱신만 완료; 실행 코드와 실제 데이터 기반 테스트 미실시.

## 2026-10-18 — 관계 자동 분석 요청·공식 Bot 경로 검증
- 사용자 요구: 수동 친밀도 지정 대신 실제 대화의 호칭/농담/분위기에서 자연스럽게 반응 차별화.
- 설계 선택: 실시간 대화에 기반한 임시 상대별 톤 적응은 지원, Discord API 수집 데이터 기반 장기 관계 프로파일링은 금지 대상이므로 보류.
- 공식 Developer Portal bot 사용. DiscordChatExporter의 bot-token 내보내기 가능성과 AI 훈련 허가 조건을 구분.
- 문서 검토/수정만 수행, 구현·실행 검증 없음.

## 2026-10-18 — 단일 페르소나 중심 재정의
- 사용자 요청: 본인 페르소나 하나만 개발하고 Discord 웹에서 과거 대화 내역 전체 확보 가능성 검토.
- 공식 Discord 검색은 작성자 필터 제공, 다만 일괄 내보내기 불가. self-bot 및 비공식 웹 자동 수집 정책 위험을 분명히 함.
- 새 문서 docs/SINGLE-PERSONA-PLAN.md; 프로젝트 정의/로드맵/인수인계의 최신 우선순위 변경.
- 구현된 데이터 추출기 없음. 원본 메시지 수집·AI 학습 미수행.

## 2026-10-18 — 운영 중 지속 적응 설계
- 추가 요청: 봇이 미래 대화에서 상대별 반응·친밀도를 조금씩 갱신했으면 함.
- 신규 설계 docs/CONTINUOUS-ADAPTATION.md 작성 및 관련 문서 갱신.
- 분리: 실시간 대화 톤(임시) / 명시적 본인 피드백으로 누적되는 스타일(지속) / 사용자 직접 선호. API 메시지에 기반한 장기 관계 프로파일링은 구현하지 않음.
- 실제 코드/테스트 없음.

## 2026-10-18 — DiscordChatExporter GUI 사용 설명
- Windows v2.48.0의 로그인 화면 기준으로 공식 봇 토큰 생성·초대·최소 권한·스레드 표시·JSON 출력 절차 정리.
- docs/DISCORDCHATEXPORTER-GUIDE.md 생성.
- 보안: 토큰/GitHub 업로드 금지, 개인 계정 self-bot 금지, AI 모델 학습과 단순 백업 구분.
- 실제 내보내기·코드 빌드·학습 테스트 미실시.

## 2026-10-18 — Bot/Studio 프로세스 분리 결정
- 사용자: EchoMate Bot을 표시 이름/프로필 사진·모델 로드·대화 빈도/대상 채널/스레드 기능으로 축소하고, DiscordChatExporter 파일을 이용하는 오프라인 학습 도구와 분리 요청.
- docs/DEPLOYMENT-SEPARATION.md 신규, PROJECT-DEFINITION/ARCHITECTURE/ROADMAP/AI-HANDOFF 정합성 갱신.
- 모델 아티팩트 형식, 캐시/검증/롤백, 봇 allowlist와 학습 분리 경계 명시.
- 설계만 완료. Discord/학습 동작 테스트 미수행.

## 2026-10-18 — 채널별 데이터/최근 가중치/미디어 출력 제한
- 사용자 확인으로 입력 2개 JSON이 각각 단일 채널의 기록임을 문서화.
- 신규 문서 docs/TEMPORAL-STYLE-AND-MEDIA.md: 최근 스타일 가중치 반감기 후보, 파일별 발화 묶기 주의, 기본 Unicode 이모지 허용/커스텀 이모지·GIF·스티커 금지.
- 원본 JSON/GitHub 업로드 없음. 구현 및 학습 시험 미실시.

## 2026-10-18 — EchoMate Studio 분석기 첫 구현
- 코드: src/echomate_studio/__init__.py, src/echomate_studio/analyze.py
- 테스트: tests/test_analyze.py (합성 데이터 5건 단위 테스트 통과), 본인 제공 대용량 JSON 2개 분석 성공
- 문서: docs/STUDIO-QUICKSTART.md
- 입력: 각 파일은 단일 채널, 총 304,997건, 파일 내부 메시지 ID 중복 0건.
- URL/멘션/커스텀 이모지 제거 후 텍스트 후보 270,989건.
- 기능은 개인정보를 제외한 *통계 분석*이며 모델 학습·RAG/QLoRA 구현 아님. Discord 정책상 학습 이용허가 판단도 하지 않음.
- 주의: 메모리 내 전체 JSON 적재 방식은 향후 streaming으로 최적화 예정. 출처에 채널 ID 및 UTC 오프셋이 없어 임의 추정 금지.

## 2026-10-18 — Windows 검증 보고서 수령 및 문서 기준선 정리
- Windows PowerShell에서 Studio unittest 5개 모두 OK, 실제 두 JSON으로 `report.json` 생성 완료. 사용자가 보고서를 전달했고 필드·수치 확인.
- messages1: 원본 244,976 / 필터 후 223,737 / 발화 묶음 후보 114,009.
- messages2: 원본 60,021 / 필터 후 47,252 / 발화 묶음 후보 28,588.
- 합계: 원본 304,997 / 필터 후 270,989. 독립된 채널의 단일 화자 기록.
- README.md, PROJECT-DEFINITION.md, ROADMAP.md, AI-HANDOFF.md를 최신 방향으로 재작성. 이전 단일 페르소나 한정 등 상충하던 과거 결정을 현재 계획과 명확히 구분.
- 최신 기준: EchoMate Studio(오프라인 허가된 데이터 학습 및 버전별 아티팩트 제작) + EchoMate Bot(읽기 전용 모델 로드와 자율 대화). 첫 자료는 본인 것, 향후 적격 사용자별 페르소나 선택 가능.
- 정책: 백업/파일 소유와 AI 학습 사용 허가는 구분. 본인 데이터 패키지에 대한 무조건적 사용 허가를 주장하지 않음.
- 이번 변경은 **문서만 수정**. 추가 코드 기능 구현이나 모델 학습 테스트는 수행하지 않음.

## 2026-10-18 — 폐기 요구 문서 정리 및 N개 채널 파일 입력 명확화
- 과거 요구에만 해당하는 문서 5개 삭제: SINGLE-PERSONA-PLAN, RELATIONSHIP-PERSONALIZATION, CONTINUOUS-ADAPTATION, DATA-ACQUISITION-OPTIONS, DISCORDCHATEXPORTER-GUIDE.
- README, PROJECT-DEFINITION, ROADMAP, AI-HANDOFF, TEMPORAL-STYLE-AND-MEDIA, STUDIO-QUICKSTART, ARCHITECTURE, DATA-GOVERNANCE에서 기존 2개 고정으로 보일 수 있는 서술을 **JSON 1개 이상, 입력 개수 제한 없음, 파일 하나 = 채널 하나** 기준으로 변경.
- 기존 Studio CLI의 argparse `nargs="+"`가 임의 개수 입력을 이미 지원함을 확인. 입력 파일은 각각 별개 보고 항목이며 채널 간 발화 병합 기능 없음.
- 회귀 테스트 추가: `test_cli_accepts_three_independent_channel_files` (합성 채널 3개를 CLI에 전달하는 검증).
- **신규 테스트는 커밋되었으나 사용자 Windows 실행 확인 전**, 기존 5개 테스트의 통과와 구분한다.
- 과거 기록 자체는 Git 커밋 이력에 남을 수 있으나 현재 브랜치에서는 삭제됨.

## 2026-10-18 — JSON 파서 메모리 경량화
- 증분 JSON 배열 리더와 청크 단위 SHA-256 계산 도입. 콘텐츠 문자열 장기 저장 제거.
- 추가된 합성 테스트: 650 레코드 이상의 청크 경계, 잘못된 배열 문법/후행 데이터, 단일 채널 입력.
- 이전 6개 Windows 테스트 OK(사용자 제공), 신규 3개는 Windows QA 확인 전.
- 실제 JSON에서의 종전 수치와 신규 계산 수치를 비교하도록 `report-v2.json` 출력 절차 작성.
- 설계 제약: 메타데이터 정렬/ID 중복 검사 RAM 사용은 여전히 데이터 수에 비례.

## 2026-10-18 — 데이터 분석 회귀 완료 및 Ollama 기준선 코드
- 사용자 Windows 테스트 9개 전부 OK; 업로드 `report-v2.json`을 이전 `report.json`과 비교해 양쪽 파일 SHA-256/통계 값 모두 일치.
- 구현: 로컬 Ollama `/api/chat` 동기 클라이언트, 대화 문맥 프롬프트 빌더, AI 봇 고지, 커스텀 이모지/URL/이미지 마크다운 출력 필터, 대화 CLI.
- 신규 모킹 단위 테스트 6개 작성. 신규 테스트와 모델 실기기는 아직 미실행/검증 전. 학습 데이터의 이용 허가 여부와 분리해 진행.
- 새 문서 LOCAL-BASELINE.md; README/ROADMAP/HANDOFF 최신화.

## 2026-10-18 — 채팅 텍스트 소거 버그 해결 및 이모지 반응 정책 설계
- 사용자 검증: 기존 15개 테스트 중 2개 실패, 두 번의 Ollama 단발 생성 모두 출력 공백. 오류는 출력 공백 정규식이 정상 문자까지 제거하는 것이 직접 원인.
- `conversation.py`의 정규식 수정. `ollama_client.py` think=false 지정, 생성 토큰 예산 확대, 빈 모델 출력 진단 메시지 추가.
- 테스트: 정상 한국어/기본 이모지 보존, thinking-only 빈 응답 오류 검증 2개 추가.
- 자율 Discord 기본 이모지 반응 요구 반영: 반응 채널/스레드·확률·쿨다운 별도 설정, 자신·봇 메시지/opt-out 제외. 정책 모듈과 합성 단위 테스트 6개 추가.
- 이번 커밋의 신규 테스트는 Windows 실행 미검증. 봇 전송/Discord 반응 기능은 아직 없음.

## 2026-10-18 — Windows Ollama 실기기 통과 및 발언 판단 모듈
- 사용자 Windows 테스트 23개 모두 통과; 로컬 Ollama Qwen 9B 실제 자연어 답변 성공.
- 새 요구: 활발한 모드여도 민감하거나 끼어들 필요 없거나 장기간 조용한 대화에는 침묵.
- `participation.py`에서 권한/범위·옵트아웃·봇 제외·쿨다운·장시간 비활성·민감 분위기·기여도·개입 적절성·확률 순으로 평가하여 결정.
- 새 합성 테스트 7개 작성. **Windows 신규 테스트 미확인**; 실제 맥락 평가기/Discord Bot 구현된 것으로 간주 금지.

## 2026-10-18 — 단기 대화 연속성 상태 구현
- 사용자 Windows 테스트 30개 통과 보고.
- 채널/스레드별 대화 상태 및 TTL·화자·답장 메타데이터·스냅샷 버전 모듈 생성.
- 합성 테스트 5개 추가: 범위 격리, 중복/역순 제한, 최대수/시간 경계, stale 버전, 화자 및 답장 표현.
- 실제 Discord 봇 네트워크 통합과 대화 내용의 의미적 판단은 아직 미구현. 신규 단위 테스트 실기기 검증 필요.

## 2026-10-18 — 대화 기억 범위 확장
- 사용자 실기기 35개 unittest 모두 OK 확인.
- 사용자 RAM 32GB 환경에서 채널/스레드별 대화 버퍼 기본 500턴/24시간으로 상향. 실제 LLM 입력은 별도 문자 예산 16000으로 제한해 큰 메모리를 통째로 입력하지 않음.
- 100턴 보존/작은 프롬프트 버짓 및 잘못된 예산 입력 테스트 2건 추가.
- 주의: 문자 예산은 tokenizer의 토큰 한도 보증이 아니며 `num_ctx`/VRAM/요약·검색은 후속 작업. 신규 Windows 테스트 결과는 아직 없음.

## 2026-10-18 — 대화 흐름 평가기 추가
- 사용자 Windows 37개 테스트 OK.
- 현 대화 흐름을 Qwen 로컬 모델로 JSON 평가하는 `context_assessor.py` 구현. 실패한 평가는 침묵으로 처리.
- `autonomy_probe.py`(합성 대화 프로브) 및 파서/오류/전달 검증 단위 테스트 7개 추가.
- 실제 Discord 메시지, 실제 사람 대화에 대한 품질 검증/봇 연동은 아직 없음. Windows QA 요청 예정.

## 2026-10-18 — Ollama 실문맥 침묵 확인 및 발언 오케스트레이션
- 사용자 Windows unittest 44개 모두 OK.
- Qwen 실문맥 샘플(보스 모집→9시 가능→9시 확정): sensitive=false, useful=false, interrupt=false, 결과 no_useful_contribution 침묵.
- `turn_pipeline.py` 새 단일 턴 오케스트레이터 구현: 대화 스냅샷→활동 제어→맥락 평가→조건부 생성→stale 검사; 전송은 하지 않음.
- 6개 합성 테스트 작성(정상 생성, 민감 차단, 비활성, 동시 새 메시지, 예외, 빈 컨텍스트). 사용자 Windows 새 테스트 미확인.

## 2026-10-18 — Windows 50개 QA 통과, stale 회복 및 페르소나 우선 계획
- 사용자 Windows unittest 50개 모두 OK.
- 새 모듈 stale_recovery.py: 생성 중 새 메시지 발생 시 유한 재평가, 기본 최대 2회, 불확실 시 침묵; 합성 테스트 5건 추가(Windows 아직 미실행).
- 웹 검색은 필요한 경우만 opt-in 및 외부 전송 최소화. 페르소나 Style Profile v1부터 다음 작업 시작. docs/SEARCH-AND-PERSONA-PLAN.md 작성.
- QLoRA/모델 학습 및 Discord/Web 실제 연결은 이 변경에 포함되지 않음.

## 2026-10-18 — Style Profile v1 착수
- Windows 기존 55개 unittest 모두 OK.
- 로컬 JSON N개를 대상으로 최근 가중치 기반 말투 집계만 저장하는 Studio Style Profile 코드 추가.
- Qwen 단발 대화 probe에 선택적 스타일 프로필 입력 옵션 추가. 회귀 테스트 3건 작성, Windows 미검증.
- 원문 텍스트를 저장하거나 Ollama 학습에 넣는 기능 아님. 페르소나 품질 비교용 기준선.

## 2026-10-18 — 페르소나 출력 품질 실패 분석 및 교정
- 사용자 Windows unittest 58개 OK, Style Profile 생성 OK. 모델 답변: 존재하는 메이플스토리를 서비스 중단으로 오인, 비자연스러운 긴 존댓말 및 사용빈도에 안 맞는 이모지.
- 프롬프트를 짧은 한국어 채팅체·일상 초대 해석·검증 없는 서비스 상태 단정 금지 방향으로 수정. 스타일 안내는 평범한 반응 기본/이모지 드물게 사용.
- 지연 진단용 `chat_probe --timing` 추가; 프롬프트 회귀 테스트 1개 추가.
- Lost in the Middle 및 3개 유사 프로젝트 조사/현행 적용 여부 문서 작성. 근본적인 사실성/유사도 보장 전 실제 다중 사례 평가 필요.

- 후속 지연 개선 시도: chat single-turn `max_tokens=128`로 생성 상한 감소(기존 512). 실제 지연 개선/응답 부족 여부는 Windows 테스트 전이며, 필요하면 옵션화할 것.

## 2026-10-18 — 59개 QA 후 페르소나 응답 재검토
- Windows 59개 unittest 모두 OK. 기본 Qwen: `네, 지금 바로 시작할까? 준비됐으면 같이 들어올게.` (4.55초), 프로필 Qwen: `그거 지금 언제 하는 거야?` (0.23초).
- 둘 다 품질 불충분. 기본은 실제 게임 접속할 수 있는 듯한 표현, 프로필은 초대를 불필요하게 되묻는 반응. 워밍/캐시 차이로 4.55초와 0.23초를 모델/프롬프트 속도 우열로 판단 금지.
- `conversation.py`: 게임 접속 약속 금지, 이미 이해된 초대는 불필요하게 재질문 금지.
- `ab_probe.py`: 여러 질문, 번갈아 순서를 바꾸는 반복 A/B 응답/시간 측정과 로컬 JSON 리포트 생성. 사용자 Windows 시험 전.

## 2026-10-18 — 16회 A/B 품질 불안정 대응
- Windows 59개 테스트 OK. A/B 기본 중앙값 0.31초, 프로필 중앙값 0.29초, 응답 내용은 둘 다 불안정.
- 프롬프트에서 세부 금지사항 반복을 줄이고 현재 문맥·질문 의도·물리적 행동 불가·자연스러운 짧은 답변을 우선.
- 자동 QA 플래그 도구 및 모킹 불필요 순수 테스트 4개 추가. A/B JSON에 기계적 품질 경고 첨부.
- 개선된 응답의 실제 품질 및 테스트 63개는 사용자 PC 미검증.

## 2026-10-18 — Qwen/Gemma 모델 비교 환경
- 사용자 Windows에 `gemma3:12b` 설치 성공(7.3GB 모델 레이어 및 854MB 기타 레이어), 기존 Qwen 9B 유지.
- 모델별 말투 프롬프트 동일 조건 반복 교차 비교 CLI 및 합성 테스트 3개 작성. Windows 신규 테스트와 비교기 실제 실행 전.
- GPU 메모리 및 모델 로딩 교체가 지연에 영향을 줄 수 있으므로 중앙값 결과는 설명과 함께 판단 예정.

## 2026-10-18 — 모델 비교 및 실제 다중 턴 확인 기반
- 사용자 Windows 총 66개 테스트 OK, Gemma 12B 설치 후 로컬 20회 비교 성공.
- Gemma는 자연스러운 단문 답변 경향. 그러나 제공하지 않은 '저녁 7시' 반복 생성, 사실성 문제. Qwen3.5는 `ㅋㅋㅋㅋ`에 중국어로 응답하는 문제 확인.
- 기록 없는 약속을 창작하지 않고, 9시를 10시로 변경한 경우 최신 확정 내용을 반영하도록 프롬프트 보강.
- 순수 합성 다중 턴 평가 도구 및 4개 단위 테스트 구현. 신규 테스트 실기기 검증 전.

## 2026-10-18 — 다중 턴 대조 QA 결과와 프롬프트 오염 수정
- 사용자 Windows 70개 테스트 전부 통과; 현 대화 평가 8건에서 Gemma 무정보 시간 추측(10시), 9시 확정 사례 두 모델 모두 10시라고 잘못 응답.
- 시스템 프롬프트에 9→10시 예시가 들어 있던 것을 발견. 해당 하드코딩 예시가 모델의 답변에 섞일 가능성을 없애도록 일반적 변경 원칙으로 교체.
- 하드코딩된 시간 예시 재도입 방지 테스트 1개 추가. 신규 테스트 실기기 미검증.

## 2026-10-18 — 프롬프트 오염 제거 후 실측
- 사용자 Windows 71개 단위 테스트 OK. Gemma3 12B: 없는 시간 → 없음, 9시 약속 → 9시, 변경 → 10시. Qwen3.5 9B: 없는 시간 → 없음, 9시 약속 → 미결정(오답), 변경 → 10시.
- 자동 QA에서 정상 문구 `시간 정보가 없습니다`에 근거 없는 시간 플래그를 붙이는 오탐 확인. 정규식 정밀화, 회귀 테스트 추가. Windows 새 테스트 미실행.

## 2026-10-18 — 미세조정 범위 승인과 준비 단계
- 사용자 Windows 72개 전체 테스트 통과.
- 사용자 요청에 따라 향후 Gemma 3 QLoRA 미세조정 목표 추가. Discord 개인 데이터 패키지의 AI 학습 권한 불명확; API 데이터는 개발자 정책 §21 명시 허가 필요. 현재 권리 확인 전 실제 모델 학습/개별 발언 추출은 보류.
- 스트리밍 집계형 style_diagnostics(분포/종결 표현), 튜닝 준비상태 체크 CLI 및 4개 단위 테스트 작성. 새 테스트 미검증.

## 2026-10-18 — 76개 QA 성공, Ending 분석 결함 수정
- 사용자 76개 unittest OK, 원본 메시지 2개 스타일 심화 분석 및 QLoRA readiness 보고서 생성 확인.
- 길이 구간 12자 이하 86.94% (최근 가중치). Ending 지표 전부 0 → 소스 정규식의 백슬래시 중복 이스케이프 버그 확인, 수정 및 테스트 3건 추가. 수정 뒤 실제 Windows 통계는 미확인.
- readiness not_ready 유지, 원본 메시지 추출/모델 학습 미시작.

## 2026-10-18 — 원본 직접 분석 및 안전 QA
- 사용자 원본 2개 파일의 메타데이터를 로컬에서 확인: 244976 + 60021건, 각 파일 역시간순, 채널별만 취급. 빈 문자열 제외 228342 + 52788건; 반복문구가 많음.
- 학습 전 원본 문자열을 저장하지 않는 corpus_audit CLI / 합성 단위 테스트 3건 추가. 실데이터 자동 QA와 학습 권한 점검은 별도. 82개 테스트 예상, Windows 검증 전.

## 2026-10-18 — 멘션 테스트 오류 및 활성 대화 연속성
- Windows 91개 실행에서 7개 실패: mention 정규식의 백슬래시 이중 이스케이프. 수정.
- 자율 첫 참여와 활성 대화의 후속 응답 구분: 이어가기에는 확률/자율 쿨타임을 적용하지 않고 봇 대상·같은 주제·시간제한·안전 조건 확인.
- 신규 5개 테스트 작성. 예상 총 96개, 검증 전.

## 2026-10-18 — 96개 QA 중 3개 실패 수정
- 직접 봇 멘션 경로에서 자율 발언 유용성 조건을 적용해 오차단하던 버그 수정. 멘션은 응답 기회지만 위험 상황에서는 침묵.
- 활성 대화 만료 테스트의 expected reason을 cooldown→frequency_gate로 정정, 민감도 테스트는 실제 180초 이내로 입력 수정. 96개 재확인 필요.

## 2026-10-18 — Discord 대화 맥락 우선 연속성
- 사용자 96개 Windows 테스트 전부 통과.
- 활성 대화 기본 180초 타임아웃 제거(max_gap_seconds=None). 봇 대상·주제 연속성·실제 이전 참여 상태로 후속 답변 판단. 오랫동안 이어진 대화도 유지 가능, 몇 초 내 주제 전환은 연속성 해제.
- 연속성 회귀 1개 추가 및 기존 테스트 수정. 실환경 결과 미검증.

## 2026-10-18 — 대화 상대 판별 근거 강화
- 사용자 97개 Windows 테스트 모두 OK. 최근 시간 간격만으로는 이어가기 판단하지 않는 상태.
- 신규 engagement_evidence: 실제 `reply_to`가 봇 발언을 참조하는 경우만 이어가기 후보로 인정; 주제 연결성은 별도 입력 필요.
- 턴 파이프라인 연동과 테스트 6개 추가. Windows 103개 QA 필요.

## 2026-10-18 — 연속 대화 로컬 AI 판정 연결
- Windows 기존 103개 테스트 OK.
- 실제 bot reply 대상과 인간 답장의 주제 연속성을 로컬 Ollama JSON 분류로 평가하는 `topic_assessor.py` 추가; 잘못된 데이터/추론 장애 시 false.
- 기존 TurnPipeline에 선택적 assessor 함수 주입, 신규 회귀 테스트 6개. 총 109개 예상, 사용자 Windows QA 전.

## 2026-10-18 — 109 테스트 통과 및 Gemma 주제판정 실측 준비
- Windows 109개 unittest 모두 OK.
- 실제 Ollama를 대상으로 6가지 합성 답장/대화 전환 상황에서 topic_continues 성능을 측정하는 CLI와 2개 테스트 추가. 111개 Windows QA 및 `local_data/topic-qa.json` 실측 대기.

## 2026-10-18 — Windows 111/111 및 실제 Gemma 6/6
- 사용자가 111개 unittest OK와 실제 Ollama Gemma 3 12B topic_qa 6/6 정답 보고. 첫 호출 9.306초, 이후 대부분 약 0.25~0.29초. Discord 실환경 일반화 불확실.

## 2026-10-18 — 명시적 답장 없는 대화 연속성 판정
- 111개 Windows QA 및 Gemma 6/6 결과 확인. 로컬 모델 기반 implicit-address 검증 및 선택적 파이프라인 경로 구현. 두 개의 boolean 필드 모두 참이어야 대화 이어가기 가능. 회귀 테스트 4개 추가, 115개 예상.

## 2026-10-18 — 예약 멘션 로컬 코어 추가
- 사용자 114개 Windows 테스트 OK, 2시간 뒤 본인 @멘션 등 간단 부탁 자동처리 요구.
- 상대 시간 파싱/SQLite 저장·복구/중복 방지/claim 처리와 합성 테스트 4개 추가. 총 118개 예상, Windows 미검증. Discord 실제 발송 미연동.

## 2026-10-18 — 예약 관리 및 영속성 호환
- 사용자가 118 tests OK 보고 후 예약 취소/조회 확대 요구.
- 본인 소유 예약만 조회·취소하는 저장소 API, 한국어 예약 확인/선택취소/전부취소 명령 분기, 기존 sqlite CHECK 제약 마이그레이션 구현. 5개 회귀 테스트 추가, Windows 총 123개 재검증 필요.

## 2026-10-18 — 페르소나 학습 상태 재정리 / SQLite 잠금 QA
- 페르소나 학습은 아직 실제 파인튜닝 미시작. 기존 것은 원본 분석, 통계/프로필, 로컬 Gemma 추론 및 품질 평가. 이후 진행의 우선순위를 실제 가중치 학습 검증으로 재설정함.
- Windows 사용자 로그: 123 tests 중 1 ERROR, `old.db` 임시폴더 삭제시 WinError32; DB 연결을 contextlib.closing으로 명시 종료하도록 수정, 재검증 필요.

## 2026-10-18 — Windows 임시 SQLite 테스트 파일 잠금 수정
- Windows 123개 중 1 ERROR 재발. 테스트 자체의 sqlite3.connect 컨텍스트가 커넥션을 닫지 않아 old.db 임시 파일 삭제 실패. closing + 명시 commit으로 수정, 재검증 대기.

## 2026-10-18: 123 Windows QA green, persona preparation
- Added local aggregate-only eligibility audit and three unit tests. 126 total expected; fine-tuning not started.

## 2026-10-18 — 실제 페르소나 원본 분석 실측 반영
- 사용자 Windows 126개 unittest OK. 두 원본 합계 304,997개 중 추가 검수 후보 185,608개. 나머지 초단문 45,455, 동일 문자열 중복 36,275, 정규화 뒤 빈 메시지 34,008, 개인식별 의심 2,060, 반복 단일문자 1,587, 과도한 장문 4.
- 이 수치는 상호배타적 분류별 건수이지 미세조정 승인 수가 아니다. 개인정보 휴리스틱은 완전하지 않고 실제 QLoRA는 미시작.

## 2026-10-18
- Implemented reaction_reply.py for exclusive text, emoji, or silence decisions. Five offline tests added; Discord send integration pending.

## 2026-10-18 — 131 tests OK / QLoRA environment diagnostics
- Added read-only qlora_environment CLI with optional nvidia-smi and seven local package version checks. No weights download, no data extraction, no training. 3 tests added; expected 134 Windows tests.

## 2026-10-18 QLoRA GPU mock regression
- Windows 134 tests, 1 test_gpu_query failure checking last subprocess mock call timeout. Test now checks matching NVIDIA query call, rerun required.

## 2026-10-18 GPU QA
- Windows 134 tests OK. Local GPU: RTX 4070 Ti SUPER, 16GB, 12.7GB free. Python 3.10.11, torch CPU-only, 5 training packages absent. Isolated CUDA environment needed. No training yet.

## 2026-10-18 CUDA persona bootstrap
- User 134 Windows tests OK. GPU RTX 4070 Ti SUPER 16GB, torch CPU-only. Added isolated Python 3.10 environment PowerShell setup, CUDA tensor verification, optional training libraries, 3 tests. Expected 137 tests; user GPU result pending. No dataset or model weights involved.

## 2026-10-18 — CUDA GPU ready, toolchain pending
- Windows user reports 137 tests OK, isolated torch 2.9.1+cu128 runtime 12.8 RTX 4070 Ti SUPER CUDA calculation success. NumPy missing warning observed; optional install now includes NumPy and import smoke test. Actual QLoRA fine-tuning not started.

## 2026-10-18 — QLoRA library setup: quote bug fixed
- Training library installation and pip check succeeded. Final Python -c verification failed due to PowerShell quote parsing, NOT package installation. Replaced it with standalone import smoke test and three mock unit tests. New expected baseline 140.

## 2026-10-18 — QLoRA 140 QA pass and NF4 GPU probe
- Confirmed 140 Windows unit tests OK and isolated training stack imported fully. Added synthetic GPU NF4 Linear4bit operation probe with privacy-safe memory summary, 3 mocked unit tests. Next: 143 tests and native NF4 result, no model downloaded/trained.

## 2026-10-18 — NF4 actual GPU smoke QA
- User Windows 143 tests OK. Tiny synthetic bitsandbytes NF4 CUDA operation success on RTX 4070 Ti SUPER, max PyTorch allocated 0.08 MiB, free GPU memory after 15073 MiB. Not a full-model VRAM benchmark.

## 2026-10-18 — Real Gemma 3 4B loading probe prepared
- User confirmed 143 tests and real NF4 CUDA kernel OK, 15073 MiB GPU free after tiny probe. Added gated HF model NF4 load CLI opt-in only, 2 tests. Requires Google Gemma license acceptance; no weight downloaded/training executed.

## 2026-10-18 Gemma 4B gating debug
- 145 Windows tests OK. Local HF identity works but real NF4 Gemma load OSError; no proof of license grant/download. Added redacted failure category and removed torch_dtype deprecation warning, 2 new tests.

## 2026-10-18 Gemma 3 4B access diagnostic
- Windows 147 QA OK, full-model load OSError categorized as access denied; HF whoami succeeded. Added config.json-only auth probe and 2 tests, no weights download. Expected 149 Windows tests.

## 2026-10-18 Gemma config access OK
- User confirmed Windows 149 tests OK and google/gemma-3-4b-it config.json access succeeded. Real weight download/VRAM load still unverified; previously denied. Next is opt-in load retry.

## 2026-10-18 — Gemma 4B real NF4 load successful
- Two official gated model shards downloaded. Actual NF4 load OK, GPU memory delta 4266 MiB; free_after 10845 MiB; PyTorch peak 4100.9 MiB. Training step not tested yet.

## 2026-10-18 LoRA GPU optimizer dry-run
- Real Gemma3 4B NF4 load verified. Added opt-in synthetic-only, bounded LoRA backward/optimizer smoke test and 3 preflight tests. Expected 148 tests; device run pending.

## 2026-10-18 — First actual GPU LoRA optimizer step successful
- User 152 tests OK; synthetic Gemma3 4B NF4 forward/backward/AdamW succeeded. Trainable 1,611,776; seq len32; peak allocated 5660.7 MiB; free 8235 MiB. Loss=2.49 synthetic only. Explicit non-reentrant gradient checkpoint patch made; not rerun yet.

## 2026-10-18 — Synthetic LoRA repeat success
- Repeated private-data-free Gemma3 4B NF4 adapter training report status ok, peak allocation 5660.7 MiB; no real messages used. Console warning state unavailable from JSON.

## 2026-10-18 — Persona split audit and rights review
- After synthetic Gemma 3 4B QLoRA optimizer success, implemented local aggregate-only chronological train/validation and cross-split dedup analysis. Added 3 unit tests; expected 155. Current user personal Discord messages not trained. Official API content ML training requires Discord express permission; personal-data export route still requires independent review.

## 2026-10-18 — Real persona split audit QA
- 155 tests OK, 2 exports analyzed: eligible instances 221883; train unique 164662, val unique 20356, cross split overlap 2130, clean val unique 18226. No raw messages/hashes in reports. Rights/privacy gate remains open.

## 2026-10-18 — Persona research review
- Compared primary LoRA/QLoRA/DoRA papers, memorization risks, and TRL/PEFT examples. Created docs/PERSONA-RESEARCH.md with EchoMate-specific baselines and experiment gate. No private message uploads or model training.

## 2026-10-18 — Research-driven one-speaker dataset pipeline
- Implemented private, double-gated local JSONL export with chronological validation and exact cross-split dedup. Synthetic regression tests added (3). Previous 155 Windows OK; new 158 expected. Private corpus generation not executed.

## 2026-10-18 — Private local LoRA runner
- User 158 QA OK. Added offline Gemma3 4B NF4 LoRA training runner with explicit owner-data approval gate, private output paths, conservative step/token bounds and three unit tests. Expected 161 tests. No user data trained yet.

## 2026-10-18 — Fix Windows training-runner import syntax
- User reported 159 tests with one module-import SyntaxError (`tools/train_persona_lora.py` validation sample generator expression, unmatched `)`). Replaced with clear `for` loop and candidate length check. Source change committed, Windows rerun pending. Expected 161 passing cases with the three new tests imported.

## 2026-10-18 — Gemma4 12B model trial
- User requested Gemma4 12B. Verified official model identifier and approx 23.9 GB base weight download. Implemented opt-in config/CUDA probe and cached-weight synthetic NF4 LoRA smoke test. Four regression tests added. Previous 161 Windows OK; now expect 165; GPU not yet run. Existing Gemma3 working environment remains untouched.

## 2026-10-18 — Gemma4 library import blocker mitigation (Windows pending)
- Chosen model: google/gemma-4-12B-it, initial conversation-focused preference over base google/gemma-4-12B, subject to empirical comparison.
- Official model instructions use AutoModelForMultimodalLM. Transformers 4.57.6 Gemma4 direct-class import failed in user report; separate .venv-gemma4 setup uses Transformers >=5.10,<6 and existing CUDA torch baseline, without changing .venv-train.
- Updated probe and synthetic smoke loader; created tools/setup_gemma4_env.ps1, tests/test_gemma4_staged.py, docs/GEMMA4-SETUP.md; .gitignore protects separate environment.
- Confirmed user Windows previous 165 tests OK. Newly added 3 tests and modified probes NOT yet executed on RTX 4070 Ti SUPER. No 12B weight load/LoRA training proof; no owner-message training.
- Next: run isolated installation, unittest, small-file config preflight; review diagnostic JSON before opting into 23.9GB download, NF4 load and synthetic backward.

## 2026-10-18 — User Windows Gemma4 preflight verified (NO WEIGHTS YET)
- New independent .venv-gemma4 successfully installed: torch 2.9.1+cu128, transformers 5.20.1, accelerate 1.15.0, bitsandbytes 0.50.2, peft 0.21.2, huggingface_hub 2.2.0. pip check clean; CUDA True.
- User ran unittest discovery: **168 tests, all OK** (0.441s), including 3 new staged probe regression tests.
- User-provided JSON: model google/gemma-4-12B-it, status ready_for_optional_load, weight_download_allowed=false; config_model_type=gemma4_unified, config_access=ok; VRAM free_before=15111.0 MiB, total=16375.5 MiB.
- This verifies environment imports and small official config access only. No Gemma4 weights downloaded, NF4 loading measured, optimizer step or private owner-data tuning. Next: explicitly opt into weight download/NF4 measurement using --allow-download --allow-load, examine aggregate report; do not start actual persona tuning yet.

## 2026-10-18 — Gemma4 12B IT full weight NF4 GPU load VERIFIED
- User Windows PowerShell loaded official google/gemma-4-12B-it checkpoint (23.9GB reconstructed), 677/677 weights; probe status=ok, stage=nf4_load, CUDA=True on RTX 4070 Ti SUPER 16GB.
- Aggregate JSON: free_before_mib=15111.0, total_mib=16375.5, peak_allocated_mib=7381.7, free_after_mib=7621.0. These are actual NF4 load measurements; model successfully loaded, but no backward pass or optimizer update yet.
- Existing separate .venv-gemma4 with Transformers 5.20.1 succeeded; preserve .venv-train/Gemma3 4B.
- Next: cached-weight synthetic one-step LoRA test (seq_len32) under GPU monitoring, diagnose any OOM or multimodal PEFT incompatibility. Do not train private Discord data until separate corpus reviews.

## 2026-10-18 — Gemma4 12B IT synthetic QLoRA optimizer step VERIFIED on Windows
- User Windows executed `.venv-gemma4\\Scripts\\python.exe tools/smoke_gemma4_12b_lora.py --allow-synthetic-step --seq-len 32`; 677/677 weights loaded and command returned `Gemma4 12B LoRA: ok`.
- Local private-data-free JSON report: model google/gemma-4-12B-it, status=ok, synthetic_only=true, seq_len=32, trainable_params=2,596,864, loss=32.8467, peak_allocated_mib=11163.6, free_after_mib=2418.9.
- Confirms a single NF4 LoRA forward/loss/backward/AdamW optimizer step on RTX 4070 Ti SUPER 16GB. Loss is from repeated synthetic tokens and NOT a language quality score. Free-after is only ~2.36 GiB; longer sequences/batches, concurrent GPU apps and full corpus training remain unverified/OOM risks.
- Keep `.venv-train` and Gemma3 fallback unchanged. Next: conservative length32 multi-step synthetic GPU memory/stability, validate tokenizer/actual Gemma4 text-only label masking, ensure private reviewed corpus governance, then small approved offline training and held-out baseline/adapter evaluation. No personal Discord messages trained yet.

## 2026-10-18 — Gemma4 synthetic tokenizer / repeated-step QA implementation
- Preserved working Gemma3 and Gemma4 single-step results. Enhanced Gemma4 synthetic-only smoke with `--steps` (1..3), `--tokenizer-smoke` (fixed synthetic Korean words), finite loss checks, stage-coded failures and aggregate-only loss/memory metrics.
- Added tests/test_gemma4_extended_synthetic.py (3 regression tests). Previously user reported 168 tests OK. New suite and CUDA multi-step paths remain Windows UNVERIFIED. No private messages read or output.

## 2026-10-18 — Confirmed Windows Gemma4 synthetic Korean-tokenized 2-step test
- All 171 unit tests passed in 0.606s on Windows.
- Actual Gemma4 NF4 LoRA (seq32, 2 optimizer updates, official tokenizer with fixed synthetic Korean text): status OK, losses 22.9326 and 22.8617; 2,596,864 trainable; peak 11,163.6 MiB; free_after 2,344.8 MiB.
- No real Discord messages used or exported. Two consecutive synthetic updates demonstrate execution feasibility, not model quality or 16GB long-context fitness. Next: controlled Gemma4 trainer implementation, private corpus review, holdout, OOM safety.

## 2026-10-18 — Gemma4 private QLoRA runner implemented; execution pending
- Added opt-in local-only Gemma4 12B-it text language model fine-tuning tool, saved private adapter, one-sample validation before/after (not quality evaluation), strict private paths, model cache-only loading, triple approval gate, 1..10 steps at max64 tokens. Existing Gemma3 code unchanged.
- Three static/validation tests added. Previously reported 171 tests OK; expected 174 after code change. No actual Discord training, new GPU runner verification, or privacy clearance claimed.

## 2026-10-18 — User Windows 174 QA green; synthetic E2E trainer test prepared
- User reported `Ran 174 tests in 0.681s OK`. Confirms new Gemma4 trainer validation unit tests, NOT its GPU training/saving path.
- Added `tools/run_gemma4_synthetic_e2e.ps1` creating only fixed invented Korean single-speaker train/validation JSONL inside ignored local_data, then invoking the gated Gemma4 private trainer at 2 steps, seq32. The three flags in this script certify **only synthetic test inputs**, never user-data authorization. Script refuses to overwrite an existing adapter.
- Two no-GPU script tests added. Expected Windows unittest count now 176; script's GPU E2E and adapter saving NOT YET EXECUTED.

## 2026-10-18 — Windows PowerShell 5.1 encoding fix
- User Windows unittest 176/176 OK (0.397s). Synthetic E2E .ps1 stopped during parsing, before training; PowerShell displayed corrupted Korean source and unterminated quote. This is a script encoding defect, NOT evidence of a Gemma4 training/GPU failure.
- Changed tools/run_gemma4_synthetic_e2e.ps1 source to ASCII-only and reconstructs fixed synthetic Korean phrases from Base64 UTF-8 bytes. Generated JSONL remains UTF-8. No real owner messages used.
- Added regression test test_powershell_51_source_is_ascii; expected suite now 177 tests, NOT yet Windows verified. Retry the same E2E command. Old output directory may exist from script parse failure only if an earlier run created it; do not overwrite any existing adapter automatically.

## 2026-10-18 — Windows 177 tests and actual saved synthetic Gemma4 adapter
- 177 unit tests passed in 0.402s. Windows PowerShell ASCII source script ran end-to-end (previous encoding error resolved).
- Actual Gemma4 12B IT NF4 two-step private-free synthetic train and local adapter save completed; report: validation 23.6352 -> 23.6266, peak 11163.6 MiB, free 2454.3 MiB, 2,596,864 trainable params.
- Uploaded adapter header independently inspected: 176 F32 tensors / 2,596,864 elements / approx 10.4MB; adapter_config LoRA rank 4, q/v projections, correct base. Not yet reloaded/inferred on GPU; this is not personal training or quality proof.

## 2026-10-18 — Before owner-data training: adapter reload + corpus gates
- Implemented cached-only Gemma4 NF4 synthetic adapter reload comparison with explicit GPU flag; separate private JSONL exact-overlap/heuristic near-duplicate/identifier audit. Three mocked/static no-GPU tests added. All aggregate reports remain local_data; no messages or tokens in reports.
- Prior Windows suite: 177 OK and 2-step synthetic adapter save verified. New suite expected 180, GPU reload and real-corpus inspection are UNVERIFIED. A heuristic-clean corpus does not mean approved, legally cleared or safe to train.

## 2026-10-18 — Gemma4 adapter reload GPU QA green
- Windows 180 unit tests OK, 0.515s. Cached 677/677 base weights and saved synthetic rank4 LoRA adapter reloaded; GPU report status ok.
- On 2 fixed synthetic prompts, losses base-disabled 23.795/22.2657 vs adapter-on 23.7906/22.196. Free GPU memory after test 7585.0 MiB. These are synthetic-only loss probes, not owner style quality measurements.
- Completed technical synthetic train/save/reload milestone. Private owner Discord training not performed.

## 2026-10-18 — Corpus overwrite and near-duplicate protections
- Inspected current owner export split builder and corpus preflight. Hardened builder against overwriting nonempty existing output folder; extended heuristic prefix/suffix near overlap screening. Added 2 regression tests, expected Windows total 182, execution pending. Existing 180 tests and synthetic GPU adapter reloading already confirmed. No private corpus training run.

## 2026-10-18 — Global multi-file chronology defect fixed
- After user Windows 182/182 suite passed, reviewed approved raw owner exports privately (244976 + 60021, all timestamps). Combined 90th-percentile time cutoff was 2026-04-26 06:56:16 UTC. Dataset builder previously used independent per-file cutoffs; fixed to global UTC cutoff with one new synthetic test (expected 183 on Windows).
- Aggregate short-text bins: len<3 54927/14395; len3..7 113624/23460. Originals remain off GitHub. No private training or dataset export run. Global time split alone is not sufficient contextual privacy protection.

## 2026-10-18 — 183 Windows regression tests green
- User executed unittest suite following the global chronological split fix: **183 tests OK in 0.463s**. Confirms unit-level behavior, not a full private-data privacy clearance, corpus authorization, or live QLoRA training.

## 2026-10-18 — Two-character style preservation opt-in
- Extended local-only approved dataset builder to optionally retain two-character expressions (e.g. laughter reactions) while keeping global holdout duplicate protection. Default exclusion unchanged. One regression test added, expect Windows 184 tests. No owner-data training or corpus build.
- Follow-up required: short records may fail trainer >=8-token sampling; do not equate corpus retention with model learning.

## 2026-10-18 — Windows 184 tests successful
- User ran `python -m unittest discover -s tests -v`: 184 tests, 0.476s, OK. Includes new two-character expression retention/heldout synthetic unit test.
- This validates unit behavior only. Gemma4 current trainer still skips token sequences under 8 IDs; short-style corpus retention is not proof of short-expression learning. No original Discord messages trained or committed.

## 2026-10-18 — Short independent sample path
- Implemented explicit `--include-short-samples` in Gemma4 private trainer (min 3 token IDs rather than 8) to support short Discord writing style without artificially joining separate messages. Kept default behavior and privacy approval gates unchanged; new synthetic selection unit test. Previous Windows 184 pass; now expect 185, unverified.

## 2026-10-18 — Short-sample syntax failure corrected
- Windows log: failure to import `test_train_persona_gemma4` due to literal `\\n` in trainer source; 182 discovered tests, one import error, no GPU work. Fixed trainer Python syntax and malformed new JSONL fixture, added AST regression guard. Expected after fix: 186 tests, pending Windows run.

## 2026-10-18 — Gated first-persona QLoRA orchestration
- Implemented ASCII PowerShell 5.1 synthetic short-message GPU smoke with unique local output; separate real private training runner with mandatory rights/privacy/training confirmations and fail-closed overlap/PII preflight. Private JSONL must already exist and be human reviewed; no automatic original export conversion. 2 static regression tests added, expected 188 on Windows (not tested yet). Existing 186 passed. No private training run yet.

## 2026-10-18 — Short-example GPU synthetic integration green
- User Windows 188/188 unit tests OK, 0.425s. Actual Gemma4 12B IT synthetic short-sample QLoRA 2-step trained, saved rank4 q/v LoRA. Uploaded checkpoint header: 176 FP32 tensors, 2,596,864 weights (~10.4 MB), as expected.
- Report loss on SINGLE synthetic validation sample rose from 18.5799 to 18.6001; do not interpret successful execution as model quality gain. VRAM peak allocation 11163.6 MiB, free after 2893.5 MiB. Actual owner-message training not started.

## 2026-10-18 — Privacy gate and split audit alignment
- 188 prior Windows tests passed. Count-only local owner export scan: 3,963 URL matches and 7,995 Discord mention matches across both files (some may overlap), no direct token= pattern detected. No original texts copied to GitHub.
- Added URL/Discord mention/credential-like exclusions to training candidacy; harmonized per-file split audit to global UTC chronological cutoff. Two synthetic tests; expected 190 Windows tests, not yet run. No personal-data model training.

## 2026-10-18 — 190-test privacy classifier fix awaiting Windows verification
- Windows 190 suite had one failed classifier test: raw URL-only text was normalized to empty before identifier scan. Regexes for URL and secret markers also had excess backslash escaping. Corrected both: identify sensitive raw patterns before normalization and use single regex escapes. No model failure and no owner-data training. Re-run Windows 190 tests.

## 2026-10-18 — Windows privacy classifier regression verified
- User Windows unittest result: 190 tests, 0.430s, OK. Fix for raw URL/mention/secret detection ordering and regex escaping is unit-test verified.
- Real personal Discord QLoRA remains unstarted. Next gate: locally reviewed corpus with third-party contextual privacy screening and rights assessment; no raw files or derived private adapters in GitHub.

## 2026-10-18 — Original file counts and dry-run preview
- 190 Windows tests pass. Privately scanned owner-provided exports (304,997 total) without publishing messages. Found 30,848 exactly 2-char message contents; 23,867 empty; 3,963 URLs; 7,995 Discord mentions; 27,624 rows with attachments (sets may overlap). Added aggregate-only preview tool reproducing builder dedup/global split and 2-char opt-in counts, with two synthetic tests. Expected 192 Windows tests, unverified. No actual owner-data QLoRA performed.

## 2026-10-18 — Corpus-wide sampling and multi-example validation
- Updated Gemma4 trainer to choose deterministic evenly spread eligible examples rather than first N rows. Validation now averages up to min(8, max_steps) heldout examples, reducing dependence on one sentence; still a smoke experiment, not full quality evaluation.
- Synthetic unit test for selection indices added. Last user test 192 OK before this change; expected 193 but Windows GPU and regression not yet run. No private owner-data training conducted.
- Screened source ZIP remains NOT APPROVED. Optional short style set has no independently guaranteed chronological validation membership, so do not mix it into train until provenance / leakage review and applicable privacy rights are resolved.

## 2026-10-18 — Prepared gated full training protocol
- Separate longer Gemma4 12B QLoRA runner, checkpoints (adapter-only), validation average, best adapter, patience stop, JSON-only private metrics, and fail-closed PowerShell launcher. Added 3 tests. Last confirmed 193 Windows tests; now expected 196, Windows/GPU full-run not executed. No personal training executed. Training on screened-NOT-APPROVED archive remains blocked pending data permission and contextual review.

## 2026-10-18 — 실제 ML 불일치 분석 및 bounded pilot 실행

- 최신 사용자의 명시적 지시에 따라 기존 reviewed 자료만 로컬 학습에 사용. 원본/새 원천/유료 GPU·API/Discord 송수신은 사용하지 않음. 과거 문서의 학습 미시작 기록과 실제 로컬 300/2,500 summary가 달라 최신 상태를 문서 첫 절에 정정.
- 확인: 기존 raw text LM과 chat-template 추론 불일치, turn 종료 미학습, 짧은 검증 표본 0건, A/B 8건 중 3건 완전 동일. 검증 loss 개선과 생성 말투 실패를 구분.
- 변경 파일: `tools/persona_experiments.py`, `tools/persona_report.py`, `tools/persona_adapter_diagnostics.py`, `tools/prepare_persona_pilots.py`, `tests/test_persona_experiments.py`, README, PROJECT-DEFINITION, ARCHITECTURE, AI-HANDOFF, CURRENT-STATUS, 신규 ML-EXPERIMENTS.
- 구현 의도: 실제 대화 쌍을 꾸미지 않는 독립 스타일 적응. 응답/종료만 loss, 작은 길이별 표본, NF4/BF16, 후보 큐, 자원/오류/수동 중단, 원자 저장, optimizer/scheduler/RNG 재개, 합성 생성/블라인드/집계 평가. 실제 Bot 정책 코어 변경 없음.
- 실제 실행: 첫 FP16 pilot은 optimizer 업데이트 전 gradient 비유한 값으로 중단. 기존 모델 보존. BF16 rank4 q/v 및 rank8 q/k/v/o 각 60단계 예비 실험을 순차 실행. 완료 수치는 아래 후속 기록 및 ML-EXPERIMENTS에 기록.
- 검증 명령: `$env:PYTHONPATH='src'; .\.venv-gemma4\Scripts\python.exe -m unittest discover -s tests -q` → 204건 OK(0.760초, 이후 대시보드/범위 테스트 추가분은 최종 재검증 예정). 실제 tokenizer prefix 133토큰 확인. GPU 접근 및 학습/검증 forward 실제 실행 확인.
- 미확인: 사람의 화자 말투 평가, 실제 Discord 대화 품질, fresh private 시간축 최종 평가, 중단 재개의 비트 단위 동등성. 구버전 validation은 개발용으로만 사용. 공개 문서에 원문·응답·개인 경로/해시 기록 없음.
- Git: 작업 시작 HEAD `7e1e77f`, 이번 변경 아직 커밋/푸시하지 않음. 비공개 산출물 `local_data/experiments/`는 Git 추적에서 제외.

## 2026-10-18 — 실제 GPU 비교/실패 수정/최종 인수인계 완료

- BF16 실제 학습: style-v2 rank4 q/v 60단계 best 9.34640, rank8 q/k/v/o 60단계 best 6.84984, style-v3 rank8 LR 절반 120단계 best 6.70987. 동일 새 목적함수 초기 개발 loss 10.38176, validation 32건. GPU 최대 allocated 12,168.4 MiB. 모델 로딩·전처리를 제외한 loop 218.3초 / 50.0+81.8초(중단 재개) / 215.8초. 원래 300/2,500단계 모델 보존.
- rank8 20단계 checkpoint의 optimizer/scheduler/RNG 상태 복원 후 실제 학습 완료. 비트 단위 재개 동등성 비교는 안 함. 저장 소스/데이터 해시/설정/버전/시간/상태를 로컬 보존. 성공 이전 체크포인트를 삭제하지 않음.
- 기존 2,500단계 어댑터가 실제 forward에 적용됨을 확인. 단일 합성 raw/chat 입력에서 영향 크기 차이를 측정해 형식 불일치 가설을 보강. 결과 원문·어댑터·원천 데이터는 공개하지 않음.
- 동일 개발 생성 10상황: 스타일 지시 없는 기본 162.3자, 지시 기준선 36.3자, 제한적 반응 검색 36.3자, legacy+지시 40.2자, 새 rank4 36.4자, rank8 32.3자, 120단계 후속 32.2자. 문자 수는 품질 점수가 아님. 120단계와 60단계 응답 6/10 동일, 추가 생성 이득 정체로 더 학습하지 않고 60단계 rank8을 실험 후보로 보존.
- 첫 합성 최종 7건에서 실제 참여 수락/요청 절차의 본 작업 누락을 발견. 정상 EOS와 규칙 점수로 잡히지 않는 품질 실패로 기록. 이 집합을 개발용으로 은퇴시키고 응답 원문 보존. evaluator 전용 정책 v2로 능력 한계와 완결성을 지시하고 개발 2건 재시험. 모델 가중치/실행 Bot 정책은 변경하지 않음.
- 정책 개발 전에 고정한 새 합성 최종 7건을 동일 1,024토큰 상한으로 실제 실행: 양쪽 7/7 종료, 새 chat-role 문맥 변경 답변/정보 부재/보안 요청/실제 참여 불가 확인. 설명은 준비·테스트·시작까지 제시됐으나 기술 사실과 최신성은 평가하지 않음. 개인정보 검출·암기 검사는 휴리스틱이며 안전 보증 아님. 새 최종을 보고 다시 튜닝하지 않음. 인간 말투/선호 평가는 없음.
- 최종 검증: `$env:PYTHONPATH='src'; .\.venv-gemma4\Scripts\python.exe -m unittest discover -s tests -q` → **208건 OK, 0.715초**. 새 도구 5개 `py_compile` 성공, `git diff --check` 확인. 큐의 child 오류가 비정상 종료로 전파되도록 보강한 합성 회귀는 처음 기본 임시 폴더 rename 권한으로 실패했으나 허용된 저장소 고유 임시 폴더에서 재실행해 통과. 이 실패를 GPU/모델 실패로 혼동하지 않음.
- 상세 변경 파일: 앞 절 파일들에 버전 정책/실제 chat-role/개발·은퇴·최종 집합 분리/출력 source snapshot/블라인드 Markdown/실패 종료 전파 보강. README, PROJECT-DEFINITION, ARCHITECTURE, AI-HANDOFF, CURRENT-STATUS, ML-EXPERIMENTS 최신 상태 갱신. 기존 Bot 코어 소스 변경 없음.
- 사람 평가 파일 `local_data/experiments/style-v2/fresh-final-generation.blind.md`, 누적 `local_data/experiments/dashboard.md`, 선정 `local_data/experiments/selection.json`. 키는 별도 보존. Codex 파일 열기는 queued 응답이므로 표시 완료를 보장하지 않음. GPU 작업 종료 후 점유 약 1,601MiB로 확인.
- 최종 실사용 승인 없음. 다음: 사람 블라인드 평가와 허가된 새 평가/지시 자료 설계. 현재 fresh-final을 보고 추가 튜닝하면 개발용으로 재분류. HF PEFT/기존 Ollama(고정 128토큰) 서빙 연결·실서버 동시성/취소/권한은 별도 검증.
- Git HEAD `7e1e77f`, 새 변경은 로컬 미커밋. GitHub 커밋/푸시·클라우드 GPU·유료 API·새 데이터 원천 사용 없음. 비공개 자료는 `local_data/` 밖으로 내보내지 않음.

## 2026-10-18 — 추가 품질 단계 v3 시작/예비 평가

- 기존 변경 13개를 비공개 source-before에 보존하고 기존 비공개 파일 217개의 경로/크기/수정 시각을 기록했다. 저장소 기준 재점검에서 217개 모두 보존 확인. 처음 검사 스크립트의 기준 경로 중복 결합을 수정한 뒤 재검증했으며 실제 누락은 없었다. 기존 문서의 개인 홈 경로 4곳만 비식별 입력 예시로 치환했다.
- 시작 시 기존 208개 테스트 OK(0.904초). 기존 변경의 로컬 보존 커밋 `e6b6f6d`, 새 정책/평가 기반 커밋 `7342757`. GitHub push 없음. 추적 파일 및 신규 소스 133개에서 홈 절대 경로·일반 키 패턴을 검사해 검출 없음, `git ls-files local_data` 비어 있음. 자동 검사만으로 개인정보 검수를 확정하지 않는다.
- 변경: `src/echomate_studio/response_policy.py`, `tools/persona_quality_cases.py`, `tools/persona_quality_v3.py`, `tools/persona_memorization_probe.py`, `tests/test_response_policy_v3.py`, ARCHITECTURE/ML-EXPERIMENTS/CURRENT-STATUS/AI-HANDOFF/WORKLOG. 기존 Bot 실행/참여·침묵·멘션·대화 지속·취소 코어는 변경하지 않았다.
- 의도: 실제 말투/응답 품질을 가중치·정책·집계 prior별로 분리 비교. 새 합성 pilot 8건, 사전 고정 holdout 26건/13범주, 같은 정책 프롬프트와 greedy/예산, 블라인드와 별도 key. 상황/정답 라벨을 모델에 전달하지 않는다. 독립 메시지에서 실제 대화 쌍을 조작하지 않는다. 추가 학습 0단계를 사전 결정했다.
- 실제 GPU: 합성 짧은 응답의 prefix 전체 마스킹/shifted CE 직접 계산 일치와 legacy/rank8-60/rank8-120 어댑터의 적용을 확인했다. 예비 생성에서 과한 감정 상담/되묻기, 기술 결론 모순, 절차의 반복·상한 도달·원본 보존 제약 이탈을 발견했다. 개발용 pilot에서만 정책을 수정하고 소스/실패 응답을 모두 보존한다. 새 holdout을 보고 정책을 고치지 않는다.
- 실행 안정성: 진행/부분 결과/실패를 원자 저장, 응답 사이 STOP/자원 검사, 새 run ID로만 출력. 예비 재시험용 선택 문항/정책 제한은 pilot에만 허용. 더 긴 기술 평가의 비용 절감을 위해 동일 폭/3슬롯 정책 배치를 예비 검증하며 홀드아웃 가중치 간 배치 조건도 동일하게 유지한다. 평가 KV cache 복원은 구현하지 않았고 기존 학습 optimizer/RNG 재개와 다르다.
- 검증: `$env:PYTHONPATH='src'; .\.venv-gemma4\Scripts\python.exe -m unittest discover -s tests -q` → 216개 OK(0.906초). 새 도구/정책 py_compile 및 diff whitespace 검사 성공. 실제 GPU 평가 완료 수치는 아래 후속 기록에 추가한다. 테스트 통과를 말투 개선의 근거로 사용하지 않는다.
- 상세 비공개 산출물은 `local_data/quality-v3-20261018/`. 새 대화 원천·외부 GPU·유료 API·실제 Discord 송수신 사용 없음. 사람 말투 평가/운영 승인/최종 모델 선정은 미실시.


## 2026-10-19 — quality-v3 독립 평가 완료/선정 보류

- 실행일 2026-10-18 UTC의 고정 코드 `b62633e`로 새 독립 26문항/13범주 GPU 평가 완료. 실제 10조건의 250발화 + 공통 침묵 10행 + 파생 재사용 52행 = 저장 312행. 2,482.5초(로딩 포함), peak allocated 8,498.6 MiB. 중복 배치 진단 50개 모두 대응 v3와 일치, 별도 참여 판단 2회. 새로운 GPU 학습은 0단계다.
- 같은 정책의 가중치별 prompt/seed/예산/배치 조건 일치 검사 통과. 전 문항의 비블라인드 AI 의미 검토를 private agent-semantic-review에 보존했다. 사람 평점과 구분한다. 일부 v3의 원칙적 개인정보 거절/복원 설명 이득은 있었으나 과한 장문·절차 상한 도달·기술 설명 모순·keyword 의도 오인으로 일관된 우위 미확인. prior/hybrid/selective도 승격하지 않는다. 기존 rank8-60 + v2는 잠정 후보로만 유지하고 새 selection을 별도 루트에 저장했다.
- 실패도 보존: native thinking 개발 진단은 올바른 첫 결론에도 응답 미완결로 후보 제외. 독립 얕은 복사 문항은 전 실제 조건에서 첫 결론/뒤 설명 모순, 다른 기술 대화는 full-v3가 대입과 얕은 복사를 혼동. 규칙 정답 포함/정상 종료를 정확성으로 취급하지 않는다. 독립 결과를 본 뒤 정책/문항/가중치를 변경하지 않았다.
- 별도 GPU prefix 노출 진단은 학습 2/기존 validation 2표본 × 4가중치 16생성, 남은 원문 전체 복원 0. 매우 작은 비대응 표본이며 암기/PII 안전 보증 아님. 이 도구는 시간/peak 별도 계측 없음. 원문은 local_data에만 있다.
- 신규 `tools/persona_generation_trace.py`는 소비된 정보 부재 문항을 고정 조건으로 forensic 재현하고 원 평가를 변경하지 않는다. GPU 6개 보이는 출력 모두 일치(52.0초, peak 8,236.9 MiB). prior 2조건에서 channel 제어/표시 혼입을 확인했다. 원시 토큰은 private 파일에만 남겼으며 내부 내용은 공개하지 않았다. 운영 채널 파싱 검증은 미완료. 진단 소스 커밋 `6493f7a`.
- 비공개 holdout 보고서 및 balanced/same-policy/same-weight/candidate-vs-provisional/weights-v2/duration-v2 블라인드 자료 생성. 각 고정 비교는 전 26문항 포함, key 별도. REVIEW-GUIDE에 7개 항목 및 N/A/평가 후 key 확인 절차 기록. 아직 사람 평점 없음. 사용자 말투 재현 성공을 선언하지 않는다.
- 최종 검증: `$env:PYTHONPATH='src'; .\.venv-gemma4\Scripts\python.exe -m unittest discover -s tests -q` → **217건 OK, 0.935초**. 기존 208건 유지. `py_compile tools/persona_generation_trace.py`, `git diff --check` 성공. `persona_quality_v3.py report --root local_data/quality-v3-20261018 --name holdout-a` 성공. 실제 Discord/Ollama 서빙·외부 관찰은 미실시. Bot 참여/침묵/멘션/취소 코어 소스 변경 없음.
- 최종 보존 확인: 시작 시 217개 private 파일의 크기/mtime 전부 동일, 기존 어댑터/학습·검증 자료/스타일 집계 SHA 동일, holdout 추론 3소스 해시 동일. 종료 후 GPU 38도, 사용 2,481MiB/여유 13,581MiB 확인. 추가 GPU 작업 종료.
- 공개 대상은 진단 소스와 AI-HANDOFF/CURRENT-STATUS/ML-EXPERIMENTS/WORKLOG 비식별 문서다. 추적/신규 135경로의 홈 경로/일반 키·토큰 패턴 검출 없음과 원문/결과 미포함을 검토했다. `git ls-files local_data` 비어 있음. 자동 검사가 권한/개인정보 검수의 충분조건은 아니다. 로컬 커밋만 사용, GitHub push 없음. 실제 최신 문서 커밋은 `git log -1`, 상태는 `git status --short`로 확인한다.
- 다음: 블라인드 개인 말투 평가 후, 소비한 holdout을 회귀용으로 은퇴시키고 별도 개발 자료에서 의도/채널 처리 개선 검토. 실제 응답 감독 자료는 허가된 범위에서만 설계한다. 새 최종 자료를 고정하기 전 이번 결과를 재튜닝 점수로 재사용하지 않는다. 비공개 경로 `local_data/quality-v3-20261018/`; 이전 체크포인트/선정 기록 그대로 보존.


## 2026-10-19 — 공식 Discord Bot/로컬 멀티모달 통합

- 시작 Git `4224877`, 작업 트리 깨끗함 확인. README/PROJECT-DEFINITION/ARCHITECTURE/AI-HANDOFF/CURRENT-STATUS/ML-EXPERIMENTS/WORKLOG 및 기존 참여·상태·멘션·취소/반응 소스를 읽었다. 기존 단계의 217개 비공개 산출물은 크기/mtime 보존 검사 통과. Studio/기존 QLoRA/평가 코드와 모델을 변경하지 않았다.
- 최신 사용자 요구에 따라 과거 Unicode/텍스트 전용·thread 전용 계획을 승인된 서버/채널/스레드와 사전 승인 미디어로 확장했다. PROJECT-DEFINITION/ARCHITECTURE에 변경 근거와 현재 경계를 추가했다. 관리자는 소유자 ID와 일치하지 않으면 설정 권한이 없다. 테스트 연결은 품질 미확정 모델의 운영 승격과 다르다.
- 새 `src/echomate_bot`: 서명된 원자 설정·소유자 ID bootstrap, 7가지 기분/성격/기본 비활성 자동 연출, 공식 Gateway/ephemeral 명령·패널, allowlist·명시적 스레드 상속, 기존 participation/mention/engagement/DialogueState 재사용, 단일 GPU 큐·최신 상태 취소, 행동 검증/영속 송신 예약/nonce/쿨다운·일일 한도·안전 중단, 실제 시각 분석과 서버 격리 캐시, 서명·해시·범위로 승인된 별도 미디어 라이브러리.
- 추가 파일: `configs/bot-requirements.txt`, setup/start PowerShell, `verify_bot_multimodal.py`, `verify_bot_pipeline.py`, `verify_discord_live.py`, `tests/test_bot_integration.py`, `docs/DISCORD-BOT.md`. README와 6개 주요 문서 갱신. 모든 원문·캐시·가중치·토큰·실제 서버 식별자는 local_data만 사용한다.
- 무료 discord.py 2.7.1/aiohttp 3.14.5 설치. 첫 일반 환경 pip는 DNS 제한으로 실패했고 제한 밖에서 설치했다. 기존 torch 2.9.1+cu128를 유지하며 torchvision 0.24.1+cu128만 추가했다. modality processor 설정 파일이 기존 캐시에 없어 설치된 Gemma4Unified 기본값과 cached vision config로 image-only 경로를 구성했다. 별도 공식 processor artifact와 동등성은 미검증이다.
- 제한 환경의 Windows asyncio loopback 시작이 멈춰 실제 GPU/네트워크 이전의 이번 테스트 프로세스만 정리했다. 제한 밖에서 합성 테스트와 실제 GPU/공식 연결을 각각 실행했다. 새 클라우드 GPU/유료 API/새 학습 데이터/추가 학습 없음.
- GPU `gpu-smoke`: 실제 시각 생성 뒤 JSON 포장 파싱 실패. 정확한 JSON 코드 블록만 허용하도록 보완하고 `gpu-smoke-2`에 실패/성공 분리. base/persona × PNG/GIF/기술 텍스트 6조건 완료, 전체 166.4초, peak 7,819.6MiB. 도형/색/위치와 2프레임 이동을 확인했고 실제 사진/감정/스티커 의미 품질을 증명하지 않는다. 추가 모델 다운로드 없음.
- GPU 통합 `gpu-pipeline`: 소스 사본 절대 경로 결합 오류로 GPU 전 실패, 원본 미변경 확인 후 상대 경로로 수정. `gpu-pipeline-2` 69.2초(로딩 포함)/모의 전송 1건. `gpu-pipeline-3` cold 준비35.9초 + 이벤트31.5초, heartbeat511회/최대 간격0.094초. `gpu-pipeline-release` cold36.2초 + 이벤트32.7초, heartbeat531회/최대 간격0.078초, 실제 GPU 4호출과 모의 전송 완료. 실행마다 소스/설정/진행/실패를 local_data에 보존. 실제 Discord 송신과 구분한다.
- 실제 사용자 설정 후 테스트 서버 연결 허용을 받았다. `live-qa`: 공식 Gateway ready/등록한 관리 서버 1개 확인, 소유자 권한 검사 허용3회와 실제 메시지 수신1건, 송신0. `live-qa-2`: 재접속/수신2건, 생성 중 새 메시지에 의한 취소1회, 송신0. 출력 종류 거절 시 진단이 없던 부분과 비활성 종류를 모델 후보에서 제외하지 않던 부분을 보완했다. 실제 메시지 본문을 인용하지 않았다.
- 같은 화자가 멘션 후 추가 메시지를 보내면 이전 생성은 취소되지만 새 메시지에 멘션이 없어 미처리 요청이 사라지는 실제 통합 문제를 확인했다. 최신 테스트 채널 메시지 최대4개의 멘션 여부/나이/봇 여부만 읽어 진단했으며 본문/ID는 저장·출력하지 않았다. 실제 관측한 미처리 멘션만 동일 화자·다른 대상 멘션 없음·30초 이내에 유지해 최신 문맥으로 재처리하도록 수정했다. 다른 사람/다른 대상의 메시지에는 상속하지 않는다. 원문에 멘션을 가짜로 덧붙이거나 학습 예시를 만들지 않았다. 수정 후 `live-qa-3` 실제 송신 재검증 중이며 최종 관측은 아래 후속 기록이 우선한다.
- 단위/모의 통합 회귀: 원자 저장에서 실제 Windows 일시적 교체 잠금 1회 실패를 관측해 제한 재시도/이전 파일 보존을 추가하고 예외 주입으로 검증. 패널 버튼 이름이 View.stop을 가리던 충돌도 수정했다. 최종 `$env:PYTHONPATH='src'; .\.venv-gemma4\Scripts\python.exe -m unittest discover -s tests -q` → **243개 OK, 6.627초**. 본문 비파괴 검사, owner/컴포넌트 인증, scope/스레드, 중복·취소/권한·설정 철회, 독립 반응, 캐시/파일·설정 변조, 큐 상한/취소, OOM 예외 주입을 포함한다. 실제 GPU 메모리를 고갈시키지 않고 OOM 안전 비활성화를 검증했다.
- 소스 커밋: `baeb0b1` 통합, `faab6f4` 출력 폐기 진단, `c9ea53c` 행동 후보 필터/실제 QA 소스 보존, `7b4802a` 미처리 멘션 유지. 문법/whitespace 검사와 공개 소스의 홈 경로/일반 키 패턴 미검출, local_data 추적 파일0 확인. private bootstrap은 사용자 로컬 입력/Windows ACL로 생성됐으며 Git 스테이징하지 않았다. GitHub push 없음.
- 미확인: 일반 사용자 실계정 거절, 실제 권한 철회/네트워크 단절, 다중 채널/미디어 실제 송신, 실제 OOM/장시간 안정성, 개인 말투 사람 평가. Lottie 미지원, 모델은 Gemma base/persona 선택만 제공한다. 빈도/모델 loss/모의 성공을 실사용 품질 승인으로 해석하지 않는다.


보존 최종 검사: 기존1104파일 누락0. 가중치/학습자료/원래 서명 설정은 보존했다. 실제 QA 과정에서 기존 runtime.lock, diagnostic.jsonl, sent.sqlite3, telemetry.json 네 운영 파일은 실행 기록이 갱신됐다. 원래 파일을 삭제/되돌리지 않았다. QA 설정 폴더를 써도 EchoClient의 기본 ledger 경로가 운영 폴더를 가리키던 원인을 확인해, visual/ledger/진단을 설정 폴더에 함께 두도록 수정하고 경로 회귀 검사를 추가했다. 이 최종 경로 격리 수정은 모의 SDK/전체 회귀 검증이며 실제 Discord 재시험은 하지 않았다.


최종 보존 검사: 기존 private1234파일 누락0, runtime.lock 실행 메타데이터만 갱신됐고 나머지1233파일의 크기/mtime는 보존됐다. 원래 모델 선택 persona, 자동 기억/실험 시각 OFF를 읽기 확인했으며 설정·운영DB·weights를 변경하지 않았다. 환경은 torch2.9.1+cu128/transformers5.20.1/peft0.21.2/discord.py2.7.1/tzdata2026.5다. 상세 inventory/로그는 private에만 보관한다.


### 의미 중심 변경 파일과 결함 회귀

naming/routing/sessions/runtime/dialogue_intent/inference/character/telemetry, Discord 수신·전송 모듈, desktop 상태·UI, 합성 테스트와 verify_semantic_gpu.py를 변경했다. 이름 후보 veto·문장부호 빠른 경로·새 화자 제한을 교체했다. 과정에서 별명 중 하나의 동명이인 때문에 다른 고유 호출까지 모호해지던 판정, 자기 호칭을 타인 호격으로 보는 분기, pending 이후 변경된 공유 잠금 ID, 합류 전 자동 기억의 잘못된 flow ID, stale 후보 합류, 옆 대화가 활성 집계에 남는 문제를 수정했다. SDK 시험의 오래된 가짜 snowflake 시간 때문에 거절되던 fixture도 실제 시간 기반 ID로 바로잡았다. 실제 오래된 메시지를 역순 삽입하는 방어는 유지하고 진단을 추가했다.

실행: unittest discover 전체, compileall bot/새 도구, verify_semantic_gpu.py의 GPU1~4/technical/sequence/audience, verify_direct_bursts.py. 단계별 source snapshot과 protocol은 private에 있다. 의미 수정 전의 단순 통과 집계만으로 완료하지 않고 실제 순서 재현의 누락을 추가 확인한 뒤 재검증했다. 기본/개인/성인 유머 선택지와 캐릭터 성별, 소유자·HMAC·범위, 반응·기본 스티커, 개인정보 보호와 기억/예약은 전체 회귀를 유지했다. 제거된 미디어와 실험 시각 기능은 복구/활성화하지 않았다.


추가 증거: 동일한 부정적 대상 판단을 주입한 기준66d0b02 Runtime은 등록 호칭에0응답/0생성, 현재 Runtime은1응답/1생성이었다(injected-baseline-summary.json). 이는 결정적 재현이며 당시 실제 모델이 똑같은 판단을 냈다는 증거는 아니다. 현재 로컬 서명 설정에서도 보고된 호칭의 유효 형태를 확인했고 settings/bootstrap 해시는 변하지 않았다.

초기 기분 도구의 성인 슬롯 weight를 직접 지정한 경로는 생산 turn_profile과 달라 수정했다. 기분 비교표는 수정된 GPU3의 기본/개인/성인 정책 경로만 사용한다. 초기 sequence 도구의 모드 간 원문 파일 덮어쓰기도 수정하고 gpu-sequence-confirmed에서3모드별 원문/trace를 각각 재보존했다. 실제 사용자 자료나 weights를 덮어쓴 것이 아니다.

### 변경 파일·실행 근거

- `inference.py/runtime.py/sessions.py`: 확정 직접 호출 관계 전용 분류, 유일 세션 자동 연결 제거, 완료 반응 이력 회수. 후보 A/B의 실패 원인과 최초 독립 평가를 보존했다.
- `desktop.py/desktop_ui.py/companion_ui.py`: stale 선택/필터, 서명 프로필 저장 후 적용, popup 갱신, ticket 취소·GPU 소유권 정리, DPI/긴 설정 양식·읽기 전용 상세·최근 관리 오류.
- tests의 Controller·세션·실제 숨긴 Tk 회귀 및 `tools/verify_ui_functional_audit.py`, `tools/inventory_ui_controls.py`. 새 조작은 자신의 Tk/Tcl binding에 한정한다.
- 명령: `.venv-gemma4/Scripts/python.exe -m unittest discover -s tests` →547개 OK63.119초. `tools/verify_ui_functional_audit.py --output local_data/social-ui-qa-20261020/ui-final-audit-v2.json` →420 PASS. `tools/inventory_ui_controls.py --output docs/UI-CONTROL-INVENTORY.md` →79정적 호출, 실행 coverage는 아님.
- 실제 GPU 코어 `6f81b9e`와 최종 소스의5모듈 바이트 해시 일치. 4프로필12응답 생성은 완료했으나 사람의 자연스러움 평가는 미완료다.

## 2026-10-20 프로필 파일 마감 보완

character_profiles.py·desktop.py·desktop_ui.py에서 ID 입력 없이 현재 캐릭터 내보내기/새 프로필 가져오기를 연결하고 비프로필 파일 덮어쓰기를 차단했다. tests/test_ui_workflows.py와 test_model_character_distribution.py로 실제 저장/취소/기존 자료 보존을 확인했다. PYTHONPATH=src;tests;tools의 전체 unittest575 OK75.691초, 엄격한 SDK mock 디스패치209 PASS, 숨긴 Tk 렌더420 PASS. 초기 표적33검사는 도구 import 경로 누락1건으로 실패했으며 전체 검사에서 올바른 tools 경로로 재검했다. 실제 사용자 UI와 Discord는 미검증이다.

## 2026-10-20 Portable 최종 사용자 흐름 — 소스548d0c6

최종 번들 Python·자체 숨긴 Tk·새 빈 검증 저장소에서 GUI 최초 설정(DPAPI/서명), 가상 서버/채널, 실제 분할 모델 선택/probe, 현재 캐릭터 파일 내보내기/새 항목 가져오기, 실제 GPU 미리보기와 로딩 중 닫기, 새 프로세스 복원을 확인했다. 첫 흐름87.140초·첫 UI0.406초, 재시작0.437초·첫 UI0.390초였다. 실제 Discord는 강제 차단했고 외부 HTTP0·관계/기억/예약 쓰기0·종료 worker0이었다.

로딩 중 취소는26.063초 후 정리됐고 GPU allocated1KiB/reserved2MiB였다. 안전한 로딩 구간을 즉시 물리 중단하지 않는다. Tk 검사 펌프 최대 간격1.937초가 있어 완전 무정지 UI라고 인증하지 않는다. 같은 호스트의 격리 저장소 검증이며 다른 Windows/깨끗한 VM/native 사용자 조작은 NOT VERIFIED다.

공개 Portable은24,767파일·4.590GiB이며 모델·개인 DB·토큰은 제외한다. 최종 source/docs 바이트 및 전체 파일 manifest는 별도 package audit로 대조한다. 소스와 Portable의 일반/오프라인 VBS 4진입점 /check는 앱/봇을 시작하지 않고 통과했다. 공개 다운로드 릴리즈는 만들지 않고 후보를 로컬에만 둔다.

이번 변경 파일: ui_controls.py, desktop_ui.py, companion_ui.py, test_input_controls.py, test_ui_workflows.py, test_companion_ui.py, test_ui_record_selection.py 및 UI 문서. 명령: PYTHONPATH=src;tests;tools의 unittest discover -s tests -q, verify_ui_actions.py, verify_ui_functional_audit.py. 결과·경계·실패는 UI-INTERACTION-GUIDE를 따른다. 모델/추론/큐/DB 스키마 변경 없음.
