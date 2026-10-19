"""Public HTTPS only, DNS checked at connection time, bounded reads, no browser."""
import asyncio
import ipaddress
import json
from html.parser import HTMLParser
from urllib.parse import urlsplit
import aiohttp

def public_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443) or len(url)>2048:raise ValueError('Unsafe URL')
    host=p.hostname.lower()
    try:ipaddress.ip_address(host)
    except ValueError:
        if '.' not in host or host.endswith(('.local','.localhost','.internal')):raise ValueError('Unsafe host')
    else:raise ValueError('IP URLs forbidden')
    return url

class PublicResolver(aiohttp.abc.AbstractResolver):
    def __init__(self):self.resolver=aiohttp.resolver.DefaultResolver()
    async def resolve(self,host,port=0,family=0):
        rows=await self.resolver.resolve(host,port,family)
        if not rows or any(not ipaddress.ip_address(r['host']).is_global for r in rows):raise OSError('Nonpublic DNS result')
        return rows
    async def close(self):await self.resolver.close()

class TextHTML(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0;self.dates={};self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript','svg'):self.skip+=1
        a=dict(attrs)
        if tag=='a' and len(self.links)<200 and isinstance(a.get('href'),str) and a['href'].startswith('https://'):self.links.append(a['href'])
        if tag=='meta' and a.get('property') in ('article:published_time','article:modified_time'):self.dates[a['property']]=a.get('content','')[:64]
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript','svg'):self.skip=max(0,self.skip-1)
    def handle_data(self,text):
        if not self.skip and text.strip():self.parts.append(text.strip())

class SafeWeb:
    def __init__(self,session_factory=None):self.factory=session_factory
    async def get(self,url,*,as_json=False):
        public_url(url)
        resolver=None if self.factory else PublicResolver()
        connector=None if self.factory else aiohttp.TCPConnector(resolver=resolver,limit=3)
        factory=self.factory or (lambda:aiohttp.ClientSession(connector=connector,trust_env=False,timeout=aiohttp.ClientTimeout(total=8),headers={'User-Agent':'EchoMate/1.0 (https://github.com/RuinaR/EchoMate; public evidence lookup)'}))
        try:
            async with factory() as session:
                async with session.get(url,allow_redirects=False) as response:
                    response.raise_for_status()
                    if response.status!=200:raise ValueError('Redirect or unavailable source')
                    chunks=[];length=0
                    async for chunk in response.content.iter_chunked(32768):
                        length+=len(chunk)
                        if length>1048576:raise ValueError('Oversized evidence')
                        chunks.append(chunk)
                    raw=b''.join(chunks).decode('utf8',errors='replace')
                    return json.loads(raw) if as_json else raw
        finally:
            if connector is not None:await connector.close()
            if resolver is not None:await resolver.close()
