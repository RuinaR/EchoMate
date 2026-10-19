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
    candidate_key:object=None
    direct_peers:set=field(default_factory=set)
    last_recipient:int|None=None
    link_evidence:str='unconfirmed'
    addressee:str='uncertain'
    status:str='candidate'
    candidate_keys:tuple=()
    last_action:str|None=None

class Conversations:
    def __init__(self):self.flows={};self.message_flow={}

    def choose(self,event,*,direct,pending,intent_text=None,semantic=False,bot_reply=False):
        if semantic:return self.choose_social(event,direct=direct,pending=pending,intent_text=intent_text,bot_reply=bot_reply)
        place=(event.guild,event.channel)
        own=[f for f in self.flows.values() if (f.guild,f.channel)==place and event.author in f.participants and not f.ended]
        text=(event.content if intent_text is None else intent_text).strip()
        reply=self.message_flow.get((event.guild,event.channel,str(event.reply_to))) if event.reply_to else None
        flow=self.flows.get(reply)
        if flow:
            # Actual reply proves a shared flow; Runtime separately handles verified bare calls.
            flow.ended=False
            return flow,'cancel' if CANCEL.fullmatch(text) and event.author in flow.participants else 'reply'
        if CANCEL.fullmatch(text):
            active=[f for f in own if f.key in pending]
            return (active[0],'cancel') if len(active)==1 else (None,'ambiguous_cancel')
        if END.fullmatch(text) and own:return own[0],'end'
        candidate=None
        if not own and not direct:
            shared=[f for f in self.flows.values() if (f.guild,f.channel)==place and not f.ended and f.engaged and f.last_bot and f.key not in pending]
            unique={f.conversation_id:f for f in shared}
            if len(unique)==1:candidate=next(iter(unique.values()))  # evidence candidate, not automatic membership
        if own:
            latest=own[0]
            busy=latest.key in pending
            if not INDEPENDENT.search(text):
                if not busy:return latest,'continue'
                if SUPPLEMENT.search(text):return latest,'supplement'
            # Busy independent questions own their source and version; no overwrite.
        key=event.channel if not any(f.channel==event.channel for f in self.flows.values()) else (event.guild,event.channel,secrets.token_hex(8))
        flow=Conversation(key,event.guild,event.channel,event.parent,candidate_key=candidate.key if candidate else None);self.flows[key]=flow
        return flow,'independent' if own else 'group_candidate' if candidate else 'new'

    def choose_social(self,event,*,direct,pending,intent_text=None,bot_reply=False):
        text=(event.content if intent_text is None else intent_text).strip()
        own=[f for f in self.flows.values() if (f.guild,f.channel)==(event.guild,event.channel) and event.author in f.direct_peers and not f.ended]
        reply=self.flows.get(self.message_flow.get((event.guild,event.channel,str(event.reply_to)))) if event.reply_to else None
        if reply and bot_reply:return reply,'reply'
        busy=[f for f in own if f.key in pending]
        if CANCEL.fullmatch(text):return (busy[0],'cancel') if len(busy)==1 else (None,'ambiguous_cancel')
        if END.fullmatch(text) and len(own)==1:return own[0],'end'
        if len(busy)==1 and SUPPLEMENT.search(text) and not INDEPENDENT.search(text):return busy[0],'supplement'
        # A bare attention call can retain its confirmed counterpart. A call
        # with content still needs relation evidence: one own flow does not
        # prove that a new topic belongs to it. Runtime may link the candidate
        # after semantic validation without ever suppressing the direct call.
        if direct and len(own)==1 and not busy and not text:return own[0],'continue'
        key=event.channel if not any(f.channel==event.channel for f in self.flows.values()) else (event.guild,event.channel,secrets.token_hex(8))
        flow=Conversation(key,event.guild,event.channel,event.parent,candidate_keys=tuple(f.key for f in own))
        if len(own)==1:flow.candidate_key=own[0].key
        self.flows[key]=flow
        return flow,'social_candidate'

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
