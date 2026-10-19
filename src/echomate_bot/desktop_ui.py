"""Canvas-drawn dark desktop controls; no native combobox/listbox/button styling."""
from __future__ import annotations
import queue
import tkinter as tk
from tkinter import font as tkfont
from .settings import scope
from .naming import guild_name,validate_name
from .companion_ui import CompanionViews,PAGES

BG='#0b1018';PANEL='#121b28';CARD='#182333';LINE='#273447'
FG='#e9eff9';MUTED='#94a4bb';ACCENT='#9b91ff';MINT='#5ed8b8'
MOODS=['평온','기쁨','신남','우울','화남','피곤함','부끄러움']
ACTIVITY={'조용함':'quiet','보통':'normal','활발함':'active','매우 활발함':'very_active'}
MODES={'대답하지 않기':'silent','멘션·이어지는 대화만':'mention','자연스럽게 대화에 참여':'autonomous'}
REACTION_MODES={'반응하지 않기':'silent','대화 중에만 반응':'mention','어울릴 때 가볍게 반응':'autonomous'}
STAGES={'memory_lookup':'필요한 기억 확인','private_request':'기억·예약 요청 처리','assessment':'참여·지속 판단','continuity':'대화 지속 판단','visual':'이미지 분석','action':'행동 선택','text':'답변 작성','sending':'전송'}


def rounded(canvas,x,y,w,h,fill,r=12,outline=''):
    return canvas.create_polygon(x+r,y,x+w-r,y,x+w,y,x+w,y+r,x+w,y+h-r,x+w,y+h,x+w-r,y+h,
        x+r,y+h,x,y+h,x,y+h-r,x,y+r,x,y,fill=fill,outline=outline,smooth=True,splinesteps=24)


