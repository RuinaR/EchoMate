# UX 검토 — 2026-10-20

공식 문서에서 참고한 구조와 이번 적용 범위다. 다른 앱을 설치하거나 사용자 화면을 조작하지 않았다.

- [LM Studio 시작 안내](https://lmstudio.ai/docs/app/basics), [메모리의 모델 관리](https://lmstudio.ai/docs/python/manage-models/loading): 설치된 모델과 메모리에 로딩된 모델을 구분한다. EchoMate도 파일 검사·설정 선택·GPU 준비를 서로 다른 상태로 표현한다.
- [Open WebUI 설정 구분](https://docs.openwebui.com/getting-started/quick-start/settings/), [모델 Workspace](https://docs.openwebui.com/features/workspace/models/): 관리자 정책과 개인 표현 설정을 구분한다. EchoMate의 모델/캐릭터/권한 분리를 유지한다. 개인 설정이 필수 안전·동의 정책을 덮어쓰도록 바꾸지 않는다.

이번 채택: AI 모델 상세에서 실제 largest_shard_bytes와 총 bytes를 비교해 분할 가중치를 표시하고 단위를 GiB로 정정했다. 파일 검사를 통과해도 GPU 준비는 적용 시 별도 확인한다고 명시한다. 모델별 미측정 메모리 수치를 일괄 보장하지 않는다.

기억 목록은 새 필터가 반영되기 전 옛 결과를 보여주지 않으며, 사라진 선택으로 수정/삭제 버튼이 활성화되지 않도록 했다. 캐릭터 저장이 실패했는데 적용만 진행되는 동작을 막았다. 이는 상태의 신뢰성을 우선하는 개선이다.

이번에는 전체 정보 구조 변경, 디자인 복제, 새 UI 프레임워크 도입을 하지 않았다. 모든 설정 문구·팝업·접근성을 완전히 검토했다는 의미는 아니다. 범위와 미완료는 [기능 연결 감사](UI-FUNCTIONAL-AUDIT.md)를 따른다.
