# Windows Discord Bot 실행과 검증

## 최신 — 이름으로 부르기 (2026-10-19)

앱에서 서버별 이름을 저장하면 해당 서버에서만 적용한다. 공식 Bot의 자기 Member.edit(nick=...)를 사용하며 다른 사람 이름은 변경하지 않는다. [discord.py Member.edit](https://discordpy.readthedocs.io/en/stable/api.html#discord.Member.edit) 및 [Discord Guild API](https://docs.discord.com/developers/resources/guild#modify-current-member)를 따른다. 자기 닉네임 변경 권한을 확인한다. 권한 실패 코드는 비공개 진단에 남고 이름 설정 자체는 보존된다.

이름 전체/봇 접미사 생략/한국어 호격을 후보로 인식한다. 코드/인용/URL의 예시는 호출로 취급하지 않는다. 후보만으로 전송하지 않고 현재 화자/대상·참여 적절성을 의미 판단한다. mention 전용 허용 채널에서도 처음 이름을 부르면 응답할 수 있다. 새 진입 확률과 독립이지만 권한/빈도/일시정지/민감 상황/최신 상태 검사는 유지한다. 다른 사람을 부른 것이라는 정정에는 간단히 착각을 인정하도록 지시한다. 동명이인·철자 변형의 정확한 인식과 실제 Discord 응답 품질은 아직 미검증이다.

2026-10-19 최신 기준. 현재 모델은 rank8 q/k/v/o 60단계 잠정 후보이며 품질 승인은 별개다. 등록 미디어는 제거했고 기본 에셋과 실험 시각 분석을 분리했다.

## 기존 설정이 있는 경우

`EchoMate.cmd`를 더블 클릭하거나 `tools/start_echomate_app.ps1`을 실행한다. 앱은 사용자가 닫은 상태로 유지했다. 시작 전에도 공식 Bot REST로 초대된 서버/채널/활성 스레드 목록을 불러오며 본문/이미지는 수집하지 않는다. `봇 켜기`를 눌러야 모델/Gateway와 응답을 시작한다. 첫 모델 준비는 약35~40초다. [처음부터 따라 하는 테스트](TESTING-DISCORD-APP.md).

1. **대화할 곳**에서 서버와 채널/활성 스레드를 선택한다. Ctrl+클릭으로 여러 곳을 선택하고 채팅/반응 규칙을 저장한다. 선택만으로 활성화되지 않는다. 부모 채널을 고르면 스레드 적용도 선택할 수 있다.
2. **응답 방식**에서 글/이모지/Discord 기본 스티커를 고르고 **성격과 기분**에서 기분·성격·먼저 참여하는 정도·시간·모델을 조정한다. 변경은 재시작 없이 적용한다. 멘션 전용에서도 확인된 후속 대화는 이어가며, 새로운 참여에는 자연스럽게 대화에 참여를 고른다.
3. **진행 상황**에서 단계/경과/대기/최근 답변 시간을 확인한다. 본문/토큰은 표시하지 않는다. 긴 기술 설명은 여전히 느릴 수 있다. Discord에는 작성 중 표시를 보내지만 이를 실제 속도 개선으로 세지 않는다.
4. **실험 기능**은 이미지 분석 하나의 토글이다. 기본 OFF이며 과거 QA의 vision=true를 자동 계승하지 않는다. 응답 일시정지는 문맥을 유지하고, 봇 끄기는 모델/이력을 정리한다.

패널·목록·버튼·토글은 Canvas로 직접 그렸다. 참고 구조/키보드/접근성 제한은 [DESKTOP-UI](DESKTOP-UI.md)를 확인한다. 앱과 CLI의 중복 실행은 파일 잠금으로 차단한다. 별도 QA 도구는 먼저 종료하고 시작한다. 로컬 앱은 bootstrap을 읽을 수 있는 같은 Windows 계정이 권한 경계다. 공개 HTTP 관리 포트는 열지 않는다.

## 최초 설정

이미 설정했다면 bootstrap을 덮어쓰거나 setup을 다시 실행하지 않는다.

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 공식 Application/Bot을 만들고 Message Content Intent를 켠다. Members/Presence Intent와 self-bot은 사용하지 않는다. 토큰을 채팅·명령줄 인자·스크린샷으로 보내지 않는다.
2. OAuth2에서 bot/applications.commands를 고른다. View Channels, Send Messages, Read Message History, Add Reactions, Send Messages in Threads만 요청한다. 파일 첨부 기능은 제거돼 Attach Files가 필요 없다. Administrator/Manage 권한이나 외부 커스텀 에셋 권한을 요청하지 않는다.
3. 개발자 모드에서 자신의 User ID, 테스트 서버 ID, 테스트 채널 ID를 복사한다. 닉네임으로 인증하지 않는다.
4. PowerShell에서 `tools/setup_discord_bot.ps1`을 실행하고 공식 토큰을 보안 입력에 넣는다. local_data/bot/bootstrap.json의 ACL을 현재 Windows 계정/SYSTEM으로 제한한다. 토큰/서명 키/owner ID는 mutable 설정 밖에 있다.
5. 앱 또는 `tools/start_discord_bot.ps1`로 연결한다. 기본은 정지와 테스트 채널 멘션 전용이다. 다른 서버/채널을 자동 활성화하지 않는다.

기존 venv와 모델 캐시만 사용한다. configs/bot-requirements.txt 의존성과 현재 torch 2.9.1+cu128 / torchvision 0.24.1+cu128 조합을 유지하며 무작정 업그레이드하지 않는다. 실행 중 모델을 자동 다운로드하거나 학습하지 않는다. 같은 Windows 계정이 공격자에게 넘어간 상황의 비밀 보호는 보장하지 않는다. 설정을 직접 편집하면 HMAC 검사가 실패한다.

## 소유자 관리

모든 `/echo` 명령/패널은 실제 Discord User ID와 등록된 관리 서버를 검사하고 ephemeral로 답한다. 서버 관리자 권한만으로 검사를 통과할 수 없다. GUI는 현재 초대 서버 목록에서 소유자가 직접 범위를 적용할 수 있으며, 슬래시 명령 등록은 bootstrap 관리 서버에 한정한다.

| 명령/설정 | 용도 |
|---|---|
| `/echo panel` | 활성/중지·상태·기분 |
| `/echo set` | mood, warmth, cuteness, playfulness, auto_mood, model, text, reactions, stickers, vision, activity, cooldown, engagement_seconds, daily_limit, enabled |
| `vision` | 실험 이미지 분석. 기본 OFF, 커스텀 에셋 전송 허용과 무관 |
| `model` | 신뢰된 base/persona만. 임의 모델 코드/경로 실행 금지 |
| `activity` | quiet/normal/active/very_active. 신규 참여 기회만 조절 |
| `/echo guild`, `/echo scope` | 관리 서버 활성/범위. GUI는 채팅/반응을 독립 설정하며 legacy scope 명령은 공통 모드를 설정 |
| `/echo cache` | 실험 시각 캐시 삭제/갱신. 허용 범위+실험 ON에서만 실제 분석. 기본 5개, limit 1~10/offset |
| `/echo shutdown` | 안전 종료 |

`media_add`/`media` 명령과 등록/승인/파일 전송 코드는 제거했다. 기존 private 미디어 파일과 이전 실험 결과는 삭제하지 않았다.

## 기본 에셋과 실험 시각 기능

일반 인식/사용은 Unicode 이모지와 Discord **STANDARD** 기본 스티커다. 기본 스티커는 공식 팩의 설명·태그로 구분하고 실제 픽셀을 봤다고 주장하지 않는다. 서버 **GUILD** 스티커와 커스텀/움직이는 이모지는 송신하지 않는다. 팩 조회 실패 시 보수적으로 비활성화한다. 사용 불가능한 스티커는 실패 후 반복 시도하지 않는다. 기본 스티커 실제 송신은 별도 Discord QA가 필요하다.

실험 ON에서만 일반 첨부/커스텀 에셋/PNG·GIF·WebP·APNG/임베드 픽셀을 분석한다. Lottie/JSON 픽셀 분석은 미지원이다. 공식 기본 스티커의 네이티브 전송과 로컬 Lottie 분석 지원은 별개다. 신뢰된 Discord CDN/프록시만 사용하고 임의 외부 URL/redirect는 금지한다. 8MiB, 12MP, 최대 변8192, 애니메이션200프레임/전체48MP 제한, 최대4프레임 시간 순서 샘플링·640px 축소. 불명확한 의미나 표본 밖 움직임을 확정하지 않는다. 실험을 켜도 커스텀 에셋이나 등록 파일을 전송할 수 없다.

현재 캐시에 modality processor 파일이 없어 설치된 Gemma4Unified 기본값+vision 크기 설정을 이용했다. 별도 공식 artifact와 동등성/실제 사진·표정 정확성은 미확인이다. 실험 결과는 ML-EXPERIMENTS와 local_data에 보관한다.

## 대화·지연·안정성

명시적 멘션과 실제 이력에서 확인한 봇 메시지의 Discord 답장은 끼어들기 투표 없이 TEXT 1회 생성이 가능하다. 그 밖의 무멘션 참여/지속에는 문맥 판단을 유지한다. 텍스트는 Discord reply로 보내며 미응답 원래 멘션 ID를 보관해 같은 화자의 추가 메시지가 와도 원래 질문에 답장한다. 대상 삭제/새 문맥/권한 변경/설정 변경 시 낡은 출력은 취소한다. 작성 중 표시의 갱신도 취소하며 부분 모델 출력은 보내지 않는다.

신규 참여 쿨다운 기본60초, 직접 멘션/확인된 지속은2초, 일일 상한100. 같은 화자의 실제 미응답 멘션은30초 내 추가 문맥에 한해 보존한다. 다른 사람의 발언을 멘션으로 추정하지 않는다. 대화당100턴/1시간·최대32채널이며 재시작 후 영구 기억을 보장하지 않는다. 기분 변경은 이력을 보존한다.

단일 GPU worker/최대12 대기, 입력6000토큰, generate 최대90초. OOM/온도85도/여유VRAM512MiB 미만/RAM2GiB 미만은 안전 중단한다. 이벤트 수신은 추론 완료를 기다리지 않는다. 최신 상태/권한/범위/중복/영속 예약/nonce를 전송 직전에 재검사한다. 애매한 HTTP 실패는 재생하지 않는다. 3회 연속 실패는 안전 정지, 텍스트+반응은 원자적이지 않다.

## 단계별 실제 QA

- A: 테스트 서버 연결/소유자·비소유자 권한/미허용 채널 차단/멘션 답장.
- B: 무멘션 후속/다중 화자·채널/지연 원래 질문 reply/생성 취소/재연결.
- C: Unicode 반응과 공식 기본 스티커. 커스텀 송신·등록 파일 전송 거절.
- 실험: OFF에서 이미지 다운로드·분석 없음, ON에서 실제 픽셀/다중 프레임/오류 처리.
- D: 권한 철회·보관/삭제·큐 상한·OOM 장애 주입·장기 안정성.

모의 테스트/단일 GPU 성공을 실제 Discord 품질 승인이라고 보고하지 않는다. 최신 관측은 CURRENT-STATUS/WORKLOG, 비공개 상태와 성능은 local_data/bot에 있다. 운영 서버 발언은 명시적 사용자 허용 범위 밖으로 확대하지 않는다.
