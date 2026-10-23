"""Canvas-drawn dark desktop controls; no native combobox/listbox/button styling."""
from __future__ import annotations
import queue
import tkinter as tk
from tkinter import font as tkfont
from .settings import scope
from .naming import guild_name,validate_name
from .companion_ui import CompanionViews,PAGES
from .ui_controls import CanvasFeedback,range_field,choice_field

BG='#0b1018';PANEL='#121b28';CARD='#182333';LINE='#273447'
FG='#e9eff9';MUTED='#94a4bb';ACCENT='#9b91ff';MINT='#5ed8b8'
MOODS=['평온','기쁨','신남','우울','화남','피곤함','부끄러움']
ACTIVITY={'조용함':'quiet','보통':'normal','활발함':'active','매우 활발함':'very_active'}
MODES={'대답하지 않기':'silent','멘션·이어지는 대화만':'mention','자연스럽게 대화에 참여':'autonomous'}
REACTION_MODES={'반응하지 않기':'silent','대화 중에만 반응':'mention','어울릴 때 가볍게 반응':'autonomous'}
STAGES={'utterance_wait':'메시지 보충 대기','social':'실제 청자·대화 흐름 판정','summary':'대화 요약 확인·압축', 'memory_lookup':'필요한 기억 확인','private_request':'기억·예약 요청 처리','assessment':'참여·지속 판단','continuity':'대화 지속 판단','visual':'이미지 분석','action':'행동 선택','text':'답변 작성','sending':'전송','research':'인터넷 근거 확인','output_check':'출력 검사','conversation_wait':'앞선 대화 기다림','member_resolution':'호칭·대상 근거 확인'}


def rounded(canvas,x,y,w,h,fill,r=12,outline=''):
    return canvas.create_polygon(x+r,y,x+w-r,y,x+w,y,x+w,y+r,x+w,y+h-r,x+w,y+h,x+w-r,y+h,
        x+r,y+h,x,y+h,x,y+h-r,x,y+r,x,y,fill=fill,outline=outline,smooth=True,splinesteps=24)


