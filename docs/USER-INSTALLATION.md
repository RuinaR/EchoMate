# 일반 사용자 설치·시작 안내

## 2026-10-20 최종 안정화 — 최신

마감: **523회귀 OK58.467초**, 실제20분 혼합 운용1912 mock 답변·GPU10/10·worker0, source 및 Portable의 실제 shard 로딩/모델 선택·미리보기 PASS. 최종 shard peak12.92GiB(최초13.01), 원본31.35GiB. 운영 자료 보존·독립 청자26/32로 **릴리즈 BLOCKED**. 실제 Discord/다른 Windows/Maple/24시간/사람 말투 평가는 NOT VERIFIED. 상세·소스/패키지·Git 마감은 STABILIZATION-QA를 우선한다.

현재 정식 릴리즈는 BLOCKED이며 실제 Discord/다른 Windows/Maple 병행/24시간은 검증되지 않았다. 기존 HF 원본은 그대로 쓸 수 있다. 개발 QA에서 만든 동일 텐서 shard 복사본은 AI 모델 화면의 폴더 선택으로 별도 등록할 수 있지만 운영 설정을 자동 전환하지 않았다. 복사본은 추가 약22.28GiB 디스크가 필요하며 패키지에 포함되지 않는다. 부족한 자원은 안내하고 페이지 파일·다른 프로그램을 자동 변경하지 않는다.

상세 근거·실패·미검증·재현·마감: [최종 안정화 QA](STABILIZATION-QA.md). 아래 이전 차수의 숫자는 당시 기록이다.


Portable은 릴리즈 승인 전 검증 후보다. 설치 프로그램/자동 업데이터/깨끗한 VM 지원 완료를 선언하지 않는다. 후보 폴더에 Python·의존성이 있고 모델은 없다. 소스 실행에는 기존 가상환경이 필요하다.

1. Portable 폴더 전체를 보존해 EchoMate.vbs를 실행한다. runtime/src/docs/models를 따로 떼거나 runtime만 교체하지 않는다.
2. 처음 사용 안내에서 본인의 공식 Bot을 만든다. [Developer Portal](https://discord.com/developers/applications)의 Bot 화면에서 Message Content Intent를 켠다. Members/Presence Intent는 요구하지 않는다.
3. OAuth2 설치에 bot·applications.commands를 사용하고 채널 보기·기록 보기·메시지/스레드 송신·반응 추가만 허용한다. Administrator 전체 권한은 필요 없다. [공식 설치 문서](https://discord.com/developers/docs/topics/oauth2), [Gateway](https://github.com/discord/discord-api-docs/blob/main/developers/events/gateway.mdx).
4. 본인 Discord User ID(Discord 개발자 모드의 ID 복사)와 Bot Token을 앱에 입력한다. 토큰은 채팅/이슈에 보내지 않는다. 새 설치는 Windows DPAPI 사용자 범위로 저장한다. 동일 Windows 계정은 로컬 신뢰 경계이며 같은 계정의 악성 프로그램으로부터 완전한 격리를 보장하지 않는다.
5. 공식 Gemma4 12B 파일을 라이선스를 확인해 준비한다. models 폴더 또는 AI 모델의 폴더 선택을 사용한다. HF 캐시가 있으면 다시 다운로드하지 않는다. 앱은 가중치를 다운로드하지 않는다. GGUF/LoRA는 현재 실행 불가다.
6. 캐릭터를 고르고 미리보기를 확인한다. 대화할 곳에서 직접 새로고침해야 서버 목록을 요청한다. 허용 범위를 저장하고 봇을 시작한다. 목록 선택만으로 발언을 허용하지 않는다.
7. 구성원은 /동의에서 친밀도/장기 기억/요약을 각각 관리한다. 소유자는 대신 켤 수 없다. [동의와 삭제](PRIVACY-COMMANDS.md).

## 자료 위치와 업데이트

소스 실행은 기존 local_data/bot를 유지한다. Portable은 `%LOCALAPPDATA%/EchoMate/local_data`에 저장하며 프로그램과 분리한다. 모델은 프로그램/models 또는 지정 폴더다. 다른 PC의 DB·토큰을 공유하지 않는다. 개발 폴더를 Portable로 자동 이전/삭제하지 않는다. 수동 이전은 앱 종료·백업·서명 키와 Windows 계정 DPAPI 제약을 고려한 별도 절차가 필요하다.

업데이트는 새 프로그램 폴더에 풀어 사용자 데이터 경로를 유지한다. 자동 업데이트/제거 도구는 없다. 프로그램을 지워도 AppData 자료와 외부 모델은 남는다. 동의 없이 DB/모델을 자동 삭제하지 않는다. 백업에는 토큰/서명 키가 포함될 수 있으므로 공개하지 않는다.

## 하드웨어

기존 검증 PC는 RTX4070Ti SUPER16GB/RAM32GB, Python3.10.11·Torch2.9.1+cu128이다. GPU 드라이버는 별도 필요하다. 다른 GPU/CPU-only/깨끗한 Windows10·11은 미검증이다. Portable 약5GiB 외에 원본 모델 약22GiB 이상과 자료 여유가 필요하다. Windows commit 부족1455로 새 기본 모델 최종 검증을 마치지 못했다. 다른 프로그램을 임의 종료하지 않으며 작업을 마친 뒤 메모리 여유를 확보해 준비해야 한다. 시스템 설정을 앱이 임의 변경하지 않는다.
