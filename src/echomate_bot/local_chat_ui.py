"""Owned Tk widgets only: credential-free local conversation view."""
import tkinter as tk
from .desktop_ui import BG, PANEL, FG, MUTED, ACCENT, CARD


class LocalChatView:
    def destroy(self):
        # Tk variables/widgets must lose their final references on the owning
        # UI thread, before Controller/executor GC can run elsewhere.
        frame=getattr(self,'local_frame',None)
        if frame:frame.destroy()
        for key in ('local_frame','local_state','local_input','local_transcript','local_scope',
                    'local_detail','local_load_button','local_send_button','local_future'):
            if hasattr(self,key):delattr(self,key)
        super().destroy()

    def render(self):
        frame=getattr(self,'local_frame',None)
        if frame:frame.place_forget()
        super().render()
        if self.page!='local':return
        if frame is None:
            self.build_local_widgets();frame=self.local_frame
        w=max(1040,self.canvas.winfo_width());h=max(740,self.canvas.winfo_height())
        frame.place(x=226,y=143,width=w-252,height=h-210)
        snapshot=self.snapshot or {};chat=snapshot.get('local_chat') or {}
        lime=snapshot.get('lime') or {};busy=lime.get('busy',False)
        ready=lime.get('stage') in ('ready','local_ready')
        qualification=(snapshot.get('execution_readiness') or {}).get('LOCAL_CHAT',{})
        self.local_state.configure(text=f"LOCAL_CHAT · {lime.get('name','라임')} · {chat.get('status','idle')}\n"
            + ('LOCAL_CHAT_READY' if qualification.get('ready') else '로컬 시험 사용 · READY 인증 아님 · 고위험 사실성 검증 미완료')
            + '\nDiscord 연결 없음 · 합성 DB만 사용'
            + ('\n로컬 알림 서비스 중단 · 새 예약 불가, 재시작 필요' if chat.get('notification_service')=='FAILED' else ''))
        self.local_send_button.configure(state='normal' if ready and not busy else 'disabled')
        self.local_load_button.configure(state='normal' if not lime.get('resident') and not busy else 'disabled')
        future=getattr(self,'local_future',None)
        if future and future.done():
            try:ok=future.result().get('ok',False)
            except Exception:ok=False
            if not ok and not self.local_input.get('1.0','end-1c'):
                self.local_input.insert('1.0',self.local_draft)
            self.local_future=None
        rows=chat.get('rows',[])
        def label(row):
            scope=row.get('scope')
            return (('A' if scope[2]==4 else 'B')+' · 채널'+('1' if scope[1]==3 else '2')) if scope in ([2,3,4],[2,3,5],[2,6,4],[2,6,5]) else '합성 세션'
        text='\n\n'.join(('나' if r['role']=='user' else lime.get('name','라임'))+
                         ' ['+label(r)+']\n'+r['text'] for r in rows)
        if chat.get('partial'):text+='\n\n'+lime.get('name','라임')+' (검증 전 스트리밍)\n'+chat['partial']
        if text!=getattr(self,'local_displayed',None):
            bottom=getattr(self,'local_displayed',None) is None or self.local_transcript.yview()[1]>=.98;position=self.local_transcript.yview()[0]
            self.local_transcript.configure(state='normal');self.local_transcript.delete('1.0','end')
            self.local_transcript.insert('1.0',text);self.local_transcript.configure(state='disabled')
            if bottom:
                self.local_transcript.see('end')
                self.root.after_idle(lambda:self.local_transcript.see('end') if hasattr(self,'local_transcript') and not self.disposed else None)
            else:self.local_transcript.yview_moveto(position)
            self.local_displayed=text
        last=chat.get('last') or {};context=last.get('context') or {}
        subject=last.get('test_subject') or {}
        self.local_detail.configure(text=f"기능 {last.get('operation_state','NOT_REQUESTED')} · 조회 {last.get('lookup','미조회')} · 영수증 {len(last.get('receipts',[]))} · "
            f"입력 {context.get('input_tokens','—')}token · 제외된 과거 대화 {context.get('removed_exchanges',0)}쌍\n"
            f"직전 확인 · 기억 동의 {subject.get('memory_consent','—')} · 관계 동의 {subject.get('relationship_consent','—')} · 친밀도 {subject.get('affinity','—')}",
            wraplength=w-300,justify='left')

    def build_local_widgets(self):
        frame=self.local_frame=tk.Frame(self.canvas,bg=PANEL)
        frame.columnconfigure(0,weight=1);frame.rowconfigure(2,weight=1)
        self.local_state=tk.Label(frame,bg=PANEL,fg=FG,anchor='w',justify='left',font=('맑은 고딕',10))
        self.local_state.grid(row=0,column=0,columnspan=2,sticky='ew',padx=12,pady=8)
        tools=tk.Frame(frame,bg=PANEL);tools.grid(row=1,column=0,columnspan=2,sticky='ew',padx=12)
        def button(parent,label,action):
            return tk.Button(parent,text=label,command=action,bg=CARD,fg=FG,activebackground=ACCENT,
                             activeforeground=BG,relief='flat',highlightthickness=1,highlightcolor=ACCENT)
        self.local_load_button=button(tools,'모델 로딩',lambda:self.controller.submit('lime_load'))
        self.local_load_button.pack(side='left',padx=3)
        for label,op in [('생성 취소','lime_cancel'),('대화 초기화','local_reset'),('세션 저장','local_save'),('불러오기','local_restore')]:
            button(tools,label,lambda o=op:self.controller.submit(o)).pack(side='left',padx=3)
        button(tools,'알림 확인',lambda:self.controller.submit('local_ack')).pack(side='left',padx=3)
        self.local_scope=tk.StringVar(value='A · 채널1')
        menu=tk.OptionMenu(tools,self.local_scope,'A · 채널1','B · 채널1','A · 채널2','B · 채널2')
        menu.configure(bg=CARD,fg=FG,activebackground=ACCENT,highlightthickness=0);menu.pack(side='right')
        self.local_transcript=tk.Text(frame,wrap='word',state='disabled',bg=BG,fg=FG,insertbackground=FG,
            selectbackground=ACCENT,font=('맑은 고딕',11),relief='flat',padx=10,pady=8)
        self.local_transcript.grid(row=2,column=0,sticky='nsew',padx=(12,0),pady=10)
        scroll=tk.Scrollbar(frame,command=self.local_transcript.yview);scroll.grid(row=2,column=1,sticky='ns',pady=10)
        self.local_transcript.configure(yscrollcommand=scroll.set)
        self.local_input=tk.Text(frame,height=3,wrap='word',bg=CARD,fg=FG,insertbackground=FG,
            font=('맑은 고딕',11),relief='flat',padx=8,pady=6)
        self.local_input.grid(row=3,column=0,columnspan=2,sticky='ew',padx=12)
        self.local_input.bind('<Return>',self.local_enter)
        self.local_input.bind('<Shift-Return>',lambda e:None)
        bottom=tk.Frame(frame,bg=PANEL);bottom.grid(row=4,column=0,columnspan=2,sticky='ew',padx=12,pady=8)
        self.local_send_button=button(bottom,'보내기 · Enter',self.local_send);self.local_send_button.pack(side='left')
        tk.Label(bottom,text='Shift+Enter 줄바꿈 · /도움말: 테스트 기능',bg=PANEL,fg=MUTED).pack(side='left',padx=10)
        self.local_detail=tk.Label(frame,bg=PANEL,fg=MUTED,anchor='w',font=('맑은 고딕',9))
        self.local_detail.grid(row=5,column=0,columnspan=2,sticky='ew',padx=12,pady=(0,8))

    def local_enter(self,event):
        self.local_send();return 'break'

    def local_send(self):
        pending=getattr(self,'local_future',None)
        if pending and not pending.done():return
        lime=(self.snapshot or {}).get('lime',{})
        if lime.get('busy') or lime.get('stage') not in ('ready','local_ready'):return
        text=self.local_input.get('1.0','end-1c')
        if not text.strip():return
        label=self.local_scope.get();scope=(2,3 if '1' in label else 6,4 if label.startswith('A') else 5)
        self.local_draft=text;self.local_future=self.controller.submit('local_send',text=text,scope=scope)
        self.local_input.delete('1.0','end')
