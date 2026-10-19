"""Private, channel-scoped alias evidence. No inferred identity authorizes actions."""
import re
from .naming import validate_name
from .settings import positive_id

SCHEMA='''
CREATE TABLE IF NOT EXISTS member_aliases(guild TEXT,channel TEXT,user TEXT,alias TEXT,status TEXT,updated REAL,PRIMARY KEY(guild,channel,user,alias));
CREATE TABLE IF NOT EXISTS alias_evidence(guild TEXT,channel TEXT,user TEXT,alias TEXT,source TEXT,witness TEXT,kind TEXT,at REAL,PRIMARY KEY(guild,channel,user,alias,source));
'''

def alias_key(value):
    value=validate_name(value)
    if not re.fullmatch(r'[가-힣A-Za-z0-9_ -]{2,32}',value):raise ValueError('Unsupported alias')
    return value.casefold()

class MemberAliases:
    def aliases(self,guild,channel=None,user=None):
        sql="SELECT * FROM member_aliases WHERE guild=? AND (status='confirmed' OR updated>?)";args=[str(guild),self.clock()-90*86400]
        if channel is not None:sql+=' AND channel=?';args.append(str(channel))
        if user is not None:sql+=' AND user=?';args.append(str(user))
        with self.db() as db:
            rows=[dict(r) for r in db.execute(sql+' ORDER BY updated DESC LIMIT 3000',args)]
            for r in rows:
                n,w=db.execute('SELECT COUNT(*),COUNT(DISTINCT witness) FROM alias_evidence WHERE guild=? AND channel=? AND user=? AND alias=?',tuple(r[k] for k in ('guild','channel','user','alias'))).fetchone()
                r.update(observations=n,witnesses=w,confidence=1.0 if r['status']=='confirmed' else min(.89,.35+.08*n+.05*w),evidence='owner' if r['status']=='confirmed' else 'mention/reply/self-report')
        return rows

    def set_alias(self,guild,channel,user,alias,status='confirmed',*,require_consent=False):
        for value in (guild,channel,user):positive_id(value)
        if status not in ('confirmed','candidate','deleted'):raise ValueError('Invalid alias status')
        alias=alias_key(alias)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if require_consent and status!='deleted' and not db.execute("SELECT 1 FROM consent_choices WHERE guild=? AND user=? AND category='relationships' AND enabled=1",(str(guild),str(user))).fetchone():raise ValueError('본인의 친밀도 저장 동의가 필요해요')
            if status!='deleted' and self.opted_out(db,guild,user):raise ValueError('Subject opted out')
            if db.execute('SELECT COUNT(*) FROM member_aliases').fetchone()[0]>=3000 and not db.execute('SELECT 1 FROM member_aliases WHERE guild=? AND channel=? AND user=? AND alias=?',tuple(map(str,(guild,channel,user)))+(alias,)).fetchone():raise ValueError('Alias limit')
            db.execute('INSERT INTO member_aliases VALUES(?,?,?,?,?,?) ON CONFLICT(guild,channel,user,alias) DO UPDATE SET status=excluded.status,updated=excluded.updated',tuple(map(str,(guild,channel,user)))+(alias,status,self.clock()))
            if status=='deleted':db.execute('DELETE FROM alias_evidence WHERE guild=? AND channel=? AND user=? AND alias=?',tuple(map(str,(guild,channel,user)))+(alias,))

    def observe_alias(self,guild,channel,user,alias,source,witness,kind,*,observed=None):
        for value in (guild,channel,user,source,witness):positive_id(value)
        if kind not in ('mention','reply','self-report'):raise ValueError('Invalid evidence')
        alias=alias_key(alias);key=tuple(map(str,(guild,channel,user)))+(alias,)
        with self.db() as db:
            if self.opted_out(db,guild,user):return
            consent=db.execute("SELECT enabled,at FROM consent_choices WHERE guild=? AND user=? AND category='relationships'",(str(guild),str(user))).fetchone()
            if not consent or not consent[0] or observed is not None and observed<consent[1]:return
            if db.execute('SELECT 1 FROM tombstones WHERE guild=? AND source=?',(str(guild),str(source))).fetchone():return
            row=db.execute('SELECT status FROM member_aliases WHERE guild=? AND channel=? AND user=? AND alias=?',key).fetchone()
            if row and row[0]=='deleted':return
            if not row and db.execute('SELECT COUNT(*) FROM member_aliases').fetchone()[0]>=3000:return
            db.execute('DELETE FROM alias_evidence WHERE at<?',(self.clock()-90*86400,))
            # Bounded evidence per candidate, IDs only; no utterance is retained.
            if db.execute('SELECT COUNT(*) FROM alias_evidence WHERE guild=? AND channel=? AND user=? AND alias=?',key).fetchone()[0]>=30:return
            db.execute("INSERT INTO member_aliases VALUES(?,?,?,?,'candidate',?) ON CONFLICT(guild,channel,user,alias) DO UPDATE SET updated=excluded.updated",key+(self.clock(),))
            db.execute('INSERT OR IGNORE INTO alias_evidence VALUES(?,?,?,?,?,?,?,?)',key+(str(source),str(witness),kind,self.clock()))

    def clear_aliases(self,guild,user=None,channel=None):
        sql=' WHERE guild=?';args=[str(guild)]
        if user is not None:sql+=' AND user=?';args.append(str(user))
        if channel is not None:sql+=' AND channel=?';args.append(str(channel))
        with self.db() as db:
            for table in ('member_aliases','alias_evidence'):db.execute('DELETE FROM '+table+sql,args)
            if user is not None:
                db.execute('DELETE FROM alias_evidence WHERE guild=? AND witness=?'+(' AND channel=?' if channel is not None else ''),[str(guild),str(user)]+([str(channel)] if channel is not None else []))
