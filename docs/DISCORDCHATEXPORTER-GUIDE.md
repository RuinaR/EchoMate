# DiscordChatExporter 사용 및 데이터 가져오기 지침

작성일: 2026-10-18
대상 도구: DiscordChatExporter v2.48.0 (Windows GUI)
상태: 사용자가 도구 설치 후 토큰 입력 화면을 열었음. 실제 내보내기 및 학습 검증 전.

## 선택한 방식
- Discord Developer Portal의 **공식 봇 계정**을 사용한다.
- 일반 사용자 계정의 `authorization` 헤더/사용자 토큰을 추출하는 self-bot 경로는 사용하지 않는다.
- 서버 관리자의 허락을 받아 필요한 서버/채널에 봇을 설치한다.
- DiscordChatExporter로 권한 내 기록을 **백업·구조 검증**하는 작업과 EchoMate에서 **AI 모델 학습**하는 작업은 엄격히 분리한다.
- Discord 개발자 정책 §21에 따라 API 메시지 내용의 AI/ML 학습은 Discord의 명시적 허가가 있을 때에만 실행한다. 오프라인 LoRA/RAG 구축도 자동 면제되지 않는다.
- Discord 개발자 정책 §16에 따라 API 데이터를 이용해 사용자의 관계·친밀도를 프로파일링하지 않는다.

## 1. 공식 봇 생성 및 초대
1. https://discord.com/developers/applications 에 로그인.
2. New Application → `EchoMate` 생성.
3. Bot 화면에서 토큰을 발급받고 비공개 보관한다. **절대로 GitHub나 채팅에 붙여넣지 않는다.**
4. Bot → Privileged Gateway Intents의 Message Content Intent 활성화. 해당 권한의 사용 가능 여부/요구 승인 사항 확인.
5. Installation 또는 OAuth2에서 Guild Install에 `bot` 및 `applications.commands` 범위 설정.
6. 최소 권한: `View Channels`, `Read Message History`. 운영 중 발언할 경우 `Send Messages` 및 스레드 쓰기 권한 별도 검토.
7. 서버 관리자에게 앱 설치 URL로 초대 요청. 비공개 채널은 접근 대상에서 제외하거나 개별 권한 검토.
8. 본인 봇의 토큰만 DiscordChatExporter 로그인 화면에 넣는다.

## 2. Windows GUI에서 내보내기
1. DiscordChatExporter를 실행한다.
2. 화면 아래의 **To get the token for your bot** 안내에 따라 생성한 봇 토큰을 입력 후 Enter/화살표.
3. 우측 톱니바퀴에서 **Show threads = All** 선택(설치 버전에 따라 명칭이 다를 수 있음).
4. 보이는 서버와 채널 목록 중 관리자와 합의한 백업 대상부터 선택.
5. 내보내기 옵션에서 **JSON** 선택. 학습에 필요하지 않은 다운로드 에셋/첨부는 제외하는 것을 기본값으로 한다.
6. 파일은 PC의 개인 로컬 폴더에 저장, 원본 보호, 해시 계산 및 접근 제어.
7. 누락/오류를 확인한다. 보관 스레드·비공개 스레드·삭제 메시지·권한/접근 제한에 따라 전체 내역이 보장되지 않는다.
8. GitHub에 원본/추출 JSON 업로드 금지.

## 3. 향후 EchoMate Importer 연결
- JSON/CSV 포맷 식별, 서버/채널/스레드/메시지 ID, 작성자 ID, 시각, 본문 구조 점검.
- 작성자별 메타데이터 목록은 **사용 권한 확인된 데이터에서만** 생성하고 실 학습 및 관계 분석과 분리.
- 학습 대상을 선택할 경우 당사자 동의, 데이터 출처, Discord 학습 허가 상태 확인 후에만 훈련/영속 인덱싱 허용.
- 파일 해시, 기록의 마지막 시각, 중복 및 누락, 학습 버전을 구분하여 모델 캐시를 갱신.
- 데이터 미허가 시 import preview/스키마 검증 전용. 학습 버튼 비활성화.

## 4. 주의/공식 출처
- https://github.com/Tyrrrz/DiscordChatExporter
- https://github.com/slatinsky/DiscordChatExporter-frontend
- https://support-dev.discord.com/hc/ko/articles/8563934450327-Discord-%EA%B0%9C%EB%B0%9C%EC%9E%90-%EC%A0%95%EC%B1%85
- https://discord.com/developers/docs
