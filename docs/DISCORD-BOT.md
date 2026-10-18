# Windows Discord Bot 실행과 검증

2026-10-19. 공식 Bot 계정만 사용한다. 모델 품질 확정/운영 승격과 테스트 연결은 별개다. 현재 잠정 rank8-60은 보존하며 실사용 품질은 미확정이다. 이 문서는 테스트 서버부터 연결하는 절차다.

## 최초 설정

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 Application/Bot을 만들고 Bot 탭의 **Message Content Intent**를 켠다. Presence/Members Intent는 필요 없다. 토큰은 채팅·스크린샷·명령줄 인자로 보내지 않는다.
2. OAuth2 URL Generator에서 `bot`, `applications.commands`를 선택한다. 테스트 서버에서 View Channels, Send Messages, Read Message History를 허용한다. 반응은 Add Reactions, 미디어는 Attach Files, 스레드는 Send Messages in Threads를 추가한다. Administrator/Manage Messages/Manage Channels/외부 이모지·스티커 권한은 요청하지 않는다. 위 선택 권한을 모두 쓰는 비트 값은 `274878008384`다.
3. Discord 설정 → 고급 → 개발자 모드를 켠 뒤 **자신의 사용자 ID**, 테스트 서버 ID, 테스트 텍스트 채널 ID를 복사한다. 닉네임으로 인증하지 않는다.
4. 저장소 루트 PowerShell에서 `./tools/setup_discord_bot.ps1` 실행. 보안 입력 프롬프트에 공식 Bot Token을 넣는다. 생성되는 `local_data/bot/bootstrap.json`에 소유자·관리 서버·토큰·서명 키가 저장된다. Windows ACL 상속을 제거하고 현재 Windows 계정/SYSTEM만 허용한다. 설정 디렉터리를 다른 계정과 공유하지 않는다.
5. `./tools/start_discord_bot.ps1` 실행. 공식 Gateway에 연결하고 등록한 관리 서버에만 슬래시 명령을 동기화한다. 설정 기본은 **정지**, 테스트 채널은 **멘션만**이다. `/echo panel`에서 활성화하거나 `/echo set key:enabled value:true`를 실행한다. 채널에 봇을 실제로 멘션해 시험한다. 일반 서버 전체를 자동 활성화하지 않는다.

기존 `.venv-gemma4`에 `configs/bot-requirements.txt`의 discord.py/aiohttp를 추가한다. 기존 torch/transformers를 무작정 업그레이드하지 않는다. 현재 검증 환경은 torch 2.9.1+cu128와 torchvision 0.24.1+cu128 조합이다. torchvision은 `python -m pip install torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cu128 --no-deps`로 별도 설치한다. 모델은 캐시된 Gemma만 읽으며 실행 시 자동 다운로드하지 않는다.

토큰/서명 키/소유자는 슬래시 명령이나 mutable 설정으로 바꿀 수 없다. 로컬 bootstrap은 신뢰 경계다. 같은 Windows 계정을 통제하는 공격자로부터 비밀을 보호한다고 주장하지 않는다. 설정 파일을 직접 편집하면 서명 검사가 실패한다. 설정을 고치려면 정상 소유자 명령을 사용한다. 손상 파일은 백업 후 소유자가 로컬에서 복구하며 기존 모델/학습 파일을 삭제하지 않는다. bootstrap 재설정은 새 키를 만들기 때문에 기존 서명된 설정/미디어 승인을 자동 복구하지 않는다.

## 소유자 관리

모든 `/echo` 명령과 패널 동작은 서버 측에서 소유자 ID 및 로컬 관리 서버를 확인한다. 응답은 ephemeral이다. 슬래시 명령 이름 자체를 모든 일반 사용자에게 숨긴다고 보장하지는 않는다. Discord 서버 설정 → Integrations에서 소유자에게만 명령 사용을 허용하면 발견 범위도 줄일 수 있다. 서버 관리자라는 이유만으로 소유자 검사를 통과하지 않는다.

| 명령/설정 | 용도 |
|---|---|
| `/echo panel` | 상태, 활성/중지, 7가지 기분 선택 |
| `/echo set` | 설정 키/값. boolean은 true/false |
| `mood` | 평온/기쁨/신남/우울/화남/피곤함/부끄러움 |
| `warmth`, `cuteness`, `playfulness` | 0..100, 기본 75/40/20 |
| `auto_mood` | 기본 false. true일 때 축하/휴식 표현에 한정한 일시적 연출; 사람 감정 추론/영구 프로필 아님 |
| `model` | base/persona. 같은 GPU 모델에서 어댑터 활성/비활성. 임의 모델 경로 실행 금지 |
| `text`, `reactions`, `stickers`, `media`, `vision` | 별도 토글. text 외 기본 false |
| `activity` | quiet/normal/active/very_active. 적절성 검사 후 신규 참여 확률만 변경 |
| `cooldown`, `engagement_seconds` | 기본 60초/600초. 대화 중임을 문맥으로 확인해야 지속 |
| `media_probability`, `daily_limit` | 자동 미디어 제안 기회 기본 .05, 모든 출력 일일 상한 기본 100 |
| `/echo guild` | 현재 관리 서버 활성/비활성 |
| `/echo scope` | 현재 서버의 채널/스레드와 silent/mention/autonomous/reaction 선택 |
| scope의 `inherit` | 부모 채널에서 명시적으로 true일 때만 미등록 하위 스레드 상속. 스레드의 명시적 silent가 우선 |
| `/echo cache` | 현재 서버 캐시 삭제. refresh=true는 허용 채널+vision 활성 상태에서 실제 에셋 분석, offset으로 50개씩 갱신 |
| `/echo media_add` | 소유자가 첨부한 승인 파일 검증·실제 분석 후 등록 |
| `/echo media` | list/delete/tags/purpose/enabled/cooldown/guilds. 허용 서버 목록은 로컬 관리 서버에 한정 |
| `/echo shutdown` | 안전한 종료. 다시 시작은 Windows 스크립트 사용 |

