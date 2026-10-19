"""Evaluation-only single-slot llama.cpp client. No private LoRA or Discord API.

Caller holds InstanceLease and must close the Transformers backend first.
Loopback authenticated HTTP, one request at a time, disconnect cancellation.
"""
import asyncio
import json
import os
import secrets
import socket
import subprocess
import time
from pathlib import Path
import aiohttp
from echomate_bot.processes import background_options
from echomate_bot.settings import private_path


class GGUFProbe:
    def __init__(self,engine,model,root):
        self.engine=private_path(engine);self.model=private_path(model);self.root=private_path(root)
        self.process=None;self.log=None;self.session=None;self.lock=asyncio.Lock()

    async def start(self):
        self.root.mkdir(parents=True,exist_ok=True)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        key=secrets.token_urlsafe(32)
        self.url=f'http://127.0.0.1:{port}'
        self.log=(self.root/'engine.log').open('wb')
        env=dict(os.environ,LLAMA_API_KEY=key)
        args=[str(self.engine),'-m',str(self.model),'--host','127.0.0.1','--port',str(port),
              '-ngl','99','-lm','none','--no-host','-c','2048','-b','128','-ub','64','-fa','on','-np','1','--jinja','--reasoning','off',
              '--chat-template-kwargs','{"enable_thinking":false}','--no-webui','--no-cache-prompt']
        self.process=subprocess.Popen(args,stdout=self.log,stderr=self.log,env=env,**background_options())
        self.session=aiohttp.ClientSession(trust_env=False,connector=aiohttp.TCPConnector(force_close=True),
            headers={'Authorization':'Bearer '+key,'Connection':'close'},
            timeout=aiohttp.ClientTimeout(total=150))
        deadline=time.monotonic()+150
        try:
            while time.monotonic()<deadline:
                if self.process.poll() is not None:raise RuntimeError('GGUF server exited during load')
                try:
                    async with self.session.get(self.url+'/health',timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status==200:
                            async with self.session.get(self.url+'/props') as props:
                                data=await props.json()
                                (self.root/'properties.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
                            return
                except (aiohttp.ClientError,asyncio.TimeoutError):pass
                await asyncio.sleep(.5)
            raise TimeoutError('GGUF startup timeout')
        except BaseException:
            await self.close();raise

    async def generate(self,messages,budget):
        queued=time.perf_counter()
        async with self.lock:
            entered=time.perf_counter();first=None;parts=[];usage={};finish=None
            body=dict(messages=messages,temperature=0,top_p=1,top_k=0,min_p=0,repeat_penalty=1,
                      seed=2026,max_tokens=budget,stream=True,stream_options={'include_usage':True},
                      chat_template_kwargs={'enable_thinking':False})
            async with self.session.post(self.url+'/v1/chat/completions',json=body) as response:
                response.raise_for_status()
                async for line in response.content:
                    if not line.startswith(b'data: '):continue
                    payload=line[6:].strip()
                    if payload==b'[DONE]':continue
                    item=json.loads(payload)
                    if item.get('usage'):usage=item['usage']
                    for choice in item.get('choices',[]):
                        piece=choice.get('delta',{}).get('content') or ''
                        if piece and first is None:first=time.perf_counter()
                        parts.append(piece)
                        if choice.get('finish_reason'):finish=choice['finish_reason']
            seconds=time.perf_counter()-entered
            return ''.join(parts),dict(seconds=seconds,ttft_seconds=first-entered if first else None,
                queue_seconds=entered-queued,input_tokens=usage.get('prompt_tokens'),
                output_tokens=usage.get('completion_tokens'),ended=finish=='stop',finish_reason=finish,
                tokens_per_second=usage.get('completion_tokens',0)/max(seconds,1e-6))

    async def close(self):
        if self.session:
            await self.session.close();self.session=None
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                try:await asyncio.wait_for(asyncio.to_thread(self.process.wait),15)
                except asyncio.TimeoutError:
                    self.process.kill();await asyncio.to_thread(self.process.wait)
            self.process=None
        if self.log:self.log.close();self.log=None
