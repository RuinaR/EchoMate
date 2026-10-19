# UI 컨트롤 정적 연결 목록

소스의 button/toggle/choices/form 호출 지점을 모두 열거한다. 반복 생성되는 항목은 하나의 호출 지점으로 표시한다. **실제 클릭·Controller·DB/API 성공을 전수 검증했다는 뜻이 아니다.** 기능별 확인과 미검증은 [UI 기능 감사](UI-FUNCTIONAL-AUDIT.md)를 따른다.

정적 호출 지점 75개. Tk Entry 입력란과 SelectionList의 각 데이터 행은 포함하지 않는다. 동적 항목·중첩 콜백은 소스를 확인해야 한다.

|소스 위치|종류|표시 또는 분류|확인된 메서드 참조|실행 검증|
|---|---|---|---|---|
|[render:283](../src/echomate_bot/desktop_ui.py#L283)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[render:284](../src/echomate_bot/desktop_ui.py#L284)|button|봇 끄기|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[render:271](../src/echomate_bot/desktop_ui.py#L271)|button|동적 항목 · 소스 참조|set_page|개별 PASS 미부여|
|[render:289](../src/echomate_bot/desktop_ui.py#L289)|toggle|응답 허용|set_value|개별 PASS 미부여|
|[draw_spaces:311](../src/echomate_bot/desktop_ui.py#L311)|button|새로고침|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_spaces:334](../src/echomate_bot/desktop_ui.py#L334)|button|동적 항목 · 소스 참조|save_scope|개별 PASS 미부여|
|[draw_spaces:335](../src/echomate_bot/desktop_ui.py#L335)|button|동적 항목 · 소스 참조|change_guild|개별 PASS 미부여|
|[draw_spaces:313](../src/echomate_bot/desktop_ui.py#L313)|button|동적 항목 · 소스 참조|toggle_channel_view|개별 PASS 미부여|
|[draw_spaces:318](../src/echomate_bot/desktop_ui.py#L318)|button|동적 항목 · 소스 참조|edit_name|개별 PASS 미부여|
|[draw_spaces:319](../src/echomate_bot/desktop_ui.py#L319)|button|별명·시간대 설정|server_options|개별 PASS 미부여|
|[draw_spaces:327](../src/echomate_bot/desktop_ui.py#L327)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_spaces:329](../src/echomate_bot/desktop_ui.py#L329)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_spaces:332](../src/echomate_bot/desktop_ui.py#L332)|toggle|이 채널의 스레드도 적용|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[choices:339](../src/echomate_bot/desktop_ui.py#L339)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[number:343](../src/echomate_bot/desktop_ui.py#L343)|button|−|set_value|개별 PASS 미부여|
|[number:344](../src/echomate_bot/desktop_ui.py#L344)|button|+|set_value|개별 PASS 미부여|
|[draw_character:349](../src/echomate_bot/desktop_ui.py#L349)|choices|동적 항목 · 소스 참조|set_value|개별 PASS 미부여|
|[draw_character:351](../src/echomate_bot/desktop_ui.py#L351)|choices|동적 항목 · 소스 참조|set_value|개별 PASS 미부여|
|[draw_character:353](../src/echomate_bot/desktop_ui.py#L353)|choices|동적 항목 · 소스 참조|set_value|개별 PASS 미부여|
|[draw_character:359](../src/echomate_bot/desktop_ui.py#L359)|button|프로필 편집·복제|edit_profile|개별 PASS 미부여|
|[draw_character:360](../src/echomate_bot/desktop_ui.py#L360)|button|저장한 프로필|profile_library|개별 PASS 미부여|
|[draw_character:361](../src/echomate_bot/desktop_ui.py#L361)|button|로컬 미리보기|character_preview|개별 PASS 미부여|
|[draw_character:362](../src/echomate_bot/desktop_ui.py#L362)|button|가져오기·내보내기|profile_files|개별 PASS 미부여|
|[draw_character:363](../src/echomate_bot/desktop_ui.py#L363)|toggle|성인 유머 · 연령 제한 채널에서만|set_value|개별 PASS 미부여|
|[draw_character:364](../src/echomate_bot/desktop_ui.py#L364)|button|표현 고급 설정|advanced_profile|개별 PASS 미부여|
|[draw_setup:372](../src/echomate_bot/desktop_ui.py#L372)|button|동적 항목 · 소스 참조|setup_credentials|개별 PASS 미부여|
|[draw_setup:373](../src/echomate_bot/desktop_ui.py#L373)|button|모델 확인하기|set_page|개별 PASS 미부여|
|[setup_credentials:377](../src/echomate_bot/desktop_ui.py#L377)|form|내 봇 정보 등록|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_models:387](../src/echomate_bot/desktop_ui.py#L387)|button|모델 폴더 선택|choose_model_folder|개별 PASS 미부여|
|[draw_models:388](../src/echomate_bot/desktop_ui.py#L388)|button|다시 검색|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_models:390](../src/echomate_bot/desktop_ui.py#L390)|button|기본 모델 사용|set_value|개별 PASS 미부여|
|[draw_models:405](../src/echomate_bot/desktop_ui.py#L405)|button|검증 후 적용|set_value|개별 PASS 미부여|
|[edit_profile:427](../src/echomate_bot/desktop_ui.py#L427)|form|캐릭터 편집 · 복제해서 저장|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[advanced_profile:468](../src/echomate_bot/desktop_ui.py#L468)|form|표현 고급 설정|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[profile_files:477](../src/echomate_bot/desktop_ui.py#L477)|form|프로필 파일|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[approve_commands:512](../src/echomate_bot/desktop_ui.py#L512)|form|다음 연결의 명령 정리 승인|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_status:523](../src/echomate_bot/desktop_ui.py#L523)|button|개인정보 없는 진단 저장|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_outputs:573](../src/echomate_bot/desktop_ui.py#L573)|button|Discord 명령 정리 승인|approve_commands|개별 PASS 미부여|
|[draw_outputs:572](../src/echomate_bot/desktop_ui.py#L572)|toggle|동적 항목 · 소스 참조|set_value|개별 PASS 미부여|
|[draw_labs:581](../src/echomate_bot/desktop_ui.py#L581)|toggle|이미지 내용 분석을 시험해 보기|set_value|개별 PASS 미부여|
|[draw_labs:582](../src/echomate_bot/desktop_ui.py#L582)|button|이 서버 캐시 비우기|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_labs:583](../src/echomate_bot/desktop_ui.py#L583)|button|선택 범위 다시 분석 · 최대5개|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[member_alias_editor:42](../src/echomate_bot/companion_ui.py#L42)|form|이 사람의 호칭 관리|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[server_options:82](../src/echomate_bot/companion_ui.py#L82)|form|이 서버의 호칭과 시간대|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[edit_record:101](../src/echomate_bot/companion_ui.py#L101)|form|친밀도 조절|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[edit_record:115](../src/echomate_bot/companion_ui.py#L115)|form|기억 확인·수정|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[edit_record:109](../src/echomate_bot/companion_ui.py#L109)|form|기억 직접 추가|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[edit_record:121](../src/echomate_bot/companion_ui.py#L121)|form|알림 수정|record_action|개별 PASS 미부여|
|[reset_records:130](../src/echomate_bot/companion_ui.py#L130)|form|기록 삭제 확인|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_records:139](../src/echomate_bot/companion_ui.py#L139)|toggle|동적 항목 · 소스 참조|set_value|개별 PASS 미부여|
|[draw_records:140](../src/echomate_bot/companion_ui.py#L140)|button|목록 새로고침|refresh_records|개별 PASS 미부여|
|[draw_records:183](../src/echomate_bot/companion_ui.py#L183)|button|전체 사용자|refresh_records|개별 PASS 미부여|
|[draw_records:184](../src/echomate_bot/companion_ui.py#L184)|button|선택 수정|edit_record|개별 PASS 미부여|
|[draw_records:198](../src/echomate_bot/companion_ui.py#L198)|button|이 사람 초기화|reset_records|개별 PASS 미부여|
|[draw_records:199](../src/echomate_bot/companion_ui.py#L199)|button|서버 전체 초기화|reset_records|개별 PASS 미부여|
|[draw_records:200](../src/echomate_bot/companion_ui.py#L200)|button|만료 기록 정리|record_action|개별 PASS 미부여|
|[draw_records:186](../src/echomate_bot/companion_ui.py#L186)|button|동적 항목 · 소스 참조|edit_record, show_legacy_summaries|개별 PASS 미부여|
|[draw_records:187](../src/echomate_bot/companion_ui.py#L187)|button|검색·종류|form, search_records|개별 PASS 미부여|
|[draw_records:188](../src/echomate_bot/companion_ui.py#L188)|button|동적 항목 · 소스 참조|cycle_record_status|개별 PASS 미부여|
|[draw_records:196](../src/echomate_bot/companion_ui.py#L196)|button|동적 항목 · 소스 참조|remove_record|개별 PASS 미부여|
|[draw_records:197](../src/echomate_bot/companion_ui.py#L197)|button|별명·시간대|server_options|개별 PASS 미부여|
|[draw_records:202](../src/echomate_bot/companion_ui.py#L202)|button|일시 문맥 지우기|record_action|개별 PASS 미부여|
|[draw_records:203](../src/echomate_bot/companion_ui.py#L203)|toggle|이전 관련 발췌 사용|set_value|개별 PASS 미부여|
|[draw_records:204](../src/echomate_bot/companion_ui.py#L204)|button|보관·요약 설정|memory_defaults|개별 PASS 미부여|
|[draw_records:190](../src/echomate_bot/companion_ui.py#L190)|button|동적 항목 · 소스 참조|cycle_record_status|개별 PASS 미부여|
|[draw_records:191](../src/echomate_bot/companion_ui.py#L191)|button|유예 시간|form, set_value|개별 PASS 미부여|
|[draw_records:187](../src/echomate_bot/companion_ui.py#L187)|form|기억·요약 검색|search_records|개별 PASS 미부여|
|[draw_records:193](../src/echomate_bot/companion_ui.py#L193)|button|호칭 추가·관리|member_alias_editor|개별 PASS 미부여|
|[draw_records:194](../src/echomate_bot/companion_ui.py#L194)|button|대화 요약 보기|show_summaries|개별 PASS 미부여|
|[draw_records:191](../src/echomate_bot/companion_ui.py#L191)|form|늦어진 알림 처리|set_value|개별 PASS 미부여|
|[memory_defaults:226](../src/echomate_bot/companion_ui.py#L226)|form|새 기억의 기본 만료 기간|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[show_digest:241](../src/echomate_bot/companion_ui.py#L241)|form|대화 요약 · 출처가 있는 압축 기록|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[show_legacy_summaries:246](../src/echomate_bot/companion_ui.py#L246)|form|선택한 사람의 발언 요약 · 로컬 조회|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[remove_record:260](../src/echomate_bot/companion_ui.py#L260)|form|선택한 기록 삭제|confirm_remove|개별 PASS 미부여|
|[remove_record:255](../src/echomate_bot/companion_ui.py#L255)|form|대화 요약 삭제|record_action|개별 PASS 미부여|
