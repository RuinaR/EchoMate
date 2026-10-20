"""Bounded, transient source-preserving assembly; never grants response eligibility.

Only an unfinished clause/bare invitation opens a buffer. Time closes that
buffer, but is never evidence of audience or conversation membership.
"""
import asyncio
from dataclasses import dataclass, field, replace
import hashlib
import re
import secrets
import time


def unfinished(text, *, bare=False,direct=False):
    # Syntactic tails are assembly hints, not question/audience classification.
    text=text.strip()
    if bare:return True
    if not text or text[-1:] in '.?!。？！':return False
    if direct and re.search(r'(?:^|\s)(?:이|그|저)\s+[가-힣A-Za-z0-9]+$',text):return True
    return bool(re.search(r'(?:[,，]|(?:해서|하면|되면|인데|지만|거든|다가|면서|어서|아서|는데|은데|려고|려면|고|으로|로|부터|까지|걸로|말고|않게)|(?:일단은|아\s*근데))$',text)
        or re.search(r'\S+(?:이|가|을|를|도|은|는)\s*$',text) and len(text)<100)


@dataclass
class Pending:
    parts:list
    started:float
    uid:str=field(default_factory=lambda:'utt:'+secrets.token_hex(12))
    task:object=None
    bare:bool=False


class Utterances:
    def __init__(self,emit,note,*,idle=.8,maximum=4.,budget=8000,capacity=64):
        self.emit=emit;self.note=note;self.idle=idle;self.maximum=maximum
        self.budget=budget;self.capacity=capacity;self.pending={};self.closed=False
        self.emitting=set();self.changes={}

    @staticmethod
    def key(event):return event.guild,event.channel,event.parent,event.author

    @staticmethod
    def compose(parts,uid):
        root,last=parts[0],parts[-1]
        return replace(last,content='\n'.join(p.content for p in parts),raw_parts=tuple(parts),
            utterance_id=uid,utterance_version=len(parts),response_to=(root.response_to or root.id) if len(parts)>1 else root.response_to,
            reply_to=root.reply_to,reply_author=root.reply_author,received_at=root.received_at,
            target_content_hash=hashlib.sha256(root.content.encode()).hexdigest(),
            source_content_hash=hashlib.sha256(last.content.encode()).hexdigest())

    def take(self,key):
        row=self.pending.pop(key)
        if row.task and row.task is not asyncio.current_task():row.task.cancel()
        self.note('utterance_combined' if len(row.parts)>1 else 'utterance_finalized')
        return self.compose(row.parts,row.uid)

    async def later(self,key,row):
        try:
            await asyncio.sleep(max(0,min(self.idle,self.maximum-(time.monotonic()-row.started))))
            if self.pending.get(key) is row and not self.closed:
                event=self.take(key)
                # Keep ownership through permission checks, invalidation and shutdown.
                self.emitting.add(asyncio.current_task())
                try:await self.emit(event)
                finally:self.emitting.discard(asyncio.current_task())
        except asyncio.CancelledError:raise

    def offer(self,event,*,bare=False,direct=False,human=False):
        key=self.key(event);row=self.pending.get(key);ready=[]
        if row and any(p.id==event.id for p in row.parts):return []
        # Reply / explicit audience changes and independent requests are real
        # boundaries. A repeated bare call is not a new independent question.
        from .sessions import INDEPENDENT,SUPPLEMENT
        boundary=bool(row and (human or event.reply_to not in (None,row.parts[0].reply_to,row.parts[0].id)
            or direct and not bare and not row.bare and not SUPPLEMENT.search(event.content)
            or INDEPENDENT.search(event.content)
            or sum(len(p.content)+128 for p in row.parts)+len(event.content)+128>self.budget
            or time.monotonic()-row.started>=self.maximum))
        if boundary:ready.append(self.take(key));row=None;self.note('utterance_separated')
        if row:
            row.parts.append(event);row.bare=row.bare and bare
            if row.task:row.task.cancel()
            if not unfinished(event.content,bare=bare,direct=direct):ready.append(self.take(key))
            else:row.task=asyncio.create_task(self.later(key,row),name='echomate-fragment-wait')
        elif not human and unfinished(event.content,bare=bare,direct=direct) and len(event.content)<=self.budget and len(self.pending)<self.capacity:
            row=Pending([event],time.monotonic(),bare=bare);self.pending[key]=row
            row.task=asyncio.create_task(self.later(key,row),name='echomate-fragment-wait');self.note('utterance_waiting')
        else:ready.append(self.compose([event],'utt:'+secrets.token_hex(12)))
        return ready

    def changed(self,guild,channel,message):
        now=time.monotonic();self.changes[(guild,channel,message)]=now
        self.changes={k:v for k,v in self.changes.items() if now-v<180}
        # Exhaustion fails closed for old work instead of evicting tombstones.
        if len(self.changes)>5000:self.closed=True
        self.discard(lambda p:(p.guild,p.channel,p.id)==(guild,channel,message))

    def valid(self,event):
        return not self.closed and all(self.changes.get((p.guild,p.channel,p.id),0)<p.received_at for p in event.raw_parts)

    def discard(self,predicate):
        for key,row in list(self.pending.items()):
            if any(predicate(p) for p in row.parts):
                self.pending.pop(key);row.task.cancel();self.note('utterance_invalidated')

    async def close(self):
        self.closed=True
        tasks=[r.task for r in self.pending.values()]+list(self.emitting)
        self.pending.clear()
        for task in tasks:task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
