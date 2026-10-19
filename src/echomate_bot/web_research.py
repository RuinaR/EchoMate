"""Unauthenticated public encyclopedia/news discovery and grounded local answers."""
import asyncio
from datetime import datetime,timezone
import json
import re
import time
from urllib.parse import quote,urlsplit
from urllib.robotparser import RobotFileParser
import aiohttp
from .safe_web import SafeWeb,TextHTML,public_url

KINDS={'chat','opinion','context','knowledge','verify','current','premise','uncertain'}
PRIMARY_HOSTS={'docs.python.org','docs.discord.com','discordpy.readthedocs.io','learn.microsoft.com','www.nasa.gov','science.nasa.gov','www.esa.int','www.law.go.kr'}
def primary_url(url):
    p=urlsplit(url)
    return p.hostname in PRIMARY_HOSTS or bool(p.hostname and p.hostname.endswith(('.gov','.go.kr')))
def explicit_lookup(text):
    if re.search(r'검색\s*(?:없이|하지|말고)|찾지\s*마',text):return False
    return bool(re.search(r'출처|검색해|검색해\s*줘|찾아서|자료.*(?:찾|확인)|공식.*확인',text))
def private_query(query,blocked=()):
    if not isinstance(query,str) or not 2<=len(query)<=100:return True
    if not re.fullmatch(r'[가-힣A-Za-z0-9 .+_-]+',query):return True
    if re.search(r'https?://|<@|@|\d{7,}|hf_|sk-|비밀번호|토큰|전화번호|연락처|이메일|개인정보|본명|취향|주민|주소|내\s|우리\s*서버|디스코드\s*(?:대화|유저)|[\r\n{}<>]',query,re.I):return True
    return any(len(n)>=2 and n.casefold() in query.casefold() for n in blocked)

