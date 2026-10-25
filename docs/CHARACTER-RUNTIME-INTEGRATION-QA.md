# 캐릭터 Runtime 통합 QA — 2026-10-25

시작 main/origin `ba84c52653fcbba8102d1ab2489f830933d5fac1`, clean. 최신 사용자 지시의 사전 학습 캐릭터 제품을 따른다. **RELEASE BLOCKED**. 아래 합성/기술 PASS는 모델 품질이나 제품 전체 PASS가 아니다. 종료 커밋은 Git 이력과 AI-HANDOFF의 마감 기록을 따른다. 원문·자원 로그·소스 SHA는 비공개 `local_data/character-runtime-20261025/`에만 보존한다.

## 재사용과 실제 변경

기존 CompanionStore v7의 조회·권한·영수증·삭제, Runtime 공정 큐·메시지 조립·최신성·알림, CharacterModelManager를 재사용했다. 학습 경로로 돌아가지 않았고 운영 모델/설정/DB를 자동 전환하지 않았다.

- `gguf_backend`는 hash 고정 Lime/b11721/2048 context만 허용하는 실험적 concrete backend다. 인증된 loopback 서버 하나를 소유하고 기존 InstanceLease/fair queue를 사용한다. 스트림 종료/채널/finite-choice 출력을 확인한다. HTTP 취소 뒤 실제 native slot idle을 확인해야 큐를 반환하며 불확실하면 자체 서버를 정지한다. 다른 프로세스를 조사하거나 종료하지 않는다.
- Runtime은 기존 manager에 이미 상주한 backend를 adopt한다. 전환/이름 변경 시 epoch 무효화→접수 중지→작업/조립/자동 추출 drain→해제 확인→admission→로딩/검증 순서다. 미종료 작업은 참조를 유지하고 RecoveryRequired로 정지한다. 옛 생성/기억 조회/송신 callback은 새 캐릭터에 귀속되지 않는다. 전환 중 들어온 발언의 자동 재생 정책은 아직 없으며 접수를 중지한다.
- 캐릭터별 실제 SQLite table namespace로 기억·관계·대화 사건·요약을 격리한다. 공통 동의/철회와 예약은 공유한다. 삭제/정정의 기존 근거·영수증 및 선택 검증에 CharacterId를 결합했다. 개인정보 삭제는 legacy와 등록된 전체 namespace에 단일 transaction으로 적용하고 중간 실패 시 rollback한다. 다른 hub의 namespace 등록도 재확인한다.
- 새 파일 생성 또는 명시적 read-only legacy snapshot 복사만 허용한다. 원본을 새 캐릭터에 자동 귀속하지 않는다. 현재 CompanionStore API는 namespace marker가 있는 DB를 legacy 방식으로 열지 못한다. **운영 마이그레이션은 미실행**이다. 구형 v7 바이너리는 marker를 모르므로 실제 UI 이관 전 DB 버전/downgrade 거부 정책이 추가로 필요하다. 공통 사용자 사실 공유 UI/정책도 미완료다.
- 명시적 기존 기능 명령은 결정적 실행 결과/조회 실패/영수증을 안내한다. 조회 실패를 빈 목록으로 표현하지 않는다. 일반 자유 생성의 모든 한국어 주장에 대한 신뢰 가능한 자동 차단기를 구현한 것은 아니다.
- 사전 학습 모드의 로컬 slash 계약은 `/동의` + 읽기 전용 ephemeral `/캐릭터`다. legacy 모드는 `/동의` + 소유자 전용 `/성격`을 유지한다. 실제 등록/삭제/조회는 하지 않았다. EchoClient의 store/backend 조회는 Runtime의 전환 결과를 따른다. GGUF는 vision 미지원이며 기술 로딩과 의미 검증 미완료를 구분해 표시한다.

## 실제 GPU 결과와 실패 기록

