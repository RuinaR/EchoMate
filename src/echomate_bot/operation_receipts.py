"""Ephemeral commit evidence. Never model-authored, persisted, or a tool grant.

Capture inside the existing write transaction; validate in a new read snapshot
immediately before transport. This cannot make SQLite and Discord atomic.
"""
from dataclasses import dataclass

REMINDER_FIELDS=('reminder_id','guild','channel','thread','parent','requester',
                 'target','due_at','timezone','text','status','source')


@dataclass(frozen=True)
class Receipt:
    kind:str
    guild:str
    user:str
    channel:str
    key:str
    values:tuple
    consent_version:int|None=None
    character_id:str|None=None

    def current(self,store):
        if self.kind.startswith('memory') and self.character_id!=getattr(store,'character_id',None):return False
        with store.db() as db:
            db.execute('BEGIN')
            expected=dict(self.values)
            if self.kind.startswith('memory'):
                consent=db.execute("SELECT enabled,version FROM consent_choices WHERE guild=? AND user=? AND category='memory'",
                                   (self.guild,self.user)).fetchone()
                if not consent or consent['version']!=self.consent_version:return False
                if self.kind=='memory_cleared':
                    return not consent['enabled'] and not db.execute('SELECT 1 FROM memories WHERE guild=? AND user=?',
                                                                     (self.guild,self.user)).fetchone()
                if not consent['enabled']:return False
                row=db.execute('SELECT * FROM memories WHERE memory_id=? AND guild=? AND user=? AND channel=?',
                               (self.key,self.guild,self.user,self.channel)).fetchone()
                if self.kind=='memory_removed':
                    return row is None and bool(db.execute('SELECT 1 FROM tombstones WHERE guild=? AND source=?',
                                                           (self.guild,expected['source'])).fetchone())
                if self.kind!='memory_saved' or not row or dict(row)!=expected:return False
                return ((row['expires_at'] is None or row['expires_at']>store.clock()) and
                        not db.execute('SELECT 1 FROM tombstones WHERE guild=? AND source=?',
                                       (self.guild,row['source'])).fetchone())
            if self.kind!='reminder':return False
            row=db.execute('SELECT * FROM reminders WHERE reminder_id=? AND guild=? AND requester=? AND channel=?',
                           (self.key,self.guild,self.user,self.channel)).fetchone()
            if not row or {k:row[k] for k in REMINDER_FIELDS}!=expected:return False
            if row['status']=='cancelled':return True
            return (row['status']=='scheduled' and row['due_at']>store.clock() and
                    not db.execute('SELECT 1 FROM tombstones WHERE guild=? AND source=?',
                                   (self.guild,row['source'])).fetchone())


def memory_receipt(db,kind,guild,user,channel,key='',row=None):
    g,u,ch=str(guild),str(user),str(channel)
    consent=db.execute("SELECT enabled,version FROM consent_choices WHERE guild=? AND user=? AND category='memory'",(g,u)).fetchone()
    if not consent or bool(consent['enabled'])!=(kind!='memory_cleared'):
        raise ValueError('Memory acknowledgement consent changed')
    if row is None and kind=='memory_saved':
        row=db.execute('SELECT * FROM memories WHERE memory_id=? AND guild=? AND user=? AND channel=?',(key,g,u,ch)).fetchone()
    data=dict(row) if row is not None else {}
    if kind in ('memory_saved','memory_removed') and (not data or tuple(data[k] for k in ('guild','user','channel'))!=(g,u,ch)):
        raise ValueError('Memory acknowledgement scope changed')
    return Receipt(kind,g,u,ch,key,tuple(sorted(data.items())),consent['version'],getattr(db,'character_id',None))


def reminder_receipt(row):
    return Receipt('reminder',row['guild'],row['requester'],row['channel'],row['reminder_id'],
                   tuple((k,row[k]) for k in REMINDER_FIELDS))


@dataclass(frozen=True)
class ReadReceipt:
    kind:str
    guild:int
    user:int
    channel:int
    values:tuple
    consent:tuple
    character_id:str|None=None

    def current(self,store):
        if self.kind!='reminders' and self.character_id!=getattr(store,'character_id',None):return False
        if self.consent and read_epochs(self.kind,store.subject_snapshot(self.guild,self.user))!=self.consent:return False
        if self.kind=='memory':rows=store.memories(self.guild,self.user,self.channel)[:3]
        elif self.kind=='summaries':rows=store.summaries(self.guild,self.user,self.channel)[:4]
        elif self.kind=='reminders':rows=[r for r in store.reminders(self.guild,self.user,active=True) if r['channel']==str(self.channel)][:10]
        else:return False
        return (read_values(self.kind,rows)==self.values and
                (not self.consent or read_epochs(self.kind,store.subject_snapshot(self.guild,self.user))==self.consent))


def read_epochs(kind,consent):
    return ((kind,consent[kind]),) if kind in ('memory','summaries') else ()


def read_values(kind,rows):
    return tuple(tuple((k,row[k]) for k in REMINDER_FIELDS) if kind=='reminders'
                 else tuple(sorted(row.items())) for row in rows)


def read_receipt(kind,event,rows,consent,*,character_id=None):
    maximum={'memory':3,'summaries':4,'reminders':10}.get(kind)
    if maximum is None or len(rows)>maximum:raise ValueError('Read acknowledgement bounds')
    owner='requester' if kind=='reminders' else 'user'
    if any((r['guild'],r[owner],r['channel'])!=(str(event.guild),str(event.author),str(event.channel)) for r in rows):
        raise ValueError('Read acknowledgement scope')
    return ReadReceipt(kind,event.guild,event.author,event.channel,read_values(kind,rows),read_epochs(kind,consent),character_id)


@dataclass(frozen=True)
class MemorySelection:
    """Same permitted retrieval, including an empty or top-three selection.

    Query prose stays in request RAM and is never logged or sent to a model by
    this guard. Reuse the Store's filters/ranking rather than a second index.
    """
    guild:int
    user:int
    channel:int
    query:str
    conversation_id:str
    archive:bool
    values:tuple
    consent_version:int
    character_id:str|None=None

    def current(self,store):
        if self.character_id!=getattr(store,'character_id',None):return False
        rows=[dict(row) for row in self.values]
        def valid(values):
            if values:return store.memory_evidence_current(self.guild,self.user,self.channel,values,self.consent_version)
            return store.subject_snapshot(self.guild,self.user)['memory']==(True,self.consent_version)
        if not valid(rows):return False
        current=store.memories(self.guild,self.user,self.channel,self.query,
                               conversation_id=self.conversation_id,allow_user_archive=self.archive)[:3]
        return (read_values('memory',current)==self.values and
                valid(current))
