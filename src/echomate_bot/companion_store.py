"""Private SQLite relationships, selective memories and executable reminders.

No network/model calls. Connections are short-lived and serialized; callers use
to_thread. No automatic backups containing deleted subjects are created.
"""
from contextlib import contextmanager,closing
import json
import re
import secrets
import sqlite3
import threading
import time
from .settings import private_path,positive_id
from .context import terms
from .temporal import parse_when
from .member_aliases import MemberAliases,SCHEMA as ALIAS_SCHEMA
from .privacy import PrivacyStore,SCHEMA as PRIVACY_SCHEMA
from .summary_store import SummaryStore,SCHEMA as SUMMARY_SCHEMA

SENSITIVE=re.compile(r'비밀번호|패스워드|토큰|인증번호|주민번호|계좌|주소|전화|연락처|이메일|생년|성생활|성관계|섹스|병원|진단|처방|질병|질환|복용|약\s*먹|비밀|DM|디엠|https?://|\b\d{3}[- ]\d{3,4}[- ]\d{4}\b',re.I)


def safe_subject_text(text):
    return (isinstance(text,str) and 0<len(text)<=500 and not SENSITIVE.search(text)
            and not re.search(r'<@|@everyone|@here|```|["“”]',text))


class CompanionStore(MemberAliases,PrivacyStore,SummaryStore):
    def __init__(self,path,clock=time.time):
        self.path=private_path(path);self.clock=clock;self.lock=threading.RLock();self.error=None;self.last_error=None;self.schema_version=None
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            with self.db() as db:
                version=db.execute('PRAGMA user_version').fetchone()[0]
                self.schema_version=version
                if version>7:raise ValueError('Newer companion schema')
                db.executescript('''
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS relationships(guild TEXT,user TEXT,affinity REAL DEFAULT 50,interactions INTEGER DEFAULT 0,last_at REAL DEFAULT 0,day TEXT,delta REAL DEFAULT 0,PRIMARY KEY(guild,user));
CREATE TABLE IF NOT EXISTS relationship_events(guild TEXT,event TEXT,user TEXT,kind TEXT,delta REAL,day TEXT,active INTEGER DEFAULT 1,at REAL,PRIMARY KEY(guild,event));
CREATE INDEX IF NOT EXISTS relationship_history ON relationship_events(guild,user,at);
CREATE TABLE IF NOT EXISTS optouts(guild TEXT,user TEXT,PRIMARY KEY(guild,user));
CREATE TABLE IF NOT EXISTS memory_optouts(guild TEXT,user TEXT,PRIMARY KEY(guild,user));
CREATE TABLE IF NOT EXISTS tombstones(guild TEXT,source TEXT,PRIMARY KEY(guild,source));
CREATE TABLE IF NOT EXISTS source_parts(guild TEXT,source TEXT,part TEXT,PRIMARY KEY(guild,source,part));
CREATE INDEX IF NOT EXISTS source_part_lookup ON source_parts(guild,part);
CREATE TABLE IF NOT EXISTS memory_cutoffs(guild TEXT,user TEXT,at REAL,PRIMARY KEY(guild,user));
CREATE TABLE IF NOT EXISTS memories(memory_id TEXT PRIMARY KEY,guild TEXT,user TEXT,kind TEXT,summary TEXT,source TEXT,channel TEXT,created_at REAL,updated_at REAL,observed_at REAL,last_confirmed_at REAL,event_start_at REAL,event_end_at REAL,expires_at REAL,timezone TEXT,temporal_precision TEXT,temporal_confidence REAL,confidence REAL,status TEXT,access_scope TEXT,expiration_policy TEXT,UNIQUE(guild,source,kind));
CREATE INDEX IF NOT EXISTS memories_lookup ON memories(guild,user,channel,status,expires_at);
CREATE TABLE IF NOT EXISTS reminders(reminder_id TEXT PRIMARY KEY,guild TEXT,channel TEXT,thread TEXT,parent TEXT,requester TEXT,target TEXT,created_at REAL,due_at REAL,timezone TEXT,text TEXT,status TEXT,delivery_attempts INTEGER DEFAULT 0,last_attempt_at REAL,delivered_at REAL,deduplication_key TEXT UNIQUE,source TEXT,error_code TEXT);
CREATE INDEX IF NOT EXISTS reminders_due ON reminders(status,due_at);
CREATE TABLE IF NOT EXISTS memory_flows(memory_id TEXT PRIMARY KEY REFERENCES memories(memory_id) ON DELETE CASCADE,conversation_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS subject_consents(guild TEXT,user TEXT,at REAL,PRIMARY KEY(guild,user));
'''+ALIAS_SCHEMA+'''
'''+PRIVACY_SCHEMA+SUMMARY_SCHEMA+'''
INSERT OR IGNORE INTO consent_choices SELECT s.guild,s.user,'relationships',1,1,s.at FROM subject_consents s WHERE NOT EXISTS(SELECT 1 FROM optouts o WHERE o.guild=s.guild AND o.user=s.user);
INSERT OR IGNORE INTO consent_choices SELECT s.guild,s.user,'memory',1,1,s.at FROM subject_consents s WHERE NOT EXISTS(SELECT 1 FROM optouts o WHERE o.guild=s.guild AND o.user=s.user) AND NOT EXISTS(SELECT 1 FROM memory_optouts o WHERE o.guild=s.guild AND o.user=s.user);
PRAGMA user_version=7;
COMMIT;
''')
            self.cleanup()
            self.schema_version=7
        except (sqlite3.Error,OSError,ValueError) as exc:self.error=type(exc).__name__;self.last_error=type(exc).__name__

    def recover_readonly(self):
        """Retry transient initialization failures only on a complete v7 DB.

        Never creates a DB, runs migration/cleanup, or repairs corrupt data.
        """
        if not self.error:return True
        if self.error not in ('OperationalError','OSError','PermissionError'):return False
        with self.lock:
            try:
                with closing(sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.25)) as db:
                    db.execute('PRAGMA query_only=ON')
                    db.execute('BEGIN')
                    version=db.execute('PRAGMA user_version').fetchone()[0]
                    if version!=7:return False
                    required={'relationships','relationship_events','optouts','memory_optouts','tombstones','source_parts','memory_cutoffs','memories','reminders','memory_flows','subject_consents','member_aliases','alias_evidence','consent_choices','conversation_summaries','dialogue_summaries','summary_participants','summary_sources','summary_tombstones'}
                    if not required<={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}:return False
                    for table,columns in (('consent_choices','guild,user,category,enabled,version,at'),('relationships','guild,user'),('memories','guild,user,source'),('reminders','guild,requester'),('source_parts','guild,source,part'),('summary_participants','guild,user'),('conversation_summaries','guild,user')):
                        db.execute('SELECT '+columns+' FROM '+table+' LIMIT 0')
                self.error=None;self.last_error=None;self.schema_version=version
                return True
            except (sqlite3.Error,OSError) as exc:
                self.last_error=type(exc).__name__;return False

    @contextmanager
    def db(self):
        if self.error:raise RuntimeError('Companion storage unavailable')
        with self.lock:
            db=None
            try:
                db=sqlite3.connect(self.path,timeout=.25);db.row_factory=sqlite3.Row
                db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA secure_delete=ON');db.execute('PRAGMA foreign_keys=ON')
                with db:yield db
                self.last_error=None
            except sqlite3.DatabaseError as exc:
                self.last_error=type(exc).__name__
                if 'malformed' in str(exc).lower() or 'not a database' in str(exc).lower():self.error=type(exc).__name__
                raise
            finally:
                if db is not None:db.close()

    def opted_out(self,db,guild,user):
        return db.execute('SELECT 1 FROM optouts WHERE guild=? AND user=?',(str(guild),str(user))).fetchone() is not None

    def automatic_allowed(self,guild,user,category='relationships'):
        return self.consent(guild,user).get(category,False)

    def relationship(self,guild,user,event,kind='conversation',*,remove=False,observed=None):
        now=self.clock();day=time.strftime('%Y-%m-%d',time.gmtime(now));g=str(guild);u=str(user);key=str(event)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if self.opted_out(db,g,u):return
            consent=db.execute("SELECT enabled,at FROM consent_choices WHERE guild=? AND user=? AND category='relationships'",(g,u)).fetchone()
            if not remove and (not consent or not consent[0] or observed is not None and observed<consent[1]):return
            previous=db.execute('SELECT * FROM relationship_events WHERE guild=? AND event=?',(g,key)).fetchone()
            if previous:
                if remove and previous['active']:
                    db.execute('UPDATE relationship_events SET active=0 WHERE guild=? AND event=?',(g,key))
                    db.execute('UPDATE relationships SET affinity=MAX(0,affinity-?) WHERE guild=? AND user=?',(previous['delta'],g,u))
                return
            if remove:return
            db.execute('INSERT OR IGNORE INTO relationships(guild,user,day) VALUES(?,?,?)',(g,u,day))
            row=db.execute('SELECT * FROM relationships WHERE guild=? AND user=?',(g,u)).fetchone()
            daily=row['delta'] if row['day']==day else 0
            delta=min(.25 if kind=='conversation' else .1,max(0,2-daily)) if now-row['last_at']>=600 else 0
            db.execute('INSERT INTO relationship_events VALUES(?,?,?,?,?,?,1,?)',(g,key,u,kind,delta,day,now))
            db.execute('UPDATE relationships SET affinity=MIN(100,affinity+?),interactions=interactions+1,last_at=?,day=?,delta=? WHERE guild=? AND user=?',(delta,now,day,daily+delta,g,u))
            db.execute('DELETE FROM relationship_events WHERE at<?',(now-30*86400,))

    def set_affinity(self,guild,user,value,*,require_consent=False):
        positive_id(guild);positive_id(user)
        if not 0<=value<=100:raise ValueError('Affinity must be 0..100')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if require_consent and not db.execute("SELECT 1 FROM consent_choices WHERE guild=? AND user=? AND category='relationships' AND enabled=1",(str(guild),str(user))).fetchone():raise ValueError('본인의 친밀도 저장 동의가 필요해요')
            db.execute('INSERT INTO relationships(guild,user,affinity) VALUES(?,?,?) ON CONFLICT(guild,user) DO UPDATE SET affinity=excluded.affinity',(str(guild),str(user),value))

    def add_memory(self,guild,user,channel,summary,kind='explicit',*,source=None,observed=None,tz='Asia/Seoul',expires=None,status='active',policy=None,conversation_id=None,require_consent=False,source_event=None,receipts=None):
        positive_id(guild);positive_id(user);positive_id(channel)
        if kind not in ('plan','state','goal','preference','explicit') or status not in ('active','disabled','uncertain'):raise ValueError('Invalid memory kind/status')
        if not safe_subject_text(summary):raise ValueError('Sensitive, third-party or unsupported memory')
        now=self.clock();observed=observed or now
        policy=policy or {}
        from datetime import datetime,timezone
        when=parse_when(summary,datetime.fromtimestamp(observed,timezone.utc),tz)
        start=when.start.timestamp() if when.start else None;end=when.end.timestamp() if when.end else None
        if kind=='plan':
            if start is None:status='uncertain'
            if start is not None and expires is None:
                grace=policy.get('memory_date_grace',86400) if when.precision=='date' else policy.get('memory_plan_grace',3600)
                expires=end+grace
        elif kind=='state':expires=expires if expires is not None else (end if end else observed+policy.get('memory_state_hours',6)*3600)
        if expires is not None and expires<=now:raise ValueError('Memory already expired')
        source=str(source) if source is not None else 'manual:'+secrets.token_hex(12);g=str(guild);u=str(user)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if require_consent:
                consent=db.execute("SELECT enabled,at FROM consent_choices WHERE guild=? AND user=? AND category='memory'",(g,u)).fetchone()
                if not consent or not consent[0] or observed<consent[1]:return None
            if self.opted_out(db,g,u) or db.execute('SELECT 1 FROM memory_optouts WHERE guild=? AND user=?',(g,u)).fetchone() or db.execute('SELECT 1 FROM tombstones WHERE guild=? AND source=?',(g,source)).fetchone():return None
            cutoff=db.execute("SELECT MAX(at) FROM memory_cutoffs WHERE guild=? AND user IN (?, '*')",(g,u)).fetchone()[0]
            if not source.startswith('manual:') and cutoff is not None and observed<=cutoff:return None
            if source_event is not None and not self.register_source_parts(db,source_event):return None
            old=db.execute('SELECT memory_id FROM memories WHERE guild=? AND source=? AND kind=?',(g,source,kind)).fetchone()
            if old:
                if receipts is not None:
                    from .operation_receipts import memory_receipt
                    receipts.append(memory_receipt(db,'memory_saved',guild,user,channel,old[0]))
                return old[0]
            if db.execute('SELECT COUNT(*) FROM memories WHERE guild=? AND user=?',(g,u)).fetchone()[0]>=100 or db.execute('SELECT COUNT(*) FROM memories').fetchone()[0]>=5000:raise ValueError('Memory limit')
            key=secrets.token_hex(8)
            db.execute('INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(key,g,u,kind,summary,source,str(channel),now,now,observed,observed,start,end,expires,tz,when.precision,1 if start else 0,1 if status=='active' else .5,status,'source_channel','kind_default'))
            if conversation_id:db.execute('INSERT INTO memory_flows VALUES(?,?)',(key,conversation_id))
            if receipts is not None:
                from .operation_receipts import memory_receipt
                receipts.append(memory_receipt(db,'memory_saved',guild,user,channel,key))
            return key

    def register_source_parts(self,db,event):
        parts=getattr(event,'raw_parts',())
        if len(parts)<2:return True
        if any((p.guild,p.channel,p.author)!=(event.guild,event.channel,event.author) for p in parts):raise ValueError('Mixed source identity')
        g=str(event.guild);source=str(event.id)
        if any(db.execute('SELECT 1 FROM tombstones WHERE guild=? AND source=?',(g,str(p.id))).fetchone() for p in parts):return False
        db.executemany('INSERT OR IGNORE INTO source_parts VALUES(?,?,?)',[(g,source,str(p.id)) for p in parts])
        return True

    @staticmethod
    def prune_source_parts(db):
        db.execute('''DELETE FROM source_parts WHERE NOT EXISTS(SELECT 1 FROM memories m WHERE m.guild=source_parts.guild AND m.source=source_parts.source)
            AND NOT EXISTS(SELECT 1 FROM reminders r WHERE r.guild=source_parts.guild AND r.source=source_parts.source AND r.status IN ('scheduled','processing'))''')

    def extract(self,event,tz,*,text=None,policy=None,receipts=None):
        if not self.automatic_allowed(event.guild,event.author,'memory'):return None
        observed=min(p.timestamp.timestamp() for p in (getattr(event,'raw_parts',()) or (event,)))
        with self.db() as db:
            consent_at=db.execute("SELECT at FROM consent_choices WHERE guild=? AND user=? AND category='memory'",(str(event.guild),str(event.author))).fetchone()
            if consent_at and any(p.timestamp.timestamp()<consent_at[0] for p in (getattr(event,'raw_parts',()) or (event,))):return None
        text=(event.content if text is None else text).strip()
        if not safe_subject_text(text) or not re.search(r'나는|난\s|저는|내\s|기억해\s*줘',text):return None
        if re.search(r'친구|걔|그 사람|누가|농담|인용|아마|일지도|할까|하자|좋아한다고|선호한다고|라고\s*했|들었',text):return None
        kind=('preference' if re.search(r'좋아해|선호해|불러\s*줘',text) else 'state' if re.search(r'오늘|이번\s*주|지금',text) and re.search(r'피곤|휴가|게임\s*중|기분',text) else 'goal' if re.search(r'개발\s*중|육성\s*중|연습\s*중|목표',text) else 'plan' if re.search(r'약속|모임|만나|게임하',text) else 'explicit' if re.search(r'기억해\s*줘',text) else None)
        if not kind:return None
        if kind in ('plan','goal') and re.search(r'취소|완료|끝났|변경|옮겼',text):
            rows=[r for r in self.memories(event.guild,event.author,kind=kind,conversation_id=getattr(event,'conversation_id',None)) if r['channel']==str(event.channel) and r['status']=='active']
            if len(rows)!=1:return None
            row=rows[0]
            if re.search(r'취소|완료|끝났',text):
                with self.db() as db:
                    db.execute('BEGIN IMMEDIATE')
                    if not db.execute("SELECT 1 FROM consent_choices WHERE guild=? AND user=? AND category='memory' AND enabled=1 AND at<=?",(str(event.guild),str(event.author),observed)).fetchone():return None
                    db.execute('INSERT OR IGNORE INTO tombstones VALUES(?,?)',(str(event.guild),row['source']))
                    db.execute('DELETE FROM memories WHERE memory_id=?',(row['memory_id'],))
                    if receipts is not None:
                        from .operation_receipts import memory_receipt
                        receipts.append(memory_receipt(db,'memory_removed',event.guild,event.author,event.channel,row['memory_id'],row))
                return row['memory_id']
            when=parse_when(text,event.timestamp,tz)
            if not when.start:return None
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                if not db.execute("SELECT 1 FROM consent_choices WHERE guild=? AND user=? AND category='memory' AND enabled=1 AND at<=?",(str(event.guild),str(event.author),observed)).fetchone():return None
                if not self.register_source_parts(db,event):return None
                db.execute('INSERT OR IGNORE INTO tombstones VALUES(?,?)',(str(event.guild),row['source']))
                grace=(policy or {}).get('memory_date_grace',86400) if when.precision=='date' else (policy or {}).get('memory_plan_grace',3600)
                db.execute('UPDATE memories SET summary=?,source=?,observed_at=?,last_confirmed_at=?,updated_at=?,event_start_at=?,event_end_at=?,expires_at=?,timezone=?,temporal_precision=? WHERE memory_id=?',(text[:300],str(event.id),event.timestamp.timestamp(),event.timestamp.timestamp(),self.clock(),when.start.timestamp(),when.end.timestamp(),when.end.timestamp()+grace,tz,when.precision,row['memory_id']))
                if receipts is not None:
                    from .operation_receipts import memory_receipt
                    receipts.append(memory_receipt(db,'memory_saved',event.guild,event.author,event.channel,row['memory_id']))
            return row['memory_id']
        return self.add_memory(event.guild,event.author,event.channel,text[:300],kind,source=event.id,observed=observed,tz=tz,policy=policy,conversation_id=getattr(event,'conversation_id',None),require_consent=True,source_event=event,receipts=receipts)

    def memories(self,guild,user=None,channel=None,query='',kind=None,*,conversation_id=None,allow_user_archive=False,include_expired=False):
        now=self.clock();sql='SELECT * FROM memories WHERE guild=?';args=[str(guild)]
        if not include_expired:sql+=' AND (expires_at IS NULL OR expires_at>?)';args.append(now)
        if user is not None:sql+=' AND user=?';args.append(str(user))
        if channel is not None:sql+=" AND channel=? AND status='active' AND (kind!='plan' OR event_end_at>?) AND (kind!='goal' OR last_confirmed_at>?)";args.extend((str(channel),now,now-90*86400))
        if kind:sql+=' AND kind=?';args.append(kind)
        if conversation_id and not allow_user_archive:
            sql+=" AND (kind IN ('preference','explicit') OR memory_id IN (SELECT memory_id FROM memory_flows WHERE conversation_id=?))";args.append(conversation_id)
        with self.db() as db:rows=[dict(x) for x in db.execute(sql+' ORDER BY updated_at DESC LIMIT 100',args)]
        if query:
            q=terms(query);plan_query=bool(re.search(r'언제|약속|몇\s*시|일정|모임',query))
            rows=[r for r in rows if q & terms(r['summary']) or (plan_query and r['kind']=='plan')]
            rows.sort(key=lambda r:(len(q & terms(r['summary'])),r['updated_at']),reverse=True)
        return rows

    def memory_evidence_current(self,guild,user,channel,rows,consent_version):
        """Read-only delivery guard for the exact facts used by generation.

        Re-consenting is not permission to send an older in-flight answer.
        A correction, expiry, deletion or source invalidation also retires it.
        """
        if not rows or len(rows)>3 or type(consent_version) is not int:return False
        scope=(str(guild),str(user),str(channel));now=self.clock()
        with self.db() as db:
            db.execute('BEGIN')
            consent=db.execute("SELECT enabled,version FROM consent_choices WHERE guild=? AND user=? AND category='memory'",scope[:2]).fetchone()
            if not consent or not consent['enabled'] or consent['version']!=consent_version:return False
            for expected in rows:
                if tuple(expected.get(k) for k in ('guild','user','channel'))!=scope:return False
                current=db.execute('SELECT * FROM memories WHERE memory_id=? AND guild=? AND user=? AND channel=?',
                    (expected.get('memory_id'),*scope)).fetchone()
                if not current or dict(current)!=expected or current['status']!='active':return False
                if current['expires_at'] is not None and current['expires_at']<=now:return False
                if current['kind']=='plan' and (current['event_end_at'] is None or current['event_end_at']<=now):return False
                if current['kind']=='goal' and (current['last_confirmed_at'] is None or current['last_confirmed_at']<=now-90*86400):return False
                if db.execute('SELECT 1 FROM tombstones WHERE guild=? AND source=?',(scope[0],current['source'])).fetchone():return False
        return True

    def delete_source(self,guild,source,*,known=True):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            dependencies=[r[0] for r in db.execute('SELECT source FROM source_parts WHERE guild=? AND part=?',(str(guild),str(source)))]
            if db.execute('SELECT 1 FROM summary_sources WHERE guild=? AND source=?',(str(guild),str(source))).fetchone():known=True
            if not known and not dependencies and not db.execute('SELECT 1 FROM memories WHERE guild=? AND source=? UNION SELECT 1 FROM reminders WHERE guild=? AND source=? UNION SELECT 1 FROM alias_evidence WHERE guild=? AND source=? UNION SELECT 1 FROM conversation_summaries WHERE guild=? AND source=?',(str(guild),str(source))*4).fetchone():return
            for source in set([str(source),*dependencies]):
                db.execute('INSERT OR IGNORE INTO tombstones VALUES(?,?)',(str(guild),str(source)))
                db.execute('DELETE FROM dialogue_summaries WHERE id IN (SELECT id FROM summary_sources WHERE guild=? AND source=?)',(str(guild),str(source)))
                db.execute('DELETE FROM memories WHERE guild=? AND source=?',(str(guild),str(source)))
                db.execute('DELETE FROM alias_evidence WHERE guild=? AND source=?',(str(guild),str(source)))
                db.execute('DELETE FROM conversation_summaries WHERE guild=? AND source=?',(str(guild),str(source)))
                db.execute("UPDATE reminders SET status='cancelled',text='' WHERE guild=? AND source=? AND status IN ('scheduled','processing')",(str(guild),str(source)))
            self.prune_source_parts(db)

    def delete_memory(self,guild,key):
        with self.db() as db:
            row=db.execute('SELECT source FROM memories WHERE guild=? AND memory_id=?',(str(guild),key)).fetchone()
            if row:db.execute('INSERT OR IGNORE INTO tombstones VALUES(?,?)',(str(guild),row[0]))
            db.execute('DELETE FROM memories WHERE guild=? AND memory_id=?',(str(guild),key))
            self.prune_source_parts(db)

    def edit_memory(self,guild,key,summary,expires,status):
        if not safe_subject_text(summary) or status not in ('active','disabled','uncertain'):raise ValueError('Invalid memory edit')
        if expires is not None and expires<=self.clock():raise ValueError('Expiry must be future')
        with self.db() as db:
            # Recomputing plan dates requires delete/add; do not leave stale event times.
            row=db.execute('SELECT * FROM memories WHERE guild=? AND memory_id=?',(str(guild),key)).fetchone()
            if not row:raise ValueError('Memory not found')
            if row['kind']=='plan' and summary!=row['summary']:raise ValueError('Replace plan to recompute its date')
            db.execute('UPDATE memories SET summary=?,expires_at=?,status=?,updated_at=?,last_confirmed_at=? WHERE guild=? AND memory_id=?',(summary,expires,status,self.clock(),self.clock() if status=='active' else row['last_confirmed_at'],str(guild),key))

    def forget(self,guild,user=None):
        g=str(guild)
        with self.db() as db:
            subjects=[str(user)] if user is not None else [r[0] for r in db.execute('SELECT user FROM memories WHERE guild=? UNION SELECT user FROM relationships WHERE guild=? UNION SELECT requester FROM reminders WHERE guild=? UNION SELECT user FROM subject_consents WHERE guild=? UNION SELECT user FROM member_aliases WHERE guild=? UNION SELECT user FROM consent_choices WHERE guild=? UNION SELECT user FROM conversation_summaries WHERE guild=?',(g,g,g,g,g,g,g))]
            for u in subjects:
                db.execute('INSERT OR IGNORE INTO summary_tombstones SELECT s.guild,s.source FROM summary_sources s JOIN summary_participants p ON s.id=p.id WHERE p.guild=? AND p.user=?',(g,u))
                db.execute('INSERT OR IGNORE INTO summary_tombstones SELECT guild,source FROM conversation_summaries WHERE guild=? AND user=?',(g,u))
                db.execute('DELETE FROM dialogue_summaries WHERE id IN (SELECT id FROM summary_participants WHERE guild=? AND user=?)',(g,u))
                db.execute('INSERT OR IGNORE INTO optouts VALUES(?,?)',(g,u))
                db.execute('INSERT INTO memory_cutoffs VALUES(?,?,?) ON CONFLICT(guild,user) DO UPDATE SET at=excluded.at',(g,u,self.clock()))
                for table in ('memories','relationships','relationship_events','member_aliases','alias_evidence'):db.execute(f'DELETE FROM {table} WHERE guild=? AND user=?',(g,u))
                db.execute('INSERT OR IGNORE INTO tombstones SELECT guild,source FROM reminders WHERE guild=? AND requester=?',(g,u))
                db.execute('DELETE FROM reminders WHERE guild=? AND requester=?',(g,u))
                db.execute('DELETE FROM subject_consents WHERE guild=? AND user=?',(g,u))
                db.execute('DELETE FROM alias_evidence WHERE guild=? AND witness=?',(g,u))
                db.execute('DELETE FROM conversation_summaries WHERE guild=? AND user=?',(g,u))
                db.execute('UPDATE consent_choices SET enabled=0,version=version+1,at=? WHERE guild=? AND user=?',(self.clock(),g,u))
            self.prune_source_parts(db)
        # No data backups are restored automatically. WAL checkpoint is best effort.
        with self.db() as db:db.execute('PRAGMA wal_checkpoint(TRUNCATE)')

    def forget_memories(self,guild,user,*,receipts=None):
        self.set_consent(guild,user,'memory',False)
        with self.db() as db:
            db.execute('INSERT OR IGNORE INTO memory_optouts VALUES(?,?)',(str(guild),str(user)))
            db.execute('INSERT INTO memory_cutoffs VALUES(?,?,?) ON CONFLICT(guild,user) DO UPDATE SET at=excluded.at',(str(guild),str(user),self.clock()))
            db.execute('DELETE FROM memories WHERE guild=? AND user=?',(str(guild),str(user)))
            self.prune_source_parts(db)
            if receipts is not None:
                from .operation_receipts import memory_receipt
                receipts.append(memory_receipt(db,'memory_cleared',guild,user,''))

    def users(self,guild):
        with self.db() as db:return [dict(r) for r in db.execute('SELECT * FROM relationships WHERE guild=? ORDER BY last_at DESC LIMIT 100',(str(guild),))]

    def familiarity(self,guild,user):
        with self.db() as db:
            row=db.execute('SELECT affinity FROM relationships WHERE guild=? AND user=?',(str(guild),str(user))).fetchone()
            return row[0] if row else 50

    def resume_subject(self,guild,user):
        # Compatibility for explicit self opt-in fixtures/old local integrations.
        for category in ('relationships','memory'):self.set_consent(guild,user,category,True)
        with self.db() as db:
            db.execute('DELETE FROM optouts WHERE guild=? AND user=?',(str(guild),str(user)))
            db.execute('DELETE FROM memory_optouts WHERE guild=? AND user=?',(str(guild),str(user)))
            db.execute('INSERT INTO subject_consents VALUES(?,?,?) ON CONFLICT(guild,user) DO UPDATE SET at=excluded.at',(str(guild),str(user),self.clock()))

    def relationship_history(self,guild,user):
        with self.db() as db:return [dict(r) for r in db.execute('SELECT kind,delta,active,at FROM relationship_events WHERE guild=? AND user=? ORDER BY at DESC LIMIT 10',(str(guild),str(user)))]

    def clear_records(self,guild,area,user=None):
        if area not in ('memories','relationships','reminders'):raise ValueError('Invalid record area')
        g=str(guild);u=str(user) if user is not None else None
        with self.db() as db:
            if area=='memories':db.execute('INSERT INTO memory_cutoffs VALUES(?,?,?) ON CONFLICT(guild,user) DO UPDATE SET at=excluded.at',(g,u or '*',self.clock()))
            column='requester' if area=='reminders' else 'user'
            if area=='reminders':db.execute("INSERT OR IGNORE INTO tombstones SELECT guild,source FROM reminders WHERE guild=?"+(' AND requester=?' if u else ''),(g,u) if u else (g,))
            db.execute('DELETE FROM '+area+' WHERE guild=?'+(' AND '+column+'=?' if u else ''),(g,u) if u else (g,))
            if area=='relationships':db.execute('DELETE FROM relationship_events WHERE guild=?'+(' AND user=?' if u else ''),(g,u) if u else (g,))

    def reserve_reminder(self,event,due,tz,text,*,receipts=None):
        now=self.clock();g=str(event.guild);u=str(event.author)
        if not safe_subject_text(text) or due<=now or due-now>366*86400:raise ValueError('Invalid or private reminder')
        dedup=f'{event.guild}:{event.id}'
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            existing=db.execute('SELECT * FROM reminders WHERE deduplication_key=?',(dedup,)).fetchone()
            if existing:
                if existing['status']!='scheduled':raise ValueError('Request already closed')
                if receipts is not None:
                    from .operation_receipts import reminder_receipt
                    receipts.append(reminder_receipt(existing))
                return dict(existing)
            if not self.register_source_parts(db,event) or db.execute('SELECT 1 FROM tombstones WHERE guild=? AND source=?',(g,str(event.id))).fetchone():raise ValueError('Request withdrawn')
            if db.execute("SELECT COUNT(*) FROM reminders WHERE guild=? AND requester=? AND status IN ('scheduled','processing')",(g,u)).fetchone()[0]>=10:raise ValueError('Active reminder limit')
            if db.execute('SELECT COUNT(*) FROM reminders WHERE guild=? AND requester=? AND created_at>?',(g,u,now-86400)).fetchone()[0]>=30:raise ValueError('Daily reminder limit')
            if db.execute("SELECT COUNT(*) FROM reminders WHERE status IN ('scheduled','processing')").fetchone()[0]>=1000:raise ValueError('Global reminder limit')
            key=secrets.token_hex(12)
            db.execute('INSERT INTO reminders(reminder_id,guild,channel,thread,parent,requester,target,created_at,due_at,timezone,text,status,deduplication_key,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(key,g,str(event.channel),str(event.channel) if event.parent else None,str(event.parent) if event.parent else None,u,u,now,due,tz,text,'scheduled',dedup,str(event.id)))
            row=dict(db.execute('SELECT * FROM reminders WHERE reminder_id=?',(key,)).fetchone())
            if receipts is not None:
                from .operation_receipts import reminder_receipt
                receipts.append(reminder_receipt(row))
            return row

    def reminders(self,guild,user=None,*,active=False):
        sql='SELECT * FROM reminders WHERE guild=?';args=[str(guild)]
        if user is not None:sql+=' AND requester=?';args.append(str(user))
        if active:sql+=" AND status='scheduled'"
        with self.db() as db:return [dict(r) for r in db.execute(sql+" ORDER BY CASE status WHEN 'scheduled' THEN 0 WHEN 'processing' THEN 0 WHEN 'failed' THEN 1 ELSE 2 END,due_at LIMIT 1000",args)]

    def change_reminder(self,guild,user,key,*,due=None,text=None,cancel=False,owner=False,receipts=None):
        if due is not None and not self.clock()<due<=self.clock()+366*86400:raise ValueError('Invalid reminder date')
        if text is not None and not safe_subject_text(text):raise ValueError('Unsafe reminder text')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM reminders WHERE guild=? AND reminder_id=?',(str(guild),key)).fetchone()
            if not row or (not owner and row['requester']!=str(user)):raise PermissionError('Not your reminder')
            if row['status']!='scheduled':raise ValueError('Reminder is no longer scheduled')
            if cancel:
                db.execute('INSERT OR IGNORE INTO tombstones VALUES(?,?)',(str(guild),row['source']))
                db.execute("UPDATE reminders SET status='cancelled',text='' WHERE reminder_id=?",(key,))
            else:
                if due is not None:db.execute('UPDATE reminders SET due_at=? WHERE reminder_id=?',(due,key))
                if text is not None:db.execute('UPDATE reminders SET text=? WHERE reminder_id=?',(text,key))
            if receipts is not None:
                from .operation_receipts import reminder_receipt
                receipts.append(reminder_receipt(db.execute('SELECT * FROM reminders WHERE reminder_id=?',(key,)).fetchone()))

    def due(self,grace):
        now=self.clock()
        with self.db() as db:
            db.execute("UPDATE reminders SET status='expired',text='' WHERE status='scheduled' AND due_at<?",(now-grace,))
            return [dict(r) for r in db.execute("SELECT * FROM reminders WHERE status='scheduled' AND due_at<=? AND (last_attempt_at IS NULL OR last_attempt_at<=?) ORDER BY due_at LIMIT 5",(now,now-30))]

    def defer_preflight(self,key,code):
        with self.db() as db:db.execute("UPDATE reminders SET last_attempt_at=?,error_code=? WHERE reminder_id=? AND status='scheduled'",(self.clock(),code,key))

    def claim(self,key):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            cursor=db.execute("UPDATE reminders SET status='processing',delivery_attempts=delivery_attempts+1,last_attempt_at=? WHERE reminder_id=? AND status='scheduled' AND due_at<=?",(self.clock(),key,self.clock()))
            return dict(db.execute('SELECT * FROM reminders WHERE reminder_id=?',(key,)).fetchone()) if cursor.rowcount==1 else None

    def processing(self,key):
        with self.db() as db:return db.execute("SELECT 1 FROM reminders WHERE reminder_id=? AND status='processing'",(key,)).fetchone() is not None

    def finish(self,key,status,error=None):
        if status not in ('delivered','failed','expired'):raise ValueError('Invalid delivery outcome')
        with self.db() as db:db.execute("UPDATE reminders SET status=?,delivered_at=?,error_code=?,text='' WHERE reminder_id=? AND status='processing'",(status,self.clock() if status=='delivered' else None,error,key))

    def recover(self):
        with self.db() as db:db.execute("UPDATE reminders SET status='failed',error_code='restart_ambiguous',text='' WHERE status='processing'")

    def cleanup(self):
        now=self.clock()
        with self.db() as db:
            db.execute('DELETE FROM conversation_summaries WHERE expires<=?',(now,))
            db.execute('DELETE FROM dialogue_summaries WHERE expires<=?',(now,))
            db.execute('DELETE FROM relationship_events WHERE at<?',(now-30*86400,))
            db.execute('DELETE FROM alias_evidence WHERE at<?',(now-90*86400,))
            db.execute("DELETE FROM member_aliases WHERE status!='confirmed' AND updated<?",(now-90*86400,))
            db.execute('DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at<=?',(now,))
            self.prune_source_parts(db)
            db.execute("UPDATE memories SET status='uncertain' WHERE kind='goal' AND status='active' AND last_confirmed_at<?",(now-90*86400,))
            db.execute("DELETE FROM reminders WHERE status IN ('cancelled','expired','failed','delivered') AND created_at<?",(now-7*86400,))
