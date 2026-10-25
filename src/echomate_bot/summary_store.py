"""Source-indexed multi-turn digests, isolated by guild/channel and consent."""
import hashlib
import json
import secrets
from .settings import positive_id

SCHEMA='''
CREATE TABLE IF NOT EXISTS dialogue_summaries(id TEXT PRIMARY KEY,guild TEXT,channel TEXT,conversation TEXT,body TEXT,created REAL,updated REAL,expires REAL,fingerprint TEXT,UNIQUE(guild,channel,conversation));
CREATE TABLE IF NOT EXISTS summary_participants(id TEXT REFERENCES dialogue_summaries(id) ON DELETE CASCADE,guild TEXT,user TEXT,version INTEGER,PRIMARY KEY(id,user));
CREATE TABLE IF NOT EXISTS summary_sources(id TEXT REFERENCES dialogue_summaries(id) ON DELETE CASCADE,guild TEXT,source TEXT,PRIMARY KEY(id,source));
CREATE INDEX IF NOT EXISTS digest_subject ON summary_participants(guild,user);
CREATE INDEX IF NOT EXISTS digest_source ON summary_sources(guild,source);
CREATE TABLE IF NOT EXISTS summary_tombstones(guild TEXT,source TEXT,PRIMARY KEY(guild,source));
'''

class SummaryStore:
    def digest_consent(self,guild,participants):
        with self.db() as db:
            result={}
            for user in participants:
                r=db.execute("SELECT version,at FROM consent_choices WHERE guild=? AND user=? AND category='summaries' AND enabled=1",(str(guild),str(user))).fetchone()
                if not r:return None
                result[str(user)]=dict(version=r[0],at=r[1])
            return result
    def save_digest(self,guild,channel,conversation,body,turns,versions):
        from .companion_store import safe_subject_text
        positive_id(guild);positive_id(channel)
        if set(map(str,versions or {}))!={t.author_id for t in turns if not t.is_bot}:return None
        if not versions or not body.get('items') or any(not safe_subject_text(x['text']) for x in body['items']):return None
        source_ids={t.message_id for t in turns};now=self.clock();key=secrets.token_hex(12)
        fingerprint=hashlib.sha256(json.dumps([(t.message_id,t.content) for t in turns],ensure_ascii=False).encode()).hexdigest()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            for user,v in versions.items():
                r=db.execute("SELECT version,at FROM consent_choices WHERE guild=? AND user=? AND category='summaries' AND enabled=1",(str(guild),str(user))).fetchone()
                if not r or r[0]!=v['version'] or r[1]!=v['at']:return None
                times=[t.timestamp.timestamp() for t in turns if not t.is_bot and t.author_id==str(user)]
                if not times or min(times)<r[1]:return None
                cutoff=db.execute("SELECT MAX(at) FROM memory_cutoffs WHERE guild=? AND user IN (?, '*')",(str(guild),str(user))).fetchone()[0]
                if cutoff and min(times)<=cutoff:return None
            if any(db.execute('SELECT 1 FROM tombstones WHERE guild=? AND source=?',(str(guild),sid)).fetchone() for sid in source_ids):return None
            if any(db.execute('SELECT 1 FROM summary_tombstones WHERE guild=? AND source=?',(str(guild),sid)).fetchone() for sid in source_ids):return None
            old=db.execute('SELECT id FROM dialogue_summaries WHERE guild=? AND channel=? AND conversation=?',(str(guild),str(channel),conversation)).fetchone()
            if old:db.execute('DELETE FROM dialogue_summaries WHERE id=?',(old[0],))
            if db.execute('SELECT COUNT(*) FROM dialogue_summaries').fetchone()[0]>=2000:return None
            db.execute('INSERT INTO dialogue_summaries VALUES(?,?,?,?,?,?,?,?,?)',(key,str(guild),str(channel),conversation,json.dumps(body,ensure_ascii=False),now,now,now+30*86400,fingerprint))
            db.executemany('INSERT INTO summary_participants VALUES(?,?,?,?)',[(key,str(guild),str(u),v['version']) for u,v in versions.items()])
            db.executemany('INSERT INTO summary_sources VALUES(?,?,?)',[(key,str(guild),sid) for sid in source_ids])
        return key
    def digests(self,guild,user,channel=None,*,include_expired=False):
        positive_id(guild);positive_id(user)
        sql='SELECT d.* FROM dialogue_summaries d JOIN summary_participants p ON d.id=p.id WHERE d.guild=? AND p.user=?';args=[str(guild),str(user)]
        if channel is not None:sql+=' AND d.channel=?';args.append(str(channel))
        if not include_expired:sql+=' AND d.expires>?';args.append(self.clock())
        with self.db() as db:
            rows=[dict(r) for r in db.execute(sql+' ORDER BY d.updated DESC LIMIT 50',args)]
            for row in rows:
                try:row['body']=json.loads(row['body'])
                except (ValueError,TypeError):row['body']=dict(items=[]);row['damaged']=True
                if not isinstance(row['body'],dict) or not isinstance(row['body'].get('items'),list) or any(not isinstance(i,dict) or not all(isinstance(i.get(k),str) for k in ('kind','text','source')) for i in row['body']['items']):row['body']=dict(items=[]);row['damaged']=True
                row['sources']=[r[0] for r in db.execute('SELECT source FROM summary_sources WHERE id=?',(row['id'],))]
                row['participants']=[r[0] for r in db.execute('SELECT user FROM summary_participants WHERE id=?',(row['id'],))]
                row['consent_versions']={r[0]:r[1] for r in db.execute('SELECT user,version FROM summary_participants WHERE id=?',(row['id'],))}
                # A participant's withdrawal suspends automatic/shared retrieval.
                row['usable']=all(db.execute("SELECT 1 FROM consent_choices c JOIN summary_participants p ON p.guild=c.guild AND p.user=c.user WHERE p.id=? AND c.guild=? AND c.user=? AND c.category='summaries' AND c.enabled=1 AND c.version=p.version",(row['id'],str(guild),u)).fetchone() for u in row['participants'])
                if row.get('damaged'):row['usable']=False
        return rows
    def delete_digest(self,guild,key):
        with self.db() as db:
            # Keep source tombstones: a queued summary must not restore deletion.
            db.execute('INSERT OR IGNORE INTO summary_tombstones SELECT guild,source FROM summary_sources WHERE guild=? AND id=?',(str(guild),key))
            db.execute('DELETE FROM dialogue_summaries WHERE guild=? AND id=?',(str(guild),key))
    def has_digest(self,guild,channel,user,key):
        with self.db() as db:return db.execute('SELECT 1 FROM dialogue_summaries d JOIN summary_participants p ON d.id=p.id WHERE d.id=? AND d.guild=? AND d.channel=? AND p.user=? AND d.expires>?',(key,str(guild),str(channel),str(user),self.clock())).fetchone() is not None
    def clear_digests(self,guild,user=None):
        with self.db() as db:
            ids=[r[0] for r in db.execute('SELECT id FROM dialogue_summaries WHERE guild=?' if user is None else 'SELECT id FROM summary_participants WHERE guild=? AND user=?',(str(guild),) if user is None else (str(guild),str(user)))]
            for key in ids:
                db.execute('INSERT OR IGNORE INTO summary_tombstones SELECT guild,source FROM summary_sources WHERE id=?',(key,))
                db.execute('DELETE FROM dialogue_summaries WHERE id=?',(key,))
