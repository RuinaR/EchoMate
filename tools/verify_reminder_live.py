"""Explicitly authorized one-owner reminder QA in an already allowed test scope.

Original signed settings are read-only. A QA copy enables only one preapproved
admin-guild text channel; only the bootstrap owner can trigger a reservation.
No slash sync, nickname edits, private corpus reads, or arbitrary test messages.
"""
import argparse
import asyncio
import json
import logging
from pathlib import Path
import time
from echomate_bot.settings import Settings,ROOT,private_path,scope,atomic_private_json
from echomate_bot.instance import InstanceLease
from echomate_bot.inference import LocalBackend
from echomate_bot.discord_app import EchoClient,DiscordTransport


async def run(root,confirm):
    if not confirm:raise ValueError('Explicit owner-ping confirmation required')
    root.mkdir(parents=True,exist_ok=False);lease=InstanceLease()
    bootstrap=json.loads((ROOT/'bootstrap.json').read_text(encoding='utf-8'))
    original=Settings(bootstrap['owner_id'],bootstrap['signing_key']);cfg=original.get()
    selected=None
    for gid in bootstrap['admin_guilds']:
        guild=cfg['guilds'].get(str(gid),{})
        if not guild.get('enabled'):continue
        for cid,rule in guild.get('channels',{}).items():
            if rule['mode'] in ('mention','autonomous'):
                selected=(int(gid),int(cid));break
        if selected:break
    if not selected:raise ValueError('No previously approved test text channel')
    gid,cid=selected;settings=Settings(bootstrap['owner_id'],bootstrap['signing_key'],root/'settings.json')
    def configure(data):
        data.update(cfg)
        data.update(enabled=True,text=True,reactions=False,stickers=False,vision=False,memory_auto=False,relations_auto=False,reminders_enabled=True)
        data['guilds']={str(gid):dict(enabled=True,channels={str(cid):dict(mode='mention',inherit=False,reaction_mode='silent')},threads={},
                                      **{key:value for key,value in cfg['guilds'][str(gid)].items() if key in ('name','aliases','partial_names','timezone')})}
    settings.change(bootstrap['owner_id'],configure)
    ready=asyncio.Event();result=dict(real_discord=True,received=0,acknowledged=0,delivered=0,disconnected=0,gpu_overlap=False)
    def save(phase):
        result['phase']=phase;atomic_private_json(root/'status.json',result)
        print(json.dumps(dict(phase=phase,received=result['received'],acknowledged=result['acknowledged'],delivered=result['delivered'])),flush=True)

    class WatchTransport(DiscordTransport):
        async def execute(self,event,action,library,fresh):
            message=await super().execute(event,action,library,fresh)
            if message:result['acknowledged']+=1;save('acknowledged')
            return message
        async def deliver_reminder(self,row,fresh):
            started=time.time();overlap=self.client.backend.pending>0
            message=await super().deliver_reminder(row,fresh)
            result.update(delivered=result['delivered']+1,gpu_overlap=overlap,
                delivery_late_seconds=time.time()-row['due_at'],api_seconds=time.time()-started)
            save('delivered');return message

    class QAClient(EchoClient):
        async def setup_hook(self):pass  # Do not change registered commands during QA.
        async def on_ready(self):self.runtime.start_services();ready.set();save('ready')
        async def on_disconnect(self):result['disconnected']+=1;await super().on_disconnect()
        async def on_message(self,message):
            if message.author.bot:return
            result['human_events']=result.get('human_events',0)+1
            if not message.guild or message.guild.id!=gid or message.channel.id!=cid or message.author.id!=bootstrap['owner_id']:
                result['out_of_test_scope']=result.get('out_of_test_scope',0)+1;save('ready');return
            result['owner_events']=result.get('owner_events',0)+1
            if result['received']:return
            # Require a real owner message, explicit bot mention and one-minute request.
            import re
            if not re.search(r'<@!?'+str(self.user.id)+r'>',message.content) or not re.search(r'(?:1|한)\s*분\s*(?:뒤|후)',message.content):
                result['request_format_mismatch']=result.get('request_format_mismatch',0)+1;save('ready');return
            result['received']+=1;save('received');await super().on_message(message)

    client=QAClient(settings,LocalBackend(),[gid]);client.runtime.transport=WatchTransport(client)
    gateway=None;gpu=None
    try:
        save('loading');await client.backend.ready()
        gateway=asyncio.create_task(client.start(bootstrap['token'],reconnect=True))
        await asyncio.wait_for(ready.wait(),60)
        deadline=time.monotonic()+300
        while time.monotonic()<deadline:
            if gateway.done():await gateway;raise RuntimeError('Gateway stopped')
            reservations=await asyncio.to_thread(client.companion.reminders,gid,bootstrap['owner_id'])
            row=reservations[0] if reservations else None
            if row and row['status']=='scheduled' and not gpu and time.time()>=row['due_at']-5:
                gpu=asyncio.create_task(client.backend._job([dict(role='user',content='1부터 200까지 숫자를 빠짐없이 쉼표로 구분해서 적어 줘.')],budget=512,weight='base'))
                save('gpu_overlap_probe')
            if row and row['status']=='delivered':break
            if row and row['status'] in ('cancelled','failed','expired'):raise RuntimeError('Reminder did not deliver')
            if (root/'STOP').exists():raise RuntimeError('QA stopped locally')
            await asyncio.sleep(.5)
        else:raise TimeoutError('Owner request/delivery timeout')
        result['source_settings_unchanged']=original.get()==Settings(bootstrap['owner_id'],bootstrap['signing_key']).get()
        atomic_private_json(root/'summary.json',result);save('complete')
    except Exception as exc:
        result['error_type']=type(exc).__name__;save('failed');raise
    finally:
        if gpu:
            if not gpu.done():gpu.cancel()
            await asyncio.gather(gpu,return_exceptions=True)
        try:
            # This QA store is never reused to replay an unfinished test later.
            await asyncio.to_thread(client.companion.clear_records,gid,'reminders')
            await client.close()
            if gateway:await asyncio.gather(gateway,return_exceptions=True)
        finally:lease.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--confirm-owner-ping',action='store_true')
    args=parser.parse_args();logging.getLogger('discord').setLevel(logging.CRITICAL)
    asyncio.run(run(private_path(args.output),args.confirm_owner_ping))
