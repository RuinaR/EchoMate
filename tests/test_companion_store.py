"""Real SQLite, injected civil time and source isolation; no live Discord/GPU."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from echomate_bot.companion_store import CompanionStore
from echomate_bot.companion import handle_request,request_kind
from echomate_bot.temporal import parse_when,zone,editor_timestamp
from echomate_bot.settings import DEFAULTS
from echomate_bot.naming import name_candidate
from echomate_bot.context import build_context
from echomate_studio.dialogue_state import DialogueState,Turn


class CivilTime(unittest.TestCase):
    def setUp(self):self.at=datetime(2026,10,19,10,tzinfo=zone('Asia/Seoul'))
    def test_source_relative_and_next_week_are_not_current_machine_time(self):
        for text,minutes in [('20분 후',20),('한 시간 있다가',60),('반 시간 뒤',30)]:
            self.assertEqual(parse_when(text,self.at,exact=True).start,self.at+timedelta(minutes=minutes))
        self.assertEqual(parse_when('다음 주 토요일',self.at).start.astimezone(zone('Asia/Seoul')).date().isoformat(),'2026-10-31')
        self.assertEqual(parse_when('다음 주 토요일 오후 3시에 만나니까 1시간 전에 알려줘',self.at,exact=True).start.astimezone(zone('Asia/Seoul')).hour,14)
    def test_ambiguous_or_invalid_dates_never_gain_guessed_hours(self):
        for text in ('이번 주말','다음 주쯤','내일 저녁에','내일 3시','2026-02-30 오후 3시','내일 오후 25시','다음 주 금요일'):
            self.assertIsNone(parse_when(text,self.at,exact=True).start,text)
    def test_leap_year_end_midnight_and_zone_change(self):
        for at,expected in [(datetime(2028,2,28,23,50,tzinfo=zone('Asia/Seoul')),'2028-02-29'),(datetime(2026,12,31,23,50,tzinfo=zone('Asia/Seoul')),'2027-01-01')]:
            self.assertEqual(parse_when('20분 뒤',at,exact=True).start.astimezone(zone('Asia/Seoul')).date().isoformat(),expected)
        kst=parse_when('내일 오후 3시',self.at,'Asia/Seoul',exact=True).start
        utc=parse_when('내일 오후 3시',self.at,'UTC',exact=True).start
        self.assertEqual((utc-kst).total_seconds(),9*3600)
        self.assertEqual(parse_when('내일 0시',self.at,exact=True).start.astimezone(zone('Asia/Seoul')).hour,0)
    def test_editor_does_not_guess_date_format(self):
        self.assertIsNone(editor_timestamp('','UTC'))
        with self.assertRaises(ValueError):editor_timestamp('내일 3시','UTC')
    def test_dst_nonexistent_and_repeated_time_require_confirmation(self):
        at=datetime(2026,3,1,tzinfo=timezone.utc)
        for text in ('2026-03-08 오전 2시 30분','2026-11-01 오전 1시 30분'):
            self.assertIsNone(parse_when(text,at,'America/New_York',exact=True).start)
        before=datetime(2026,3,8,1,30,tzinfo=zone('America/New_York'))
        after=parse_when('1시간 뒤',before,'America/New_York',exact=True).start
        self.assertEqual(after.astimezone(zone('America/New_York')).hour,3)


class PrivateRecords(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='local_data');self.now=datetime(2026,10,19,10,tzinfo=zone('Asia/Seoul')).timestamp()
        self.path=Path(self.tmp.name)/'records.sqlite3';self.store=CompanionStore(self.path,clock=lambda:self.now)
        self.store.resume_subject(2,4)
        self.cfg=dict(DEFAULTS,guilds={'2':dict(enabled=True,channels={'3':dict(mode='mention',inherit=False)},threads={})})
    def tearDown(self):self.tmp.cleanup()
    def event(self,text,id=100,user=4,guild=2,channel=3):return SimpleNamespace(id=id,guild=guild,channel=channel,author=user,parent=None,content=text,timestamp=datetime.fromtimestamp(self.now,timezone.utc))
    def test_expiry_excluded_before_cleanup_and_restart_physically_removes(self):
        self.store.add_memory(2,4,3,'나는 RPG를 좋아해','preference',source=1)
        self.store.add_memory(2,4,3,'내일 모임은 오후 3시야','plan',source=2)
        self.now+=3*86400
        self.assertEqual(len(self.store.memories(2,4,3)),1)
        restored=CompanionStore(self.path,clock=lambda:self.now)
        with restored.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM memories').fetchone()[0],1)
    def test_relative_memory_is_rendered_as_computed_date_and_complete_json(self):
        import json
        from echomate_bot.memory_context import memory_context
        self.store.add_memory(2,4,3,'내일 모임은 오후 3시야','plan',source=1)
        self.now+=86400
        text=memory_context(self.store.memories(2,4,3),'Asia/Seoul')
        records=json.loads(text.split('] ',1)[1])
        self.assertEqual(records[0]['event_start_local'],'2026-10-20 15:00')
        self.assertEqual(records[0]['subject_user_id'],'4')
        self.assertLessEqual(len(text),1400)
    def test_scope_subject_relevance_and_manual_source_are_separate(self):
        for guild,user,channel in ((2,4,3),(5,4,3),(2,6,3),(2,4,7)):self.store.add_memory(guild,user,channel,'나는 RPG 게임을 좋아해','preference')
        self.assertEqual(len(self.store.memories(2,4,3,'RPG')),1)
        self.assertFalse(self.store.memories(2,4,3,'라면 레시피'))
    def test_selective_extraction_rejects_third_party_and_sensitive_data(self):
        for text in ('ㅋㅋ','친구는 RPG를 좋아해','나는 비밀번호를 기억해 줘','나는 "다음 주에 만나자"라고 했어','나는 친구가 RPG를 좋아하는 걸 기억해 줘'):
            self.assertIsNone(self.store.extract(self.event(text),'Asia/Seoul'))
        self.assertIsNotNone(self.store.extract(self.event('나는 RPG 게임을 좋아해'),'Asia/Seoul'))
    def test_delete_source_and_bulk_cutoff_prevent_queued_resurrection(self):
        e=self.event('나는 RPG를 좋아해');self.store.extract(e,'Asia/Seoul');self.store.delete_source(2,e.id)
        self.assertIsNone(self.store.extract(e,'Asia/Seoul'))
        e2=self.event('나는 퍼즐을 좋아해',id=101);self.store.clear_records(2,'memories')
        self.assertIsNone(self.store.extract(e2,'Asia/Seoul'))
        self.now+=1
        self.assertIsNotNone(self.store.extract(self.event('나는 퍼즐을 좋아해',id=102),'Asia/Seoul'))
    def test_forget_is_persistent_opt_out_and_does_not_affect_other_guild(self):
        self.store.add_memory(2,4,3,'나는 RPG를 좋아해');self.store.add_memory(5,4,3,'나는 퍼즐을 좋아해')
        self.store.forget(2,4)
        self.assertIsNone(self.store.extract(self.event('나는 RPG를 좋아해'),'Asia/Seoul'))
        self.assertEqual(len(self.store.memories(5,4)),1)
        self.store.resume_subject(2,4);self.now+=1
        self.assertIsNotNone(self.store.extract(self.event('나는 RPG를 좋아해',id=102),'Asia/Seoul'))
    def test_relationship_day_cap_duplicate_and_remove_cannot_farm(self):
        self.store.relationship(2,4,'r1','reaction');first=self.store.familiarity(2,4)
        self.store.relationship(2,4,'r1','reaction');self.assertEqual(self.store.familiarity(2,4),first)
        self.store.relationship(2,4,'r1','reaction',remove=True);self.store.relationship(2,4,'r1','reaction')
        self.assertEqual(self.store.familiarity(2,4),50)
        for i in range(100):self.now+=601;self.store.relationship(2,4,str(i))
        self.assertLessEqual(self.store.familiarity(2,4),52)
        restored=CompanionStore(self.path,clock=lambda:self.now);self.assertEqual(restored.familiarity(2,4),self.store.familiarity(2,4));self.assertEqual(restored.familiarity(5,4),50)
    def test_reminder_save_then_ack_dedup_target_and_access(self):
        e=self.event('<@999> 20분 뒤에 나 불러줘')
        answer=handle_request(self.store,e,self.cfg,999)
        rows=self.store.reminders(2,4,active=True);self.assertEqual(len(rows),1);self.assertIn('예약',answer);self.assertEqual(rows[0]['target'],'4')
        handle_request(self.store,e,self.cfg,999);self.assertEqual(len(self.store.reminders(2)),1)
        with self.assertRaises(PermissionError):self.store.change_reminder(2,7,rows[0]['reminder_id'],cancel=True)
        with self.assertRaises(PermissionError):self.store.change_reminder(5,4,rows[0]['reminder_id'],cancel=True)
        self.assertIn('본인',handle_request(self.store,self.event('<@8> 20분 뒤에 불러줘',101),self.cfg,999))
    def test_reminder_late_grace_restart_and_uncertain_delivery_not_retried(self):
        row=self.store.reserve_reminder(self.event('20분 뒤'),self.now+1200,'Asia/Seoul','물 마시기')
        self.assertFalse(self.store.claim(row['reminder_id']));self.now+=1201
        self.assertEqual(len(self.store.due(900)),1);self.assertTrue(self.store.claim(row['reminder_id']));self.assertFalse(self.store.claim(row['reminder_id']))
        restored=CompanionStore(self.path,clock=lambda:self.now);restored.recover()
        self.assertEqual(restored.reminders(2)[0]['status'],'failed');self.assertFalse(restored.due(900))
        row=restored.reserve_reminder(self.event('あと',101),self.now+60,'Asia/Seoul','물 마시기');self.now+=2000
        self.assertFalse(restored.due(900));self.assertEqual(restored.reminders(2)[-1]['status'],'expired')
    def test_claim_uses_latest_owner_edit_and_rejects_edit_after_claim(self):
        row=self.store.reserve_reminder(self.event('20분 뒤'),self.now+1200,'Asia/Seoul','물 마시기')
        self.store.change_reminder(2,1,row['reminder_id'],text='잠깐 쉬기',owner=True)
        self.now+=1201
        claimed=self.store.claim(row['reminder_id'])
        self.assertEqual(claimed['text'],'잠깐 쉬기')
        with self.assertRaises(ValueError):self.store.change_reminder(2,1,row['reminder_id'],text='바뀐 내용',owner=True)
        self.assertIsNone(self.store.claim(row['reminder_id']))
    def test_natural_list_cancel_postpone_and_ambiguity(self):
        handle_request(self.store,self.event('20분 뒤에 나 불러줘'),self.cfg,999)
        self.assertIn('예약 시간을 변경',handle_request(self.store,self.event('10분 더 늦춰줘',101),self.cfg,999))
        self.assertAlmostEqual(self.store.reminders(2)[0]['due_at'],self.now+1800)
        self.assertIn('·',handle_request(self.store,self.event('내가 부탁한 알림 뭐 있어?',102),self.cfg,999))
        handle_request(self.store,self.event('20분 뒤에 불러줘',103),self.cfg,999)
        self.assertIn('구분',handle_request(self.store,self.event('알림 취소해줘',104),self.cfg,999))
        self.assertIn('시각',handle_request(self.store,self.event('내일 깨워줘',105),self.cfg,999))
    def test_time_information_questions_are_not_executable_reminders(self):
        for text in ('모임 장소와 시간을 알려줘','내일 약속 시간을 한 문장으로 알려 줘','현재 시간이 몇 시인지 알려 줘'):
            self.assertIsNone(request_kind(text))
        for text in ('한 시간 있다가 게임 끄라고 해줘','30분 뒤에 알려줘','다음 주 토요일 저녁 8시에 알려줘'):
            self.assertEqual(request_kind(text),'reminder')
    def test_memories_and_reminders_expire_independently(self):
        self.store.add_memory(2,4,3,'나는 RPG를 좋아해',expires=self.now+20)
        self.store.reserve_reminder(self.event('알림'),self.now+60,'UTC','물 마시기')
        self.now+=30;self.store.cleanup();self.assertFalse(self.store.memories(2,4));self.assertEqual(len(self.store.reminders(2,4,active=True)),1)
    def test_forget_memory_does_not_cancel_reminder_or_erase_affinity(self):
        self.store.add_memory(2,4,3,'나는 RPG를 좋아해');self.store.relationship(2,4,'dialogue')
        self.store.reserve_reminder(self.event('알림'),self.now+60,'UTC','물 마시기')
        self.store.forget_memories(2,4)
        self.assertFalse(self.store.memories(2,4));self.assertEqual(len(self.store.reminders(2,4,active=True)),1);self.assertGreater(self.store.familiarity(2,4),50)
        self.now+=1;self.assertIsNone(self.store.extract(self.event('나는 퍼즐을 좋아해',id=101),'Asia/Seoul'))
    def test_two_hundred_due_records_and_concurrent_duplicate_reservation(self):
        from concurrent.futures import ThreadPoolExecutor
        event=self.event('알림')
        with ThreadPoolExecutor(4) as pool:
            keys=list(pool.map(lambda _:self.store.reserve_reminder(event,self.now+60,'UTC','물 마시기')['reminder_id'],range(8)))
        self.assertEqual(len(set(keys)),1)
        for i in range(199):self.store.reserve_reminder(self.event('알림',id=101+i,user=100+i),self.now+60,'UTC','쉬는 시간')
        self.now+=61;delivered=[]
        while rows:=self.store.due(900):
            for row in rows:
                self.assertTrue(self.store.claim(row['reminder_id']));delivered.append(row['reminder_id']);self.store.finish(row['reminder_id'],'delivered')
        self.assertEqual(len(set(delivered)),200)
        with self.store.db() as db:self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
    def test_corruption_never_overwrites_broken_db(self):
        path=Path(self.tmp.name)/'corrupt.sqlite3';path.write_bytes(b'broken fixture')
        broken=CompanionStore(path);self.assertIsNotNone(broken.error);self.assertEqual(path.read_bytes(),b'broken fixture')
    def test_unambiguous_plan_update_and_cancel_preserve_no_stale_plan(self):
        self.store.extract(self.event('내 모임은 내일 오후 3시야'),'Asia/Seoul')
        self.store.extract(self.event('내 모임은 모레 오후 4시로 변경했어',101),'Asia/Seoul')
        rows=self.store.memories(2,4);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['source'],'101')
        self.store.extract(self.event('내 모임은 취소됐어',102),'Asia/Seoul');self.assertFalse(self.store.memories(2,4))


class ContextAndNames(unittest.TestCase):
    def test_twenty_turn_context_retrieves_source_and_edits_invalidate(self):
        state=DialogueState(limit=100);at=datetime.now(timezone.utc)
        for i in range(25):state.append(channel_id=3,thread_id=None,turn=Turn(str(i),'4','모임 장소는 별빛 도서관이야' if i==0 else '다른 주제의 긴 이야기 '+('가'*250),at+timedelta(microseconds=i)))
        version,context=build_context(state,3,'모임 장소가 어디였지?')
        self.assertIn('별빛 도서관',str(context));self.assertIn('source',str(context))
        state.change_message(channel_id=3,thread_id=None,message_id='0',content='모임 장소는 달빛 공원이야')
        self.assertFalse(state.is_current(channel_id=3,thread_id=None,version=version))
        self.assertIn('달빛 공원',str(build_context(state,3,'모임 장소?')[1]))
        state.change_message(channel_id=3,thread_id=None,message_id='0')
        self.assertNotIn('별빛 도서관',str(build_context(state,3,'모임 장소?')[1]))
    def test_bounded_name_forms_aliases_quotes_and_substrings(self):
        for text in ('민랑아','야 민랑','민랑 뭐해?','민랑 응답하라'):
            self.assertTrue(name_candidate(text,'민랑mk2'))
        self.assertTrue(name_candidate('별빛아','민랑mk2',['별빛']))
        for text in ('"민랑아"라고 불렀어','https://example.com/민랑','주민랑은 다른 이름','민랑mk20'):
            self.assertFalse(name_candidate(text,'민랑mk2'))
        self.assertFalse(name_candidate('민랑아','민랑mk2',partial=False))