Lime 파일: [공식 저장소](https://huggingface.co/naksyu/lime_Q6_K), revision `99280194d4593f0efe2d6a9ac79a697b0ec5e880`, SHA256 `bafcfe3f624f0e1f84014c9b9136788992629955f7ce9146941226cd280d618e`. llama.cpp b11721 executable SHA256 `a3f027944366d2b9d5154df43c31483c2bc8c9f9fa3c878d0b07115acc7e6624`. 모델/engine 파일은 공개 소스나 Portable에 포함하지 않았다.

`final-gpu-diagnostic/report.json`: 단일 Lime을 두 차례 **순차** 로딩했다. 첫 인스턴스 종료 확인 후 두 번째 로딩, 양쪽 종료/회수 확인. native slot busy 상태에서 취소→idle 확인→후속 생성 성공. 이름 5턴 중 이름을 요구한 4턴 모두 유나를 유지했고 재로딩 후 새 이름 검사도 통과했다. 이것은 30턴/인격 차별성 인증이 아니다.

| 측정 | 실제 결과/범위 |
|---|---|
| aggregate free VRAM 최소 | 7,342MiB |
| RAM available 최소 / commit available 최소 | 6.276GiB / 21.614GiB |
| GPU 온도 최고 | 47°C |
| 로딩 시간 | 4.390초 / 3.360초; 파일 캐시 조건 차이 있어 속도 개선 주장 안 함 |
| 완료 호출 10개 / 출력 | 합계100token, 짧은 identity·진단 응답 |
| 지연 / TTFT | p50 0.422초, nearest-rank p95 3.969초, TTFT 중앙0.274초 |

취소 호출은 완료 호출 지표에 포함하지 않았다. 실패/취소까지 전체 호출·토큰 원가 계측은 보강 과제다. aggregate free 변화는 다른 프로그램의 변동도 포함하므로 자체 allocated/reserved로 표기하지 않는다.

**엄격한 semantic startup gate는 FAIL**이다. 인간에게 한 질문에 `bot_group join 1 acknowledgement no`를 출력했다. frames가 없는데 anchor1을 생성하는 구조 오류를 발견해 GGUF에만 실제 frames 기반 finite grammar를 적용했다. 같은 입력/모델/seed의 ABBA 비교에서 legacy765 choices는 두 번 같은 잘못된 anchor, grounded165 choices는 두 번 `bot new none question yes`였다. 유효하지 않은 anchor는 제거됐지만 사람을 향한 발언이라는 정답은 여전히 틀렸다. 구조 보정만 인정하고 의미 품질 성공/READY로 승격하지 않았다. 기존 Gemma classifier 선택 공간은 변경하지 않았다.

중간 버전은 deterministic human-recipient guard가 startup probe까지 우회하는 결함이 있었다. 전체 회귀가 이를 발견해 semantic probe를 직접 검사하도록 수정했다. 그 중간 버전의 실제 GPU Runtime→SDK HTTP mock 6송신은 물리 경로/명시 기능 실패 안내의 **구성요소 증거**로만 보존한다. 최종 소스의 모델 자격 통과·전체 통합 PASS로 사용하지 않는다. 이후 엄격 gate가 막아 최종 GPU 다중 사용자/조각/전환 전체 시퀀스는 실행하지 못했다.

추가 전환 시도 하나는 로딩 중 자원 watcher가 자체 서버를 정지했다. 당시 상세 unsafe counter가 없어 RAM 원인이라고 확정하지 않는다. 후속 코드에는 정확한 실패 counter/extrema와 모델 준비 RAM admission 7GiB(관측 aggregate 감소 약3.4GiB를 4GiB로 올림 + 기존 여유3GiB)를 추가했다. free VRAM2GiB/RAM3GiB/commit2GiB/85°C 미만의 기존 실행 기준을 낮추지 않았다. 2048 이외 context나 다른 모델에 측정을 일반화하지 않는다.

## 모델별 자격과 외부 조건

| 캐릭터 | 현재 상태 |
|---|---|
| Lime | 실제 GPU 기술 수명주기·짧은 이름 인식 확인. 의미 청자 FAIL, 이전 조회 실패/허위 알림 발언 미해결. 제품 READY 아님. |
| Yaho | [원본](https://huggingface.co/ChanLumerico/EXAONE-3.5-7.8B-Instruct-Yaho), 고정 revision `24a501c8107a07ea18c9657e84525a081741be02`. 제공 EXAONE LICENSE의 연구 목적 제한을 재확인. 제품 사용/배포 검토 BLOCKED, 가중치 미다운로드. |
| 여성 IT 기획자 | [원본](https://huggingface.co/92doolgi/Persona-Driven_Korean_Debate_Bot), revision `3001bbc98605fbdb8754e16c17513cdc1724656f` 재확인. adapter weights 없음, placeholder 모델 지시만으로 정확한 기반/파일 확보 불가. BLOCKED. |

제공자 모델카드를 EchoMate 품질 PASS로 인용하지 않는다. 새 세 캐릭터와 기존 Gemma의 공정한 전체 품질 A/B는 미완료다. 사람이 느끼는 자연스러움/매력은 NOT VERIFIED다.

## 검증과 남은 작업

초기 전체978검사에서 semantic gate 우회1건/축소 fixture 호환2건 실패를 보존하고 수정했다. 이후 소스별981/984/985/987 전체 통과 기록은 비공개에 보존한다. 추가 최종 실행 한 번은 프로젝트 환경 대신 시스템 Python을 사용해 aiohttp 등 의존성 누락으로 844검사/247오류였다. 소스 결함으로 숨기거나 PASS 처리하지 않고 해당 로그를 보존한 뒤 의존성이 설치된 프로젝트 Python으로 재실행한다. 최종 검사와 Portable/보존/커밋은 아래 마감 항목에 추가한다. 새 테스트는 finite grammar/실제 slot drain 모의 서버, epoch/미종료 작업/실패 복구, SQLite 원자 삭제/legacy 격리/외부 namespace 등록, 로컬 slash 계약을 포함한다. 전체 GUI 포함 회귀는 자체 생성한 **비활성 Desktop**에서 검증하고 외부 socket을 차단했다. 사용자 Desktop 입력·전체 화면 캡처·다른 앱 프로세스 조사 없음.

현재 완료 범위는 Phase A 재사용 감사, B concrete Lime backend 부분, C/D/E/F Runtime·저장소·영수증 경계, H 로컬 명령 계약이다. **Windows 캐릭터 선택/다운로드 UI와 legacy controller 첫 활성화 lease/store handoff는 미구현**이다. 설치/중단재개/manifest UX, 다른 모델 실제 전환, DB downgrade 정책, 30분GPU·2/8시간 새 구조 soak, 다른 Windows·실제 Portable GPU도 NOT VERIFIED다. 운영 migration/실제 Discord는 별도 승인 필요지만 아직 다른 필수 품질 작업도 남아 있다.

다음 순서: (1) 새 UI/controller opt-in 첫 활성화 및 실패 표시를 synthetic store/lease에서 연결 (2) downloader pinned hash/라이선스 동의/부분 파일 복구 (3) Lime 사회적 판단의 원천 분리 진단; 같은 prompt 조정 반복/기준 완화 금지 (4) 신규 구조 장기 시퀀스/모델 전환/Portable GPU (5) 다른 Windows/마지막 실제 Discord 별도 승인. 실제 모델 품질이 미달인 상태에서 시작 gate를 제거하거나 Ready로 꾸미지 않는다.

재현: `PYTHONPATH=src;tools;tests`로 `python -m unittest discover -s tests`를 프로젝트 전용 비활성 Desktop/외부 네트워크 차단 wrapper에서 실행한다. GPU는 private diagnostic의 소스 hash·고정 engine/model·2GiB reserve·상기 RAM admission을 확인하고 단일 인스턴스로만 실행한다. 이전 실패 실험을 무조건 재실행하지 않는다.

## 최종 소스 검증 체크포인트

- 최종 프로젝트 Python 전체 **988개 OK279.346초**. `full-regression-final-environment.log`/`regression-final-environment.json`, 비활성 Desktop 검증·외부 socket 차단. 이전 잘못된 시스템 Python 실행의 오류는 별도 보존했다.
- 갱신된 Portable 실제 번들 Python/번들 src import 확인 후 **64개 OK5.799초**. 캐릭터 store/manager/Runtime/명령/GGUF loopback·예약 freshness 합성 검사이며 실제 Portable GPU/신규 Windows UI 검증이 아니다.
- 운영 설정/bootstrap/두 DB/평가 소비 장부 **5개 SHA256 동일**, 원본 모델 **12개 shard 동일**. 기존 adapter/학습/최종316 자료 미변경·미소비. 신규 운영 SQLite 이관0, 실제 Discord 인증/REST/Gateway/명령 변경/송신0.
- 공개 예정27개 명시 경로의 전체 staged 내용/diff와 확장자·토큰/개인 경로/개인키 패턴을 감사했다. 모델·DB·원문 평가·비공개 로그 미포함. 패턴 미검출은 모든 비밀의 수학적 부재 보장은 아니다.
- Portable 공개182경로는 소스/문서와 바이트 일치하도록 동기화했다. 전체 manifest 해시 감사 결과와 종료 Git HEAD는 이어지는 마감 기록/커밋 이력을 따른다. 다른 Windows/실제 Discord/장기 안정성의 필수 차단은 유지한다.
