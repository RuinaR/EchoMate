"""Actual GPU + synthetic Discord events; never connects or sends to Discord."""
import argparse
import asyncio
from dataclasses import replace
from datetime import datetime,timezone
import hashlib
import json
import random
from pathlib import Path
import secrets
from echomate_bot.runtime import Runtime,Event
from echomate_bot.inference import LocalBackend
from echomate_bot.settings import Settings,private_path,atomic_private_json
from echomate_bot.instance import InstanceLease


class Transport:
    bot_id=999
    def __init__(self):self.sent=[];self.allowed=True
    async def permissions(self,event):return dict(view=self.allowed,send=self.allowed,react=False,attach=False,age_restricted=True)
    async def catalog(self,event,cache):return dict(reactions={},stickers={})
    async def execute(self,event,action,library,fresh):
        if not await fresh():raise ValueError('Stale synthetic event')
        self.sent.append(dict(event=event.id,response_to=event.response_to or event.id,text=action.text))
        return 9000+len(self.sent)


async def run(root):
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease();backend=LocalBackend()
    settings=Settings(1,secrets.token_hex(32),root/'settings.json');transport=Transport()
    settings.set(1,'enabled',True);settings.set(1,'activity','quiet')
    runtime=Runtime(settings,backend,transport,None,None,ledger_path=root/'ledger.sqlite3',rng=random.Random(2026))
    results=[];restore_checks=[];counter=1000
    atomic_private_json(root/'manifest.json',dict(synthetic=True,real_discord=False,seed=2026,
        source={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/echomate_bot').glob('*.py')},
        simulated_ledger_elapsed_seconds=[3,700],models=['base','persona','adult'],
        preparation_failure_injected=True,age_restricted_channel_simulated=True))
    async def send(model,label,text,channel,*,author=4,reply_to=None,parent=None,cancel=None,gap_seconds=3):
        nonlocal counter
        counter+=1;before=len(transport.sent)
        with runtime.ledger.db() as db:db.execute('UPDATE sent SET at=at-?',(gap_seconds,))
        event=Event(counter,2,channel,author,text,datetime.now(timezone.utc),reply_to=reply_to,parent=parent)
        await runtime.ingest(event)
        if cancel:
            for _ in range(500):
                if backend.pending or not runtime.tasks:break
                await asyncio.sleep(.01)
            if cancel=='delete':runtime.invalidate(channel)
            elif cancel=='permission':transport.allowed=False
            elif cancel=='model':await runtime.switch_model(1,'base' if model!='base' else 'persona')
            elif cancel=='new_message':
                counter+=1
                follow=replace(event,id=counter,content='추가 문맥이야. 장소는 달빛 공원으로 바꿨어. 바뀐 장소만 한 문장으로 알려 줘.',timestamp=datetime.now(timezone.utc))
                await runtime.ingest(follow)
        await asyncio.gather(*list(runtime.tasks.values()),return_exceptions=True)
        results.append(dict(model=model,scenario=label,outputs=len(transport.sent)-before,
            records=transport.sent[before:],last_trace=runtime.traces[-1] if runtime.traces else None))
        atomic_private_json(root/'results.json',results)
        print(json.dumps(dict(model=model,scenario=label,outputs=len(transport.sent)-before)),flush=True)
        transport.allowed=True
    try:
        await backend.ready()
        import torch
        torch.manual_seed(2026)
        for index,model in enumerate(('base','persona','adult')):
            channel=30+index;settings.set_scope(1,2,channel,'mention',inherit=True)
            await runtime.switch_model(1,model)
            await send(model,'mention','<@999> 합성 모임 장소는 별빛 도서관이고 시간은 16시야. 한 문장으로 확인해 줘.',channel)
            await send(model,'implicit_followup_after_simulated_pause','장소가 어디였지? 짧게 다시 알려 줘.',channel,gap_seconds=700)
            await send(model,'speaker_change','나도 모임에 갈게. 몇 시에 가면 돼?',channel,author=5)
            last=9000+len(transport.sent) if transport.sent else None
            await send(model,'reply_new_topic','다른 질문인데, 8 더하기 9는 얼마야?',channel,author=6,reply_to=last)
            await send(model,'implicit_new_topic','이번에도 너에게 물어보는 건데, 9에서 4를 빼면 얼마야?',channel,author=5)
            await send(model,'other_people_sidechat','이건 봇 말고 B한테 묻는 거야. B는 언제 갈 거야?',channel)
            await send(model,'ending','고마워. 여기까지면 충분해. 이제 다른 친구랑 이야기할게.',channel)
            await send(model,'short_ack','응.',channel)
            await send(model,'restart_after_end','<@999> 새 모임은 달빛 공원에서 18시야. 짧게 확인해 줘.',channel)
            await send(model,'thread_isolation','<@999> 여긴 별도 스레드야. 한 문장으로 인사해 줘.',channel+100,parent=channel)
            await send(model,'new_message_during_generation','<@999> 모임 계획을 설명해 줘.',channel,cancel='new_message')
            await send(model,'model_change_during_generation','<@999> 짧은 여행 계획을 알려 줘.',channel,cancel='model')
            await runtime.switch_model(1,model)
            previous_identity=id(backend.model);prepare=backend.prepare_mode
            async def fail_prepare(mode):raise FileNotFoundError('Synthetic preparation failure; no model file changed')
            backend.prepare_mode=fail_prepare
            try:
                try:await runtime.switch_model(1,'base' if model!='base' else 'adult')
                except FileNotFoundError:pass
                restore_checks.append(dict(mode=model,selection_preserved=settings.get()['model']==model,
                    resident_object_preserved=id(backend.model)==previous_identity))
                atomic_private_json(root/'model-restore-checks.json',restore_checks)
            finally:backend.prepare_mode=prepare
            await send(model,'response_after_injected_prepare_failure','<@999> 준비 실패 뒤에도 정상이라면 한 문장으로 인사해 줘.',channel)
            await send(model,'delete_during_generation','<@999> 인사해 줘.',channel+100,parent=channel,cancel='delete')
            await send(model,'permission_revoked','<@999> 한 문장으로 인사해 줘.',channel,cancel='permission')
        atomic_private_json(root/'summary.json',dict(real_gpu=True,real_discord=False,scenarios=len(results),
            outcomes=[{k:r[k] for k in ('model','scenario','outputs')} for r in results],
            caution='Outputs count is not a quality or semantic-correctness judgment'))
    finally:
        try:await runtime.close()
        finally:lease.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    asyncio.run(run(private_path(p.parse_args().output)))
