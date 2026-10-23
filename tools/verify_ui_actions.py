"""Offline Canvas dispatch audit. Uses owned withdrawn Tk and temporary data.

This records dispatch coverage separately from storage postconditions in
test_ui_workflows. Native file chooser appearance and Discord are not tested.
"""
import argparse
import asyncio
from datetime import datetime,timezone
import inspect
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch

from echomate_bot.settings import private_path
from echomate_bot.runtime import Event
import test_ui_workflows as workflows

PAGES=('setup','spaces','models','character','outputs','relations','memories','reminders','status','labs')

async def offline_discord_request(route,**kwargs):
    """Real discord.py parsers, synthetic HTTP responses, no socket request."""
    user=dict(id='999',username='Synthetic',discriminator='0000',avatar=None,bot=True,flags=0)
    if route.path=='/users/@me':return user
    if route.path=='/oauth2/applications/@me':
        return dict(id='999',name='Synthetic',description='',icon=None,owner=user,verify_key='',bot_public=False,bot_require_code_grant=False)
    if route.path=='/users/@me/guilds':return [dict(id='2',name='Synthetic guild',icon=None,owner=True,permissions='0',features=[])]
    if route.path=='/guilds/{guild_id}/channels':return [dict(id='3',guild_id='2',type=0,name='Synthetic channel',position=0,permission_overwrites=[])]
    if route.path=='/guilds/{guild_id}/threads/active':return dict(threads=[],members=[],has_more=False)
    raise AssertionError('Unexpected Discord route in offline UI audit')

async def fixture(page):
    case=workflows.UIWorkflows();await case.asyncSetUp()
    app=case.app;store=case.c.companion
    for category in ('relationships','memory','summaries'):store.set_consent(2,4,category,True)
    store.set_affinity(2,4,50)
    memory=store.add_memory(2,4,3,'합성 취미 기록',require_consent=True)
    store.reserve_reminder(Event(810,2,3,4,'synthetic',datetime.now(timezone.utc)),time.time()+3600,'Asia/Seoul','합성 준비 알림')
    entry=dict(id='base',name='Synthetic model',path='models--google--gemma-4-12B-it/synthetic',format='Transformers',backend='mock preparation',bytes=100,compatible=True,reason='UI fixture only')
    case.c.models=[SimpleNamespace(**entry,public=lambda:dict(entry))]
    async def serving():await asyncio.Event().wait()
    case.c._run_bot=serving
    await case.c.refresh_companion(2,'4');await case.sync()
    app.page=page;app.record_user='4';app.model_id='base'
    app.record_key=memory if page=='memories' else store.reminders(2,4)[0]['reminder_id'] if page=='reminders' else '4'
    app.render()
    return case

def collect(app):
    entries=[];original=app.button;original_toggle=app.toggle
    def button(*args,**kw):
        caller=inspect.currentframe().f_back
        if kw.get('enabled',True):
            entries.append(dict(method=caller.f_code.co_name,line=caller.f_lineno,label=str(args[4]),rect=args[:4]))
        return original(*args,**kw)
    def toggle(x,y,label,on,callback):
        caller=inspect.currentframe().f_back
        entries.append(dict(method=caller.f_code.co_name,line=caller.f_lineno,label=label,rect=(x,y,38,22)))
        return original_toggle(x,y,label,on,callback)
    app.button=button;app.toggle=toggle
    try:app.render()
    finally:app.button=original;app.toggle=original_toggle
    return entries

async def run(output,pages=PAGES):
    def source_hashes():
        paths=[*Path('src').rglob('*.py'),Path(__file__),Path('tests/test_ui_workflows.py')]
        return {p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    sources=source_hashes()
    rows=[]
    for page in pages:
        first=await fixture(page)
        try:targets=collect(first.app)
        finally:await first.asyncTearDown()
        for target in targets:
            case=await fixture(page);before=len(case.commands);started=time.monotonic()
            try:
                # No GPU/backend load; model preparation and native file picker
                # are injected boundaries, explicitly recorded in the report.
                backend=SimpleNamespace(model=None,failed=False,prepare_mode=AsyncMock(),close=AsyncMock(),text=AsyncMock(return_value='합성 미리보기'))
                with patch('discord.http.HTTPClient.request',new=AsyncMock(side_effect=offline_discord_request)) as sdk_http,patch('aiohttp.ClientSession._request',new=AsyncMock(side_effect=AssertionError('External network forbidden'))) as outbound,patch('echomate_bot.inference.LocalBackend',return_value=backend),patch('tkinter.filedialog.askdirectory',return_value=''),patch('tkinter.filedialog.askopenfilename',return_value=''),patch('tkinter.filedialog.asksaveasfilename',return_value=''):
                    x,y,w,h=target['rect'];event=SimpleNamespace(x=x+w/2,y=y+h/2)
                    case.app.press(event);case.app.feedback.release(event)
                    await case.sync()
                    outbound.assert_not_awaited()
                    dialogs=[v for v in case.root.winfo_children() if isinstance(v,workflows.tk.Toplevel)]
                    # Every opened popup is cancelled using its own Escape
                    # binding when present. This is not a successful save.
                    for dialog in dialogs:
                        if dialog.bind('<Escape>'):workflows.invoke(dialog,'<Escape>')
                        else:dialog.destroy()
                    await case.sync()
                expected_error='봇 연결 후 명령 목록을 확인해 주세요' if target['label']=='명령 목록 확인 · 정리' and case.c.client is None else ''
                operations=[op for op,kw in case.commands[before:]]
                safe_offline_block=bool(expected_error and case.c.error==expected_error and operations==['command_review'] and sdk_http.await_count==0)
                rows.append(dict(page=page,method=target['method'],line=target['line'],label=target['label'],
                    passed=safe_offline_block if expected_error else not bool(case.c.error),expected_error=expected_error,sdk_http_mock_calls=sdk_http.await_count,external_network_calls=outbound.await_count,
                    commands=[op for op,kw in case.commands[before:]],popups_cancelled=len(dialogs),
                    controller_error=case.c.error,seconds=time.monotonic()-started))
            except Exception as exc:
                rows.append(dict(page=page,method=target['method'],line=target['line'],label=target['label'],passed=False,error=type(exc).__name__))
            finally:await case.asyncTearDown()
    result=dict(real_tk=True,native_desktop_input=False,real_discord=False,gpu=False,temporary_storage=True,
                scope='enabled Canvas button dispatch and popup cancellation; saves verified separately in test_ui_workflows',
                native_file_picker='mock boundary',model_preparation='mock boundary',source_hashes=sources,
                source_unchanged=sources==source_hashes(),rows=rows,passed=sources==source_hashes() and all(v['passed'] for v in rows))
    output=private_path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(dispatches=len(rows),passed=result['passed'],failed=[v for v in rows if not v['passed']])))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--page',choices=PAGES);a=p.parse_args()
    asyncio.run(run(a.output,(a.page,) if a.page else PAGES))
