"""Real GPU lifecycle with synthetic transport and isolated real SQLite."""
import argparse
import asyncio
from datetime import datetime,timezone
from pathlib import Path
import secrets
import shutil
import time
from echomate_bot.settings import Settings,private_path,atomic_private_json
from echomate_bot.runtime import Runtime,Event
from echomate_bot.inference import LocalBackend
from echomate_bot.instance import InstanceLease
from echomate_bot.companion_store import CompanionStore
from verify_parallel_gpu import Transport,Borrowed,settle

async def run(root):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend()
    settings=Settings(1,secrets.token_hex(32),root/'settings.json');settings.set_scope(1,2,3,'mention');settings.set(1,'enabled',True);settings.set(1,'model','base')
    class TimerTransport(Transport):
        def __init__(self):super().__init__();self.deliveries=0
        async def deliver_reminder(self,row,fresh):
            if not await fresh():raise ValueError('Stale synthetic timer')
            self.deliveries+=1;return 8000
    transport=TimerTransport();store=CompanionStore(root/'companion.sqlite3')
    runtime=Runtime(settings,Borrowed(backend),transport,None,None,ledger_path=root/'sent.sqlite3',companion=store)
    for p in Path('src').rglob('*.py'):
        target=root/'source'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    def event(number,text,user=4):return Event(number,2,3,user,text,datetime.now(timezone.utc))
    long='<@999> 1부터 40까지 숫자를 빠짐없이 쉼표로 구분해 적어 줘.'
    result=dict(real_gpu=True,real_discord=False)
    try:
        await backend.ready();await runtime.ingest(event(100,long));await asyncio.sleep(1)
        await runtime.ingest(event(101,'<@999> 6 더하기 7의 답만 알려 줘.',5))
        result['switch_while_gpu_busy']=backend.pending>0
        await runtime.switch_model(1,'persona');await settle(runtime,backend)
        result['switch_preserved_targets']={r['source'] for r in transport.sent}=={100,101}
        result['prepared_selection']=settings.get()['model']=='persona'
        original_prepare=backend.prepare_mode
        async def fail(mode):raise RuntimeError('Injected preparation failure')
        backend.prepare_mode=fail
        try:
            try:await runtime.switch_model(1,'adult')
            except RuntimeError:pass
        finally:backend.prepare_mode=original_prepare
        result['failed_switch_retained_selection']=settings.get()['model']=='persona'
        await runtime.ingest(event(102,'<@999> 9 곱하기 9의 답만 알려 줘.'));await settle(runtime,backend)
        result['gpu_replied_after_failed_switch']=any(r['source']==102 for r in transport.sent)
        await runtime.ingest(event(103,long.replace('40','45')))
        timer=store.reserve_reminder(event(104,'본인 합성 알림'),time.time()+1,'Asia/Seoul','합성 알림')
        await asyncio.sleep(1.1);result['timer_overlapped_gpu']=backend.pending>0
        started=time.perf_counter();await runtime.deliver_reminders();result['timer_dispatch_seconds']=time.perf_counter()-started
        await runtime.deliver_reminders();result['timer_single_delivery']=transport.deliveries==1
        result['timer_delivered_status']=next(r for r in store.reminders(2,4) if r['reminder_id']==timer['reminder_id'])['status']=='delivered'
        await settle(runtime,backend)
        atomic_private_json(root/'responses-private.json',dict(responses=transport.sent,traces=runtime.traces))
        atomic_private_json(root/'summary.json',result);print(str(result),flush=True)
    finally:
        try:await runtime.close();await backend.close()
        finally:lease.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    asyncio.run(run(private_path(parser.parse_args().output)))
