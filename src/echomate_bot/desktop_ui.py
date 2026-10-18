"""Canvas-drawn dark desktop controls; no native combobox/listbox/button styling."""
from __future__ import annotations
import queue
import tkinter as tk

BG='#0b1018';PANEL='#121b28';CARD='#182333';LINE='#273447'
FG='#e9eff9';MUTED='#94a4bb';ACCENT='#9b91ff';MINT='#5ed8b8'
MOODS=['평온','기쁨','신남','우울','화남','피곤함','부끄러움']
ACTIVITY={'조용함':'quiet','보통':'normal','활발함':'active','매우 활발함':'very_active'}
MODES={'침묵':'silent','멘션·이어가기':'mention','자율 참여':'autonomous'}
STAGES={'assessment':'참여·지속 판단','continuity':'대화 지속 판단','visual':'이미지 분석','action':'행동 선택','text':'답변 작성','sending':'전송'}


def rounded(canvas,x,y,w,h,fill,r=12,outline=''):
    return canvas.create_polygon(x+r,y,x+w-r,y,x+w,y,x+w,y+r,x+w,y+h-r,x+w,y+h,x+w-r,y+h,
        x+r,y+h,x,y+h,x,y+h-r,x,y+r,x,y,fill=fill,outline=outline,smooth=True,splinesteps=24)


