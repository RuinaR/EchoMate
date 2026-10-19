# UI 컨트롤 정적 연결 목록

소스의 button/toggle/choices/form 호출 지점을 모두 열거한다. 반복 생성되는 항목은 하나의 호출 지점으로 표시한다. **실제 클릭·Controller·DB/API 성공을 전수 검증했다는 뜻이 아니다.** 기능별 확인과 미검증은 [UI 기능 감사](UI-FUNCTIONAL-AUDIT.md)를 따른다.

정적 호출 지점 83개. Tk Entry 입력란과 SelectionList의 각 데이터 행은 포함하지 않는다. 동적 항목·중첩 콜백은 소스를 확인해야 한다.

|소스 위치|종류|표시 또는 분류|확인된 메서드 참조|실행 검증|
|---|---|---|---|---|
|[show_status_detail:219](../src/echomate_bot/desktop_ui.py#L219)|form|현재 상태와 오류|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[edit_name:300](../src/echomate_bot/desktop_ui.py#L300)|form|이 서버의 봇 이름|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[render:326](../src/echomate_bot/desktop_ui.py#L326)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[render:327](../src/echomate_bot/desktop_ui.py#L327)|button|봇 끄기|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[render:332](../src/echomate_bot/desktop_ui.py#L332)|button|상태·오류|show_status_detail|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[render:311](../src/echomate_bot/desktop_ui.py#L311)|button|동적 항목 · 소스 참조|set_page|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[render:333](../src/echomate_bot/desktop_ui.py#L333)|toggle|응답 허용|set_value|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:355](../src/echomate_bot/desktop_ui.py#L355)|button|새로고침|중첩 함수/Controller · 소스 참조|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:377](../src/echomate_bot/desktop_ui.py#L377)|button|동적 항목 · 소스 참조|save_scope|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:378](../src/echomate_bot/desktop_ui.py#L378)|button|동적 항목 · 소스 참조|change_guild|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:357](../src/echomate_bot/desktop_ui.py#L357)|button|동적 항목 · 소스 참조|toggle_channel_view|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:362](../src/echomate_bot/desktop_ui.py#L362)|button|동적 항목 · 소스 참조|edit_name|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:363](../src/echomate_bot/desktop_ui.py#L363)|button|별명·시간대 설정|server_options|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:368](../src/echomate_bot/desktop_ui.py#L368)|button|이모지 켜기 → 응답 방식|set_page|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:370](../src/echomate_bot/desktop_ui.py#L370)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:372](../src/echomate_bot/desktop_ui.py#L372)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_spaces:375](../src/echomate_bot/desktop_ui.py#L375)|toggle|이 채널의 스레드도 적용|중첩 함수/Controller · 소스 참조|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[choices:382](../src/echomate_bot/desktop_ui.py#L382)|button|동적 항목 · 소스 참조|중첩 함수/Controller · 소스 참조|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[number:386](../src/echomate_bot/desktop_ui.py#L386)|button|−|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[number:387](../src/echomate_bot/desktop_ui.py#L387)|button|+|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:392](../src/echomate_bot/desktop_ui.py#L392)|choices|동적 항목 · 소스 참조|set_value|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:394](../src/echomate_bot/desktop_ui.py#L394)|choices|동적 항목 · 소스 참조|set_value|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:396](../src/echomate_bot/desktop_ui.py#L396)|choices|동적 항목 · 소스 참조|set_value|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:402](../src/echomate_bot/desktop_ui.py#L402)|button|프로필 편집·복제|edit_profile|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:403](../src/echomate_bot/desktop_ui.py#L403)|button|저장한 프로필|profile_library|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:404](../src/echomate_bot/desktop_ui.py#L404)|button|로컬 미리보기|character_preview|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:405](../src/echomate_bot/desktop_ui.py#L405)|button|가져오기·내보내기|profile_files|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:406](../src/echomate_bot/desktop_ui.py#L406)|toggle|성인 유머 · 연령 제한 채널에서만|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_character:407](../src/echomate_bot/desktop_ui.py#L407)|button|표현 고급 설정|advanced_profile|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_setup:415](../src/echomate_bot/desktop_ui.py#L415)|button|동적 항목 · 소스 참조|setup_credentials|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_setup:416](../src/echomate_bot/desktop_ui.py#L416)|button|모델 확인하기|set_page|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[setup_credentials:420](../src/echomate_bot/desktop_ui.py#L420)|form|내 봇 정보 등록|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_models:430](../src/echomate_bot/desktop_ui.py#L430)|button|모델 폴더 선택|choose_model_folder|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_models:431](../src/echomate_bot/desktop_ui.py#L431)|button|다시 검색|중첩 함수/Controller · 소스 참조|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_models:433](../src/echomate_bot/desktop_ui.py#L433)|button|기본 모델 사용|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_models:445](../src/echomate_bot/desktop_ui.py#L445)|button|모델 상세 보기|form|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_models:451](../src/echomate_bot/desktop_ui.py#L451)|button|검증 후 적용|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_models:445](../src/echomate_bot/desktop_ui.py#L445)|form|선택한 모델 정보|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[edit_profile:473](../src/echomate_bot/desktop_ui.py#L473)|form|캐릭터 편집 · 복제해서 저장|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[profile_library:532](../src/echomate_bot/desktop_ui.py#L532)|form|저장한 캐릭터 삭제|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[advanced_profile:561](../src/echomate_bot/desktop_ui.py#L561)|form|표현 고급 설정|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[profile_files:579](../src/echomate_bot/desktop_ui.py#L579)|form|프로필 파일|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[approve_commands:622](../src/echomate_bot/desktop_ui.py#L622)|form|다음 연결의 명령 정리 승인|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_status:633](../src/echomate_bot/desktop_ui.py#L633)|button|개인정보 없는 진단 저장|중첩 함수/Controller · 소스 참조|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_outputs:683](../src/echomate_bot/desktop_ui.py#L683)|button|Discord 명령 정리 승인|approve_commands|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_outputs:682](../src/echomate_bot/desktop_ui.py#L682)|toggle|동적 항목 · 소스 참조|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_labs:691](../src/echomate_bot/desktop_ui.py#L691)|toggle|이미지 내용 분석을 시험해 보기|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_labs:692](../src/echomate_bot/desktop_ui.py#L692)|button|이 서버 캐시 비우기|중첩 함수/Controller · 소스 참조|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_labs:693](../src/echomate_bot/desktop_ui.py#L693)|button|선택 범위 다시 분석 · 최대5개|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[member_alias_editor:43](../src/echomate_bot/companion_ui.py#L43)|form|이 사람의 호칭 관리|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[server_options:199](../src/echomate_bot/companion_ui.py#L199)|form|이 서버의 호칭과 시간대|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[edit_record:218](../src/echomate_bot/companion_ui.py#L218)|form|친밀도 조절|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[edit_record:232](../src/echomate_bot/companion_ui.py#L232)|form|기억 확인·수정|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[edit_record:226](../src/echomate_bot/companion_ui.py#L226)|form|기억 직접 추가|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[edit_record:238](../src/echomate_bot/companion_ui.py#L238)|form|알림 수정|record_action|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[reset_records:247](../src/echomate_bot/companion_ui.py#L247)|form|기록 삭제 확인|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:256](../src/echomate_bot/companion_ui.py#L256)|toggle|동적 항목 · 소스 참조|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:257](../src/echomate_bot/companion_ui.py#L257)|button|목록 새로고침|refresh_records|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:300](../src/echomate_bot/companion_ui.py#L300)|button|전체 사용자|refresh_records|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:301](../src/echomate_bot/companion_ui.py#L301)|button|선택 수정|edit_record|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:315](../src/echomate_bot/companion_ui.py#L315)|button|이 사람 초기화|reset_records|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:316](../src/echomate_bot/companion_ui.py#L316)|button|서버 전체 초기화|reset_records|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:317](../src/echomate_bot/companion_ui.py#L317)|button|만료 기록 정리|record_action|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:303](../src/echomate_bot/companion_ui.py#L303)|button|동적 항목 · 소스 참조|edit_record, show_legacy_summaries|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:304](../src/echomate_bot/companion_ui.py#L304)|button|검색·종류|form, search_records|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:305](../src/echomate_bot/companion_ui.py#L305)|button|동적 항목 · 소스 참조|cycle_record_status|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:313](../src/echomate_bot/companion_ui.py#L313)|button|동적 항목 · 소스 참조|remove_record|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:314](../src/echomate_bot/companion_ui.py#L314)|button|별명·시간대|server_options|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:319](../src/echomate_bot/companion_ui.py#L319)|button|일시 문맥 지우기|record_action|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:320](../src/echomate_bot/companion_ui.py#L320)|toggle|이전 관련 발췌 사용|set_value|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:321](../src/echomate_bot/companion_ui.py#L321)|button|보관·요약 설정|memory_defaults|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:307](../src/echomate_bot/companion_ui.py#L307)|button|동적 항목 · 소스 참조|cycle_record_status|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:308](../src/echomate_bot/companion_ui.py#L308)|button|유예 시간|form, set_value|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:304](../src/echomate_bot/companion_ui.py#L304)|form|기억·요약 검색|search_records|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:310](../src/echomate_bot/companion_ui.py#L310)|button|호칭 추가·관리|member_alias_editor|화면/팝업·취소 확인 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:311](../src/echomate_bot/companion_ui.py#L311)|button|대화 요약 보기|show_summaries|클릭→Controller 확인 · 일부 경계 mock · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[draw_records:308](../src/echomate_bot/companion_ui.py#L308)|form|늦어진 알림 처리|set_value|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[memory_defaults:343](../src/echomate_bot/companion_ui.py#L343)|form|새 기억의 기본 만료 기간|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[show_digest:362](../src/echomate_bot/companion_ui.py#L362)|form|대화 요약 · 출처가 있는 압축 기록|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[show_legacy_summaries:367](../src/echomate_bot/companion_ui.py#L367)|form|선택한 사람의 발언 요약 · 로컬 조회|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[remove_record:384](../src/echomate_bot/companion_ui.py#L384)|form|선택한 기록 삭제|confirm_remove|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[remove_record:379](../src/echomate_bot/companion_ui.py#L379)|form|대화 요약 삭제|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
|[setup_credentials:56](../src/echomate_bot/user_check.py#L56)|form|오프라인 검증용 가짜 정보|중첩 함수/Controller · 소스 참조|개별 실행 증거 미부여 · [성공/실패/저장 범위](UI-ACTION-QA.md)|
