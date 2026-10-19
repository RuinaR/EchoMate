"""Bounded public-source lookup. Raw Discord text is never an HTTP query.

Fixed public topics only; unsupported live facts fail explicitly rather than
pretending to be a general search engine. Clients are injectable for HTTP QA.
"""
import asyncio
import json
import re
import time
from urllib.parse import urlsplit
import aiohttp

TOPICS={
 'discord.py':('https://pypi.org/pypi/discord.py/json','pypi'),
 'transformers':('https://api.github.com/repos/huggingface/transformers/releases/latest','github'),
 '마인크래프트':('https://piston-meta.mojang.com/mc/game/version_manifest_v2.json','minecraft'),
 '리그 오브 레전드':('https://ddragon.leagueoflegends.com/api/versions.json','riot'),
 '파이썬':('https://api.github.com/repos/python/cpython/tags?per_page=30','python'),
}
ALIASES={'discord.py':('discord.py','디스코드 파이','디스코드파이'),'transformers':('transformers','트랜스포머스'),'마인크래프트':('마인크래프트','minecraft'),'리그 오브 레전드':('리그 오브 레전드','롤 패치','lol 패치'),'파이썬':('파이썬','python')}

def needed(text):return bool(re.search(r'최신|현재\s*버전|패치|업데이트|검색해|찾아\s*봐|출처|공식.*확인|오늘.*뉴스|가격|법률|규정',text,re.I))

class PublicResearch:
    def __init__(self,client_factory=None,clock=time.monotonic):
        self.factory=client_factory or (lambda:aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=7),trust_env=False,headers={'User-Agent':'EchoMate/1.0 public-source lookup','Accept':'application/json'}))
        self.clock=clock;self.cache={};self.locks={topic:asyncio.Lock() for topic in TOPICS}

    async def _read(self,client,url):
        # Exact application-generated endpoints; never follow user/result URLs.
        if url not in {v[0] for v in TOPICS.values()}:raise ValueError('Unapproved source')
        async with client.get(url,allow_redirects=False) as response:
            response.raise_for_status()
            if response.status!=200:raise ValueError('Redirect or invalid source status')
            chunks=[];size=0
            async for chunk in response.content.iter_chunked(65536):
                size+=len(chunk)
                if size>1048576:raise ValueError('Source too large')
                chunks.append(chunk)
            return json.loads(b''.join(chunks))

    async def lookup(self,text,enabled):
        if not needed(text):return None
        if not enabled:return dict(answer='지금은 인터넷 근거 조회가 꺼져 있어서 최신 정보나 출처를 확인할 수 없어. 확인한 것처럼 답하지 않을게.',urls=[],status='disabled')
        topic=next((k for k,words in ALIASES.items() if any(w in text.lower() for w in words)),None)
        if topic is None:return dict(answer='지금 지원하는 공식 정보 조회 주제에 해당하지 않아. 최신 사실이나 법률·가격을 확인할 근거가 없어서 확답할 수 없어.',urls=[],status='unsupported')
        async with self.locks[topic]:
            cached=self.cache.get(topic)
            if cached and self.clock()-cached[0]<(600 if cached[1]['status']=='verified' else 30):return dict(cached[1],cached=True)
            endpoint,kind=TOPICS[topic]
            try:
                async with self.factory() as client:data=await asyncio.wait_for(self._read(client,endpoint),7)
                if kind=='github':
                    version=data['tag_name'];url=data['html_url'];parsed=urlsplit(url)
                    repo=urlsplit(endpoint).path.split('/releases')[0].removeprefix('/repos')
                    if parsed.scheme!='https' or parsed.hostname!='github.com' or parsed.username or parsed.port not in (None,443) or not parsed.path.startswith(repo+'/releases/tag/'):raise ValueError('Invalid source URL')
                elif kind=='pypi':version=data['info']['version'];url=endpoint
                elif kind=='minecraft':version=data['latest']['release'];url=endpoint
                elif kind=='riot':version=data[0];url=endpoint
                else:
                    stable=[r['name'] for r in data if re.fullmatch(r'v\d+\.\d+\.\d+',r.get('name',''))]
                    version=max(stable,key=lambda v:tuple(map(int,v[1:].split('.'))));url=endpoint
                if not isinstance(version,str) or not re.fullmatch(r'[A-Za-z0-9._+-]{1,50}',version):raise ValueError('Invalid version')
                qualifier='공식 태그 목록에서 확인한 정식 형태의 태그' if kind=='python' else '공식 클라이언트 데이터 버전' if kind=='riot' else '공식 배포 정보의 버전'
                result=dict(answer=f'{topic}에서 확인한 {qualifier}: {version}. 태그·클라이언트 데이터는 실제 서비스 반영 시점과 다를 수 있어. 확인 자료(최대 10분 캐시): {url}',urls=[url],status='verified',cached=False)
                self.cache[topic]=(self.clock(),result);return result
            except (aiohttp.ClientError,asyncio.TimeoutError,ValueError,KeyError,IndexError,TypeError) as exc:
                result=dict(answer='공식 자료 조회에 실패해서 지금 정보를 확인할 수 없어. 버전이나 출처를 추측해서 말하지 않을게.',urls=[],status='failed',error_type=type(exc).__name__,http_status=getattr(exc,'status',None))
                self.cache[topic]=(self.clock(),result);return result
