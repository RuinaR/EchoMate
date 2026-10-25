# Lime 최초 출시 계획과 변경 QA

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

학습·성격 카드 편집은 새 주요 흐름에서 제외한다. 기존 운영·레거시 자료는 삭제하지 않는다. 미래 모델은 사용자가 실행할 수 없는 기본 선택지로 나열하지 않는다. 필요할 때만 정확한 미지원 사유를 별도 안내한다. **현재 Windows 앱은 아직 이 새 흐름으로 연결되지 않았다.** 계획 문서/카탈로그 필터를 화면 구현으로 과장하지 않는다.

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
