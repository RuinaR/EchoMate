"""Render synthetic EchoMate widgets on an inactive, owned Windows Desktop.

Never switches desktops, sends global input, or captures the input desktop.
The worker verifies its Desktop and each target HWND's process before capture.
"""
import argparse
import ctypes as c
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

PAGES=('setup','models','spaces','outputs','character','relations','memories','reminders','status','labs')


def api():
    user=c.WinDLL('user32',use_last_error=True)
    for name,args,result in (
        ('CreateDesktopW',[w.LPCWSTR,w.LPCWSTR,c.c_void_p,w.DWORD,w.DWORD,c.c_void_p],w.HANDLE),
        ('OpenDesktopW',[w.LPCWSTR,w.DWORD,w.BOOL,w.DWORD],w.HANDLE),
        ('SetThreadDesktop',[w.HANDLE],w.BOOL),('CloseDesktop',[w.HANDLE],w.BOOL),
        ('GetThreadDesktop',[w.DWORD],w.HANDLE),
        ('GetUserObjectInformationW',[w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.POINTER(w.DWORD)],w.BOOL),
        ('GetWindowThreadProcessId',[w.HWND,c.POINTER(w.DWORD)],w.DWORD),
        ('GetDC',[w.HWND],w.HDC),('ReleaseDC',[w.HWND,w.HDC],c.c_int),
        ('PrintWindow',[w.HWND,w.HDC,w.UINT],w.BOOL)):
        fn=getattr(user,name);fn.argtypes=args;fn.restype=result
    return user


def capture(widget,path,user):
    from PIL import Image
    hwnd=widget.winfo_id();pid=w.DWORD();user.GetWindowThreadProcessId(hwnd,c.byref(pid))
    if pid.value!=os.getpid():raise RuntimeError('Capture target is not owned')
    width=widget.winfo_width();height=widget.winfo_height();gdi=c.WinDLL('gdi32')
    for name,args,result in (
        ('CreateCompatibleDC',[w.HDC],w.HDC),('CreateDIBSection',[w.HDC,c.c_void_p,w.UINT,c.POINTER(c.c_void_p),w.HANDLE,w.DWORD],w.HANDLE),
        ('SelectObject',[w.HDC,w.HANDLE],w.HANDLE),('DeleteObject',[w.HANDLE],w.BOOL),('DeleteDC',[w.HDC],w.BOOL)):
        fn=getattr(gdi,name);fn.argtypes=args;fn.restype=result
    class Header(c.Structure):
        _fields_=[('size',w.DWORD),('width',w.LONG),('height',w.LONG),('planes',w.WORD),('bits',w.WORD),
            ('compression',w.DWORD),('image',w.DWORD),('x',w.LONG),('y',w.LONG),('used',w.DWORD),('important',w.DWORD)]
    header=Header(c.sizeof(Header),width,-height,1,32,0,0,0,0,0,0);bits=c.c_void_p()
    dc=user.GetDC(hwnd);mem=gdi.CreateCompatibleDC(dc);bmp=gdi.CreateDIBSection(dc,c.byref(header),0,c.byref(bits),None,0)
    if not dc or not mem or not bmp:raise RuntimeError('Capture allocation failed')
    old=gdi.SelectObject(mem,bmp)
    try:
        if not user.PrintWindow(hwnd,mem,2):raise RuntimeError('Owned widget rendering unavailable')
        image=Image.frombytes('RGB',(width,height),c.string_at(bits,width*height*4),'raw','BGRX')
        if len(image.getcolors(width*height) or [])<2:raise RuntimeError('Blank render is not a screenshot')
        image.save(path)
    finally:gdi.SelectObject(mem,old);gdi.DeleteObject(bmp);gdi.DeleteDC(mem);user.ReleaseDC(hwnd,dc)


