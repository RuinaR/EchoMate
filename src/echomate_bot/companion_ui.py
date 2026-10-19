"""Owner-only Canvas management views. No network or database access on Tk thread."""
import time
import tkinter as tk
from .temporal import display_time

PAGES={'relations':'사람과 관계','memories':'기억 관리','reminders':'예약 알림'}
KINDS={'전체':None,'약속':'plan','잠깐의 상태':'state','진행 중 목표':'goal','취향':'preference','직접 기억':'explicit','대화 요약':'summary'}
STATES={'scheduled':'예약 중','processing':'발송 확인 중','delivered':'전송 완료','cancelled':'취소됨','expired':'기한 지남','failed':'실패·확인 필요','active':'사용 중','disabled':'잠시 끔','uncertain':'확인 필요'}


class CompanionViews:
    def setup_records(self):
        from .desktop_ui import SelectionList
        self.record_user=None;self.record_key=None;self.record_search='';self.record_kind=None;self.record_status='전체'
        self.people_list=SelectionList(self.canvas,self.select_person)
        self.record_list=SelectionList(self.canvas,self.select_record)

    def refresh_records(self):
        if not self.guild_id:return
        self._records_refreshed_at=time.monotonic()
        if self.guild_id:self.controller.submit('companion',action='refresh',guild=self.guild_id,user=self.record_user,query=self.record_search,kind=self.record_kind)

    def select_person(self,ids):
        self.record_user=next(iter(ids),None);self.record_key=None;self.refresh_records()

    def select_record(self,ids):
        self.record_key=next(iter(ids),None)
        if self.page=='relations' and self.record_key and not self.record_key.startswith('alias:'):self.record_user=self.record_key;self.refresh_records()
        self.render()

    def record_action(self,action,**values):
        if self.guild_id:self.controller.submit('companion',action=action,guild=self.guild_id,user=self.record_user,query=self.record_search,kind=self.record_kind,**values)

    def member_alias_editor(self):
        if not self.record_user:return
        data=(self.snapshot or {}).get('companion',{})
        rows=[r for r in data.get('aliases',[]) if r['user']==self.record_user]
        row=next((r for r in rows if 'alias:'+r['channel']+':'+r['alias']==self.record_key),{})
        g=self.snapshot['cfg']['guilds'].get(str(self.guild_id),{})
        channel=row.get('channel',next(iter(g.get('channels',{})),next(iter(g.get('threads',{})),'')))
        def save(v):self.record_action('member_alias',channel=v['channel'],alias=v['alias'],status={'확정':'confirmed','후보':'candidate','삭제':'deleted'}[v['status']])
        self.form('이 사람의 호칭 관리',[
            ('channel','호칭을 사용할 허용 채널 / 스레드 ID',channel),
            ('alias','호칭 · 변경하려면 이전 호칭을 삭제한 뒤 새로 추가',row.get('alias','')),
            ('status','처리 · 확정 / 후보 / 삭제','확정')],save,
            '이 채널에서만 사용해요. 후보는 반복되어도 자동 확정하지 않아요. 같은 호칭을 가진 사람이 여럿이면 보류해요. 기억·알림 대상 권한은 바뀌지 않아요.')

    def form(self,title,fields,submit,help_text=''):
        from .desktop_ui import PANEL,CARD,FG,MUTED,ACCENT,BG,rounded
        dialog=tk.Toplevel(self.root);dialog.title(title);dialog.configure(bg=PANEL);dialog.transient(self.root)
        width=580;height=150+len(fields)*62;dialog.geometry(f'{width}x{height}');dialog.resizable(False,False);dialog.grab_set()
        canvas=tk.Canvas(dialog,bg=PANEL,highlightthickness=0);canvas.pack(fill='both',expand=True)
        canvas.create_text(22,18,text=title,anchor='nw',fill=FG,font=('맑은 고딕',14,'bold'))
        values={};entries=[]
        for index,(key,label,value) in enumerate(fields):
            y=58+index*62;canvas.create_text(22,y,text=label,anchor='nw',fill=MUTED,font=('맑은 고딕',9))
            var=tk.StringVar(dialog,value=str(value));values[key]=var
            entry=tk.Entry(dialog,textvariable=var,bg=CARD,fg=FG,insertbackground=FG,relief='flat',font=('맑은 고딕',10))
            entry.place(x=22,y=y+22,width=535,height=28);entries.append(entry)
        hint=canvas.create_text(22,height-83,text=help_text,anchor='nw',fill=MUTED,font=('맑은 고딕',9),width=535)
        def save():
            try:submit({k:v.get().strip() for k,v in values.items()})
            except (ValueError,KeyError):canvas.itemconfigure(hint,text='입력 형식과 선택값을 다시 확인해 주세요.');return
            dialog.destroy()
        rounded(canvas,352,height-43,92,30,CARD,8);rounded(canvas,456,height-43,100,30,ACCENT,8)
        canvas.create_text(398,height-28,text='닫기',fill=FG,font=('맑은 고딕',10))
        canvas.create_text(506,height-28,text='적용',fill=BG,font=('맑은 고딕',10,'bold'))
        def click(event):
            if height-43<=event.y<=height-13:
                if 352<=event.x<=444:dialog.destroy()
                elif 456<=event.x<=556:save()
        canvas.bind('<Button-1>',click);dialog.bind('<Escape>',lambda e:dialog.destroy());dialog.bind('<Control-Return>',lambda e:save())
        if entries:entries[0].focus_set();entries[0].select_range(0,'end')

    def server_options(self):
        if not self.guild_id or not self.snapshot:return
        g=self.snapshot['cfg']['guilds'].get(str(self.guild_id),{})
        def save(values):
            if values['partial_names'] not in ('켜기','끄기'):raise ValueError()
            self.record_action('server_options',aliases=values['aliases'],timezone=values['timezone'],partial_names=values['partial_names']=='켜기')
        self.form('이 서버의 호칭과 시간대',[
            ('aliases','추가 별명 · 쉼표로 구분 (최대 8개)',','.join(g.get('aliases',[]))),
            ('timezone','서버 시간대',g.get('timezone','Asia/Seoul')),
            ('partial_names','접미사를 줄인 호출 · 켜기 / 끄기','켜기' if g.get('partial_names',True) else '끄기')],save,
            '별명도 문맥을 보고 판단해요. 한국은 Asia/Seoul, 세계 표준시는 UTC예요.')

    def edit_record(self,add=False):
        if not add and self.record_key and self.record_key.startswith('digest:'):self.show_digest();return
        data=(self.snapshot or {}).get('companion',{});page=self.page
        table=data.get('memories' if page=='memories' else 'reminders',[])
        row=next((r for r in table if r.get('memory_id',r.get('reminder_id'))==self.record_key),None)
        cfg=self.snapshot['cfg'];g=cfg['guilds'].get(str(self.guild_id),{});tz=g.get('timezone','Asia/Seoul')
        if page=='relations':
            if not self.record_user:return
            person=next((r for r in data.get('people',[]) if r['user']==self.record_user),{})
            def affinity(values):
                value=float(values['value'])
                if not 0<=value<=100:raise ValueError()
                self.record_action('affinity',value=value)
            self.form('친밀도 조절',[('value','캐릭터 친밀도 · 0~100',person.get('affinity',50))],affinity,'실제 감정이나 사람에 대한 평가가 아니에요. 권한과 안전 정책에는 영향을 주지 않아요.');return
        if page=='memories':
            if add:
                channels=[*g.get('channels',{}),*g.get('threads',{})]
                def create(values):
                    user=int(values.pop('subject'));kind=KINDS[values.pop('type')]
                    if not user or kind is None or kind=='summary':raise ValueError()
                    self.controller.submit('companion',action='memory_add',guild=self.guild_id,user=user,kind=kind,**values)
                self.form('기억 직접 추가',[
                    ('subject','당사자 User ID',self.record_user or ''),('channel','출처 채널 / 스레드 ID',next(iter(self.channel_ids),channels[0] if channels else '')),
                    ('type','종류 · 약속 / 잠깐의 상태 / 진행 중 목표 / 취향 / 직접 기억','직접 기억'),('summary','기억할 내용 · 민감정보 제외',''),
                    ('expires','만료 시각 · YYYY-MM-DD HH:MM (장기 기억은 비움)','')],create,'서버 시간대로 입력해요. 약속은 내용에도 날짜와 시각을 적어 주세요.');return
            if not row:return
            def edit(values):self.record_action('memory_edit',key=row['memory_id'],summary=values['summary'],expires=values['expires'],status={'사용':'active','잠시 끄기':'disabled','확인 필요':'uncertain'}[values['status']])
            self.form('기억 확인·수정',[
                ('summary','기억 내용 · 약속 본문은 새로 추가해 날짜를 다시 계산',row['summary']),
                ('expires','만료 시각 · YYYY-MM-DD HH:MM (없으면 비움)',display_time(row['expires_at'],tz) if row['expires_at'] else ''),
                ('status','상태 · 사용 / 잠시 끄기 / 확인 필요',{'active':'사용','disabled':'잠시 끄기','uncertain':'확인 필요'}[row['status']])],edit,
                f"출처 메시지 {row['source']} · 채널 {row['channel']}\n저장 {display_time(row['created_at'],tz)} / 확인 {display_time(row['last_confirmed_at'],tz)}")
        elif row and row['status']=='scheduled':
            self.form('알림 수정',[('due','알림 시각 · YYYY-MM-DD HH:MM',display_time(row['due_at'],tz)),('text','알림 내용 · 민감정보 제외',row['text'])],lambda values:self.record_action('reminder_edit',key=row['reminder_id'],due=values['due'],text=values['text']),'서버 시간대로 입력해요. 이미 발송 중이거나 끝난 알림은 변경하지 않아요.')

    def reset_records(self,all_users=False):
        if not self.guild_id or (not all_users and not self.record_user):return
        action={'memories':'memory_reset','relations':'relationship_reset','reminders':'reminder_reset'}[self.page]
        if self.page=='memories' and self.record_kind=='summary':action='summary_reset'
        def confirm(values):
            if values['confirm']!='삭제':raise ValueError()
            self.controller.submit('companion',action=action,guild=self.guild_id,user=None if all_users else self.record_user)
        self.form('기록 삭제 확인',[('confirm','계속하려면 삭제라고 입력','')],confirm,
                  ('이 서버 전체' if all_users else '선택한 사람')+'의 현재 화면 기록만 삭제해요. 다른 종류의 기록은 유지해요.')

    def draw_records(self,w,h,cfg):
        from .desktop_ui import PANEL,MUTED,FG,ACCENT,rounded
        if not cfg:return
        tz=cfg['guilds'].get(str(self.guild_id),{}).get('timezone','Asia/Seoul')
        rounded(self.canvas,226,143,w-252,h-210,PANEL)
        setting={'relations':'relations_auto','memories':'memory_auto','reminders':'reminders_enabled'}[self.page]
        self.toggle(246,160,{'relations':'교류에 따라 친밀도 갱신','memories':'대화에서 자동 기억 저장','reminders':'자연어 알림 예약 허용'}[self.page],cfg[setting],lambda:self.set_value(setting,not cfg[setting]))
        self.button(w-212,153,164,30,'목록 새로고침',self.refresh_records)
        self.text(246,200,'서버',10,MUTED);self.text(462,200,'교류한 사람 · ID로 구분',10,MUTED);self.text(680,200,'기록 · '+tz,9,MUTED)
        self.server_list.place(x=240,y=230,width=200,height=max(100,h-480))
        data=(self.snapshot or {}).get('companion',{})
        if data.get('guild')!=self.guild_id:data={}
        def relationship_hint(r):
            consent=r.get('consent',{}).get('relationships',False)
            state='동의 필요' if not consent else '자동 갱신 켜짐' if cfg['relations_auto'] else '앱 자동 갱신 꺼짐'
            return f"{state} · {r['affinity']:.1f} · {r['interactions']}회"
        self.people_list.set_items([dict(id=r['user'],label=r.get('label','사용자 '+r['user']),hint=relationship_hint(r)) for r in data.get('people',[])])
        self.people_list.place(x=456,y=230,width=200,height=max(100,h-480))
        self.people_list.selected={self.record_user} if self.record_user else set()
        rows=data.get('memories' if self.page=='memories' else 'reminders',[]) if self.page!='relations' else data.get('people',[])
        if self.page!='relations' and data.get('user')!=self.record_user:rows=[]
        if self.page=='memories':
            if self.record_status=='사용 중':rows=[r for r in rows if r['status']=='active' and (r['expires_at'] is None or r['expires_at']>time.time())]
            elif self.record_status=='곧 만료':rows=[r for r in rows if r['expires_at'] is not None and time.time()<r['expires_at']<=time.time()+86400]
            elif self.record_status=='만료':rows=[r for r in rows if r['expires_at'] is not None and r['expires_at']<=time.time()]
            elif self.record_status=='잠시 끔':rows=[r for r in rows if r['status']=='disabled']
            elif self.record_status=='확인 필요':rows=[r for r in rows if r['status']=='uncertain']
            items=[dict(id=r['memory_id'],label=r['summary'],hint=next((k for k,v in KINDS.items() if v==r['kind']),r['kind'])+' · '+('장기 기억' if not r['expires_at'] else display_time(r['expires_at'],tz)+' 만료')+' · '+('만료됨' if r['expires_at'] and r['expires_at']<=time.time() else STATES[r['status']])) for r in rows]
            if self.record_kind=='summary':
                rows=data.get('digests',[]) if data.get('user')==self.record_user else []
                if self.record_status=='만료':rows=[r for r in rows if r['expires']<=time.time()]
                elif self.record_status=='사용 중':rows=[r for r in rows if r['expires']>time.time() and r['usable']]
                if self.record_search:rows=[r for r in rows if self.record_search in str(r['body'])]
                items=[dict(id='digest:'+r['id'],label='손상된 요약 · 삭제 관리 가능' if r.get('damaged') else ' / '.join(i['text'] for i in r['body']['items']),hint='대화 요약 · '+('조회 오류' if r.get('damaged') else '만료됨' if r['expires']<=time.time() else '동의 철회로 활용 중지' if not r['usable'] else '사용 중')+' · '+display_time(r['expires'],tz)+' 만료') for r in rows]
        elif self.page=='reminders':
            if self.record_status=='실패':rows=[r for r in rows if r['status']=='failed']
            elif self.record_status=='예약 중':rows=[r for r in rows if r['status']=='scheduled']
            items=[dict(id=r['reminder_id'],label=display_time(r['due_at'],tz)+' · '+STATES[r['status']],hint=f"{r['text'][:40]} · {max(0,int((r['due_at']-time.time())/60))}분 남음") for r in rows]
        else:
            aliases=[r for r in data.get('aliases',[]) if r['user']==self.record_user]
            items=[dict(id='alias:'+r['channel']+':'+r['alias'],label=r['alias']+' · '+{'confirmed':'소유자 확인','candidate':'확인 전 후보','deleted':'삭제됨'}[r['status']],hint=f"채널 {r['channel']} · 근거 {r['observations']}건 / {r['witnesses']}명 · 근거점수 {r['confidence']:.0%}") for r in aliases] if self.record_user else [dict(id=r['user'],label=r.get('label','사용자 '+r['user']),hint='사람을 선택하면 호칭 후보를 확인할 수 있어요') for r in rows]
        self.record_list.set_items(items);self.record_list.place(x=674,y=230,width=max(210,w-714),height=max(100,h-480))
        loading=(self.snapshot or {}).get('companion_loading',False)
        self.people_list.empty_hint='자료를 읽고 있어요' if loading else '저장된 사람 자료가 없어요'
        self.record_list.empty_hint='조회에 실패했어요 · 새로고침' if data.get('load_error') else '로컬 자료를 읽고 있어요' if loading else '사람을 먼저 선택해 주세요' if not self.record_user and self.page!='relations' else '이 범위에 저장된 자료가 없어요'
        self.people_list.redraw();self.record_list.redraw()
        self.record_list.selected={self.record_key} if self.record_key else set()
        y=h-226
        self.button(246,y,120,30,'전체 사용자',lambda:(setattr(self,'record_user',None),self.refresh_records()))
        self.button(376,y,120,30,'선택 수정',lambda:self.edit_record(),enabled=bool(self.record_key or self.page=='relations' and self.record_user))
        if self.page=='memories':
            self.button(506,y,120,30,'기존 발췌 보기' if self.record_kind=='summary' else '기억 추가',self.show_legacy_summaries if self.record_kind=='summary' else lambda:self.edit_record(True))
            self.button(636,y,120,30,'검색·종류',lambda:self.form('기억·요약 검색',[('query','검색어',self.record_search),('kind','종류 · 전체 / 약속 / 잠깐의 상태 / 진행 중 목표 / 취향 / 직접 기억 / 대화 요약',next((k for k,v in KINDS.items() if v==self.record_kind),'전체'))],self.search_records))
            self.button(766,y,120,30,'보기: '+self.record_status,self.cycle_record_status)
        elif self.page=='reminders':
            self.button(506,y,120,30,self.record_status,lambda:self.cycle_record_status())
            self.button(636,y,120,30,'유예 시간',lambda:self.form('늦어진 알림 처리',[('seconds','재시작 뒤 허용 지연 · 0~86400초',cfg['reminder_grace'])],lambda v:self.set_value('reminder_grace',int(v['seconds']))))
        elif self.page=='relations':
            self.button(506,y,120,30,'호칭 추가·관리',self.member_alias_editor,enabled=bool(self.record_user))
            self.button(636,y,120,30,'대화 요약 보기',self.show_summaries,enabled=bool(self.record_user))
        if self.page in ('memories','reminders'):
            self.button(246,y+40,120,30,'선택 삭제' if self.page=='memories' else '예약 취소',self.remove_record,enabled=bool(self.record_key))
        else:self.button(246,y+40,120,30,'별명·시간대',self.server_options)
        self.button(376,y+40,120,30,'이 사람 초기화',lambda:self.reset_records(False),enabled=bool(self.record_user))
        self.button(506,y+40,120,30,'서버 전체 초기화',lambda:self.reset_records(True))
        self.button(636,y+40,120,30,'만료 기록 정리',lambda:self.record_action('cleanup'))
        if self.page=='memories':
            self.button(246,y+80,164,28,'일시 문맥 지우기',lambda:self.record_action('clear_context'))
            self.toggle(436,y+82,'이전 관련 발췌 사용',cfg['context_excerpts'],lambda:self.set_value('context_excerpts',not cfg['context_excerpts']))
            self.button(758,y+80,164,28,'보관·요약 설정',lambda:self.memory_defaults(cfg))
        elif self.page=='relations':
            history=data.get('history',[])[:2]
            text=' / '.join(('대화' if r['kind']=='conversation' else '반응')+f" {r['delta']:+.2f}"+(' · 취소됨' if not r['active'] else '') for r in history)
            self.text(246,y+84,'최근 변화: '+(text or '선택한 사람의 새 교류가 아직 없어요'),9,MUTED,width=w-310)
            person=next((p for p in data.get('people',[]) if p['user']==self.record_user),{})
            choices=person.get('consent',{})
            status=' · '.join(k+(' 동의' if choices.get(v) else ' 미동의') for k,v in (('친밀도','relationships'),('기억','memory'),('요약','summaries')))
            self.text(246,y+108,status+' · 동의는 본인의 /동의에서만 변경해요',8,MUTED,width=w-310)
        hint='자동 기억 기본 꺼짐 · 본인이 /동의에서 장기 기억 저장을 켜야 해요.' if self.page=='memories' else '알림은 본인에게만 · GPU 생성과 별개로 처리 · 완료 기록은 7일 후 정리해요.' if self.page=='reminders' else '표현용 친밀도예요 · 자동 갱신은 본인의 /동의에서 친밀도 저장 동의가 필요해요.'
        if (self.snapshot or {}).get('companion_error'):hint='기억 저장소 오류 · 일반 대화는 계속 사용할 수 있어요. 로컬 진단을 확인해 주세요.'
        self.text(246,h-94,hint,9,MUTED,width=w-300)

    def search_records(self,values):
        self.record_kind=KINDS[values['kind']];self.record_search=values['query'];self.refresh_records()

    def memory_defaults(self,cfg):
        def save(v):
            values=dict(memory_plan_grace=int(v['plan'])*60,memory_date_grace=int(v['date'])*60,memory_state_hours=int(v['state']))
            values['summaries_auto']={'켜기':True,'끄기':False}[v['summaries']]
            if not 0<=values['memory_plan_grace']<=86400 or not 0<=values['memory_date_grace']<=86400 or not 1<=values['memory_state_hours']<=72:raise ValueError()
            self.controller.submit('settings',values=values)
        self.form('새 기억의 기본 만료 기간',[
            ('plan','시각이 있는 약속 · 지난 뒤 보관할 분 (0~1440)',cfg['memory_plan_grace']//60),
            ('date','날짜만 있는 약속 · 날짜 종료 후 보관할 분 (0~1440)',cfg['memory_date_grace']//60),
            ('state','기간 없는 일시 상태 · 보관할 시간 (1~72)',cfg['memory_state_hours']),
            ('summaries','참여자 모두 동의한 대화 자동 요약 · 켜기 / 끄기','켜기' if cfg['summaries_auto'] else '끄기')],save,'요약은 종료·휴지 상태에서만 낮은 우선순위로 만들고 새 요청이 오면 중단해요. 30일 후 만료하며 만료 자료는 정리 주기 뒤 목록에서 빠져요.')

    def show_summaries(self):
        self.page='memories';self.record_kind='summary';self.record_key=None;self.refresh_records();self.render()

    def show_digest(self):
        row=next((r for r in (self.snapshot or {}).get('companion',{}).get('digests',[]) if 'digest:'+r['id']==self.record_key),None)
        if not row:return
        tz=self.snapshot['cfg']['guilds'].get(str(self.guild_id),{}).get('timezone','Asia/Seoul')
        labels={'topic':'주제','question':'질문','answer':'당시 답변','correction':'정정','decision':'결정','plan':'계획','open_question':'미해결','ending':'종료'}
        fields=[(str(i),labels.get(item['kind'],'요약')+' · 출처 '+item['source'],item['text']) for i,item in enumerate(row['body']['items'])]
        self.form('대화 요약 · 출처가 있는 압축 기록',fields,lambda v:None,
                  '수정되지 않는 조회 창이에요. 정정은 실제 대화의 새 요약으로 반영해요. 채널 '+row['channel']+' · '+display_time(row['updated'],tz)+' 갱신 / '+display_time(row['expires'],tz)+' 만료')

    def show_legacy_summaries(self):
        rows=(self.snapshot or {}).get('companion',{}).get('summaries',[])[:4]
        self.form('선택한 사람의 발언 요약 · 로컬 조회',[(str(i),'출처 '+r['source']+' · 채널 '+r['channel'],r['summary']) for i,r in enumerate(rows)] or [('empty','조회 결과','저장된 요약 자료가 없어요')],lambda v:None,'본인 발언만 선별 발췌해 30일 보관해요. 동의는 본인의 /동의에서만 바꿀 수 있어요. 이 창은 읽기용이에요.')

    def cycle_record_status(self):
        values=['전체','사용 중','곧 만료','잠시 끔','확인 필요','만료'] if self.page=='memories' else ['전체','예약 중','실패']
        self.record_status=values[(values.index(self.record_status)+1)%len(values)] if self.record_status in values else values[0];self.render()

    def remove_record(self):
        if self.record_key and self.record_key.startswith('digest:'):
            key=self.record_key.removeprefix('digest:')
            self.form('대화 요약 삭제',[('confirm','삭제 라고 입력','')],lambda v:self.record_action('summary_delete',key=key) if v['confirm']=='삭제' else None,'이 요약과 출처 연결을 지워요. 대기 중 자동 요약이 같은 출처로 복원하지 못하게 막아요.');return
        data=(self.snapshot or {}).get('companion',{});table='memories' if self.page=='memories' else 'reminders'
        row=next((r for r in data.get(table,[]) if r.get('memory_id',r.get('reminder_id'))==self.record_key),None)
        if not row:return
        action='memory_delete' if self.page=='memories' else 'reminder_cancel'
        self.form('선택한 기록 삭제',[('confirm','계속하려면 삭제라고 입력','')],lambda v:self.confirm_remove(v,action),'이미 전송 중인 알림은 취소할 수 없어요. 성공 여부가 불명확한 알림은 자동 재시도하지 않아요.')

    def confirm_remove(self,values,action):
        if values['confirm']!='삭제':raise ValueError()
        self.record_action(action,key=self.record_key)
