# UX 검토 — 2026-10-20

공식 문서에서 참고한 구조와 이번 적용 범위다. 다른 앱을 설치하거나 사용자 화면을 조작하지 않았다.

- [LM Studio 시작 안내](https://lmstudio.ai/docs/app/basics), [메모리의 모델 관리](https://lmstudio.ai/docs/python/manage-models/loading): 설치된 모델과 메모리에 로딩된 모델을 구분한다. EchoMate도 파일 검사·설정 선택·GPU 준비를 서로 다른 상태로 표현한다.
- [Open WebUI 설정 구분](https://docs.openwebui.com/getting-started/quick-start/settings/), [모델 Workspace](https://docs.openwebui.com/features/workspace/models/): 관리자 정책과 개인 표현 설정을 구분한다. EchoMate의 모델/캐릭터/권한 분리를 유지한다. 개인 설정이 필수 안전·동의 정책을 덮어쓰도록 바꾸지 않는다.
- [Windows 진행 상태 지침](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/progress-controls): 완료량을 모르면 진행 중과 실제 단계를 표시하고 허구의 백분율을 만들지 않는다. EchoMate도 큐 대기·생성·전송을 별도로 유지한다. 새 progress 위젯을 구현했다는 의미는 아니다.
- [Discord 통합 관리](https://support.discord.com/hc/en-us/articles/360045093012-Server-Integrations-Page): 설치된 앱과 요청한 권한을 구분해 안내한다. EchoMate의 활동 허용 목록과 Discord 권한을 같은 설정으로 오해하지 않도록 검토했다. 실제 서버를 조회하지 않았다.
- [Microsoft To Do 알림 설정](https://support.microsoft.com/en-us/todo/add-due-dates-and-reminders-in-microsoft-to-do): 일정 날짜와 알림 시점을 구별한다. EchoMate는 표시 시간대·예약 상태·실패/만료를 구분하며, 새로운 일정 관리 기능을 추가하지 않았다.

이번 채택: AI 모델 상세에서 실제 largest_shard_bytes와 총 bytes를 비교해 분할 가중치를 표시하고 단위를 GiB로 정정했다. 파일 검사를 통과해도 GPU 준비는 적용 시 별도 확인한다고 명시한다. 모델별 미측정 메모리 수치를 일괄 보장하지 않는다.

기억 목록은 새 필터가 반영되기 전 옛 결과를 보여주지 않으며, 사라진 선택으로 수정/삭제 버튼이 활성화되지 않도록 했다. 캐릭터 저장이 실패했는데 적용만 진행되는 동작을 막았다. 이는 상태의 신뢰성을 우선하는 개선이다.

이번에는 전체 정보 구조 변경, 디자인 복제, 새 UI 프레임워크 도입을 하지 않았다. 모든 설정 문구·팝업·접근성을 완전히 검토했다는 의미는 아니다. 범위와 미완료는 [기능 연결 감사](UI-FUNCTIONAL-AUDIT.md)를 따른다.

## 최종 조정

고정 행 높이를 실제 글꼴 높이에 맞춰 DPI 겹침을 제거했다. 긴 상태와 모델 경로는 요약 표시와 읽기 전용 상세로 분리했다. 긴 설정 창은 스크롤·포커스 이동을 지원하며, 요약 조회 창의 무의미한 적용 동작은 읽기 전용 닫기로 교체했다. 마지막 관리 실패를 새로고침 뒤에도 확인할 수 있다. 실제 사용자 가독성 평가는 미검증이다.