class SelectionList(tk.Canvas):
    """Multi-select list with keyboard navigation and a drawn scroll thumb."""
    def __init__(self,parent,callback,multiple=False):
        super().__init__(parent,bg=PANEL,highlightthickness=0,takefocus=True)
        self.hover_index=None;self.pressed=False
        self.callback=callback;self.multiple=multiple;self.items=[];self.selected=set();self.offset=0;self.index=0
        self.label_font=tkfont.Font(family='맑은 고딕',size=10)
        self.selected_font=tkfont.Font(family='맑은 고딕',size=10,weight='bold')
        self.hint_font=tkfont.Font(family='맑은 고딕',size=8)
        self.bind('<Configure>',lambda e:self.redraw());self.bind('<Button-1>',self.click)
        self.bind('<Motion>',self.hover);self.bind('<Leave>',lambda e:self.hover(None));self.bind('<ButtonRelease-1>',self.release)
        self.bind('<B1-Motion>',self.drag)
        self.bind('<MouseWheel>',self.wheel)
        self.bind('<Up>',lambda e:self.move(-1));self.bind('<Down>',lambda e:self.move(1))
        self.bind('<space>',lambda e:self.select_index(self.index,bool(e.state&4)));self.bind('<Return>',lambda e:self.select_index(self.index,False))
        self.bind('<FocusIn>',lambda e:self.redraw());self.bind('<FocusOut>',lambda e:self.redraw())
    def place(self,*args,**kwargs):
        result=super().place(*args,**kwargs)
        self.redraw()
        return result
    @property
    def row_height(self):
        return max(52,max(self.label_font.metrics('linespace'),self.selected_font.metrics('linespace'))+self.hint_font.metrics('linespace')+16)
    def set_items(self,items):
        if items==self.items:return
        anchor=self.items[self.offset]['id'] if self.items and self.offset<len(self.items) and self.offset>0 else None
        focused=self.items[self.index]['id'] if self.items and self.index<len(self.items) else None
        self.items=items;self.selected.intersection_update({x['id'] for x in items})
        positions={item['id']:i for i,item in enumerate(items)}
        if anchor in positions:self.offset=positions[anchor]
        if focused in positions:self.index=positions[focused]
        visible=max(1,self.winfo_height()//self.row_height)
        self.offset=min(self.offset,max(0,len(items)-visible))
        self.index=min(self.index,max(0,len(items)-1));self.redraw()
    def destroy(self):
        # Break bound-method cycles while Tcl still belongs to the UI thread.
        self.callback=None
        super().destroy()
        self.label_font=None
        self.selected_font=None;self.hint_font=None
    def hover(self,event):
        index=self.offset+event.y//self.row_height if event is not None and event.x<self.winfo_width()-12 else None
        index=index if index is not None and 0<=index<len(self.items) else None
        if self.hover_index!=index:self.hover_index=index;self.redraw()
    def release(self,event):self.pressed=False;self.redraw()
    def click(self,event):
        if self.cget('state')=='disabled':return
        self.pressed=True;self.hover(event);self.focus_set()
        self.dragging=event.x>self.winfo_width()-12
        if event.x>self.winfo_width()-12:
            self.drag(event);return
        if not 0<=event.y<self.winfo_height()//self.row_height*self.row_height:return
        index=self.offset+event.y//self.row_height
        if index<len(self.items):self.select_index(index,bool(event.state&4))
    def drag(self,event):
        if not getattr(self,'dragging',False):return
        visible=max(1,self.winfo_height()//self.row_height)
        self.offset=max(0,min(max(0,len(self.items)-visible),round(event.y/max(1,self.winfo_height())*len(self.items))))
        self.redraw()
    def select_index(self,index,add):
        if self.cget('state')=='disabled' or not 0<=index<len(self.items) or not self.items[index].get('enabled',True):return
        self.index=index;key=self.items[index]['id']
        if self.multiple and add:
            if key in self.selected:self.selected.remove(key)
            else:self.selected.add(key)
        else:self.selected={key}
        self.redraw();self.callback(self.selected.copy())
    def move(self,direction):
        self.index=max(0,min(len(self.items)-1,self.index+direction))
        visible=max(1,self.winfo_height()//self.row_height)
        if self.index<self.offset:self.offset=self.index
        if self.index>=self.offset+visible:self.offset=self.index-visible+1
        self.select_index(self.index,False);return 'break'
    def wheel(self,event):
        visible=max(1,self.winfo_height()//self.row_height)
        self.offset=max(0,min(max(0,len(self.items)-visible),self.offset-int(event.delta/120)*2));self.redraw();return 'break'
    def redraw(self):
        self.delete('all');w=self.winfo_width();h=self.winfo_height()
        # place geometry is known before Tcl delivers Configure. Use it for
        # the first paint too; a hidden/new widget may still report 1x1.
        if self.winfo_manager()=='place':
            geometry=self.place_info()
            if geometry.get('width'):w=max(1,int(float(geometry['width'])))
            if geometry.get('height'):h=max(1,int(float(geometry['height'])))
        row_height=self.row_height
        label_height=max(self.label_font.metrics('linespace'),self.selected_font.metrics('linespace'))
        self.offset=min(self.offset,max(0,len(self.items)-max(1,h//row_height)))
        for index,item in enumerate(self.items[self.offset:]):
            y=index*row_height
            if y+row_height>h:break
            selected=item['id'] in self.selected
            disabled=self.cget('state')=='disabled' or not item.get('enabled',True)
            hover=self.offset+index==self.hover_index and not disabled
            if selected or hover:
                rounded(self,0,y,w-14,row_height-4,'#423e67' if hover and self.pressed else '#35324f' if hover and selected else '#243248' if hover else '#2c2b50',8,outline=ACCENT if selected else LINE)
            if selected:self.create_rectangle(2,y+8,5,y+row_height-12,fill=ACCENT,outline='')
            font=self.selected_font if selected else self.label_font
            label=item['label']
            if font.measure(label)>w-35:
                while label and font.measure(label+'…')>w-35:label=label[:-1]
                label+='…'
            self.create_text(13,y+6+label_height/2,text=label,anchor='w',fill=MUTED if disabled else FG if selected else '#c2cddd',font=font)
            hint=item.get('hint','')
            if self.hint_font.measure(hint)>w-35:
                while hint and self.hint_font.measure(hint+'…')>w-35:hint=hint[:-1]
                hint+='…'
            self.create_text(13,y+10+label_height+self.hint_font.metrics('linespace')/2,text=hint,anchor='w',fill=ACCENT if selected else MUTED,font=self.hint_font)
        if not self.items:self.create_text(14,12,text=getattr(self,'empty_hint','연결 후 목록이 표시돼'),anchor='nw',fill=MUTED,font=self.label_font,width=max(1,w-30))
        if len(self.items)*row_height>h and h>1:
            thumb=max(25,h*h/(len(self.items)*row_height));top=self.offset/max(1,len(self.items))*h
            rounded(self,w-8,top,4,min(thumb,h-top),LINE,2)
        self.configure(cursor='hand2' if self.hover_index is not None and self.hover_index<len(self.items) and self.items[self.hover_index].get('enabled',True) and self.cget('state')!='disabled' else '')
        if self.focus_get() is self:self.create_rectangle(1,1,w-2,h-2,outline=ACCENT)


class DesktopApp(CompanionViews):
    def __init__(self,root,controller):
        self.root=root;self.controller=controller;self.snapshot=None;self.page='spaces';self.hits=[]
        self.button_fonts={}
        self.pending_actions={}
        self.guild_id=None;self.channel_ids=set();self.text_mode='silent';self.react_mode='silent';self.inherit=False;self.drafts={};self.scope_baseline=None;self.closing=False;self.show_all=False
        self.canvas=tk.Canvas(root,bg=BG,highlightthickness=0,takefocus=True);self.canvas.pack(fill='both',expand=True)
        self.feedback=CanvasFeedback(self.canvas,activate_on_release=True)
        self.server_list=SelectionList(self.canvas,self.select_guild)
        self.channel_list=SelectionList(self.canvas,self.select_channels,True)
        self.setup_records()
        self.job_id=None;self.job_list=SelectionList(self.canvas,self.select_job)
        self.model_id=None;self.model_list=SelectionList(self.canvas,self.select_model)
        root.title('EchoMate');root.geometry('1180x820');root.minsize(1040,740);root.configure(bg=BG)
        try:
            import ctypes
            dark=ctypes.c_int(1)
            root.update_idletasks()
            ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.windll.user32.GetParent(root.winfo_id()),20,ctypes.byref(dark),4)
        except (AttributeError,OSError):pass
        self.canvas.bind('<Configure>',lambda e:self.render());self.canvas.bind('<Button-1>',self.press)
        self.canvas.bind('<Tab>',self.focus_next);self.canvas.bind('<Return>',self.activate_focus);self.focus_index=-1
        self.canvas.bind('<Shift-Tab>',self.focus_previous)
        self.canvas.bind('<KeyPress-space>',self.space_press);self.canvas.bind('<KeyRelease-space>',self.feedback.key_release)
        root.bind('<Control-s>',lambda e:self.save_scope() if self.page=='spaces' else None)
        self.disposed=False
        root.protocol('WM_DELETE_WINDOW',self.close);self.poll_id=root.after(100,self.poll)
    def text(self,x,y,value,size=11,color=FG,bold=False,width=None):
        return self.canvas.create_text(x,y,text=value,anchor='nw',fill=color,font=('맑은 고딕',size,'bold' if bold else 'normal'),width=width or 0)
    def button(self,x,y,w,h,label,callback,selected=False,primary=False,enabled=True,font_size=10,navigation=False):
        action_key=(self.page,label,x,y,self.guild_id,self.model_id,getattr(self,'record_user',None),getattr(self,'record_key',None))
        if action_key in self.pending_actions:enabled=False;label='처리 중…'
        while font_size>6 and self.button_font(font_size).measure(label)>w-16:font_size-=1
        shape=rounded(self.canvas,x,y,w,h,CARD,8)
        text=self.canvas.create_text(x+w/2,y+h/2,text=label,fill=FG,font=self.button_font(font_size),tags=('button_label',))
        self.feedback.add((x,y,w,h),shape,text,enabled=enabled,selected=selected,primary=primary,navigation=navigation,danger=('삭제' in label or '초기화' in label),callback=lambda:self.invoke_action(callback,action_key))
        if navigation and selected:self.canvas.create_rectangle(x+2,y+9,x+5,y+h-9,fill=ACCENT,outline='')
        if enabled:self.hits.append((x,y,w,h,lambda:self.invoke_action(callback,action_key)))
    def button_font(self,size):
        if size not in self.button_fonts:self.button_fonts[size]=tkfont.Font(root=self.root,family='맑은 고딕',size=size,weight='bold')
        return self.button_fonts[size]
    def toggle(self,x,y,label,on,callback):
        action_key=(self.page,label,x,y,self.guild_id,self.model_id,getattr(self,'record_user',None),getattr(self,'record_key',None))
        enabled=action_key not in self.pending_actions
        background=rounded(self.canvas,x-4,y-3,294,30,CARD,7)
        self.feedback.add((x,y,290,28),background,enabled=enabled,selected=on,callback=lambda:self.invoke_action(callback,action_key))
        rounded(self.canvas,x,y,38,22,MINT if on else LINE,11)
        self.canvas.create_oval(x+(20 if on else 3),y+3,x+(36 if on else 19),y+19,fill=BG if on else MUTED,outline='')
        self.text(x+50,y,label,10)
        if enabled:self.hits.append((x,y,290,28,lambda:self.invoke_action(callback,action_key)))
    def click(self,event):
        self.feedback.press(event);self.canvas.focus_set()
        for i,(x,y,w,h,callback) in enumerate(self.hits):
            if x<=event.x<=x+w and y<=event.y<=y+h:
                self.focus_index=i;callback();break
    def press(self,event):
        self.canvas.focus_set();self.feedback.press(event)
        for i,(x,y,w,h,callback) in enumerate(self.hits):
            if x<=event.x<=x+w and y<=event.y<=y+h:self.focus_index=i;break
    def invoke_action(self,callback,action_key=None):
        if action_key is not None and action_key in self.pending_actions:return
        before=getattr(self.controller,'last_submission',None)
        result=callback()
        from concurrent.futures import Future
        from asyncio import Future as AsyncFuture
        after=getattr(self.controller,'last_submission',None)
        future=result if isinstance(result,(Future,AsyncFuture)) else after if after is not before and isinstance(after,(Future,AsyncFuture)) else None
        if action_key is not None and future is not None and not future.done():self.pending_actions[action_key]=future
        if not self.disposed:self.render()
    def space_press(self,event):
        if 0<=self.focus_index<len(self.hits):
            box=self.hits[self.focus_index][:4]
            self.feedback.index=next((i for i,r in enumerate(self.feedback.regions) if r['box']==box),-1)
        return self.feedback.key_press(event)
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
    def set_value(self,key,value):return self.controller.submit('settings',values={key:value})
    def ellipsize(self,value,width,size=10,middle=False):
        value=str(value).replace('\n',' ');font=self.button_font(size)
        if font.measure(value)<=width:return value
        def shortened(n):return value[:(n+1)//2]+'…'+(value[-(n//2):] if n//2 else '') if middle else value[:n]+'…'
        low=0;high=len(value)
        while low<high:
            mid=(low+high+1)//2
            if font.measure(shortened(mid))<=width:low=mid
            else:high=mid-1
        return shortened(low)
    def show_status_detail(self):
        s=self.snapshot or {}
        last=s.get('last_management_error',{})
        self.form('현재 상태와 오류',[('phase','현재 상태',s.get('phase','준비 중')),('error','현재 오류',s.get('error') or '현재 오류 없음'),
                  ('last_error','이 실행에서 마지막으로 확인한 관리 오류',last.get('message','기록된 관리 오류 없음'))],lambda values:None,
                  '긴 자원 안내와 오류 유형을 전체 길이로 확인할 수 있어요.',read_only=True)
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
        # Retained settings/records are not evidence of current membership.
        servers=[s for s in self.snapshot['servers'] if s.get('joined',True)];cfg=self.snapshot['cfg']
        self.server_list.set_items([dict(id=s['id'],label=s['label'],hint='이 서버에서 대화 허용' if s['enabled'] else '사용할 채널을 골라 주세요') for s in servers])
        if self.guild_id is not None and not any(s['id']==self.guild_id for s in servers):
            self.remember_scope();self.guild_id=None;self.channel_ids.clear()
            self.server_list.selected=set()
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
        self.form('이 서버의 봇 이름',[('name','이 서버에서 사용할 이름 · 2~32자',guild_name(self.snapshot['cfg'],gid))],
            lambda values:self.controller.submit('name',guild=gid,name=validate_name(values['name'])),
            '호격·접미사를 줄인 호출도 문맥을 확인해요. 실제 Discord 이름 변경에는 권한이 필요할 수 있어요.',guard_context=True)
    def render(self):
        self.canvas.delete('all');self.hits=[];self.feedback.clear();w=max(1040,self.canvas.winfo_width());h=max(740,self.canvas.winfo_height())
        self.canvas.create_rectangle(0,0,196,h,fill='#0e1521',outline='')
        self.canvas.create_oval(24,27,44,47,fill=ACCENT,outline='');self.canvas.create_oval(30,33,38,41,fill=BG,outline='')
        self.text(56,25,'EchoMate',16,bold=True);self.text(26,63,'내 PC에서 동작하는 봇',8,MUTED)
        nav=[('setup','처음 사용 안내'),('models','AI 모델'),('spaces','대화할 곳'),('outputs','응답 방식'),('character','성격과 기분'),*PAGES.items(),('status','진행 상황'),('labs','실험 기능')]
        spacing=min(48,(h-220)//len(nav))
        for index,(page,label) in enumerate(nav):
            self.button(16,108+index*spacing,164,spacing-5,label,lambda p=page:self.set_page(p),self.page==page,navigation=True)
        self.text(24,h-90,'모델은 내 PC에서 실행',9,MUTED);self.text(24,h-65,'Gemma 4 12B',10)
        s=self.snapshot;cfg=s['cfg'] if s and s.get('cfg') else None
        title={'setup':'처음 사용 안내','models':'내 PC의 AI 모델','spaces':'대화할 곳','outputs':'응답 방식','character':'성격과 기분','status':'지금 무엇을 하고 있나요?','labs':'실험 기능',**PAGES}[self.page]
        title_size=21
        while title_size>12 and self.button_font(title_size).measure(title)>w-610:title_size-=1
        title_item=self.text(226,28,title,title_size,bold=True)
        phase_y=max(76,self.canvas.bbox(title_item)[3]+8)
        connected=bool(s and s['connected'])
        running=bool(s and s.get('running'))
        self.canvas.create_oval(w-350,39,w-342,47,fill=MINT if connected else MUTED,outline='')
        self.text(w-333,31,'연결됨' if connected else '연결 준비' if running else '봇 꺼짐',10,MUTED)
        preview_busy=bool(s and s.get('preview_busy'))
        cleanup_failed=bool(s and s.get('preview_cleanup_failed'))
        label='다시 열기 필요' if cleanup_failed else '미리보기 중' if preview_busy else '응답 재개' if connected and cfg and not cfg['enabled'] else '실행 중' if connected else '준비 중' if running else '봇 켜기'
        self.button(w-190,23,78,36,label,lambda:self.controller.submit('start'),primary=True,enabled=bool(cfg) and not preview_busy and not cleanup_failed and (not running or bool(connected and not cfg['enabled'])))
        self.button(w-102,23,78,36,'봇 끄기',lambda:self.controller.submit('stop'),enabled=running)
        error=' · '+s['error'] if s and s['error'] else ''
        phase=s['phase'] if s else '저장된 설정을 읽고 있어요'
        if phase.startswith('정지'):
            phase={'setup':'봇 정보 → 모델 → 허용 채널 순서로 준비해 주세요',
                   'models':'파일 선택과 실제 GPU 준비 상태를 따로 확인해 주세요',
                   'character':'모델을 바꾸지 않고 말투와 성격을 조절해요',
                   'status':'실행 중인 작업과 보존된 대화 이력을 구분해요',
                   'relations':'본인 동의가 있는 관계 자료를 서버별로 관리해요',
                   'memories':'장기 기억과 요약의 동의·출처·만료를 확인해요',
                   'reminders':'예약 시간과 발송 상태를 확인해요'}.get(self.page,'허용 채널을 설정한 뒤 봇을 켜 주세요')
        self.text(226,phase_y,self.ellipsize(phase+error,max(100,w-660)),10,MUTED)
        self.button(w-400,phase_y-4,130,28,'상태·오류',self.show_status_detail)
        if cfg and connected:self.toggle(w-200,78,'응답 허용',cfg['enabled'],lambda:self.set_value('enabled',not cfg['enabled']))
        self.server_list.place_forget();self.channel_list.place_forget()
        self.people_list.place_forget();self.record_list.place_forget();self.job_list.place_forget();self.model_list.place_forget()
        if self.page=='setup':self.draw_setup(w,h,cfg)
        elif self.page=='models':self.draw_models(w,h,cfg)
        elif self.page=='spaces':self.draw_spaces(w,h,cfg)
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
        if self.canvas.focus_get() is self.canvas and 0<=self.focus_index<len(self.hits):
            x,y,bw,bh,_=self.hits[self.focus_index];self.canvas.create_rectangle(x-2,y-2,x+bw+2,y+bh+2,outline=MINT)
    def draw_spaces(self,w,h,cfg):
        left=226;sy=143;bottom=h-66;right=w-274;mid=left+225
        for x,width in [(left,210),(mid,right-mid-15),(right,250)]:rounded(self.canvas,x,sy,width,bottom-sy,PANEL)
        self.text(left+16,sy+16,'가입한 서버',12,bold=True);self.text(mid+16,sy+16,'채널 · 스레드',12,bold=True)
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
            self.button(x,sy+64,216,24,'이모지 켜기 → 응답 방식',lambda:self.set_page('outputs'),font_size=8)
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
             ('먼저 말하기 간격','cooldown',10,2,3600),('대화 참여 유지','engagement_seconds',60,10,86400)]):
            self.number(250,382+index*34,label,key,max(lo,cfg[key]),step,lo,hi)
        p=cfg.get('character_profile') or {'name':'EchoMate'}
        self.text(250,559,self.ellipsize('캐릭터 · '+p['name'],w-290,10),10,MUTED)
        self.button(250,583,150,34,'프로필 편집·복제',self.edit_profile)
        self.button(410,583,128,34,'저장한 프로필',self.profile_library)
        self.button(548,583,128,34,'로컬 미리보기',self.character_preview)
        self.button(686,583,128,34,'가져오기·내보내기',self.profile_files)
        self.toggle(250,638,'성인 유머 · 연령 제한 채널에서만',cfg['adult_humor'],lambda:self.set_value('adult_humor',not cfg['adult_humor']))
        self.button(686,634,128,30,'표현 고급 설정',self.advanced_profile)
        self.text(250,671,'기분·강도는 즉시 저장해요. 팝업은 ‘적용’으로 저장해요.',9,MUTED,width=w-290)

    def draw_setup(self,w,h,cfg):
        from .onboarding import GUIDE
        rounded(self.canvas,226,143,w-252,h-210,PANEL)
        self.text(250,166,'나만의 Discord 봇을 준비해요',14,bold=True)
        for y,title,body in ((214,'1. 내 봇 정보 등록','공식 Developer Portal에서 봇을 만든 뒤\n본인 사용자 ID와 토큰을 안전하게 등록해요.'),
                             (304,'2. 모델과 캐릭터 선택','설치한 모델 폴더를 확인하고 말투를 골라요.\n모델 파일과 개인 자료는 배포판에 포함되지 않아요.'),
                             (394,'3. 활동할 채널 설정','대화할 곳에서 허용 범위를 저장해요.\n준비를 마친 뒤 직접 봇을 켜 주세요.')):
            self.text(250,y,title,11,bold=True);self.text(250,y+30,body,10,MUTED,width=w-300)
        self.button(250,h-190,190,36,'봇 정보 등록' if not cfg else '봇 정보 등록됨',self.setup_credentials,enabled=not bool(cfg))
        self.button(450,h-190,150,36,'모델 확인하기',lambda:self.set_page('models'))
        self.button(610,h-190,150,36,'연결 준비 자세히',lambda:self.form('Discord 연결 준비 안내',[],lambda values:None,GUIDE,read_only=True))
        self.text(250,h-130,'연결·서버 조회는 자동 실행하지 않아요. 준비 후 ‘대화할 곳’에서 직접 새로고침하세요.',9,MUTED,width=w-290)

    def setup_credentials(self):
        self.form('내 봇 정보 등록',[('owner','본인 Discord 사용자 ID',''),('token','Developer Portal의 공식 Bot Token','')],
                  lambda v:self.controller.submit('setup',owner=v['owner'],token=v['token']),
                  '현재 Windows 계정으로 암호화해 보관해요. 기존 정보는 덮어쓰지 않아요.')

    def draw_models(self,w,h,cfg):
        if not cfg:return
        busy=bool(self.snapshot.get('model_preparing') or self.snapshot.get('preview_busy') or self.snapshot.get('preview_cleanup_failed'))
        rounded(self.canvas,226,143,w-252,h-210,PANEL)
        self.text(250,163,'공식 기본: Gemma 4 12B · Transformers / NF4',13,bold=True)
        self.text(250,199,'폴더의 파일 구조와 템플릿을 검사해요. 실제 준비 검증이 끝나야 적용돼요.',10,MUTED,width=w-290)
        self.button(250,233,140,34,'모델 폴더 선택',self.choose_model_folder,enabled=not busy)
        self.button(400,233,110,34,'다시 검색',lambda:self.controller.submit('models'))
        official=any(m['compatible'] and 'models--google--gemma-4-12B-it' in m['path'] for m in self.snapshot.get('models',[]))
        self.button(520,233,130,34,'원본 기본 모델',lambda:self.set_value('model','base'),enabled=official and not busy)
        entries=self.snapshot.get('models',[])
        self.model_list.empty_hint='모델 목록이 비어 있어요\n모델 폴더를 선택해 주세요'
        self.model_list.set_items([dict(id=m['id'],label=m['name'],hint=m['format']+' · '+('파일 검사 통과' if m['compatible'] else '사용 불가')) for m in entries])
        self.model_list.selected={self.model_id} if self.model_id else set();self.model_list.redraw()
        self.model_list.place(x=250,y=290,width=280,height=max(90,h-435))
        if self.model_id and not any(m['id']==self.model_id for m in entries):self.model_id=None;self.model_list.selected=set()
        selected=next((m for m in entries if m['id']==self.model_id),None)
        if not selected:
            self.text(550,295,'선택한 모델의 상세 정보',12,bold=True,width=w-590)
            self.text(550,333,'왼쪽에서 모델을 선택하세요.\n아직 목록이 없다면 설치한 폴더를 지정해 주세요.',10,MUTED,width=w-590)
        phase=self.snapshot.get('model_load_phase')
        if selected:
            sharded=bool(selected.get('largest_shard_bytes',0) and selected['largest_shard_bytes']<selected['bytes'])
            self.text(550,295,selected['format']+f" · {selected['bytes']/1024**3:.1f}GiB"+(' · 분할 가중치' if sharded else ''),11,bold=True)
            self.text(550,332,self.ellipsize(selected['reason'],w-590),10,MUTED)
            self.text(550,390,self.ellipsize(selected['path'],w-590,9,middle=True),9,MUTED)
            self.button(550,420,150,30,'모델 상세 보기',lambda:self.form('선택한 모델 정보',[
                ('name','모델 이름',selected['name']),('path','폴더 위치',selected['path']),('format','형식과 백엔드',selected['format']+' · '+selected.get('backend','Transformers / NF4')),
                ('reason','파일 검사 결과',selected['reason'])],lambda values:None,'파일 검사와 실제 GPU 준비 검증은 별개예요.',read_only=True))
            self.text(550,458,self.ellipsize('파일 검사 통과 · GPU 준비는 적용할 때 확인해요' if selected['compatible'] else '지원하지 않는 모델은 적용할 수 없어요',w-590,9),9,MUTED)
            current=cfg['model']==selected['id'] or cfg['model']=='base' and 'models--google--gemma-4-12B-it' in selected['path']
            self.text(550,494,'현재 설정된 모델이에요' if current else '목록 선택만으로는 모델이 바뀌지 않아요',8,MUTED,width=w-590)
            self.button(550,540,150,34,'검증 후 적용',lambda:self.set_value('model',selected['id']),enabled=selected['compatible'] and not busy)
        if busy and phase:self.text(250,h-138,phase,9,ACCENT,width=w-290)
        elif self.snapshot.get('preview_busy'):self.text(250,h-138,'미리보기 완료 또는 취소 후 모델을 변경해 주세요.',9,MUTED,width=w-290)
        self.text(250,h-107,'GPU와 Windows 커밋 여유를 함께 확인해요.\n검증 환경: RTX 4070 Ti SUPER 16GB · RAM 32GB',9,MUTED,width=w-290)

    def choose_model_folder(self):
        from tkinter import filedialog
        folder=filedialog.askdirectory(parent=self.root,title='모델 또는 모델을 모아둔 폴더')
        if folder:self.controller.submit('models',roots=[folder])

    def select_model(self,ids):self.model_id=next(iter(ids),None);self.render()

    def edit_profile(self):
        from .character_profiles import DEFAULT_PROFILE,validate_profile
        p=dict(self.snapshot['cfg'].get('character_profile') or DEFAULT_PROFILE)
        from .character_profiles import SHARED_FIELDS
        p.update({k:self.snapshot['cfg'][k] for k in SHARED_FIELDS})
        def save(v):
            p.update(name=v['name'],introduction=v['intro'],speech={'반말':'casual','존댓말':'polite'}[v['speech']],energy=int(v['energy']),humor=int(v['humor']),detail={'간단히':'brief','균형':'balanced','자세히':'detailed'}[v['detail']])
            validate_profile(p)
            self.controller.submit('profiles',action='save_apply',key=v['key'],value=p)
        import secrets
        def submit(v):v['key']='character-'+secrets.token_hex(5);save(v)
        self.form('캐릭터 편집 · 복제해서 저장',[('name','캐릭터 이름',p['name']),('intro','소개 · 지시문이 아닌 표시 자료',p['introduction']),('speech','기본 말투 · 반말 / 존댓말','반말' if p['speech']=='casual' else '존댓말'),('energy','반응 에너지 · 0~100',p['energy']),('humor','농담 참여 성향 · 0~100',p['humor']),('detail','설명 · 간단히 / 균형 / 자세히',{'brief':'간단히','balanced':'균형','detailed':'자세히'}[p['detail']])],submit,'적용하면 같은 이름도 별도 복사본으로 저장해요. 닫으면 편집을 취소해요. 권한·개인정보·사실성·코드 출력 제한은 바뀌지 않아요.',controls={
            'speech':choice_field(['반말','존댓말']),'energy':range_field('첫 반응의 활기와 에너지를 조절해요.'),
            'humor':range_field('상황에 맞는 농담에 얼마나 적극적으로 참여할지 정해요.'),'detail':choice_field(['간단히','균형','자세히'])})

    def profile_library(self):
        self.controller.submit('profiles')
        from .character_profiles import DEFAULT_PROFILE
        dialog=tk.Toplevel(self.root);dialog.title('저장한 캐릭터');dialog.configure(bg=PANEL);dialog.geometry('540x490');dialog.transient(self.root)
        canvas=tk.Canvas(dialog,bg=PANEL,highlightthickness=0);canvas.pack(fill='both',expand=True)
        canvas.create_text(24,22,text='프로필을 고르고 적용하세요',anchor='nw',fill=FG,font=('맑은 고딕',13,'bold'))
        feedback=CanvasFeedback(canvas,keyboard=True,activate_on_release=True)
        selected=['default']
        def select_profile(ids):
            selected[0]=next(iter(ids),'default');refresh_feedback()
        listing=SelectionList(canvas,select_profile)
        listing.place(x=24,y=64,width=490,height=280)
        timer=[None];deleted_label=[None];pending=[None];completion_timer=[None]
        message=canvas.create_text(24,415,text='',anchor='nw',fill=MUTED,font=('맑은 고딕',9),width=490)
        def complete():
            from asyncio import CancelledError
            completion_timer[0]=None
            if not pending[0].done():completion_timer[0]=dialog.after(60,complete);return
            try:
                result=pending[0].result();ok=result.get('ok',False) if isinstance(result,dict) else result is not False
                error=result.get('error','') if isinstance(result,dict) else ''
            except (Exception,CancelledError) as exc:ok=False;error=type(exc).__name__
            pending[0]=None
            if ok:dialog.destroy()
            else:
                canvas.itemconfigure(message,text='적용하지 못했어요 · '+(error or '저장소를 확인한 뒤 다시 시도해 주세요'))
                listing.configure(state='normal');refresh_feedback()
        def close():
            if pending[0] is None:dialog.destroy()
        def refresh():
            values=(self.snapshot or {}).get('profiles',{}) or {'default':DEFAULT_PROFILE}
            listing.set_items([dict(id=k,label=v['name']+' · '+('기본' if k=='default' else '저장본 '+str(i)),hint=v['introduction']) for i,(k,v) in enumerate(values.items(),1)])
            if selected[0] not in values:selected[0]=next(iter(values))
            listing.selected={selected[0]};listing.redraw()
            refresh_feedback()
            timer[0]=dialog.after(400,refresh)
        for x,label in ((24,'적용'),(185,'삭제'),(346,'기본값 복원')):
            shape=rounded(canvas,x,365,145,36,CARD,8);item=canvas.create_text(x+72,383,text=label,fill=FG,font=('맑은 고딕',10))
            feedback.add((x,365,145,36),shape,item,danger=label=='삭제',callback=lambda x=x:click(type('Click',(),{'x':x+10,'y':380})()))
            if label=='삭제':deleted_label[0]=item
        def refresh_feedback():
            for i,region in enumerate(feedback.regions):region['enabled']=pending[0] is None and (i!=1 or selected[0]!='default')
            feedback.paint()
        def click(e):
            if pending[0] is not None:return
            if not 365<=e.y<=401:return
            action='apply' if 24<=e.x<=169 else 'delete' if 185<=e.x<=330 else 'restore' if 346<=e.x<=491 else None
            if action=='delete' and selected[0]=='default':return
            if action=='delete':
                key=selected[0];expected=(self.snapshot or {}).get('profiles',{}).get(key)
                if expected is None:return
                def confirm(values):
                    if values['confirm']!='삭제':raise ValueError()
                    if (self.snapshot or {}).get('profiles',{}).get(key)!=expected:raise ValueError()
                    return self.controller.submit('profiles',action='delete',key=key)
                self.form('저장한 캐릭터 삭제',[('confirm','삭제할 때만 삭제라고 입력','')],confirm,
                    expected['name']+' 저장본을 지워요. 현재 적용한 캐릭터 설정과 다른 저장본은 유지해요.')
                return
            if action:
                future=self.controller.submit('profiles',action=action,key=selected[0])
                from concurrent.futures import Future
                from asyncio import Future as AsyncFuture
                if isinstance(future,(Future,AsyncFuture)):
                    pending[0]=future;listing.configure(state='disabled');refresh_feedback();canvas.itemconfigure(message,text='저장 중 · 적용 결과를 확인하고 있어요 · 잠시 기다려 주세요')
                    completion_timer[0]=dialog.after_idle(complete)
                else:dialog.destroy()
        def closed(event):
            if event.widget is dialog:
                for job in (timer[0],completion_timer[0]):
                    if job:
                        try:dialog.after_cancel(job)
                        except tk.TclError:pass
        dialog.protocol('WM_DELETE_WINDOW',close)
        dialog.bind('<Escape>',lambda e:close());dialog.bind('<Destroy>',closed)
        refresh()

    def advanced_profile(self):
        from .character_profiles import DEFAULT_PROFILE,validate_profile
        p=dict(self.snapshot['cfg'].get('character_profile') or DEFAULT_PROFILE)
        def save(v):
            for k in ('calmness','honesty','exclamation','emoji'):p[k]=int(v[k])
            p['length']={'상황에 맞게':'adaptive','짧게':'short'}[v['length']]
            p['swearing']={'끔':False,'가벼운 감탄만':True}[v['swearing']]
            validate_profile(p);return self.set_value('character_profile',p)
        self.form('표현 고급 설정',[(k,label,p[k]) for k,label in (('calmness','차분함'),('honesty','솔직함'),('exclamation','감탄 빈도'),('emoji','답변 속 이모지 빈도'))]+[('length','잡담 길이','상황에 맞게' if p['length']=='adaptive' else '짧게'),('swearing','가벼운 비속어','가벼운 감탄만' if p['swearing'] else '끔')],save,
            '편집 중인 값이에요. 적용하면 저장하고, 닫으면 원래 값을 유지해요. 표현은 5단계 강도로 반영돼요. 필수 설명·사실·권한은 바뀌지 않아요.',controls={
                'calmness':range_field('답변을 얼마나 차분하고 안정적인 톤으로 말할지 정해요.',anchors=('0 · 생동감 있게','50 · 균형 있게','100 · 차분하게')),
                'honesty':range_field('돌려 말하기보다 결론과 한계를 직접 말하는 정도예요. 사실은 항상 지켜요.',anchors=('0 · 완곡하게','50 · 명료하게','100 · 직접적으로')),
                'exclamation':range_field('“와”, “오” 같은 짧은 감탄을 얼마나 자주 쓸지 정해요.',anchors=('0 · 거의 안 함','50 · 보통','100 · 자주')),
                'emoji':range_field('답변 글 안의 🙂 같은 이모지예요. 메시지에 누르는 반응과는 달라요. 반복 웃음 문자는 계속 억제해요.',anchors=('0 · 안 씀','50 · 드물게','100 · 상황에 맞게')),
                'length':choice_field(['짧게','상황에 맞게'],'잡담을 짧게 끝내거나 상황에 맞는 길이로 이어가요. 필요한 설명은 생략하지 않아요.'),
                'swearing':choice_field(['끔','가벼운 감탄만'],'상황을 향한 가벼운 표현만 허용해요. 사람을 모욕하거나 공격하는 표현은 허용하지 않아요.')})

    def profile_files(self):
        from tkinter import filedialog
        def act(v):
            export=v['action']=='내보내기'
            if v['action'] not in ('가져오기','내보내기'):raise ValueError()
            path=filedialog.asksaveasfilename(parent=self.root,defaultextension='.json') if export else filedialog.askopenfilename(parent=self.root,filetypes=[('캐릭터 JSON','*.json')])
            if path:
                import secrets
                self.controller.submit('profiles',action='export_current' if export else 'import',key='imported-'+secrets.token_hex(5),path=path)
        self.form('프로필 파일',[('action','작업 선택','내보내기')],act,
            '내보내기는 현재 적용한 캐릭터예요. 가져오기는 기존 자료를 덮어쓰지 않고 새 프로필로 보관해요. 저장한 프로필에서 선택해 적용하세요. 토큰·대화·기억은 포함하지 않아요.',controls={'action':choice_field(['내보내기','가져오기'])})

    def character_preview(self):
        import secrets
        session=secrets.token_hex(12);pending=[False];input_error=['']
        dialog=tk.Toplevel(self.root);dialog.title('Discord 없이 캐릭터 미리보기');dialog.configure(bg=PANEL);dialog.geometry('690x510');dialog.minsize(560,420);dialog.transient(self.root)
        tk.Label(dialog,text='합성 질문으로 말투를 확인해요 · 대화·기억·관계·예약에 저장하지 않아요',bg=PANEL,fg=MUTED,font=('맑은 고딕',10),wraplength=630).pack(padx=22,pady=16,anchor='w')
        entry=tk.Entry(dialog,bg=CARD,fg=FG,insertbackground=FG,relief='flat',font=('맑은 고딕',11),highlightthickness=1,highlightbackground=LINE,highlightcolor=ACCENT);entry.pack(padx=22,fill='x',ipady=8);entry.insert(0,'처음 만난 친구에게 짧게 인사해 줘')
        actions=tk.Canvas(dialog,bg=PANEL,height=48,highlightthickness=0);actions.pack(fill='x',padx=22)
        output=tk.Text(dialog,bg=CARD,fg=FG,relief='flat',wrap='word',font=('맑은 고딕',11),state='disabled');output.pack(padx=22,pady=(0,22),fill='both',expand=True)
        def generate():
            if not 1<=len(entry.get().strip())<=1000:
                input_error[0]='질문은 공백을 제외하고 1~1000자로 입력해 주세요.';return
            input_error[0]=''
            if not pending[0] and not (self.snapshot or {}).get('preview_busy') and not (self.snapshot or {}).get('preview_cleanup_failed') and 1<=len(entry.get())<=1000:
                pending[0]=True;self.controller.submit('preview',text=entry.get(),session=session)
        feedback=CanvasFeedback(actions,keyboard=True,activate_on_release=True)
        shape=rounded(actions,8,8,137,32,CARD,8);label=actions.create_text(76,24,text='미리보기',fill=FG,font=('맑은 고딕',10))
        feedback.add((8,8,137,32),shape,label,primary=True,callback=generate)
        entry.bind('<Return>',lambda e:generate())
        old=[''];timer=[None]
        def poll():
            snap=self.snapshot or {};mine=snap.get('preview_session')==session
            value=input_error[0] or (snap.get('preview','') if mine else '') or ('요청을 준비하고 있어요' if pending[0] else '질문을 입력하고 답변을 생성해 보세요. 창을 닫으면 이 미리보기만 취소해요.')
            if pending[0] and snap.get('preview_rejection',{}).get('session')==session:
                value='요청을 시작하지 못했어요 · '+snap['preview_rejection']['error'];pending[0]=False
            if mine and not snap.get('preview_busy'):pending[0]=False
            if value!=old[0]:output.configure(state='normal');output.delete('1.0','end');output.insert('1.0',value);output.configure(state='disabled');old[0]=value
            busy=pending[0] or bool(snap.get('preview_busy') or snap.get('preview_cleanup_failed'))
            feedback.regions[0]['enabled']=not busy;feedback.paint();actions.itemconfigure(label,text='처리 중…' if busy else '미리보기')
            timer[0]=dialog.after(400,poll)
        def closed(event):
            if event.widget is dialog and timer[0]:
                try:dialog.after_cancel(timer[0])
                except tk.TclError:pass
                if not self.closing and not self.disposed:self.controller.submit('preview_cancel',session=session)
        dialog.bind('<Destroy>',closed);poll();entry.focus_set()
    def select_job(self,ids):self.job_id=next(iter(ids),None);self.render()
    def approve_commands(self):
        plan=(self.snapshot or {}).get('command_review')
        if not plan:
            self.controller.submit('command_review');return
        def save(v):
            if v['confirm']!='동의로 교체':raise ValueError()
            self.controller.submit('command_apply',fingerprint=plan['fingerprint'])
        def command_label(c):
            return c['name']+' ('+{1:'슬래시',2:'사용자',3:'메시지'}.get(c.get('type',1),'기타')+')'+(' · 접근 범위 '+str(c.get('contexts'))+' · 설치 '+str(c.get('integration_types'))+' · 기본 권한 '+str(c.get('default_member_permissions')))
        summary='Application '+plan['application']+'\n전역: '+', '.join(command_label(c) for c in plan['global_before'])+' → /동의\n'
        summary+='\n'.join('서버 '+g+': '+(', '.join(command_label(c) for c in rows) or '없음')+' → 서버별 명령 없음' for g,rows in plan['guilds'].items())
        self.form('확인한 명령 변경 승인',[('confirm','동의로 교체 라고 입력','')],save,summary+'\n범위 0=서버, None=응답에 정보 없음. 기본 권한 None=별도 기본 제한 없음. 서버별 권한 덮어쓰기와 실제 화면 표시는 별도 확인이에요.\n승인하면 이 애플리케이션만 변경해요. 전역 /동의를 먼저 재조회하고 성공한 경우에만 서버별 구형 명령을 정리해요. 목록이 바뀌면 재승인이 필요해요. 사용자 자료는 삭제하지 않아요.')
    def draw_status(self,w,h,s):
        if not s:return
        width=(w-282)/3
        for index,(label,value) in enumerate([('처리 중인 요청',str(s['pending'])),('진행 중인 대화',str(s['contexts'])),('최근 응답 시간',str(s['latency'])+'초' if s['latency'] is not None else '아직 없음')]):
            x=226+index*(width+15);rounded(self.canvas,x,143,width,100,PANEL)
            size=24
            while size>10 and (self.button_font(size).metrics('linespace')>42 or self.button_font(size).measure(value)>width-32):size-=1
            self.text(x+16,158,label,10,MUTED);self.text(x+16,191,value,size,bold=True)
        q=s.get('scheduler',{});statistics=s.get('statistics',{})
        self.text(242,254,self.ellipsize(f"GPU 실행 {q.get('running',0)} · 대기 {q.get('waiting',0)}",270,9),9,MUTED)
        self.text(530,254,self.ellipsize(f"오늘 응답 {statistics.get('responses_today',0)} · 반응 {statistics.get('reactions_today',0)}",w-756,9),9,MUTED)
        totals=s.get('runtime_totals',{})
        self.text(242,280,self.ellipsize(f"이번 실행 처리 {totals.get('finished',0)} · 실패/불확실 전송 {statistics.get('uncertain',0)} · 취소 {q.get('counts',{}).get('cancelled',0)} · 만료 {q.get('counts',{}).get('expired',0)} · 기존 종류 미기록 {statistics.get('legacy_today',0)}",w-300,8),8,MUTED)
        self.button(w-214,252,188,30,'비식별 진단 저장',lambda:self.controller.submit('diagnostics'))
        jobs=s.get('jobs',[])
        states={'waiting':'보충 대기','running':'처리 중','sent':'전송 완료','completed':'완료','silence':'침묵·보관 생략','failed':'실패','cancelled':'취소'}
        self.job_list.empty_hint='아직 처리한 요청이 없어요'
        flows=s.get('conversations',[])
        flow_labels={'active':'대화 중','waiting':'재개 대기','idle':'잠시 쉬는 중','ended':'종료'}
        self.job_list.set_items([dict(id=f['id'],label=flow_labels.get(f['status'],'대화')+' · '+f['conversation'][:8],hint=f"확인 참여자 {f['participants']}명 · 현재 상대 {len(f['peers'])}명") for f in flows]+[dict(id=j['id'],label=states.get(j['status'],j['status'])+' · '+STAGES.get(j['stage'],j['stage']),hint=str(j['seconds'])+'초 · 대화 '+j.get('flow','')[:8]) for j in jobs])
        self.job_list.place(x=240,y=300,width=270,height=max(100,h-445));self.job_list.selected={self.job_id} if self.job_id else set()
        selected=next((j for j in jobs if j['id']==self.job_id),None)
        if selected:
            self.text(535,302,'선택한 작업 · 원본 '+('연결됨' if selected['source_attached'] else '없음')+' · '+str(selected.get('source_count',1))+'개',11,bold=True)
            gpu=selected.get('gpu',{})
            self.text(535,335,f"GPU {gpu.get('status','완료 또는 아직 요청 전')} · 우선 {gpu.get('priority','-')} · 대기 {gpu.get('wait_seconds',0)}초 · 처리 {gpu.get('processing_seconds',0)}초",9,MUTED,width=w-575)
            social=selected.get('social',{})
            targets={'bot':'봇','human':'다른 사람','bot_group':'봇 포함 그룹','broadcast':'채널 전체','uncertain':'불확실'}
            links={'new':'독립 요청','continue':'기존 대화 지속','join':'확인된 합류','resume':'봇 대화 재개','commentary':'제3자 논평','shift':'상대 전환','end':'종료','uncertain':'미확정'}
            if social:
                self.text(535,365,'청자: '+targets.get(social.get('target'),'미확정')+' · '+links.get(social.get('relation'),'미확정')+' · '+('명시적 호출' if social.get('explicit_call') else '문맥 판정'),9,MUTED,width=w-575)
                peers=social.get('current_peers',[]);peer_text=', '.join(peers[:3])+(' 외 '+str(len(peers)-3)+'명' if len(peers)>3 else '')
                self.text(535,390,'현재 상대 ID: '+(peer_text or '없음')+' · 확인 참여자 '+str(social.get('confirmed_participants',0))+'명',8,MUTED,width=w-575)
            phases=('scope_check','member_resolution','conversation_candidates','conversation_wait','social','assessment','memory_lookup','summary','research','action','text','output_check','sending')
            for n,phase in enumerate(phases):
                seconds=selected.get('stages',{}).get(phase)
                value=f'{seconds:.3f}초' if seconds is not None else '진행 중' if selected['status']=='running' and selected['stage']==phase else '대기·생략'
                col=n//7;row=n%7;column_width=max(110,(w-575)/2)
                short={'member_resolution':'호칭·답장','conversation_wait':'요청 순서','social':'청자·관계','assessment':'참여 확인','memory_lookup':'기억 조회','summary':'요약','research':'근거 검색','action':'행동 선택','text':'답변 생성','output_check':'출력 검사','sending':'전송'}
                short.update(scope_check='범위·수신 권한',conversation_candidates='대화 후보 검색')
                self.text(535+col*column_width,424+row*21,short[phase]+' · '+value,8,MUTED,width=column_width-10)
            if selected.get('tokens') is not None:self.text(535,580,f"첫 토큰 {round(selected['ttft'],2) if selected.get('ttft') is not None else '-'}초 · 생성 {selected['tokens']}토큰 · {selected.get('tokens_per_second','-')}토큰/초",8,MUTED,width=w-575)
            from .desktop import NO_RESPONSE
            reason=next((NO_RESPONSE[c] for c in reversed(selected.get('codes',[])) if c in NO_RESPONSE),'전송 완료' if selected['status']=='sent' else '실행 중 / 상세 진단 파일 참고')
            self.text(535,h-105,'판단: '+reason,8,MUTED,width=w-575)
        else:
            flow=next((f for f in flows if f['id']==self.job_id),None)
            if flow:
                self.text(535,310,'대화 '+flow['conversation'][:8]+' · '+flow_labels.get(flow['status'],'미확정'),12,bold=True)
                self.text(535,350,'확인 참여자 '+str(flow['participants'])+'명 · 현재 직접 상대 '+str(len(flow['peers']))+'명',10,MUTED,width=w-580)
                peers=flow['peers'];peer_text=', '.join(peers[:3])+(' 외 '+str(len(peers)-3)+'명' if len(peers)>3 else '')
                self.text(535,390,'현재 상대 ID: '+(peer_text or '없음'),10,MUTED,width=w-580)
                self.text(535,440,'채널 ID: '+str(flow['channel'])+' · 마지막 답변 대상 ID: '+str(flow.get('last_recipient') or '없음'),9,MUTED,width=w-580)
                self.text(535,490,'과거 참여자라고 모든 발언에 답하지 않아요. 발언마다 실제 청자를 다시 확인해요.',10,MUTED,width=w-580)
            else:self.text(535,310,'대화나 작업을 선택하면 실제 상태와 판정 결과를 볼 수 있어요.',11,MUTED,width=w-580)
        self.text(242,h-107,'최근 판단: '+s['recent_reason'] if s.get('recent_reason') else '원문 메시지와 AI 비공개 추론은 표시하지 않아요.',9,MUTED,width=w-300)
    def draw_outputs(self,w,h,cfg):
        if not cfg:return
        rounded(self.canvas,226,143,w-252,h-210,PANEL)
        self.text(250,168,'어떤 방식으로 답할까요?',18,bold=True)
        self.text(250,215,'앱 전체의 응답 기능을 정해요.\n채널별 허용 범위는 ‘대화할 곳’에서 설정해요.',11,MUTED,width=w-310)
        for i,(key,label,hint) in enumerate([('text','글로 답하기','질문에 답하거나 대화를 이어가요.'),('reactions','이모지로 가볍게 반응하기','허용한 메시지에 Unicode 반응을 남겨요.'),('web_search','인터넷 근거 검색','공개 정보의 근거를 찾고, 확인 실패도 안내해요.')]):
            y=285+i*90;self.toggle(250,y,label,cfg[key],lambda k=key:self.set_value(k,not cfg[k]));self.text(300,y+36,hint,10,MUTED,width=w-355)
        self.button(250,h-205,180,30,'명령 목록 조회',lambda:self.controller.submit('command_review'))
        self.button(446,h-205,180,30,'변경안 검토 · 승인',self.approve_commands,enabled=bool((self.snapshot or {}).get('command_review')))
        self.text(250,h-155,'조회는 읽기 전용 · 변경은 대상 검토와 별도 승인 후\nAPI 등록 확인과 Discord 화면 표시 확인은 별개예요.',9,MUTED,width=w-300)
    def draw_labs(self,w,h,cfg):
        if not cfg:return
        rounded(self.canvas,226,143,w-252,h-210,PANEL)
        rounded(self.canvas,250,168,92,26,'#3a2c1c',7);self.text(262,172,'시험 중인 기능',8,'#efba75',True)
        self.text(250,221,'시각 인식 · 분석',19,bold=True)
        self.text(250,267,'사진·GIF·시각 에셋의 내용을 이미지로 분석해요.\n기본은 꺼져 있어요. 켜면 답변이 더 오래 걸릴 수 있어요.\n이 기능을 켜도 서버 전용 에셋이나 등록 미디어를 보내지는 않아요.',11,MUTED,width=w-310)
        self.toggle(250,363,'이미지 내용 분석을 시험해 보기',cfg['vision'],lambda:self.set_value('vision',not cfg['vision']))
        self.button(250,h-190,180,30,'이 서버 캐시 비우기',lambda:self.controller.submit('visual_cache',guild=self.guild_id,refresh=False),enabled=bool(self.guild_id))
        self.button(445,h-190,210,30,'선택 범위 다시 분석 · 최대5개',lambda:self.controller.submit('visual_cache',guild=self.guild_id,channel=next(iter(self.channel_ids)),refresh=True),enabled=bool(self.guild_id and self.channel_ids and self.snapshot.get('connected') and cfg['vision']))
        self.text(250,444,'평소에는 꺼 두는 것을 권장해요',13,bold=True)
        self.text(250,485,'일반 대화와 Unicode 이모지는 이 기능을 켜지 않아도 사용할 수 있어요.\n실험 결과는 틀릴 수 있으며, Lottie 형식의 이미지 분석은 아직 지원하지 않아요.',11,MUTED,width=w-310)
    def poll(self):
        if self.disposed:return
        import time
        if self.feedback.down or self.feedback.key_armed is not None:
            if time.monotonic()-self.feedback.pressed_at<2:
                self.poll_id=self.root.after(60,self.poll);return
            self.feedback.blur(None)
        changed=False
        for key,future in list(self.pending_actions.items()):
            if future.done():self.pending_actions.pop(key);changed=True
        try:
            while True:self.snapshot=self.controller.updates.get_nowait();changed=True
        except queue.Empty:pass
        if self.snapshot and not self.snapshot.get('cfg') and not getattr(self,'_setup_shown',False):
            self.page='setup';self._setup_shown=True
        if changed:self.refresh_lists()
        if self.page in PAGES:
            if time.monotonic()-getattr(self,'_records_refreshed_at',0)>5:self.refresh_records()
        if changed:self.render()
        self.poll_id=self.root.after(400,self.poll)
    def destroy(self):
        if self.disposed:return
        self.disposed=True
        self.root.after_cancel(self.poll_id)
        self.hits.clear();self.drafts.clear();self.snapshot=None
        self.pending_actions.clear()
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