class SelectionList(tk.Canvas):
    """Multi-select list with keyboard navigation and a drawn scroll thumb."""
    def __init__(self,parent,callback,multiple=False):
        super().__init__(parent,bg=PANEL,highlightthickness=0,takefocus=True)
        self.callback=callback;self.multiple=multiple;self.items=[];self.selected=set();self.offset=0;self.index=0
        self.bind('<Configure>',lambda e:self.redraw());self.bind('<Button-1>',self.click)
        self.bind('<MouseWheel>',self.wheel)
        self.bind('<Up>',lambda e:self.move(-1));self.bind('<Down>',lambda e:self.move(1))
        self.bind('<space>',lambda e:self.select_index(self.index,False));self.bind('<Return>',lambda e:self.select_index(self.index,False))
        self.bind('<FocusIn>',lambda e:self.redraw());self.bind('<FocusOut>',lambda e:self.redraw())
    def set_items(self,items):
        if items==self.items:return
        self.items=items;self.selected.intersection_update({x['id'] for x in items})
        self.offset=min(self.offset,max(0,len(items)-1));self.redraw()
    def click(self,event):
        self.focus_set()
        if event.x>self.winfo_width()-12:
            self.offset=max(0,min(len(self.items)-1,int(event.y/max(1,self.winfo_height())*len(self.items))));self.redraw();return
        index=self.offset+event.y//52
        if index<len(self.items):self.select_index(index,bool(event.state&4))
    def select_index(self,index,add):
        if not 0<=index<len(self.items):return
        self.index=index;key=self.items[index]['id']
        if self.multiple and add:
            if key in self.selected:self.selected.remove(key)
            else:self.selected.add(key)
        else:self.selected={key}
        self.redraw();self.callback(self.selected.copy())
    def move(self,direction):
        self.index=max(0,min(len(self.items)-1,self.index+direction))
        visible=max(1,self.winfo_height()//52)
        if self.index<self.offset:self.offset=self.index
        if self.index>=self.offset+visible:self.offset=self.index-visible+1
        self.select_index(self.index,False);return 'break'
    def wheel(self,event):
        visible=max(1,self.winfo_height()//52)
        self.offset=max(0,min(max(0,len(self.items)-visible),self.offset-int(event.delta/120)*2));self.redraw();return 'break'
    def redraw(self):
        self.delete('all');w=self.winfo_width();h=self.winfo_height()
        for index,item in enumerate(self.items[self.offset:]):
            y=index*52
            if y+50>h:break
            selected=item['id'] in self.selected
            if selected:rounded(self,0,y,w-14,48,'#2c2b50',8)
            self.create_text(13,y+15,text=item['label'][:40],anchor='w',fill=FG if selected else '#c2cddd',font=('맑은 고딕',10,'bold' if selected else 'normal'))
            self.create_text(13,y+35,text=item.get('hint',''),anchor='w',fill=ACCENT if selected else MUTED,font=('맑은 고딕',8))
        if not self.items:self.create_text(14,26,text='연결 후 목록이 표시돼',anchor='w',fill=MUTED,font=('맑은 고딕',10))
        if len(self.items)*52>h and h>1:
            thumb=max(25,h*h/(len(self.items)*52));top=self.offset/max(1,len(self.items))*h
            rounded(self,w-8,top,4,min(thumb,h-top),LINE,2)
        if self.focus_get() is self:self.create_rectangle(1,1,w-2,h-2,outline=ACCENT)


class DesktopApp:
    def __init__(self,root,controller):
        self.root=root;self.controller=controller;self.snapshot=None;self.page='spaces';self.hits=[]
        self.guild_id=None;self.channel_ids=set();self.text_mode='silent';self.react_mode='silent';self.inherit=False
        self.canvas=tk.Canvas(root,bg=BG,highlightthickness=0,takefocus=True);self.canvas.pack(fill='both',expand=True)
        self.server_list=SelectionList(self.canvas,self.select_guild)
        self.channel_list=SelectionList(self.canvas,self.select_channels,True)
        root.title('EchoMate');root.geometry('1180x820');root.minsize(1040,740);root.configure(bg=BG)
        try:
            import ctypes
            dark=ctypes.c_int(1)
            root.update_idletasks()
            ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.windll.user32.GetParent(root.winfo_id()),20,ctypes.byref(dark),4)
        except (AttributeError,OSError):pass
        self.canvas.bind('<Configure>',lambda e:self.render());self.canvas.bind('<Button-1>',self.click)
        self.canvas.bind('<Tab>',self.focus_next);self.canvas.bind('<Return>',self.activate_focus);self.focus_index=-1
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(100,self.poll)
    def text(self,x,y,value,size=11,color=FG,bold=False,width=None):
        return self.canvas.create_text(x,y,text=value,anchor='nw',fill=color,font=('맑은 고딕',size,'bold' if bold else 'normal'),width=width or 0)
    def button(self,x,y,w,h,label,callback,selected=False,primary=False):
        rounded(self.canvas,x,y,w,h,ACCENT if primary else '#2d2b4d' if selected else CARD,8)
        self.canvas.create_text(x+w/2,y+h/2,text=label,fill=BG if primary else ACCENT if selected else FG,font=('맑은 고딕',10,'bold'))
        self.hits.append((x,y,w,h,callback))
    def toggle(self,x,y,label,on,callback):
        rounded(self.canvas,x,y,38,22,MINT if on else LINE,11)
        self.canvas.create_oval(x+(20 if on else 3),y+3,x+(36 if on else 19),y+19,fill=BG if on else MUTED,outline='')
        self.text(x+50,y,label,10)
        self.hits.append((x,y,290,28,callback))
    def click(self,event):
        for i,(x,y,w,h,callback) in enumerate(self.hits):
            if x<=event.x<=x+w and y<=event.y<=y+h:
                self.focus_index=i;callback();self.render();break
    def focus_next(self,event):
        if self.hits:
            self.focus_index=(self.focus_index+1)%len(self.hits);self.render()
        return 'break'
    def activate_focus(self,event):
        if 0<=self.focus_index<len(self.hits):self.hits[self.focus_index][4]()
        return 'break'
    def set_page(self,page):self.page=page;self.focus_index=-1
    def set_value(self,key,value):self.controller.submit('settings',values={key:value})
    def select_guild(self,ids):
        self.guild_id=next(iter(ids),None);self.channel_ids=set();self.channel_list.selected=set();self.refresh_lists();self.render()
    def select_channels(self,ids):
        self.channel_ids=ids
        if ids and self.snapshot:
            server=next((s for s in self.snapshot['servers'] if s['id']==self.guild_id),None)
            channel=next((c for c in server['channels'] if c['id']==next(iter(ids))),None) if server else None
            g=self.snapshot['cfg']['guilds'].get(str(self.guild_id),{})
            rule=g.get('threads' if channel and channel['thread'] else 'channels',{}).get(str(channel['id']) if channel else '',{})
            self.text_mode=rule.get('mode','silent')
            if self.text_mode=='reaction':self.text_mode='silent'
            self.react_mode=rule.get('reaction_mode',rule.get('mode','silent'))
            if self.react_mode=='reaction':self.react_mode='autonomous'
            self.inherit=rule.get('inherit',False)
        self.render()
    def refresh_lists(self):
        if not self.snapshot:return
        servers=self.snapshot['servers'];cfg=self.snapshot['cfg']
        self.server_list.set_items([dict(id=s['id'],label=s['label'],hint='활동 허용됨' if s['enabled'] else '기본 차단 · 선택 후 설정') for s in servers])
        if self.guild_id is None and servers:
            self.guild_id=servers[0]['id'];self.server_list.selected={self.guild_id};self.server_list.redraw()
        server=next((s for s in servers if s['id']==self.guild_id),None)
        items=[]
        if server:
            g=cfg['guilds'].get(str(self.guild_id),{})
            for c in sorted(server['channels'],key=lambda c:(c['thread'],c['label'])):
                rule=g.get('threads' if c['thread'] else 'channels',{}).get(str(c['id']),{})
                labels={'silent':'침묵','mention':'멘션·이어가기','autonomous':'자율','reaction':'이모지만'}
                hint='미설정 · 기본 차단' if not rule else '채팅 '+labels[rule['mode']]+'  ·  반응 '+labels[rule.get('reaction_mode',rule['mode'])]
                items.append(dict(id=c['id'],label=('↳ ' if c['thread'] else '# ')+c['label'],hint=hint))
        self.channel_list.set_items(items)
        self.channel_ids.intersection_update({i['id'] for i in items})
    def save_scope(self):
        server=next((s for s in self.snapshot['servers'] if s['id']==self.guild_id),None) if self.snapshot else None
        if not server:return
        for c in server['channels']:
            if c['id'] in self.channel_ids:
                self.controller.submit('scope',guild=self.guild_id,channel=c['id'],thread=c['thread'],text_mode=self.text_mode,
                    reaction_mode=self.react_mode,inherit=self.inherit if not c['thread'] else False,enabled=True)
    def change_guild(self):
        if self.guild_id:self.controller.submit('guild',guild=self.guild_id)
    def render(self):
        self.canvas.delete('all');self.hits=[];w=max(1040,self.canvas.winfo_width());h=max(740,self.canvas.winfo_height())
        self.canvas.create_rectangle(0,0,196,h,fill='#0e1521',outline='')
        self.canvas.create_oval(24,27,44,47,fill=ACCENT,outline='');self.canvas.create_oval(30,33,38,41,fill=BG,outline='')
        self.text(56,25,'EchoMate',16,bold=True);self.text(26,63,'LOCAL DISCORD COMPANION',8,MUTED)
        for index,(page,label) in enumerate([('spaces','활동 공간'),('character','캐릭터'),('status','처리 상태'),('labs','실험실')]):
            self.button(16,116+index*52,164,42,label,lambda p=page:self.set_page(p),self.page==page)
        self.text(24,h-90,'로컬 추론 · 비공개 설정',9,MUTED);self.text(24,h-65,'Gemma 4 12B',10)
        s=self.snapshot;cfg=s['cfg'] if s and s.get('cfg') else None
        title={'spaces':'활동 공간','character':'캐릭터 설정','status':'실시간 처리 상태','labs':'실험실'}[self.page]
        self.text(226,28,title,21,bold=True)
        connected=bool(s and s['connected'])
        self.canvas.create_oval(w-350,39,w-342,47,fill=MINT if connected else MUTED,outline='')
        self.text(w-333,31,'Discord 연결됨' if connected else '연결 안 됨',10,MUTED)
        self.button(w-190,23,78,36,'시작',lambda:self.controller.submit('start'),primary=True)
        self.button(w-102,23,78,36,'종료',lambda:self.controller.submit('stop'))
        self.text(226,76,(s['phase'] if s else '설정 읽는 중')+(' · '+s['error'] if s and s['error'] else ''),10,MUTED)
        if cfg:self.toggle(w-200,78,'활동 켜짐' if cfg['enabled'] else '활동 꺼짐',cfg['enabled'],lambda:self.set_value('enabled',not cfg['enabled']))
        self.server_list.place_forget();self.channel_list.place_forget()
        if self.page=='spaces':self.draw_spaces(w,h,cfg)
        elif self.page=='character':self.draw_character(w,h,cfg)
        elif self.page=='status':self.draw_status(w,h,s)
        elif self.page=='labs':self.draw_labs(w,h,cfg)
        self.text(226,h-29,('저장됨 · 변경 사항은 재시작 없이 적용돼' if s and s.get('notice') else '새 서버와 채널은 기본 차단 · 직접 선택한 범위에서만 활동'),9,MUTED)
        if 0<=self.focus_index<len(self.hits):
            x,y,bw,bh,_=self.hits[self.focus_index];self.canvas.create_rectangle(x-2,y-2,x+bw+2,y+bh+2,outline=MINT)
    def draw_spaces(self,w,h,cfg):
        left=226;sy=143;bottom=h-66;right=w-274;mid=left+225
        for x,width in [(left,210),(mid,right-mid-15),(right,250)]:rounded(self.canvas,x,sy,width,bottom-sy,PANEL)
        self.text(left+16,sy+16,'서버',12,bold=True);self.text(mid+16,sy+16,'채널 · 활성 스레드',12,bold=True)
        self.button(left+126,sy+12,72,28,'새로고침',lambda:self.controller.submit('refresh'))
        self.text(mid+16,sy+44,'Ctrl + 클릭으로 여러 곳 선택',9,MUTED)
        self.server_list.place(x=left+10,y=sy+54,width=190,height=bottom-sy-70)
        self.channel_list.place(x=mid+10,y=sy+78,width=right-mid-35,height=bottom-sy-94)
        x=right+16;self.text(x,sy+17,'활동 규칙',12,bold=True)
        self.text(x,sy+46,f'{len(self.channel_ids)}곳 선택됨',10,ACCENT)
        self.text(x,sy+91,'채팅',10,MUTED)
        for i,(label,mode) in enumerate(MODES.items()):self.button(x,sy+116+i*40,216,32,label,lambda m=mode:setattr(self,'text_mode',m),self.text_mode==mode)
        self.text(x,sy+256,'이모지 반응',10,MUTED)
        for i,(label,mode) in enumerate(MODES.items()):self.button(x,sy+281+i*40,216,32,label,lambda m=mode:setattr(self,'react_mode',m),self.react_mode==mode)
        self.toggle(x,sy+414,'하위 스레드에 상속',self.inherit,lambda:setattr(self,'inherit',not self.inherit))
        self.button(x,sy+461,216,36,'선택한 범위에 적용',self.save_scope,primary=True)
        server=next((s for s in self.snapshot['servers'] if s['id']==self.guild_id),None) if self.snapshot else None
        self.button(x,sy+508,216,32,'이 서버 활동 끄기' if server and server['enabled'] else '이 서버 활동 켜기',self.change_guild)
    def choices(self,x,y,choices,current,callback,width=105):
        for index,(label,value) in enumerate(choices):self.button(x+index*(width+8),y,width,35,label,lambda v=value:callback(v),value==current)
    def number(self,x,y,label,key,value,step,lo,hi):
        self.text(x,y,label,11);self.text(x+260,y,str(value),12,ACCENT,True)
        self.button(x+345,y-4,34,30,'−',lambda:self.set_value(key,max(lo,value-step)))
        self.button(x+387,y-4,34,30,'+',lambda:self.set_value(key,min(hi,value+step)))
    def draw_character(self,w,h,cfg):
        if not cfg:return
        rounded(self.canvas,226,143,w-252,h-210,PANEL)
        self.text(250,164,'대화 분위기',13,bold=True)
        self.choices(250,202,[(m,m) for m in MOODS],cfg['mood'],lambda v:self.set_value('mood',v),82)
        self.text(250,263,'활동 빈도',13,bold=True)
        self.choices(250,301,list(ACTIVITY.items()),cfg['activity'],lambda v:self.set_value('activity',v),125)
        for index,(label,key,step,lo,hi) in enumerate([('다정함','warmth',5,0,100),('귀여움','cuteness',5,0,100),('장난기','playfulness',5,0,100),
             ('새 대화 참여 간격 · 초','cooldown',10,2,3600),('대화 유지 시간 · 초','engagement_seconds',60,10,86400)]):
            self.number(250,371+index*47,label,key,cfg[key],step,lo,hi)
        self.text(250,622,'모델',10,MUTED)
        self.choices(310,612,[('개인 말투 · 잠정','persona'),('기본 Gemma 4','base')],cfg['model'],lambda v:self.set_value('model',v),156)
        self.text(250,h-100,'이미 참여한 대화는 신규 참여 확률과 별개로 이어가 · 기분 변경은 대화 이력을 유지해',9,MUTED,width=w-290)
    def draw_status(self,w,h,s):
        if not s:return
        width=(w-282)/3
        for index,(label,value) in enumerate([('GPU 작업',str(s['pending'])),('유지 중인 대화',str(s['contexts'])),('최근 전체 응답',str(s['latency'])+'초' if s['latency'] is not None else '아직 없음')]):
            x=226+index*(width+15);rounded(self.canvas,x,143,width,113,PANEL)
            self.text(x+20,160,label,10,MUTED);self.text(x+20,192,value,25,bold=True)
        rounded(self.canvas,226,277,w-252,h-344,PANEL);self.text(248,297,'진행 중인 작업',13,bold=True)
        if not s['progress']:self.text(248,348,'새 메시지를 기다리고 있어',12,MUTED)
        for i,p in enumerate(s['progress'][:8]):
            y=344+i*48;self.text(248,y,p['channel'],11);self.text(510,y,p['stage'],11,ACCENT);self.text(w-120,y,str(p['seconds'])+'초',11,MUTED)
        self.text(248,h-107,'기본 메시지는 이미지 분석 없이 처리 · 새 메시지가 오면 오래된 생성을 취소해',9,MUTED)
    def draw_labs(self,w,h,cfg):
        if not cfg:return
        rounded(self.canvas,226,143,w-252,h-210,PANEL)
        rounded(self.canvas,250,168,92,26,'#3a2c1c',7);self.text(264,172,'EXPERIMENT',8,'#efba75',True)
        self.text(250,221,'시각 인식 · 분석',19,bold=True)
        self.text(250,267,'서버 커스텀 이모지·스티커, 이미지·GIF·임베드의 실제 픽셀을 분석해.\n기본은 꺼짐이며, 켜면 GPU 처리 시간이 늘어날 수 있어.\n실험 분석을 켜도 커스텀 에셋이나 등록 이미지/GIF를 전송하지 않아.',11,MUTED,width=w-310)
        self.toggle(250,363,'실험 이미지 분석',cfg['vision'],lambda:self.set_value('vision',not cfg['vision']))
        self.text(250,433,'일반 동작',13,bold=True)
        for i,(key,label) in enumerate([('text','텍스트 답변'),('reactions','Unicode 이모지 반응'),('stickers','Discord 기본 스티커')]):
            self.toggle(250,478+i*48,label,cfg[key],lambda k=key:self.set_value(k,not cfg[k]))
        self.text(250,643,'기본 스티커는 공식 설명·태그로 해석해. 픽셀을 보았다고 주장하지 않아.',9,MUTED,width=w-300)
    def poll(self):
        try:
            while True:self.snapshot=self.controller.updates.get_nowait()
        except queue.Empty:pass
        self.refresh_lists();self.render();self.root.after(400,self.poll)
    def close(self):
        self.controller.submit('stop')
        def wait():
            if self.controller.client is None and (self.controller.job is None or self.controller.job.done()):self.root.destroy()
            else:self.root.after(200,wait)
        self.root.after(200,wait)
