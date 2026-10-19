"""Small Canvas controls. Values remain draft data until the form is applied."""
import math
import tkinter as tk
from tkinter import font as tkfont

PANEL='#121b28';CARD='#182333';FG='#e9eff9';MUTED='#94a4bb';ACCENT='#9b91ff'


class CanvasFeedback:
    """Repaint only interactive items, never a page, database or model."""
    def __init__(self,canvas,keyboard=False):
        self.canvas=canvas;self.regions=[];self.pointer=None;self.down=False;self.index=-1
        canvas.bind('<Motion>',self.motion,add='+');canvas.bind('<Leave>',self.leave,add='+')
        canvas.bind('<ButtonPress-1>',self.press,add='+');canvas.bind('<ButtonRelease-1>',self.release,add='+')
        canvas.bind('<FocusIn>',lambda e:self.paint(),add='+');canvas.bind('<FocusOut>',self.blur,add='+')
        if keyboard:
            canvas.configure(takefocus=True)
            canvas.bind('<Left>',lambda e:self.move(-1));canvas.bind('<Right>',lambda e:self.move(1))
            canvas.bind('<Return>',self.activate);canvas.bind('<space>',self.activate)
    def clear(self):self.regions=[];self.index=-1
    def add(self,box,background,text=None,*,enabled=True,selected=False,primary=False,danger=False,callback=None):
        region=dict(box=box,background=background,text=text,enabled=enabled,selected=selected,primary=primary,danger=danger,callback=callback)
        self.regions.append(region);self.paint([region]);return region
    def hit(self):
        if self.pointer is None:return None
        px,py=self.pointer
        return next((r for r in reversed(self.regions) if r['box'][0]<=px<=r['box'][0]+r['box'][2] and r['box'][1]<=py<=r['box'][1]+r['box'][3]),None)
    def motion(self,e):
        previous=self.hit();self.pointer=(self.canvas.canvasx(e.x),self.canvas.canvasy(e.y));current=self.hit()
        changed=[]
        for region in (previous,current):
            if region is not None and not any(region is item for item in changed):changed.append(region)
        self.paint(changed)
    def leave(self,e):self.pointer=None;self.down=False;self.paint()
    def blur(self,e):self.pointer=None;self.down=False;self.paint()
    def press(self,e):
        self.down=True;self.motion(e);r=self.hit()
        if r and r['enabled']:self.index=self.regions.index(r)
        self.paint()
    def release(self,e):self.down=False;self.motion(e)
    def move(self,d):
        choices=[i for i,r in enumerate(self.regions) if r['enabled']]
        if choices:self.index=choices[(choices.index(self.index)+d)%len(choices)] if self.index in choices else choices[0]
        self.paint();return 'break'
    def activate(self,e):
        if not 0<=self.index<len(self.regions):self.move(1)
        if 0<=self.index<len(self.regions):
            r=self.regions[self.index]
            if r['enabled'] and r['callback']:r['callback']()
        return 'break'
    def paint(self,only=None):
        if not self.canvas.winfo_exists():return
        hit=self.hit()
        for r in (self.regions if only is None else only):
            i=self.regions.index(r)
            active=r is hit and r['enabled'];focused=i==self.index and self.canvas.focus_get() is self.canvas
            state='disabled' if not r['enabled'] else 'pressed' if active and self.down else 'hover' if active else 'selected' if r['selected'] else 'normal'
            r['state']=state
            if state=='disabled':fill='#151d29';outline='#303b4b';color='#718096'
            elif r['danger']:fill={'pressed':'#71394a','hover':'#573040'}.get(state,'#332332');outline='#dc7e94';color='#ffb3c0'
            elif r['primary']:fill={'pressed':'#766bd2','hover':'#b0a8ff'}.get(state,ACCENT);outline=ACCENT;color='#0b1018'
            else:fill={'pressed':'#3e3b65','hover':'#303b51'}.get(state,'#2d2b4d' if r['selected'] else CARD);outline=ACCENT if r['selected'] else '#3a4860';color=ACCENT if r['selected'] else FG
            self.canvas.itemconfigure(r['background'],fill=fill,outline=ACCENT if focused else outline,width=2 if focused or r['selected'] else 1)
            if r['text']:self.canvas.itemconfigure(r['text'],fill=color)
        self.canvas.configure(cursor='hand2' if hit and hit['enabled'] else '')


