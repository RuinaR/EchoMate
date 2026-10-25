"""Bounded member evidence, separate from the bot's invitation/name policy.

Names are untrusted display metadata. Only observed channel members are exposed;
candidate IDs never select memory, affinity, reminder targets or API recipients.
"""
from dataclasses import dataclass
import re
import time
from .naming import address_forms,name_address
from .routing import prose

@dataclass(frozen=True)
class PersonCandidate:
    user:int
    form:str
    confidence:float
    evidence:str
    direct:bool=False
    role:str='uncertain'

@dataclass(frozen=True)
class MemberRoles:
    speaker:int
    addressee:int|None=None
    mentioned_people:tuple=()
    reply_target:int|None=None
    reply_author:int|None=None
    candidates:tuple=()
    ambiguous:bool=False
    bot_collision:bool=False

    def facts(self):
        return dict(speaker=str(self.speaker),addressee=str(self.addressee) if self.addressee else None,
                    mentioned_people=list(map(str,self.mentioned_people)),reply_target=str(self.reply_target) if self.reply_target else None,
                    reply_author=str(self.reply_author) if self.reply_author else None,
                    candidates=[dict(user=str(c.user),form=c.form,confidence=c.confidence,evidence=c.evidence,role=c.role) for c in self.candidates[:12]],
                    ambiguous=self.ambiguous,bot_collision=self.bot_collision,identity_actions_allowed=False)