class WebResearch:
    def __init__(self,web=None,clock=time.monotonic):self.web=web or SafeWeb();self.clock=clock;self.cache={};self.lock=asyncio.Lock();self.robots={}
    async def _article(self,url):
        public_url(url);p=urlsplit(url);origin='https://'+p.netloc
        rule=self.robots.get(origin)
        if rule and self.clock()-rule[0]>3600:rule=None
        if not rule:
            parser=RobotFileParser();parser.parse((await self.web.get(origin+'/robots.txt')).splitlines());rule=(self.clock(),parser)
            if len(self.robots)>=64:self.robots.pop(next(iter(self.robots)))
            self.robots[origin]=rule
        if not rule[1].can_fetch('EchoMate',url):raise ValueError('Robots denied')
        parser=TextHTML();parser.feed(await self.web.get(url));return ' '.join(parser.parts)[:6000],parser.dates
    async def discover(self,query,fresh=False):
        if private_query(query):raise ValueError('Private query')
        key=(query,fresh)
        async with self.lock:
            cached=self.cache.get(key)
            if cached and self.clock()-cached[0]<300:return cached[1]
            sources=[]
            if not fresh:
                language='ko' if re.search('[가-힣]',query) else 'en';base=f'https://{language}.wikipedia.org/w/rest.php/v1'
                result=await self.web.get(base+'/search/page?q='+quote(query,safe='')+'&limit=3',as_json=True)
                if not isinstance(result,dict) or not isinstance(result.get('pages',[]),list):raise ValueError('Invalid discovery schema')
                for page in result.get('pages',[])[:2]:
                    if not isinstance(page,dict):continue
                    title=page.get('key')
                    if not isinstance(title,str) or len(title)>250:continue
                    try:
                        data=await self.web.get(base+'/page/'+quote(title,safe='')+'/with_html',as_json=True)
                        if not isinstance(data,dict) or not isinstance(data.get('html'),str):raise ValueError('Invalid article schema')
                        parser=TextHTML();parser.feed(data['html']);body=' '.join(parser.parts)[:6000]
                        url=public_url(f'https://{language}.wikipedia.org/wiki/'+quote(title,safe=''))
                        sources.append(dict(title=str(data.get('title',title))[:200],url=url,text=body,updated=data['latest'].get('timestamp') if isinstance(data.get('latest'),dict) else None,published=None,kind='encyclopedia_secondary'))
                        primary=next((u for u in parser.links if primary_url(u)),None)
                        if primary and not any(s['kind']=='official_primary' for s in sources):
                            try:
                                original,dates=await self._article(primary)
                                if len(original)>120:sources.insert(0,dict(title='공식 원문',url=primary,text=original,published=dates.get('article:published_time'),updated=dates.get('article:modified_time'),kind='official_primary'))
                            except (aiohttp.ClientError,asyncio.TimeoutError,OSError,ValueError):pass
                    except (aiohttp.ClientError,asyncio.TimeoutError,ValueError,KeyError,TypeError):continue
            else:
                endpoint='https://api.gdeltproject.org/api/v2/doc/doc?query='+quote(query,safe='')+'&mode=artlist&format=json&maxrecords=5&sort=datedesc&timespan=1week'
                result=await self.web.get(endpoint,as_json=True)
                if not isinstance(result,dict) or not isinstance(result.get('articles',[]),list):raise ValueError('Invalid news schema')
                for item in result.get('articles',[])[:3]:
                    try:
                        url=public_url(item['url']);body,dates=await self._article(url)
                        if len(body)<120:continue
                        sources.append(dict(title=str(item.get('title','공개 기사'))[:200],url=url,text=body,published=dates.get('article:published_time'),updated=dates.get('article:modified_time'),indexed=item.get('seendate'),kind='news_not_primary'))
                    except (aiohttp.ClientError,asyncio.TimeoutError,OSError,ValueError,KeyError,TypeError):continue
            for i,source in enumerate(sources):source.update(id=i+1,checked=datetime.now(timezone.utc).isoformat())
            if len(self.cache)>=32:self.cache.pop(next(iter(self.cache)))
            self.cache[key]=(self.clock(),sources);return sources

    async def answer(self,text,backend,*,blocked=()):
        try:
            try:plan=await backend.plan_research(text)
            except (ValueError,KeyError,TypeError,RuntimeError):
                from .research import needed
                if not explicit_lookup(text) and not needed(text):return None
                raise
            if plan['kind']=='knowledge' and explicit_lookup(text):plan=dict(plan,kind='verify')
            if plan['kind'] in ('chat','opinion','context','knowledge'):return None
            query=' '.join(plan['query'].replace(',',' ').split()) if isinstance(plan.get('query'),str) else ''
            if private_query(query,blocked):return dict(answer='개인정보가 섞일 가능성이 있어서 이 질문은 외부 검색으로 보내지 않을게.',urls=[],status='private_blocked')
            sources=await asyncio.wait_for(self.discover(query,plan['kind']=='current'),20)
            if not sources:return dict(answer='검색 원문을 확인할 수 있는 자료를 찾지 못했어. 질문의 전제나 사실을 확인했다고 말할 수 없어.',urls=[],status='no_sources')
            answer=await backend.grounded_answer(text,sources)
            # Source URLs are rendered by the application, never invented by AI.
            from .output_policy import contains_code
            citations=set(map(int,re.findall(r'\[(\d+)\]',answer)))
            if contains_code(answer) or re.search(r'https?://',answer) or not citations or not citations<={s['id'] for s in sources}:raise ValueError('Unsafe grounded answer')
            verdict=await backend.check_grounding(text,answer,sources)
            if verdict!='supported':return dict(answer='확인한 자료만으로는 질문의 전제와 답을 확정하기 어려워. 자료가 충돌하거나 근거가 부족해.',urls=[],status='insufficient')
            urls=[s['url'] for s in sources]
            suffix='\n확인 자료(위키는 2차 자료, 보도는 절대적 사실 보증이 아님):\n'+'\n'.join(f"[{s['id']}] {s['url']}" for s in sources)
            if len(suffix)>1400:return dict(answer='출처 URL이 너무 길어서 안전한 응답 길이 안에 근거를 표시하지 못했어. 설명을 검증해 보냈다고 말하지 않을게.',urls=[],status='render_limit')
            if len(answer)+len(suffix)>1850:answer='자료는 확인했지만 답을 잘라 보내지는 않을게. 먼저 확인한 자료를 남길게.'
            answer=answer+suffix
            return dict(answer=answer,urls=urls,status='grounded',source_count=len(sources))
        except asyncio.CancelledError:raise
        except (aiohttp.ClientError,asyncio.TimeoutError,OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:
            return dict(answer='인터넷 원문이나 근거 검증을 완료하지 못했어. 확인한 것처럼 답하지 않을게.',urls=[],status='failed',error_type=type(exc).__name__)
