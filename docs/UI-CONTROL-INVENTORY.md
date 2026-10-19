# UI 컨트롤 정적 연결 목록

소스의 button/toggle/choices/form 호출 지점을 모두 열거한다. 반복 생성되는 항목은 하나의 호출 지점으로 표시한다. **실제 클릭·Controller·DB/API 성공을 전수 검증했다는 뜻이 아니다.** 기능별 확인과 미검증은 [UI 기능 감사](UI-FUNCTIONAL-AUDIT.md)를 따른다.

정적 호출 지점 79개. Tk Entry 입력란과 SelectionList의 각 데이터 행은 포함하지 않는다. 동적 항목·중첩 콜백은 소스를 확인해야 한다.

|소스 위치|종류|표시 또는 분류|확인된 메서드 참조|실행 검증|
|---|---|---|---|---|
|[show_status_detail:201](../src/echomate_bot/desktop_ui.py#L201)|form|현재 상태와 오류|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[render:323](../src/echomate_bot/desktop_ui.py#L323)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[render:324](../src/echomate_bot/desktop_ui.py#L324)|button|봇 끄기|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[render:329](../src/echomate_bot/desktop_ui.py#L329)|button|상태·오류|show_status_detail|개별 PASS 미부여|
|[render:308](../src/echomate_bot/desktop_ui.py#L308)|button|동적 항목 · 소스 참조|set_page|개별 PASS 미부여|
|[render:330](../src/echomate_bot/desktop_ui.py#L330)|toggle|응답 허용|set_value|개별 PASS 미부여|
|[draw_spaces:352](../src/echomate_bot/desktop_ui.py#L352)|button|새로고침|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_spaces:375](../src/echomate_bot/desktop_ui.py#L375)|button|동적 항목 · 소스 참조|save_scope|개별 PASS 미부여|
|[draw_spaces:376](../src/echomate_bot/desktop_ui.py#L376)|button|동적 항목 · 소스 참조|change_guild|개별 PASS 미부여|
|[draw_spaces:354](../src/echomate_bot/desktop_ui.py#L354)|button|동적 항목 · 소스 참조|toggle_channel_view|개별 PASS 미부여|
|[draw_spaces:359](../src/echomate_bot/desktop_ui.py#L359)|button|동적 항목 · 소스 참조|edit_name|개별 PASS 미부여|
|[draw_spaces:360](../src/echomate_bot/desktop_ui.py#L360)|button|별명·시간대 설정|server_options|개별 PASS 미부여|
|[draw_spaces:368](../src/echomate_bot/desktop_ui.py#L368)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_spaces:370](../src/echomate_bot/desktop_ui.py#L370)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_spaces:373](../src/echomate_bot/desktop_ui.py#L373)|toggle|이 채널의 스레드도 적용|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[choices:380](../src/echomate_bot/desktop_ui.py#L380)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[number:384](../src/echomate_bot/desktop_ui.py#L384)|button|−|set_value|개별 PASS 미부여|
|[number:385](../src/echomate_bot/desktop_ui.py#L385)|button|+|set_value|개별 PASS 미부여|
|[draw_character:390](../src/echomate_bot/desktop_ui.py#L390)|choices|동적 항목 · 소스 참조|set_value|개별 PASS 미부여|
|[draw_character:392](../src/echomate_bot/desktop_ui.py#L392)|choices|동적 항목 · 소스 참조|set_value|개별 PASS 미부여|
|[draw_character:394](../src/echomate_bot/desktop_ui.py#L394)|choices|동적 항목 · 소스 참조|set_value|개별 PASS 미부여|
|[draw_character:400](../src/echomate_bot/desktop_ui.py#L400)|button|프로필 편집·복제|edit_profile|개별 PASS 미부여|
|[draw_character:401](../src/echomate_bot/desktop_ui.py#L401)|button|저장한 프로필|profile_library|개별 PASS 미부여|
|[draw_character:402](../src/echomate_bot/desktop_ui.py#L402)|button|로컬 미리보기|character_preview|개별 PASS 미부여|
|[draw_character:403](../src/echomate_bot/desktop_ui.py#L403)|button|가져오기·내보내기|profile_files|개별 PASS 미부여|
|[draw_character:404](../src/echomate_bot/desktop_ui.py#L404)|toggle|성인 유머 · 연령 제한 채널에서만|set_value|개별 PASS 미부여|
|[draw_character:405](../src/echomate_bot/desktop_ui.py#L405)|button|표현 고급 설정|advanced_profile|개별 PASS 미부여|
|[draw_setup:413](../src/echomate_bot/desktop_ui.py#L413)|button|동적 항목 · 소스 참조|setup_credentials|개별 PASS 미부여|
|[draw_setup:414](../src/echomate_bot/desktop_ui.py#L414)|button|모델 확인하기|set_page|개별 PASS 미부여|
|[setup_credentials:418](../src/echomate_bot/desktop_ui.py#L418)|form|내 봇 정보 등록|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_models:428](../src/echomate_bot/desktop_ui.py#L428)|button|모델 폴더 선택|choose_model_folder|개별 PASS 미부여|
|[draw_models:429](../src/echomate_bot/desktop_ui.py#L429)|button|다시 검색|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_models:431](../src/echomate_bot/desktop_ui.py#L431)|button|기본 모델 사용|set_value|개별 PASS 미부여|
|[draw_models:443](../src/echomate_bot/desktop_ui.py#L443)|button|모델 상세 보기|form|개별 PASS 미부여|
|[draw_models:449](../src/echomate_bot/desktop_ui.py#L449)|button|검증 후 적용|set_value|개별 PASS 미부여|
|[draw_models:443](../src/echomate_bot/desktop_ui.py#L443)|form|선택한 모델 정보|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[edit_profile:471](../src/echomate_bot/desktop_ui.py#L471)|form|캐릭터 편집 · 복제해서 저장|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[advanced_profile:512](../src/echomate_bot/desktop_ui.py#L512)|form|표현 고급 설정|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[profile_files:521](../src/echomate_bot/desktop_ui.py#L521)|form|프로필 파일|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[approve_commands:556](../src/echomate_bot/desktop_ui.py#L556)|form|다음 연결의 명령 정리 승인|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_status:567](../src/echomate_bot/desktop_ui.py#L567)|button|개인정보 없는 진단 저장|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_outputs:617](../src/echomate_bot/desktop_ui.py#L617)|button|Discord 명령 정리 승인|approve_commands|개별 PASS 미부여|
|[draw_outputs:616](../src/echomate_bot/desktop_ui.py#L616)|toggle|동적 항목 · 소스 참조|set_value|개별 PASS 미부여|
|[draw_labs:625](../src/echomate_bot/desktop_ui.py#L625)|toggle|이미지 내용 분석을 시험해 보기|set_value|개별 PASS 미부여|
|[draw_labs:626](../src/echomate_bot/desktop_ui.py#L626)|button|이 서버 캐시 비우기|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_labs:627](../src/echomate_bot/desktop_ui.py#L627)|button|선택 범위 다시 분석 · 최대5개|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[member_alias_editor:42](../src/echomate_bot/companion_ui.py#L42)|form|이 사람의 호칭 관리|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[server_options:114](../src/echomate_bot/companion_ui.py#L114)|form|이 서버의 호칭과 시간대|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[edit_record:133](../src/echomate_bot/companion_ui.py#L133)|form|친밀도 조절|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[edit_record:147](../src/echomate_bot/companion_ui.py#L147)|form|기억 확인·수정|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[edit_record:141](../src/echomate_bot/companion_ui.py#L141)|form|기억 직접 추가|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[edit_record:153](../src/echomate_bot/companion_ui.py#L153)|form|알림 수정|record_action|개별 PASS 미부여|
|[reset_records:162](../src/echomate_bot/companion_ui.py#L162)|form|기록 삭제 확인|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[draw_records:171](../src/echomate_bot/companion_ui.py#L171)|toggle|동적 항목 · 소스 참조|set_value|개별 PASS 미부여|
|[draw_records:172](../src/echomate_bot/companion_ui.py#L172)|button|목록 새로고침|refresh_records|개별 PASS 미부여|
|[draw_records:215](../src/echomate_bot/companion_ui.py#L215)|button|전체 사용자|refresh_records|개별 PASS 미부여|
|[draw_records:216](../src/echomate_bot/companion_ui.py#L216)|button|선택 수정|edit_record|개별 PASS 미부여|
|[draw_records:230](../src/echomate_bot/companion_ui.py#L230)|button|이 사람 초기화|reset_records|개별 PASS 미부여|
|[draw_records:231](../src/echomate_bot/companion_ui.py#L231)|button|서버 전체 초기화|reset_records|개별 PASS 미부여|
|[draw_records:232](../src/echomate_bot/companion_ui.py#L232)|button|만료 기록 정리|record_action|개별 PASS 미부여|
|[draw_records:218](../src/echomate_bot/companion_ui.py#L218)|button|동적 항목 · 소스 참조|edit_record, show_legacy_summaries|개별 PASS 미부여|
|[draw_records:219](../src/echomate_bot/companion_ui.py#L219)|button|검색·종류|form, search_records|개별 PASS 미부여|
|[draw_records:220](../src/echomate_bot/companion_ui.py#L220)|button|동적 항목 · 소스 참조|cycle_record_status|개별 PASS 미부여|
|[draw_records:228](../src/echomate_bot/companion_ui.py#L228)|button|동적 항목 · 소스 참조|remove_record|개별 PASS 미부여|
|[draw_records:229](../src/echomate_bot/companion_ui.py#L229)|button|별명·시간대|server_options|개별 PASS 미부여|
|[draw_records:234](../src/echomate_bot/companion_ui.py#L234)|button|일시 문맥 지우기|record_action|개별 PASS 미부여|
|[draw_records:235](../src/echomate_bot/companion_ui.py#L235)|toggle|이전 관련 발췌 사용|set_value|개별 PASS 미부여|
|[draw_records:236](../src/echomate_bot/companion_ui.py#L236)|button|보관·요약 설정|memory_defaults|개별 PASS 미부여|
|[draw_records:222](../src/echomate_bot/companion_ui.py#L222)|button|동적 항목 · 소스 참조|cycle_record_status|개별 PASS 미부여|
|[draw_records:223](../src/echomate_bot/companion_ui.py#L223)|button|유예 시간|form, set_value|개별 PASS 미부여|
|[draw_records:219](../src/echomate_bot/companion_ui.py#L219)|form|기억·요약 검색|search_records|개별 PASS 미부여|
|[draw_records:225](../src/echomate_bot/companion_ui.py#L225)|button|호칭 추가·관리|member_alias_editor|개별 PASS 미부여|
|[draw_records:226](../src/echomate_bot/companion_ui.py#L226)|button|대화 요약 보기|show_summaries|개별 PASS 미부여|
|[draw_records:223](../src/echomate_bot/companion_ui.py#L223)|form|늦어진 알림 처리|set_value|개별 PASS 미부여|
|[memory_defaults:258](../src/echomate_bot/companion_ui.py#L258)|form|새 기억의 기본 만료 기간|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[show_digest:273](../src/echomate_bot/companion_ui.py#L273)|form|대화 요약 · 출처가 있는 압축 기록|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[show_legacy_summaries:278](../src/echomate_bot/companion_ui.py#L278)|form|선택한 사람의 발언 요약 · 로컬 조회|중첩 함수/Controller · 소스 참조|개별 PASS 미부여|
|[remove_record:292](../src/echomate_bot/companion_ui.py#L292)|form|선택한 기록 삭제|confirm_remove|개별 PASS 미부여|
|[remove_record:287](../src/echomate_bot/companion_ui.py#L287)|form|대화 요약 삭제|record_action|개별 PASS 미부여|