class RangeControl(tk.Canvas):
    """Bounded slider with value/meaning, arrows, Page keys and Home/End."""
    def __init__(self,parent,variable,minimum=0,maximum=100,step=1,anchors=('낮음','보통','높음'),**kwargs):
        super().__init__(parent,height=70,bg=PANEL,highlightthickness=1,highlightbackground=PANEL,highlightcolor=ACCENT,takefocus=True,**kwargs)
        self.variable=variable;self.minimum=minimum;self.maximum=maximum;self.step=step;self.anchors=anchors;self.hover=False;self.pressed=False
        self.bind('<Configure>',lambda e:self.redraw());self.bind('<FocusIn>',lambda e:self.redraw());self.bind('<FocusOut>',lambda e:self.redraw())
        self.bind('<Enter>',lambda e:self.over(True));self.bind('<Leave>',lambda e:self.over(False))
        self.bind('<Button-1>',self.click);self.bind('<B1-Motion>',self.drag);self.bind('<ButtonRelease-1>',self.release)
        for key,change in [('Left',-step),('Down',-step),('Right',step),('Up',step),('Prior',step*10),('Next',-step*10)]:
            self.bind('<'+key+'>',lambda e,d=change:self.adjust(d))
        self.bind('<Home>',lambda e:self.key_set(self.minimum));self.bind('<End>',lambda e:self.key_set(self.maximum))
        self.value_font=tkfont.Font(self,family='맑은 고딕',size=11,weight='bold')
        self.legend_font=tkfont.Font(self,family='맑은 고딕',size=9)
        self.number=None;self.track_y=max(32,self.value_font.metrics('linespace')+14)
        self.configure(height=max(70,self.track_y+self.legend_font.metrics('linespace')+16))
        if maximum-minimum>100:
            def valid(proposed):
                if proposed=='':return True
                if not proposed.isascii() or not proposed.isdecimal() or len(proposed)>len(str(maximum)):return False
                return minimum<=int(proposed)<=maximum
            self.number=tk.Spinbox(self,from_=minimum,to=maximum,increment=step,textvariable=variable,
                bg=CARD,fg=FG,buttonbackground=CARD,insertbackground=FG,relief='flat',
                highlightthickness=1,highlightbackground='#344259',highlightcolor=ACCENT,
                font=('맑은 고딕',10),validate='key',validatecommand=(self.register(valid),'%P'))
            number_height=max(24,self.number.winfo_reqheight());self.track_y=max(self.track_y,number_height+8)
            self.number.place(relx=1,x=-16,y=0,anchor='ne',width=104,height=number_height)
            self.configure(height=max(70,self.track_y+self.legend_font.metrics('linespace')+16))
        self.trace=variable.trace_add('write',lambda *args:self.redraw());self.bind('<Destroy>',self.cleanup)
        self.redraw()
    def cleanup(self,e):
        if e.widget is self:
            self.variable.trace_remove('write',self.trace);self.value_font=None;self.legend_font=None
    def enabled(self):return self.cget('state')!='disabled'
    def set_enabled(self,value):
        self.configure(state='normal' if value else 'disabled')
        if self.number is not None:self.number.configure(state='normal' if value else 'disabled')
        self.redraw()
    def value(self):
        try:value=float(self.variable.get())
        except (ValueError,TypeError):raise ValueError('숫자 범위를 확인해 주세요') from None
        if not math.isfinite(value) or not self.minimum<=value<=self.maximum:raise ValueError('숫자 범위를 확인해 주세요')
        return value
    def validate(self):
        value=self.value();steps=(value-self.minimum)/self.step
        if self.step>=1 and not math.isclose(steps,round(steps),abs_tol=1e-6):raise ValueError('조절 가능한 숫자 단위를 확인해 주세요')
    def set(self,value):
        value=float(value)
        if not math.isfinite(value) or not self.minimum<=value<=self.maximum:raise ValueError('숫자 범위를 확인해 주세요')
        self.variable.set(f'{value:g}');self.redraw()
    def key_set(self,value):
        if self.enabled():self.set(value)
        return 'break'
    def adjust(self,change):
        try:value=self.value()
        except ValueError:value=self.minimum
        return self.key_set(max(self.minimum,min(self.maximum,round(value+change,6))))
    def click(self,e):
        if not self.enabled():return
        self.focus_set();self.pressed=True;self.drag(e)
    def drag(self,e):
        if not self.enabled() or not self.pressed:return
        width=max(1,self.winfo_width()-32);ratio=max(0,min(1,(e.x-16)/width))
        self.set(max(self.minimum,min(self.maximum,self.minimum+round(ratio*(self.maximum-self.minimum)/self.step)*self.step)))
    def release(self,e):self.pressed=False;self.redraw()
    def over(self,value):self.hover=value;self.redraw()
    def redraw(self):
        self.delete('all');w=max(120,self.winfo_width() if self.winfo_width()>1 else int(float(self.cget('width'))));color=ACCENT if self.enabled() else MUTED
        try:value=self.value()
        except ValueError:value=self.minimum
        x=16+(w-32)*(value-self.minimum)/(self.maximum-self.minimum)
        if self.number is None:self.create_text(w-16,1,text=f'{value:g}',anchor='ne',fill=color,font=self.value_font)
        track=self.track_y
        self.create_line(16,track,w-16,track,fill='#344259',width=5)
        self.create_line(16,track,x,track,fill=color,width=5)
        radius=8 if self.pressed else 7
        self.create_oval(x-radius,track-radius,x+radius,track+radius,fill=color,outline=FG if self.hover or self.pressed else color,width=2)
        for px,anchor,text in [(16,'w',self.anchors[0]),(w/2,'center',self.anchors[1]),(w-16,'e',self.anchors[2])]:
            self.create_text(px,track+25,text=text,anchor=anchor,fill=MUTED,font=self.legend_font)


