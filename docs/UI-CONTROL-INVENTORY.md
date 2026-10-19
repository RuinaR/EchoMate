# UI 컨트롤 정적 연결 목록

소스의 button/toggle/choices/form 호출 지점을 모두 열거한다. 반복 생성되는 항목은 하나의 호출 지점으로 표시한다. **실제 클릭·Controller·DB/API 성공을 전수 검증했다는 뜻이 아니다.** 기능별 확인과 미검증은 [UI 기능 감사](UI-FUNCTIONAL-AUDIT.md)를 따른다.

정적 호출 지점 81개. Tk Entry 입력란과 SelectionList의 각 데이터 행은 포함하지 않는다. 동적 항목·중첩 콜백은 소스를 확인해야 한다.

|소스 위치|종류|표시 또는 분류|확인된 메서드 참조|실행 검증|
|---|---|---|---|---|
|[show_status_detail:201](../src/echomate_bot/desktop_ui.py#L201)|form|현재 상태와 오류|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[edit_name:282](../src/echomate_bot/desktop_ui.py#L282)|form|이 서버의 봇 이름|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[render:308](../src/echomate_bot/desktop_ui.py#L308)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[render:309](../src/echomate_bot/desktop_ui.py#L309)|button|봇 끄기|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[render:314](../src/echomate_bot/desktop_ui.py#L314)|button|상태·오류|show_status_detail|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[render:293](../src/echomate_bot/desktop_ui.py#L293)|button|동적 항목 · 소스 참조|set_page|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[render:315](../src/echomate_bot/desktop_ui.py#L315)|toggle|응답 허용|set_value|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:337](../src/echomate_bot/desktop_ui.py#L337)|button|새로고침|중첩 함수/Controller · 소스 참조|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:360](../src/echomate_bot/desktop_ui.py#L360)|button|동적 항목 · 소스 참조|save_scope|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:361](../src/echomate_bot/desktop_ui.py#L361)|button|동적 항목 · 소스 참조|change_guild|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:339](../src/echomate_bot/desktop_ui.py#L339)|button|동적 항목 · 소스 참조|toggle_channel_view|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:344](../src/echomate_bot/desktop_ui.py#L344)|button|동적 항목 · 소스 참조|edit_name|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:345](../src/echomate_bot/desktop_ui.py#L345)|button|별명·시간대 설정|server_options|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:353](../src/echomate_bot/desktop_ui.py#L353)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:355](../src/echomate_bot/desktop_ui.py#L355)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:358](../src/echomate_bot/desktop_ui.py#L358)|toggle|이 채널의 스레드도 적용|중첩 함수/Controller · 소스 참조|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[choices:365](../src/echomate_bot/desktop_ui.py#L365)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[number:369](../src/echomate_bot/desktop_ui.py#L369)|button|−|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[number:370](../src/echomate_bot/desktop_ui.py#L370)|button|+|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:375](../src/echomate_bot/desktop_ui.py#L375)|choices|동적 항목 · 소스 참조|set_value|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:377](../src/echomate_bot/desktop_ui.py#L377)|choices|동적 항목 · 소스 참조|set_value|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:379](../src/echomate_bot/desktop_ui.py#L379)|choices|동적 항목 · 소스 참조|set_value|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:385](../src/echomate_bot/desktop_ui.py#L385)|button|프로필 편집·복제|edit_profile|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:386](../src/echomate_bot/desktop_ui.py#L386)|button|저장한 프로필|profile_library|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:387](../src/echomate_bot/desktop_ui.py#L387)|button|로컬 미리보기|character_preview|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:388](../src/echomate_bot/desktop_ui.py#L388)|button|가져오기·내보내기|profile_files|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:389](../src/echomate_bot/desktop_ui.py#L389)|toggle|성인 유머 · 연령 제한 채널에서만|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:390](../src/echomate_bot/desktop_ui.py#L390)|button|표현 고급 설정|advanced_profile|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_setup:398](../src/echomate_bot/desktop_ui.py#L398)|button|동적 항목 · 소스 참조|setup_credentials|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_setup:399](../src/echomate_bot/desktop_ui.py#L399)|button|모델 확인하기|set_page|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[setup_credentials:403](../src/echomate_bot/desktop_ui.py#L403)|form|내 봇 정보 등록|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_models:413](../src/echomate_bot/desktop_ui.py#L413)|button|모델 폴더 선택|choose_model_folder|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_models:414](../src/echomate_bot/desktop_ui.py#L414)|button|다시 검색|중첩 함수/Controller · 소스 참조|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_models:416](../src/echomate_bot/desktop_ui.py#L416)|button|기본 모델 사용|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_models:428](../src/echomate_bot/desktop_ui.py#L428)|button|모델 상세 보기|form|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_models:434](../src/echomate_bot/desktop_ui.py#L434)|button|검증 후 적용|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_models:428](../src/echomate_bot/desktop_ui.py#L428)|form|선택한 모델 정보|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[edit_profile:456](../src/echomate_bot/desktop_ui.py#L456)|form|캐릭터 편집 · 복제해서 저장|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[advanced_profile:522](../src/echomate_bot/desktop_ui.py#L522)|form|표현 고급 설정|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[profile_files:533](../src/echomate_bot/desktop_ui.py#L533)|form|프로필 파일|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[approve_commands:569](../src/echomate_bot/desktop_ui.py#L569)|form|다음 연결의 명령 정리 승인|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_status:580](../src/echomate_bot/desktop_ui.py#L580)|button|개인정보 없는 진단 저장|중첩 함수/Controller · 소스 참조|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_outputs:630](../src/echomate_bot/desktop_ui.py#L630)|button|Discord 명령 정리 승인|approve_commands|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_outputs:629](../src/echomate_bot/desktop_ui.py#L629)|toggle|동적 항목 · 소스 참조|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_labs:638](../src/echomate_bot/desktop_ui.py#L638)|toggle|이미지 내용 분석을 시험해 보기|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_labs:639](../src/echomate_bot/desktop_ui.py#L639)|button|이 서버 캐시 비우기|중첩 함수/Controller · 소스 참조|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_labs:640](../src/echomate_bot/desktop_ui.py#L640)|button|선택 범위 다시 분석 · 최대5개|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[member_alias_editor:42](../src/echomate_bot/companion_ui.py#L42)|form|이 사람의 호칭 관리|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[server_options:167](../src/echomate_bot/companion_ui.py#L167)|form|이 서버의 호칭과 시간대|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[edit_record:186](../src/echomate_bot/companion_ui.py#L186)|form|친밀도 조절|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[edit_record:200](../src/echomate_bot/companion_ui.py#L200)|form|기억 확인·수정|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[edit_record:194](../src/echomate_bot/companion_ui.py#L194)|form|기억 직접 추가|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[edit_record:206](../src/echomate_bot/companion_ui.py#L206)|form|알림 수정|record_action|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[reset_records:215](../src/echomate_bot/companion_ui.py#L215)|form|기록 삭제 확인|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:224](../src/echomate_bot/companion_ui.py#L224)|toggle|동적 항목 · 소스 참조|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:225](../src/echomate_bot/companion_ui.py#L225)|button|목록 새로고침|refresh_records|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:268](../src/echomate_bot/companion_ui.py#L268)|button|전체 사용자|refresh_records|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:269](../src/echomate_bot/companion_ui.py#L269)|button|선택 수정|edit_record|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:283](../src/echomate_bot/companion_ui.py#L283)|button|이 사람 초기화|reset_records|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:284](../src/echomate_bot/companion_ui.py#L284)|button|서버 전체 초기화|reset_records|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:285](../src/echomate_bot/companion_ui.py#L285)|button|만료 기록 정리|record_action|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:271](../src/echomate_bot/companion_ui.py#L271)|button|동적 항목 · 소스 참조|edit_record, show_legacy_summaries|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:272](../src/echomate_bot/companion_ui.py#L272)|button|검색·종류|form, search_records|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:273](../src/echomate_bot/companion_ui.py#L273)|button|동적 항목 · 소스 참조|cycle_record_status|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:281](../src/echomate_bot/companion_ui.py#L281)|button|동적 항목 · 소스 참조|remove_record|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:282](../src/echomate_bot/companion_ui.py#L282)|button|별명·시간대|server_options|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:287](../src/echomate_bot/companion_ui.py#L287)|button|일시 문맥 지우기|record_action|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:288](../src/echomate_bot/companion_ui.py#L288)|toggle|이전 관련 발췌 사용|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:289](../src/echomate_bot/companion_ui.py#L289)|button|보관·요약 설정|memory_defaults|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:275](../src/echomate_bot/companion_ui.py#L275)|button|동적 항목 · 소스 참조|cycle_record_status|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:276](../src/echomate_bot/companion_ui.py#L276)|button|유예 시간|form, set_value|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:272](../src/echomate_bot/companion_ui.py#L272)|form|기억·요약 검색|search_records|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:278](../src/echomate_bot/companion_ui.py#L278)|button|호칭 추가·관리|member_alias_editor|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:279](../src/echomate_bot/companion_ui.py#L279)|button|대화 요약 보기|show_summaries|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:276](../src/echomate_bot/companion_ui.py#L276)|form|늦어진 알림 처리|set_value|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[memory_defaults:311](../src/echomate_bot/companion_ui.py#L311)|form|새 기억의 기본 만료 기간|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[show_digest:326](../src/echomate_bot/companion_ui.py#L326)|form|대화 요약 · 출처가 있는 압축 기록|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[show_legacy_summaries:331](../src/echomate_bot/companion_ui.py#L331)|form|선택한 사람의 발언 요약 · 로컬 조회|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[remove_record:348](../src/echomate_bot/companion_ui.py#L348)|form|선택한 기록 삭제|confirm_remove|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[remove_record:343](../src/echomate_bot/companion_ui.py#L343)|form|대화 요약 삭제|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[setup_credentials:56](../src/echomate_bot/user_check.py#L56)|form|오프라인 검증용 가짜 정보|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