class MemberDirectory:
    def __init__(self,clock=time.monotonic,limit=1000):
        self.clock=clock;self.limit=limit;self.people={};self.alias_cache={};self.lookup_after={}

    def prune(self):
        now=self.clock()
        for k,(_,at) in list(self.people.items()):
            if now-at>86400:self.people.pop(k,None)
        while len(self.people)>self.limit:self.people.pop(next(iter(self.people)))
        while len(self.alias_cache)>128:self.alias_cache.pop(next(iter(self.alias_cache)))
        for key,at in list(self.lookup_after.items()):
            if now>=at:self.lookup_after.pop(key,None)
        while len(self.lookup_after)>self.limit:self.lookup_after.pop(next(iter(self.lookup_after)))

    def observe(self,guild,channel,user,names):
        names=tuple(dict.fromkeys(n[:80] for n in names if isinstance(n,str) and 1<len(n)<=80))[:3]
        if not names:return
        # A fresh nickname replaces old metadata for this person, but grants no
        # access to names/aliases learned in another channel.
        for k in list(self.people):
            if k[0]==guild and k[2]==user:self.people[k]=(names,self.people[k][1])
        key=(guild,channel,user);self.people.pop(key,None);self.people[key]=(names,self.clock());self.prune()

    def clear(self,guild,user=None,channel=None):
        for key in list(self.people):
            if key[0]==guild and (user is None or key[2]==user) and (channel is None or key[1]==channel):self.people.pop(key,None)
        self.alias_cache.clear()
        for key in list(self.lookup_after):
            if key[0]==guild and (user is None or key[2]==user) and (channel is None or key[1]==channel):self.lookup_after.pop(key,None)

    def names(self,guild,channel,exclude=None):
        self.prune()
        return [n for (g,ch,u),(names,_) in self.people.items() if (g,ch)==(guild,channel) and u!=exclude for n in names]

    def resolve(self,event,bot_id,aliases=(),bot_names=()):
        self.prune();clean=prose(event.content).strip();folded=clean.casefold();candidates=[];seen=set()
        head=re.match(r'^([가-힣A-Za-z]{3,16}?)[아야](?=$|[\s,!?.])',clean)
        rows=[(u,names) for (g,ch,u),(names,_) in self.people.items() if (g,ch)==(event.guild,event.channel) and u!=bot_id]
        by_user={}
        for a in aliases:by_user.setdefault(int(a['user']),[]).append(a)
        for uid,names in rows:
            forms={n.casefold():('nickname',.95) for n in names}
            for n in names:
                for form in address_forms(n):forms.setdefault(form.casefold(),('derived',.75))
                # A Korean family-name omission is a candidate, never an ID key.
                if re.fullmatch(r'[김이박최정강조윤장임한신서권황안송전홍유고문양손배백허남심노하곽성차주우구민나진지엄채원천방공현함변염여][가-힣]{2}',n):forms.setdefault(n[1:],('partial',.65))
            for a in by_user.get(uid,()):
                if a['status']=='confirmed':forms[a['alias']]=('owner',a['confidence'])
                elif a['status']=='candidate':forms.setdefault(a['alias'],('observed',a['confidence']))
            for form,(kind,score) in forms.items():
                if form not in folded:continue
                match=re.search(r'(?<![가-힣A-Za-z0-9_])'+re.escape(form)+r'(?P<suffix>아|야|님|이|은|는|가|을|를|에게|한테)?(?=$|[\s,!.?~…:]|(?<=[아야])[가-힣])',clean,re.I)
                if not match:continue
                vocative=match['suffix'] in ('아','야','님') and (match.start()==0 or not clean[match.end():].strip(' ,!.?~…:'))
                # Korean vocatives delimit a known name even without a space.
                # A bare name needs independent second-person syntax; a noun or
                # third-person report alone never establishes an addressee.
                tail=clean[match.end():].lstrip(' ,!.?~…:')
                second_person=match.start()==0 and match['suffix'] is None and bool(re.match(r'(?:너(?:는|도|가|의)?|네가|당신(?:은|도|이)?)\s',tail))
                reported=bool(re.search(r'(?:냐고|라고|다고|자고)\s*(?:물|말|전|했|하더|부르)',tail))
                direct=bool((vocative or second_person or kind=='owner' and name_address(clean,form,partial=False)=='direct') and not reported)
                signature=(uid,form)
                if signature not in seen:
                    role='address' if direct else 'reference' if match['suffix'] in ('이','은','는','가','을','를','에게','한테') or match.start()>0 else 'uncertain'
                    candidates.append(PersonCandidate(uid,form,score,kind,direct,role));seen.add(signature)
            # Limited edit candidate: >=3 letters, one edit, vocative prefix only.
            if head and not any(c.user==uid for c in candidates):
                word=head[1].casefold()
                for form in forms:
                    if len(form)>=3 and one_edit(word,form):candidates.append(PersonCandidate(uid,word,.4,'typo',False));break
        actual=tuple(dict.fromkeys(u for u in event.member_mentions if u!=event.author))
        targets={c.user for c in candidates if c.direct and c.evidence!='typo'}
        # An unconfirmed learned label is evidence only, even after many witnesses.
        targets={u for u in targets if any(c.user==u and c.direct and c.evidence not in ('observed','typo') for c in candidates)}
        # All identities matching the same address participate in collision checks.
        direct_forms={c.form for c in candidates if c.direct}
        collision=any(len({c.user for c in candidates if c.form==form})>1 for form in direct_forms)
        bot_forms={f.casefold() for n in bot_names for f in address_forms(n)}
        bot_collision=bool(direct_forms & bot_forms);collision=collision or bot_collision
        addressee=None
        # A mention in a report/subject is not automatically its addressee.
        # A leading ID call or a matching vocative supplies address evidence;
        # otherwise the actual reply remains independent from mentioned people.
        # '>' already delimits an actual Discord mention ID. Korean/English
        # calls need no following space. A separate subject/object particle
        # still marks a reference, not an addressee. Never invent an ID absent
        # from authoritative member_mentions.
        leading=re.match(r'^<@!?'+str(actual[0])+r'>(.*)$',clean,re.S) if len(actual)==1 else None
        # Without spaces a particle-prefix can also be a word prefix. Leave
        # that ambiguity to the existing semantic path; do not force a target.
        particle=bool(leading and re.match(r'^(?:에게|한테|[이가은는을를의])',leading[1]))
        mention_call=bool(len(actual)==1 and ((leading and not particle) or any(c.user==actual[0] and c.direct for c in candidates)))
        if mention_call:addressee=actual[0]
        elif event.reply_author:addressee=event.reply_author
        elif len(targets)==1 and not collision:addressee=next(iter(targets))
        return MemberRoles(event.author,addressee,actual,event.reply_to,event.reply_author,tuple(candidates[:32]),collision or len(actual)>1 or len(targets)>1,bot_collision)

def one_edit(a,b):
    if a==b or abs(len(a)-len(b))>1:return False
    if len(a)==len(b):
        diffs=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
        return len(diffs)==1 or len(diffs)==2 and diffs[1]==diffs[0]+1 and a[diffs[0]]==b[diffs[1]] and a[diffs[1]]==b[diffs[0]]
    if len(a)>len(b):a,b=b,a
    i=next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),len(a))
    return a[i:]==b[i+1:]

def corroboration(event,roles):
    """A single actual ID anchors evidence; free text alone cannot confirm it."""
    clean=prose(event.content).strip()
    match=re.match(r'^([가-힣A-Za-z0-9_]{2,24}?)[아야](?=$|[\s,!?.])',clean)
    if match:
        actual=set(event.member_mentions)
        target=next(iter(actual)) if len(actual)==1 else event.reply_author if not actual else None
        if target and target!=event.author:return (target,match[1],'mention' if actual else 'reply')
    own=re.fullmatch(r'나를\s+([가-힣A-Za-z0-9_]{2,24}?)(?:이라고|라고)\s*불러\s*줘[.!]?',clean)
    if own:return event.author,own[1],'self-report'