def worker(output,pages=PAGES):
    user=api();name=os.environ.get('ECHOMATE_QA_DESKTOP','')
    if not name.startswith('EchoMate-QA-'):raise RuntimeError('Isolated worker only')
    desktop=user.OpenDesktopW(name,0,False,0xff)
    if not desktop or not user.SetThreadDesktop(desktop):raise c.WinError(c.get_last_error())
    own=user.GetThreadDesktop(c.WinDLL('kernel32').GetCurrentThreadId());value=c.create_unicode_buffer(256);needed=w.DWORD()
    if not user.GetUserObjectInformationW(own,2,value,c.sizeof(value),c.byref(needed)) or value.value.casefold()!=name.casefold():raise RuntimeError('Desktop verification failed')
    # No Tk objects may exist before the worker's thread is isolated.
    import queue,time,tkinter as tk
    from copy import deepcopy
    from types import SimpleNamespace
    from unittest.mock import Mock,patch
    from echomate_bot.desktop_ui import DesktopApp
    from echomate_bot.settings import DEFAULTS
    rows=[];errors=[];root=tk.Tk();root.withdraw()
    root.report_callback_exception=lambda kind,value,tb:errors.append(kind.__name__)
    app=DesktopApp(root,SimpleNamespace(updates=queue.Queue(),submit=Mock()))
    app.canvas.pack_forget()
    cfg=deepcopy(DEFAULTS);cfg['guilds']={'2':dict(enabled=True,channels={'3':dict(mode='mention')},threads={})}
    app.snapshot=dict(cfg=cfg,servers=[dict(id=2,label='합성 서버 · 긴 이름 검증',enabled=True,joined=True,channels=[dict(id=3,label='합성 채널',thread=False)])],
        phase='정지',error='',connected=False,running=False,pending=0,contexts=0,latency=None,progress=[],jobs=[],scheduler={},profiles={},
        models=[],companion=dict(people=[],memories=[],reminders=[],digests=[]))
    app.guild_id=2
    try:
        root.deiconify()
        for dpi,scale in ((100,4/3),(125,5/3),(150,2)):
            root.tk.call('tk','scaling',scale)
            for width,height in ((1040,740),(1180,820)):
                root.geometry(f'{width}x{height}');app.canvas.place(x=0,y=0,width=width,height=height)
                for page in pages:
                    app.set_page(page);app.refresh_lists();start=time.perf_counter();app.render();root.update()
                    filename=f'{page}-{dpi}-{width}.png';capture(app.canvas,output/filename,user)
                    rows.append(dict(page=page,dpi=dpi,width=width,seconds=time.perf_counter()-start,file=filename))
                if 'models' in pages:
                    app.snapshot['models']=[dict(id='synthetic-shard',name='합성 Gemma 분할 복사본',format='Transformers',path='models/synthetic-shard',bytes=22*1024**3,largest_shard_bytes=2*1024**3,compatible=True,reason='파일 검사 통과 · GPU 준비는 별도',memory_profile='gemma4-12b-sharded-2g')]
                    app.model_id='synthetic-shard';app.set_page('models');app.render();root.update()
                    filename=f'models-populated-{dpi}-{width}.png';capture(app.canvas,output/filename,user)
                    rows.append(dict(page='models_populated',dpi=dpi,width=width,file=filename))
                    app.snapshot['models']=[]
                if dpi==100 and width==1180 and 'character' in pages:
                    app.advanced_profile();root.update()
                    dialog=next(v for v in root.winfo_children() if isinstance(v,tk.Toplevel))
                    capture(dialog.winfo_children()[0],output/'advanced.png',user);dialog.destroy()
                    app.edit_profile();root.update()
                    dialog=next(v for v in root.winfo_children() if isinstance(v,tk.Toplevel))
                    canvas=dialog.winfo_children()[0];capture(canvas,output/'persona-editor-top.png',user)
                    canvas.yview_moveto(1);root.update();capture(canvas,output/'persona-editor-bottom.png',user);dialog.destroy()
                    app.preset_picker();root.update()
                    dialog=next(v for v in root.winfo_children() if isinstance(v,tk.Toplevel))
                    capture(dialog.winfo_children()[0],output/'persona-presets.png',user);dialog.destroy()
                    dialog=app.character_preview();root.update();capture(dialog,output/'persona-preview.png',user);dialog.destroy()
                if dpi==150 and width==1040 and 'outputs' in pages:
                    app.snapshot['command_review']=dict(application='42',global_before=[dict(id='100',name='synthetic_legacy',type=1,contexts=[0],integration_types=[0],default_member_permissions=None)],guilds={'2':[]},fingerprint='synthetic')
                    app.approve_commands();root.update()
                    dialog=next(v for v in root.winfo_children() if isinstance(v,tk.Toplevel))
                    capture(dialog.winfo_children()[0],output/'command-approval.png',user);dialog.destroy()
                    app.snapshot['command_review']=None
        if errors:raise RuntimeError('Tk callback failures: '+','.join(errors))
        (output/'report.json').write_text(json.dumps(dict(isolated_desktop_verified=True,user_desktop_captured=False,rows=rows,callback_errors=errors),indent=2),encoding='utf-8')
    finally:app.destroy();user.CloseDesktop(desktop)


def run(output,pages=PAGES):
    output=Path(output).resolve()
    if not output.is_relative_to((Path.cwd()/'local_data').resolve()) or output.exists():raise ValueError('Fresh private output required')
    output.mkdir(parents=True)
    user=api();name='EchoMate-QA-'+uuid.uuid4().hex;desktop=user.CreateDesktopW(name,None,None,0,0xff,None)
    if not desktop:raise c.WinError(c.get_last_error())
    try:
        startup=subprocess.STARTUPINFO();startup.lpDesktop=name
        subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker','--output',str(output),'--pages',*pages],startupinfo=startup,
            env=dict(os.environ,ECHOMATE_QA_DESKTOP=name),check=True,timeout=120)
    finally:user.CloseDesktop(desktop)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--worker',action='store_true');parser.add_argument('--pages',nargs='+',choices=PAGES,default=list(PAGES));args=parser.parse_args()
    if args.worker:worker(Path(args.output),args.pages)
    else:run(args.output,args.pages)