class SegmentControl(tk.Canvas):
    """Explicit finite choices. No arbitrary enum text is accepted."""
    def __init__(self,parent,variable,choices,**kwargs):
        self.choices=tuple(choices);self.variable=variable
        super().__init__(parent,bg=PANEL,highlightthickness=1,highlightbackground=PANEL,highlightcolor=ACCENT,takefocus=True,**kwargs)
        self.font=tkfont.Font(self,family='맑은 고딕',size=10)
        self.feedback=CanvasFeedback(self);self.boxes=[]
        self.bind('<Configure>',lambda e:self.redraw());self.bind('<Button-1>',self.click,add='+')
        for key,d in [('Left',-1),('Up',-1),('Right',1),('Down',1)]:self.bind('<'+key+'>',lambda e,d=d:self.move(d))
        self.bind('<Home>',lambda e:self.key_set(self.choices[0]));self.bind('<End>',lambda e:self.key_set(self.choices[-1]))
        self.trace=variable.trace_add('write',lambda *args:self.redraw());self.bind('<Destroy>',self.cleanup)
        self.redraw()
    def cleanup(self,e):
        if e.widget is self:
            self.variable.trace_remove('write',self.trace);self.font=None;self.feedback.clear()
    def enabled(self):return self.cget('state')!='disabled'
    def set_enabled(self,value):self.configure(state='normal' if value else 'disabled');self.redraw()
    def validate(self):
        if self.variable.get() not in self.choices:raise ValueError('목록에서 선택해 주세요')
    def set(self,value):
        if value not in self.choices:raise ValueError('목록에서 선택해 주세요')
        self.variable.set(value)
    def key_set(self,value):
        if self.enabled():self.set(value)
        return 'break'
    def move(self,d):
        self.validate();return self.key_set(self.choices[(self.choices.index(self.variable.get())+d)%len(self.choices)])
    def click(self,e):
        if not self.enabled():return
        self.focus_set()
        for box,value in self.boxes:
            x,y,w,h=box
            if x<=e.x<=x+w and y<=e.y<=y+h:self.set(value);return
    def redraw(self):
        self.delete('all');self.feedback.clear();w=max(100,self.winfo_width() if self.winfo_width()>1 else int(float(self.cget('width'))));cell=max(95,max(self.font.measure(c) for c in self.choices)+26)
        columns=max(1,min(len(self.choices),int(w//cell)));cell=(w-8*(columns-1)-4)/columns;self.boxes=[]
        self.configure(height=((len(self.choices)+columns-1)//columns)*38)
        for i,value in enumerate(self.choices):
            x=2+(i%columns)*(cell+8);y=2+(i//columns)*38;box=(x,y,cell,32)
            bg=self.create_rectangle(x,y,x+cell,y+32,fill=CARD,outline=ACCENT)
            selected=value==self.variable.get();label=('✓ ' if selected else '')+value
            text=self.create_text(x+cell/2,y+16,text=label,fill=FG,font=self.font)
            self.feedback.add(box,bg,text,enabled=self.enabled(),selected=selected,danger=value=='삭제');self.boxes.append((box,value))


def range_field(help_text='',minimum=0,maximum=100,step=1,anchors=('0 · 낮음','50 · 보통','100 · 높음')):
    return dict(kind='range',help=help_text,minimum=minimum,maximum=maximum,step=step,anchors=anchors)

def choice_field(choices,help_text=''):return dict(kind='choice',choices=choices,help=help_text)