class SelectionList(tk.Canvas):
    """Multi-select list with keyboard navigation and a drawn scroll thumb."""
    def __init__(self,parent,callback,multiple=False):
        super().__init__(parent,bg=PANEL,highlightthickness=0,takefocus=True)
        self.callback=callback;self.multiple=multiple;self.items=[];self.selected=set();self.offset=0;self.index=0
        self.label_font=tkfont.Font(family='맑은 고딕',size=10)
        self.bind('<Configure>',lambda e:self.redraw());self.bind('<Button-1>',self.click)
        self.bind('<B1-Motion>',self.drag)
        self.bind('<MouseWheel>',self.wheel)
        self.bind('<Up>',lambda e:self.move(-1));self.bind('<Down>',lambda e:self.move(1))
        self.bind('<space>',lambda e:self.select_index(self.index,bool(e.state&4)));self.bind('<Return>',lambda e:self.select_index(self.index,False))
        self.bind('<FocusIn>',lambda e:self.redraw());self.bind('<FocusOut>',lambda e:self.redraw())
    def set_items(self,items):
        if items==self.items:return
        self.items=items;self.selected.intersection_update({x['id'] for x in items})
        visible=max(1,self.winfo_height()//52)
        self.offset=min(self.offset,max(0,len(items)-visible))
        self.index=min(self.index,max(0,len(items)-1));self.redraw()
    def destroy(self):
        # Break bound-method cycles while Tcl still belongs to the UI thread.
        self.callback=None
        super().destroy()
        self.label_font=None
    def click(self,event):
        self.focus_set()
        self.dragging=event.x>self.winfo_width()-12
        if event.x>self.winfo_width()-12:
            self.drag(event);return
        index=self.offset+event.y//52
        if index<len(self.items):self.select_index(index,bool(event.state&4))
    def drag(self,event):
        if not getattr(self,'dragging',False):return
        visible=max(1,self.winfo_height()//52)
        self.offset=max(0,min(max(0,len(self.items)-visible),round(event.y/max(1,self.winfo_height())*len(self.items))))
        self.redraw()
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
            label=item['label']
            if self.label_font.measure(label)>w-35:
                while label and self.label_font.measure(label+'…')>w-35:label=label[:-1]
                label+='…'
            self.create_text(13,y+15,text=label,anchor='w',fill=FG if selected else '#c2cddd',font=('맑은 고딕',10,'bold' if selected else 'normal'))
            self.create_text(13,y+35,text=item.get('hint',''),anchor='w',fill=ACCENT if selected else MUTED,font=('맑은 고딕',8))
        if not self.items:self.create_text(14,26,text=getattr(self,'empty_hint','연결 후 목록이 표시돼'),anchor='w',fill=MUTED,font=('맑은 고딕',10))
        if len(self.items)*52>h and h>1:
            thumb=max(25,h*h/(len(self.items)*52));top=self.offset/max(1,len(self.items))*h
            rounded(self,w-8,top,4,min(thumb,h-top),LINE,2)
        if self.focus_get() is self:self.create_rectangle(1,1,w-2,h-2,outline=ACCENT)


class DesktopApp(CompanionViews):
    def __init__(self,root,controller):
        self.root=root;self.controller=controller;self.snapshot=None;self.page='spaces';self.hits=[]
        self.button_fonts={}
        self.guild_id=None;self.channel_ids=set();self.text_mode='silent';self.react_mode='silent';self.inherit=False;self.drafts={};self.scope_baseline=None;self.closing=False;self.show_all=False
        self.canvas=tk.Canvas(root,bg=BG,highlightthickness=0,takefocus=True);self.canvas.pack(fill='both',expand=True)
        self.server_list=SelectionList(self.canvas,self.select_guild)
        self.channel_list=SelectionList(self.canvas,self.select_channels,True)
        self.setup_records()
        root.title('EchoMate');root.geometry('1180x820');root.minsize(1040,740);root.configure(bg=BG)
        try:
            import ctypes
            dark=ctypes.c_int(1)
            root.update_idletasks()
            ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.windll.user32.GetParent(root.winfo_id()),20,ctypes.byref(dark),4)
        except (AttributeError,OSError):pass
        self.canvas.bind('<Configure>',lambda e:self.render());self.canvas.bind('<Button-1>',self.click)
        self.canvas.bind('<Tab>',self.focus_next);self.canvas.bind('<Return>',self.activate_focus);self.focus_index=-1
        self.canvas.bind('<Shift-Tab>',self.focus_previous);self.canvas.bind('<space>',self.activate_focus)
        root.bind('<Control-s>',lambda e:self.save_scope() if self.page=='spaces' else None)
        self.disposed=False
        root.protocol('WM_DELETE_WINDOW',self.close);self.poll_id=root.after(100,self.poll)
    def text(self,x,y,value,size=11,color=FG,bold=False,width=None):
        return self.canvas.create_text(x,y,text=value,anchor='nw',fill=color,font=('맑은 고딕',size,'bold' if bold else 'normal'),width=width or 0)
    def button(self,x,y,w,h,label,callback,selected=False,primary=False,enabled=True,font_size=10):
        while font_size>6 and self.button_font(font_size).measure(label)>w-16:font_size-=1
        rounded(self.canvas,x,y,w,h,ACCENT if primary and enabled else '#2d2b4d' if selected else CARD,8)
        self.canvas.create_text(x+w/2,y+h/2,text=label,fill=MUTED if not enabled else BG if primary else ACCENT if selected else FG,font=self.button_font(font_size),tags=('button_label',))
        if enabled:self.hits.append((x,y,w,h,callback))
    def button_font(self,size):
        if size not in self.button_fonts:self.button_fonts[size]=tkfont.Font(root=self.root,family='맑은 고딕',size=size,weight='bold')
        return self.button_fonts[size]
    def toggle(self,x,y,label,on,callback):
        rounded(self.canvas,x,y,38,22,MINT if on else LINE,11)
        self.canvas.create_oval(x+(20 if on else 3),y+3,x+(36 if on else 19),y+19,fill=BG if on else MUTED,outline='')
        self.text(x+50,y,label,10)
        self.hits.append((x,y,290,28,callback))
    def click(self,event):
        self.canvas.focus_set()
        for i,(x,y,w,h,callback) in enumerate(self.hits):
            if x<=event.x<=x+w and y<=event.y<=y+h:
                self.focus_index=i;callback();self.render();break
    def focus_next(self,event):
        if self.hits:
            if self.focus_index==len(self.hits)-1 and self.page=='spaces':
                self.server_list.focus_set();return 'break'
            self.focus_index=(self.focus_index+1)%len(self.hits);self.render()
        return 'break'
    def focus_previous(self,event):
        if self.focus_index<=0 and self.page=='spaces':self.channel_list.focus_set()
        elif self.hits:self.focus_index=(self.focus_index-1)%len(self.hits);self.render()
        return 'break'
    def activate_focus(self,event):
        if 0<=self.focus_index<len(self.hits):self.hits[self.focus_index][4]()
        return 'break'
    def set_page(self,page):
        self.page=page;self.focus_index=-1
        if page in PAGES:
            self.record_key=None;self.record_status='전체';self.refresh_records()
    def set_value(self,key,value):self.controller.submit('settings',values={key:value})
    def remember_scope(self):
        if self.guild_id and self.channel_ids:
            self.drafts[(self.guild_id,frozenset(self.channel_ids))]=(self.text_mode,self.react_mode,self.inherit)
    @property
    def scope_dirty(self):
        if not self.channel_ids or not self.snapshot or not self.snapshot.get('cfg'):return False
        server=next((s for s in self.snapshot['servers'] if s['id']==self.guild_id),None)
        if not server:return False
        guild=self.snapshot['cfg']['guilds'].get(str(self.guild_id),{})
        for channel in server['channels']:
            if channel['id'] not in self.channel_ids:continue
            rule=guild.get('threads' if channel['thread'] else 'channels',{}).get(str(channel['id']),{})
            saved=(rule.get('mode','silent'),rule.get('reaction_mode',rule.get('mode','silent')),rule.get('inherit',False))
            if saved!=(self.text_mode,self.react_mode,self.inherit if not channel['thread'] else False):return True
        return False
    def select_guild(self,ids):
        self.remember_scope()
        self.guild_id=next(iter(ids),None);self.channel_ids=set();self.channel_list.selected=set();self.refresh_lists();self.render()
        self.record_user=None;self.record_key=None
        if self.page in PAGES:self.refresh_records()
    def select_channels(self,ids):
        self.remember_scope()
        self.channel_ids=set(ids)
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
            self.scope_baseline=(self.text_mode,self.react_mode,self.inherit)
            draft=self.drafts.get((self.guild_id,frozenset(ids)))
            if draft:self.text_mode,self.react_mode,self.inherit=draft
        self.render()
    def refresh_lists(self):
        if not self.snapshot:return
        servers=self.snapshot['servers'];cfg=self.snapshot['cfg']
        self.server_list.set_items([dict(id=s['id'],label=s['label'],hint='이 서버에서 대화 허용' if s['enabled'] else '사용할 채널을 골라 주세요') for s in servers])
        if self.guild_id is None and servers:
            self.guild_id=servers[0]['id'];self.server_list.selected={self.guild_id};self.server_list.redraw()
        server=next((s for s in servers if s['id']==self.guild_id),None)
        items=[]
        if server:
            g=cfg['guilds'].get(str(self.guild_id),{})
            for c in sorted(server['channels'],key=lambda c:(c['thread'],c['label'])):
                if self.snapshot.get('running') and not self.show_all and scope(dict(cfg,enabled=True),self.guild_id,c['id'],c.get('parent'))=='silent':continue
                rule=g.get('threads' if c['thread'] else 'channels',{}).get(str(c['id']),{})
                labels={'silent':'꺼짐','mention':'대화 중에만','autonomous':'자연스럽게','reaction':'이모지만'}
                hint=('상위 채널의 활동 설정을 따름' if c.get('parent') and scope(dict(cfg,enabled=True),self.guild_id,c['id'],c.get('parent'))!='silent' else '아직 설정하지 않았어요') if not rule else '채팅 '+labels[rule['mode']]+'  ·  반응 '+labels[rule.get('reaction_mode',rule['mode'])]
                items.append(dict(id=c['id'],label=('↳ ' if c['thread'] else '# ')+c['label'],hint=hint))
        self.channel_list.empty_hint=('활동할 곳이 없어요\n전체 목록에서 설정해 주세요' if self.snapshot.get('running') and not self.show_all else '목록이 없으면 새로고침해 주세요')
        self.channel_list.set_items(items);self.channel_list.redraw()
        if server and len(self.channel_ids)==1:
            cid=next(iter(self.channel_ids));c=next((c for c in server['channels'] if c['id']==cid),None)
            if c:
                rule=g.get('threads' if c['thread'] else 'channels',{}).get(str(cid),{})
                current=(self.text_mode,self.react_mode,self.inherit)
                persisted=(rule.get('mode','silent'),rule.get('reaction_mode',rule.get('mode','silent')),rule.get('inherit',False))
                if current==persisted:
                    self.scope_baseline=current;self.drafts.pop((self.guild_id,frozenset(self.channel_ids)),None)
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
    def toggle_channel_view(self):
        self.remember_scope();self.show_all=not self.show_all;self.refresh_lists();self.render()
    def edit_name(self):
        if not self.guild_id or not self.snapshot:return
        gid=self.guild_id
        dialog=tk.Toplevel(self.root);dialog.title('이 서버의 봇 이름');dialog.configure(bg=PANEL)
        dialog.geometry('430x235');dialog.resizable(False,False);dialog.transient(self.root);dialog.grab_set()
        canvas=tk.Canvas(dialog,bg=PANEL,highlightthickness=0);canvas.pack(fill='both',expand=True)
        canvas.create_text(24,20,text='이 서버에서 어떤 이름을 쓸까요?',anchor='nw',fill=FG,font=('맑은 고딕',13,'bold'))
        value=tk.StringVar(value=guild_name(self.snapshot['cfg'],gid))
        entry=tk.Entry(dialog,textvariable=value,bg=CARD,fg=FG,insertbackground=FG,relief='flat',font=('맑은 고딕',12))
        entry.place(x=24,y=61,width=380,height=36);entry.focus_set();entry.select_range(0,'end')
        hint=canvas.create_text(24,110,text='예: 별빛봇 → “별빛아”라고 불러도 문맥을 보고 답해요.\nDiscord에서 이름 변경 권한이 필요할 수 있어요.',anchor='nw',fill=MUTED,font=('맑은 고딕',9))
        def save():
            try:name=validate_name(value.get().strip())
            except ValueError:
                canvas.itemconfigure(hint,text='이름은 2~32자로, 줄바꿈·멘션·특수 제어문자 없이 입력해 주세요.');return
            self.controller.submit('name',guild=gid,name=name);dialog.destroy()
        rounded(canvas,222,178,86,34,CARD,8);rounded(canvas,318,178,86,34,ACCENT,8)
        canvas.create_text(265,195,text='취소',fill=FG,font=('맑은 고딕',10))
        canvas.create_text(361,195,text='저장',fill=BG,font=('맑은 고딕',10,'bold'))
        canvas.bind('<Button-1>',lambda e:save() if 318<=e.x<=404 and 178<=e.y<=212 else dialog.destroy() if 222<=e.x<=308 and 178<=e.y<=212 else None)
        dialog.bind('<Return>',lambda e:save());dialog.bind('<Escape>',lambda e:dialog.destroy())
    def render(self):
        self.canvas.delete('all');self.hits=[];w=max(1040,self.canvas.winfo_width());h=max(740,self.canvas.winfo_height())
        self.canvas.create_rectangle(0,0,196,h,fill='#0e1521',outline='')
        self.canvas.create_oval(24,27,44,47,fill=ACCENT,outline='');self.canvas.create_oval(30,33,38,41,fill=BG,outline='')
        self.text(56,25,'EchoMate',16,bold=True);self.text(26,63,'내 PC에서 동작하는 봇',8,MUTED)
        for index,(page,label) in enumerate([('spaces','대화할 곳'),('outputs','응답 방식'),('character','성격과 기분'),*PAGES.items(),('status','진행 상황'),('labs','실험 기능')]):
            self.button(16,116+index*52,164,42,label,lambda p=page:self.set_page(p),self.page==page)
        self.text(24,h-90,'모델은 내 PC에서 실행',9,MUTED);self.text(24,h-65,'Gemma 4 12B',10)
        s=self.snapshot;cfg=s['cfg'] if s and s.get('cfg') else None
        title={'spaces':'대화할 곳','outputs':'응답 방식','character':'성격과 기분','status':'지금 무엇을 하고 있나요?','labs':'실험 기능',**PAGES}[self.page]
        self.text(226,28,title,21,bold=True)
        connected=bool(s and s['connected'])
        running=bool(s and s.get('running'))
        self.canvas.create_oval(w-350,39,w-342,47,fill=MINT if connected else MUTED,outline='')
        self.text(w-333,31,'Discord에 연결됨' if connected else '연결을 준비하고 있어요' if running else '봇이 꺼져 있어요',10,MUTED)
        label='응답 재개' if connected and cfg and not cfg['enabled'] else '실행 중' if connected else '준비 중' if running else '봇 켜기'
        self.button(w-190,23,78,36,label,lambda:self.controller.submit('start'),primary=True,enabled=not running or bool(connected and cfg and not cfg['enabled']))
        self.button(w-102,23,78,36,'봇 끄기',lambda:self.controller.submit('stop'),enabled=running)
        error=' · 설정이나 실행을 확인해 주세요' if s and s['error'] else ''
        phase=s['phase'] if s else '저장된 설정을 읽고 있어요'
        if phase.startswith('정지'):phase='채널을 고른 뒤 ‘봇 켜기’를 누르면 대화를 시작해요'
        self.text(226,76,phase+error,10,MUTED)
        if cfg and connected:self.toggle(w-200,78,'응답 허용',cfg['enabled'],lambda:self.set_value('enabled',not cfg['enabled']))
        self.server_list.place_forget();self.channel_list.place_forget()
        self.people_list.place_forget();self.record_list.place_forget()
        if self.page=='spaces':self.draw_spaces(w,h,cfg)
        elif self.page=='outputs':self.draw_outputs(w,h,cfg)
        elif self.page=='character':self.draw_character(w,h,cfg)
        elif self.page=='status':self.draw_status(w,h,s)
        elif self.page=='labs':self.draw_labs(w,h,cfg)
        elif self.page in PAGES:self.draw_records(w,h,cfg)
        footer=('저장하지 않은 채널 설정이 있어요 · 선택을 바꿔도 임시 보관돼요' if self.scope_dirty else
                '변경을 적용하지 못했어요. 서버 목록과 설정을 확인해 주세요.' if s and s['error'] else
                s['notice']+' · 재시작 없이 적용돼요' if s and s.get('notice') else
                '허용한 채널에서만 대화해요 · 목록을 선택하는 것만으로는 말을 하지 않아요')
        self.text(226,h-29,footer,9,MUTED)
        if 0<=self.focus_index<len(self.hits):
            x,y,bw,bh,_=self.hits[self.focus_index];self.canvas.create_rectangle(x-2,y-2,x+bw+2,y+bh+2,outline=MINT)
    def draw_spaces(self,w,h,cfg):
        left=226;sy=143;bottom=h-66;right=w-274;mid=left+225
        for x,width in [(left,210),(mid,right-mid-15),(right,250)]:rounded(self.canvas,x,sy,width,bottom-sy,PANEL)
        self.text(left+16,sy+16,'가입한 서버',12,bold=True);self.text(mid+16,sy+16,'채널과 진행 중인 스레드',12,bold=True)
        self.button(left+126,sy+12,72,28,'새로고침',lambda:self.controller.submit('refresh'))
        if self.snapshot and self.snapshot.get('running'):
            self.button(mid+16,sy+41,190,28,'활동 설정한 곳만 보기' if self.show_all else '전체 목록 · 활동 설정',self.toggle_channel_view)
        else:self.text(mid+16,sy+44,'여러 곳 선택: Ctrl + 클릭',9,MUTED)
        self.server_list.place(x=left+10,y=sy+54,width=190,height=bottom-sy-158)
        if cfg and self.guild_id:
            self.text(left+16,bottom-90,'이 서버의 봇 이름',9,MUTED)
            self.button(left+10,bottom-62,190,34,guild_name(cfg,self.guild_id)[:16]+' · 변경',self.edit_name)
            self.button(left+10,bottom-25,190,24,'별명·시간대 설정',self.server_options,font_size=8)
        self.channel_list.place(x=mid+10,y=sy+78,width=right-mid-35,height=bottom-sy-94)
        x=right+16;self.text(x,sy+17,'이곳에서 어떻게 할까요?',12,bold=True)
        self.text(x,sy+46,f'{len(self.channel_ids)}곳을 선택했어요' if self.channel_ids else '먼저 왼쪽에서 채널을 골라 주세요',9,ACCENT)
        if cfg and not cfg['reactions'] and self.react_mode!='silent':
            self.text(x,sy+68,'이모지 켜기 → 응답 방식',9,ACCENT)
            self.hits.append((x,sy+68,216,18,lambda:self.set_page('outputs')))
        self.text(x,sy+91,'채팅',10,MUTED)
        for i,(label,mode) in enumerate(MODES.items()):self.button(x,sy+116+i*40,216,32,label,lambda m=mode:setattr(self,'text_mode',m),self.text_mode==mode)
        self.text(x,sy+256,'이모지 반응',10,MUTED)
        for i,(label,mode) in enumerate(REACTION_MODES.items()):self.button(x,sy+281+i*40,216,32,label,lambda m=mode:setattr(self,'react_mode',m),self.react_mode==mode)
        server=next((s for s in self.snapshot['servers'] if s['id']==self.guild_id),None) if self.snapshot else None
        parent_selected=server and any(c['id'] in self.channel_ids and not c['thread'] for c in server['channels'])
        if parent_selected:self.toggle(x,sy+414,'이 채널의 스레드도 적용',self.inherit,lambda:setattr(self,'inherit',not self.inherit))
        else:self.text(x,sy+414,'선택한 스레드에만 적용돼요' if self.channel_ids else '채널을 선택하면 설정할 수 있어요',9,MUTED)
        self.button(x,sy+445,216,36,f'선택한 {len(self.channel_ids)}곳에 저장' if self.channel_ids else '채널을 먼저 선택하세요',self.save_scope,primary=True,enabled=bool(self.channel_ids))
        self.button(x,sy+488,216,32,'이 서버에서 모두 쉬기' if server and server['enabled'] else '이 서버에서 활동 허용',self.change_guild,enabled=bool(server))
    def choices(self,x,y,choices,current,callback,width=105,enabled=True):
        size=10
        while size>6 and max(self.button_font(size).measure(label) for label,_ in choices)>width-16:size-=1
        for index,(label,value) in enumerate(choices):self.button(x+index*(width+8),y,width,35,label,lambda v=value:callback(v),value==current,enabled=enabled,font_size=size)
    def number(self,x,y,label,key,value,step,lo,hi):
        display=str(value)+'%' if key in {'warmth','cuteness','playfulness'} else str(value//60)+'분' if key=='engagement_seconds' and value>=60 else str(value)+'초'
        self.text(x,y,label,11);self.text(x+260,y,display,12,ACCENT,True)
        self.button(x+345,y-4,34,30,'−',lambda:self.set_value(key,max(lo,value-step)))
        self.button(x+387,y-4,34,30,'+',lambda:self.set_value(key,min(hi,value+step)))
    def draw_character(self,w,h,cfg):
        if not cfg:return
        rounded(self.canvas,226,143,w-252,h-210,PANEL)
        self.text(250,164,'대화 분위기',13,bold=True)
        self.choices(250,194,[(m,m) for m in MOODS],cfg['mood'],lambda v:self.set_value('mood',v),82)
        self.text(250,245,'캐릭터 성별',11,bold=True)
        self.choices(390,236,[('여성','female'),('남성','male'),('중성/성별 없음','neutral')],cfg['gender'],lambda v:self.set_value('gender',v),156)
        self.text(250,291,'새 대화에 먼저 참여하는 정도',12,bold=True)
        self.choices(250,321,list(ACTIVITY.items()),cfg['activity'],lambda v:self.set_value('activity',v),125)
        for index,(label,key,step,lo,hi) in enumerate([('다정함','warmth',5,0,100),('귀여움','cuteness',5,0,100),('장난기','playfulness',5,0,100),
             ('먼저 말할 때 최소 간격','cooldown',10,2,3600),('문맥 보관 시간','engagement_seconds',60,3600,86400)]):
            self.number(250,382+index*34,label,key,max(lo,cfg[key]),step,lo,hi)
        self.text(250,559,'답변 모델',10,MUTED)
        self.choices(250,583,[('개인 말투 · 잠정','persona'),('기본 Gemma 4','base'),('성인 유머 · 자유로운 표현','adult')],cfg['model'],lambda v:self.set_value('model',v),220,
                     enabled=not bool(self.snapshot and self.snapshot.get('model_preparing')))
        self.text(250,635,'성인 유머: 기존 Gemma 4 + 전용 정책 · 연령 제한 채널에서만 사용',9,ACCENT if cfg['model']=='adult' else MUTED,width=w-290)
    def draw_status(self,w,h,s):
        if not s:return
        width=(w-282)/3
        for index,(label,value) in enumerate([('처리 중이거나 기다리는 요청',str(s['pending'])),('진행 중인 대화',str(s['contexts'])),('최근 답변에 걸린 시간',str(s['latency'])+'초' if s['latency'] is not None else '아직 없음')]):
            x=226+index*(width+15);rounded(self.canvas,x,143,width,113,PANEL)
            self.text(x+20,160,label,10,MUTED);self.text(x+20,192,value,25,bold=True)
        rounded(self.canvas,226,277,w-252,h-344,PANEL);self.text(248,297,'진행 중인 작업',13,bold=True)
        if not s['progress']:self.text(248,348,'새 메시지를 기다리고 있어요' if s['connected'] else '봇을 켜면 여기에서 처리 과정을 볼 수 있어요',12,MUTED)
        self.button(w-430,291,180,32,'개인정보 없는 진단 저장',lambda:self.controller.submit('diagnostics'))
        for i,p in enumerate(s['progress'][:max(1,(h-520)//48)]):
            y=344+i*48;self.text(248,y,p['channel'],11);self.text(510,y,p['stage'],11,ACCENT);self.text(w-120,y,str(p['seconds'])+'초',11,MUTED)
        q=s.get('scheduler',{})
        if s['pending']>1 or s['contexts']>1:
            counts=q.get('counts',{});self.text(248,h-157,f"GPU 실행 {q.get('running',0)} · 대기 {q.get('waiting',0)} · 최장 대기 {q.get('oldest_seconds',0)}초 · 취소 {counts.get('cancelled',0)} · 실패 {counts.get('failed',0)}",9,MUTED)
        self.text(248,h-130,f"기억 정리 대기 {s.get('memory_pending',0)}건 · 알림 확인 {'동작 중' if s.get('private_service') else '봇 연결 후 시작'}",9,MUTED)
        self.text(248,h-107,'대화 내용은 이 화면에 표시하지 않아요. 긴 답변은 작성에 시간이 더 걸릴 수 있어요.',9,MUTED)
    def draw_outputs(self,w,h,cfg):
        if not cfg:return
        rounded(self.canvas,226,143,w-252,h-210,PANEL)
        self.text(250,168,'어떤 방식으로 답할까요?',18,bold=True)
        self.text(250,215,'대화할 채널에서 사용할 응답 방식을 골라 주세요. 변경하면 바로 적용돼요.',11,MUTED,width=w-310)
        for i,(key,label,hint) in enumerate([('text','글로 답하기','질문에 답하거나 대화를 이어가요.'),('reactions','이모지로 가볍게 반응하기','추가 설명이 필요 없을 때 Unicode 이모지로 반응해요.'),('stickers','Discord 기본 스티커 사용하기','상황에 맞는 공식 스티커가 있을 때만 사용해요.')]):
            y=285+i*100;self.toggle(250,y,label,cfg[key],lambda k=key:self.set_value(k,not cfg[k]));self.text(300,y+36,hint,10,MUTED,width=w-355)
        self.text(250,619,'서버 전용 이모지·스티커와 등록 이미지/GIF는 보내지 않아요.',10,MUTED,width=w-300)
    def draw_labs(self,w,h,cfg):
        if not cfg:return
        rounded(self.canvas,226,143,w-252,h-210,PANEL)
        rounded(self.canvas,250,168,92,26,'#3a2c1c',7);self.text(262,172,'시험 중인 기능',8,'#efba75',True)
        self.text(250,221,'시각 인식 · 분석',19,bold=True)
        self.text(250,267,'사진·GIF·서버 전용 이모지와 스티커의 내용을 이미지로 분석해요.\n기본은 꺼져 있어요. 켜면 답변이 더 오래 걸릴 수 있어요.\n이 기능을 켜도 서버 전용 에셋이나 등록 미디어를 보내지는 않아요.',11,MUTED,width=w-310)
        self.toggle(250,363,'이미지 내용 분석을 시험해 보기',cfg['vision'],lambda:self.set_value('vision',not cfg['vision']))
        self.text(250,444,'평소에는 꺼 두는 것을 권장해요',13,bold=True)
        self.text(250,485,'일반 대화와 기본 이모지·스티커는 이 기능을 켜지 않아도 사용할 수 있어요.\n실험 결과는 틀릴 수 있으며, Lottie 형식의 이미지 분석은 아직 지원하지 않아요.',11,MUTED,width=w-310)
    def poll(self):
        if self.disposed:return
        try:
            while True:self.snapshot=self.controller.updates.get_nowait()
        except queue.Empty:pass
        if self.page in PAGES:
            import time
            if time.monotonic()-getattr(self,'_records_refreshed_at',0)>5:self.refresh_records()
        self.refresh_lists();self.render();self.poll_id=self.root.after(400,self.poll)
    def destroy(self):
        if self.disposed:return
        self.disposed=True
        self.root.after_cancel(self.poll_id)
        self.hits.clear();self.drafts.clear();self.snapshot=None
        self.button_fonts.clear()
        self.root.destroy()
    def close(self):
        if self.closing:return
        self.closing=True
        self.controller.submit('shutdown')
        def wait():
            if self.controller.closed.is_set():self.destroy()
            else:self.root.after(200,wait)
        self.root.after(200,wait)
