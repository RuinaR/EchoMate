# 모델·캐릭터·일반 배포 QA — 2026-10-19

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