등록 파일은 최대 8MiB, 라이브러리 100개/128MiB, 기본 파일별 재사용 쿨다운 1시간이다. 수신 첨부/시각 캐시는 송신 승인으로 승격되지 않는다. 캐시된 에셋 이름만으로 시각적 의미를 추정하지 않는다. 커스텀 이모지·스티커는 **현재 서버 소유 에셋만**, 정상 권한/존재/시각 분석 확인 후 사용한다.

## 시각 기능과 자원 제한

PNG/JPEG/GIF/WebP 및 Pillow에서 읽을 수 있는 APNG를 지원한다. 일반 첨부, 서버 커스텀 이모지/움직이는 이모지, PNG/APNG/GIF 서버 스티커, 검증한 Discord CDN 또는 Discord 이미지 프록시 임베드를 읽는다. **Lottie/JSON 스티커는 미지원**이며 이름만으로 이해한 척하지 않는다. 임의 외부 URL과 리다이렉트는 다운로드하지 않는다.

8MiB/이미지 12MP/최대 변 8192/애니메이션 200프레임 및 전체 픽셀 작업량 48MP 제한. 서로 다른 최대 4프레임을 시간 순서로 샘플링하고 640px로 줄인다. 표본 밖의 움직임은 확정하지 않는다. 시각 분석은 기본 가중치를 사용하며 텍스트 어댑터와의 호환 시험은 별도 기록한다. structured JSON 실패/미완결/채널 제어 혼입이면 해당 분석은 실패로 처리한다.

현재 모델 캐시에 modality processor 파일이 없으면 설치된 Gemma4Unified 구현의 기본 전처리와 캐시된 vision 크기 설정으로 로컬 구성한다. 별도 공개 processor artifact와 동등성은 미확인이다. 실제 GPU 결과/제약은 ML-EXPERIMENTS와 로컬 gpu-smoke 기록을 확인한다. 실제 사진·감정·스티커 이해 정확성은 합성 도형 성공만으로 검증되지 않는다.

GPU 작업은 단일 worker로 직렬화하고 최대 12개 대기 요청만 받는다. 수신 이벤트는 추론 완료를 기다리지 않는다. 최대 32개 활성 대화, 대화당 100턴/1시간, 모델 입력 6,000토큰 상한. 새 메시지/권한·설정·스레드 변경은 낡은 출력을 폐기한다. GPU 85도, GPU 여유 512MiB 미만, RAM 여유 2GiB 미만이면 안전 중단한다. OOM은 추론을 비활성화하고 프로세스 재시작을 요구한다. 모델당 generate 최대 시간은 90초이며 한 대화 턴은 여러 판정/생성 호출을 포함할 수 있다.

SQLite 송신 예약은 이벤트 중복·쿨다운·일일 상한을 재시작 후에도 유지한다. Discord nonce를 메시지 ID로 고정한다. 애매한 HTTP 실패는 앱에서 재송신하지 않는다. 텍스트+반응은 Discord의 원자 트랜잭션이 아니므로 일부만 성공할 수 있다. 3회 연속 실패 시 안전 정지하고 문제 에셋 재사용을 차단한다. 에셋 수정 후 소유자 cache 명령/프로세스 재시작으로 재검토한다.

## 단계별 실제 QA

- A: 테스트 서버 로그인/ready, 소유자 명령 허용·다른 사용자 거절, 테스트 채널 멘션 송수신, 미허용 채널 무응답.
- B: 명시적 멘션/답장/이어지는 질문, 새 메시지 도착 중 취소, 두 채널 동시 입력, 기분/활동 설정, 네트워크 재연결 후 과거 응답 미재생.
- C: Unicode 반응만, 이름을 가린 커스텀 이모지/스티커의 실제 이미지 의미, 다중 프레임 GIF, 승인 미디어만 송신, 삭제 에셋 거절.
- D: 권한 철회·보관/삭제 스레드, 다운로드 실패/잘못된 파일, 큐 상한, GPU OOM 시 침묵, 장시간 안정성.

외부 메시지는 테스트 서버/허용 채널에만 발송한다. 설정 도구 실행과 기본 정지 상태의 로그인만으로 실제 메시지 QA 성공을 선언하지 않는다. 실제 QA 기록은 CURRENT-STATUS/WORKLOG가 기준이다. 로그에는 토큰/메시지/URL 대신 최소 이벤트 코드만 남기며 `local_data/bot/diagnostics.json`, `performance.json`은 비공개다.
