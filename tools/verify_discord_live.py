"""Bounded, explicitly authorized test-server session. Secrets stay in bootstrap."""
import argparse
import asyncio
import json
import logging
from pathlib import Path
import time
from echomate_bot.settings import ROOT,Settings,private_path
from echomate_bot.inference import LocalBackend
from echomate_bot.discord_app import EchoClient


async def run(output,duration):
    output.mkdir(parents=True,exist_ok=False)
    bootstrap=json.loads((ROOT/'bootstrap.json').read_text(encoding='utf-8'))
    settings=Settings(bootstrap['owner_id'],bootstrap['signing_key'])
    backend=LocalBackend();client=EchoClient(settings,backend,bootstrap['admin_guilds'])
    logging.getLogger('discord').setLevel(logging.CRITICAL)
    summary=dict(status='loading',real_discord=True,authorized_scope='bootstrap test guilds and signed allowlist',
                 ready_events=0,messages_sent=0,actions=[],owner_checks_allowed=0,owner_checks_denied=0,
                 received_allowed_events=0,started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    def save():
        tmp=output/'status.tmp';tmp.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(output/'status.json')
    save()
    ready=client.on_ready
    async def on_ready():
        await ready();summary['status']='connected';summary['ready_events']+=1
        summary['registered_test_guilds_present']=sum(client.get_guild(g) is not None for g in bootstrap['admin_guilds']);save()
    client.on_ready=on_ready
    check=client.owner_check
    async def owner_check(interaction):
        allowed=await check(interaction)
        summary['owner_checks_allowed' if allowed else 'owner_checks_denied']+=1;save();return allowed
    client.owner_check=owner_check
    execute=client.runtime.transport.execute
    async def execute_counted(event,action,library,fresh):
        if event.guild not in bootstrap['admin_guilds']:raise PermissionError('Outside live QA scope')
        result=await execute(event,action,library,fresh)
        summary['actions'].append(action.kind.value)
        if result:summary['messages_sent']+=1
        save();return result
    client.runtime.transport.execute=execute_counted
    message=client.on_message
    async def on_message(event):
        if event.guild and event.guild.id in bootstrap['admin_guilds'] and not event.author.bot:
            summary['received_allowed_events']+=1;save()
        await message(event)
    client.on_message=on_message
    start=None
    try:
        await backend.ready();summary['status']='connecting';save()
        start=asyncio.create_task(client.start(bootstrap['token'],reconnect=True))
        deadline=time.monotonic()+duration
        while time.monotonic()<deadline:
            await asyncio.sleep(2)
            if start.done():await start;break
            summary['diagnostics']=client.runtime.diagnostics
            summary['metrics']=backend.metrics
            save()
        summary['status']='finished';save()
    except Exception as exc:
        summary['status']='failed';summary['error_type']=type(exc).__name__;save()
        print('Live test stopped:',type(exc).__name__,flush=True)
    finally:
        await client.close()
        if start:
            start.cancel();await asyncio.gather(start,return_exceptions=True)
        summary['metrics']=backend.metrics;summary['diagnostics']=client.runtime.diagnostics
        save()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--seconds',type=int,default=600)
    args=parser.parse_args()
    if not 30<=args.seconds<=1800:raise SystemExit('Test session must be bounded to 30..1800 seconds')
    asyncio.run(run(private_path(args.output),args.seconds))
