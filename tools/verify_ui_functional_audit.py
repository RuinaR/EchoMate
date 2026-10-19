"""Withdrawn Tk screen inventory and timing. Not a claim of end-to-end control QA."""
import argparse
from copy import deepcopy
import gc
import json
from pathlib import Path
import queue
import time
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import Mock

from echomate_bot.desktop_ui import DesktopApp
from echomate_bot.settings import DEFAULTS


def run(output):
    target=Path(output).resolve()
    target.relative_to((Path.cwd()/'local_data').resolve())
    if target.exists():raise ValueError('Use a fresh output file')
    rows=[]
    for dpi,scaling in ((100,4/3),(125,5/3),(150,2)):
        root=tk.Tk();root.withdraw();root.tk.call('tk','scaling',scaling)
        controller=SimpleNamespace(updates=queue.Queue(),submit=Mock())
        app=DesktopApp(root,controller)
        try:
            # A packed child of a withdrawn root may remain 1x1 despite the
            # root's geometry. Allocate it explicitly; never map the window.
            app.canvas.pack_forget()
            cfg=deepcopy(DEFAULTS)
            cfg['guilds']={'2':dict(enabled=True,channels={'3':dict(mode='mention',inherit=False)},threads={})}
            app.snapshot=dict(cfg=cfg,servers=[dict(id=2,label='긴 합성 서버 이름 '*12,enabled=True,channels=[dict(id=3,label='긴 채널 이름 '*12,thread=False)])],
                connected=False,running=False,phase='정지',error='',pending=0,contexts=0,latency=None,progress=[],jobs=[],scheduler={},
                companion=dict(guild=2,user=None,query='',kind=None,people=[dict(user=str(i),label='긴 합성 사용자 이름 '*10,affinity=50,interactions=0,last_at=0) for i in range(4,504)],memories=[],reminders=[]))
            app.guild_id=2
            for size in ('1040x740','1180x820'):
                requested_width,requested_height=map(int,size.split('x'))
                root.geometry(size);app.canvas.place(x=0,y=0,width=requested_width,height=requested_height);root.update_idletasks()
                if (app.canvas.winfo_width(),app.canvas.winfo_height())!=(requested_width,requested_height):raise AssertionError('Canvas geometry not allocated')
                original=deepcopy(app.snapshot)
                for scenario in ('empty','populated','loading','error','preparing'):
                    app.snapshot=deepcopy(original);snap=app.snapshot
                    snap['companion'].update(user='4',people=[] if scenario=='empty' else original['companion']['people'])
                    if scenario=='populated':
                        snap['models']=[dict(id=f'm{i}',name='긴 합성 모델 이름 '*8,path=f'models/demo{i}',format='Transformers',bytes=22*1024**3,largest_shard_bytes=2*1024**3,compatible=True,reason='합성 파일 검사 상태') for i in range(128)]
                        snap['companion']['memories']=[dict(memory_id=f'mem{i}',summary='긴 합성 기억 설명 '*8,kind='preference',status='active',expires_at=None) for i in range(500)]
                        snap['companion']['reminders']=[dict(reminder_id=f'r{i}',due_at=2000000000,text='합성 예약',status='scheduled') for i in range(500)]
                        app.model_id='m0'
                    elif scenario=='loading':snap['companion_loading']=True
                    elif scenario=='error':snap['error']='합성 조회 오류';snap['companion']['load_error']=True
                    elif scenario=='preparing':snap.update(model_preparing=True,running=True)
                    for page in ('setup','models','spaces','outputs','character','relations','memories','reminders','status','labs'):
                        app.set_page(page);app.record_user='4'
                        started=time.perf_counter();app.render();root.update_idletasks()
                        width=max(1040,app.canvas.winfo_width());height=max(740,app.canvas.winfo_height())
                        outside=[(x,y,w,h) for x,y,w,h,cb in app.hits if x<0 or y<0 or x+w>width or y+h>height]
                        clipped=[]
                        for item in app.canvas.find_withtag('button_label'):
                            box=app.canvas.bbox(item)
                            if box and (box[0]<0 or box[1]<0 or box[2]>width or box[3]>height):clipped.append(box)
                        rows.append(dict(dpi=dpi,size=size,actual_canvas=[width,height],page=page,scenario=scenario,render_ms=round((time.perf_counter()-started)*1000,3),
                            enabled_hit_targets=len(app.hits),outside=outside,clipped_button_labels=clipped))
        finally:
            app.destroy();app=None;root=None;gc.collect()
    result=dict(real_tk=True,desktop_input=False,discord=False,gpu=False,backend_mutations_verified=False,
        scope='screen render, enabled hit bounds and timing only; dialog flows and all control effects not certified',rows=rows,
        passed=not any(row['outside'] or row['clipped_button_labels'] for row in rows))
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(screens=len(rows),passed=result['passed'],max_render_ms=max(r['render_ms'] for r in rows))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
