"""RAM-only flow routing from actual message/reply/author evidence, never invented turns."""
from dataclasses import dataclass,field
import re
import secrets
import time

SUPPLEMENT=re.compile(r'^(?:아[, ]|아니[, ]|참[, ]|추가(?:\s|조건|설명|내용|문맥)|정정|조건|대신|이\s*내용도|그게|협동|멀티|정확히)|(?:으로|만|말고|포함해서|함께)\s*(?:해\s*줘|봐\s*줘|부탁해|[.!]?\s*$)')
INDEPENDENT=re.compile(r'그리고|별개|다른\s*질문|새\s*질문|그건\s*그렇고|또\s*하나')
CANCEL=re.compile(r'^(?:아[, ]*)?(?:그\s*)?(?:요청|질문|답변|생성)?\s*(?:취소해|취소|그만해|답하지\s*마)[.!? ]*$')
END=re.compile(r'^(?:고마워|고마워요|됐어|여기까지|나중에\s*봐|잘\s*자|대화\s*끝)[.!~ ]*$')

@dataclass
class Conversation:
    key:object
    guild:int
    channel:int
    parent:int|None
    conversation_id:str=field(default_factory=lambda:secrets.token_hex(12))
    participants:set=field(default_factory=set)
    messages:set=field(default_factory=set)
    last_at:float=field(default_factory=time.monotonic)
    ended:bool=False
    engaged:bool=False
    topic:str=''
    last_bot:str|None=None

class Conversations:
    def __init__(self):self.flows={};self.message_flow={}

    def choose(self,event,*,direct,pending,intent_text=None):
        place=(event.guild,event.channel)
        own=[f for f in self.flows.values() if (f.guild,f.channel)==place and event.author in f.participants and not f.ended]
        own.sort(key=lambda f:f.last_at,reverse=True)
        text=(event.content if intent_text is None else intent_text).strip()
        reply=self.message_flow.get((event.guild,event.channel,str(event.reply_to))) if event.reply_to else None
        flow=self.flows.get(reply)
        if flow:
            # Explicit reply is the only automatic way for a new speaker to join.
            flow.ended=False
            return flow,'cancel' if CANCEL.fullmatch(text) and event.author in flow.participants else 'reply'
        if CANCEL.fullmatch(text):
            active=[f for f in own if f.key in pending]
            return (active[0],'cancel') if len(active)==1 else (None,'ambiguous_cancel')
        if END.fullmatch(text) and own:return own[0],'end'
        if not own and not direct and re.search(r'그\s*이야기|나도|저도|우리도|같이',text):
            shared=[f for f in self.flows.values() if (f.guild,f.channel)==place and not f.ended and f.last_bot and f.key not in pending]
            if len(shared)==1:return shared[0],'group_candidate'  # still requires semantic addressee approval
        if own:
            latest=own[0]
            busy=latest.key in pending
            if not INDEPENDENT.search(text):
                if not busy:return latest,'continue'
                if SUPPLEMENT.search(text):return latest,'supplement'
            # Busy independent questions own their source and version; no overwrite.
        key=event.channel if not any(f.channel==event.channel for f in self.flows.values()) else (event.guild,event.channel,secrets.token_hex(8))
        flow=Conversation(key,event.guild,event.channel,event.parent);self.flows[key]=flow
        return flow,'independent' if own else 'new'

    def observe(self,flow,event):
        flow.participants.add(event.author);flow.messages.add(str(event.id));flow.last_at=time.monotonic()
        flow.topic=event.content[:160]  # private RAM only, never diagnostics
        self.message_flow[(event.guild,event.channel,str(event.id))]=flow.key
        if len(flow.messages)>200:
            # Rebuild reverse mappings from bounded actual state at runtime pruning.
            oldest=[k for k,v in self.message_flow.items() if v==flow.key]
            for k in oldest[:-200]:self.message_flow.pop(k,None);flow.messages.discard(k[2])

    def bot(self,flow,message):
        flow.last_bot=str(message);flow.messages.add(str(message))
        self.message_flow[(flow.guild,flow.channel,str(message))]=flow.key

    def drop(self,key):
        self.flows.pop(key,None)
        for msg,k in list(self.message_flow.items()):
            if k==key:self.message_flow.pop(msg,None)
