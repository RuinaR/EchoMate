"""Server-scoped, explicit per-subject consent. Never an owner override."""
import json
import re
from .settings import positive_id

CATEGORIES=('relationships','memory','summaries')
SCHEMA='''
CREATE TABLE IF NOT EXISTS consent_choices(guild TEXT,user TEXT,category TEXT,enabled INTEGER,version INTEGER DEFAULT 1,at REAL,PRIMARY KEY(guild,user,category));
CREATE TABLE IF NOT EXISTS conversation_summaries(guild TEXT,user TEXT,channel TEXT,source TEXT,conversation TEXT,summary TEXT,participants TEXT,created REAL,expires REAL,PRIMARY KEY(guild,source));
'''

class PrivacyStore:
    def guild_ids(self):
        with self.db() as db:return [int(r[0]) for r in db.execute('SELECT guild FROM relationships UNION SELECT guild FROM memories UNION SELECT guild FROM reminders UNION SELECT guild FROM member_aliases UNION SELECT guild FROM consent_choices UNION SELECT guild FROM conversation_summaries')]
    def consent_users(self,guild):
        with self.db() as db:return [r[0] for r in db.execute('SELECT user FROM consent_choices WHERE guild=?',(str(guild),))]
    def consenting_users(self,guild,category):
        with self.db() as db:return {int(r[0]) for r in db.execute('SELECT user FROM consent_choices WHERE guild=? AND category=? AND enabled=1',(str(guild),category))}
    def consent(self,guild,user):
        result={k:False for k in CATEGORIES}
        with self.db() as db:
            for r in db.execute('SELECT category,enabled FROM consent_choices WHERE guild=? AND user=?',(str(guild),str(user))):
                if r[0] in result:result[r[0]]=bool(r[1])
        return result

    def set_consent(self,guild,actor,category,enabled,*,subject=None):
        positive_id(guild);positive_id(actor)
        if subject is not None and (type(subject) is not int or subject!=actor):raise PermissionError('Self consent only')
        if category not in CATEGORIES or type(enabled) is not bool:raise ValueError('Invalid consent')
        with self.db() as db:
            db.execute('INSERT INTO consent_choices VALUES(?,?,?,?,1,?) ON CONFLICT(guild,user,category) DO UPDATE SET enabled=excluded.enabled,version=consent_choices.version+1,at=excluded.at',(str(guild),str(actor),category,int(enabled),self.clock()))
            # Historic opt-out flags are not a substitute for category choices.
            if enabled:
                db.execute('DELETE FROM optouts WHERE guild=? AND user=?',(str(guild),str(actor)))
                if category=='memory':db.execute('DELETE FROM memory_optouts WHERE guild=? AND user=?',(str(guild),str(actor)))

    def consent_version(self,guild,user,category):
        with self.db() as db:
            r=db.execute('SELECT version FROM consent_choices WHERE guild=? AND user=? AND category=? AND enabled=1',(str(guild),str(user),category)).fetchone()
            return r[0] if r else None

    def data_counts(self,guild,user):
        with self.db() as db:
            return {key:db.execute('SELECT COUNT(*) FROM '+table+' WHERE guild=? AND user=?',(str(guild),str(user))).fetchone()[0]
                    for key,table in (('relationships','relationships'),('memory','memories'),('summaries','conversation_summaries'))}

    def delete_personal(self,guild,actor,category):
        if category not in CATEGORIES:raise ValueError('Invalid category')
        self.set_consent(guild,actor,category,False)
        with self.db() as db:
            tables={'relationships':('relationships','relationship_events','member_aliases','alias_evidence'),'memory':('memories',),'summaries':('conversation_summaries',)}[category]
            for table in tables:db.execute('DELETE FROM '+table+' WHERE guild=? AND user=?',(str(guild),str(actor)))
            if category=='relationships':db.execute('DELETE FROM alias_evidence WHERE guild=? AND witness=?',(str(guild),str(actor)))
            # Prevent pending work from recreating deleted personal records.
            db.execute('INSERT INTO memory_cutoffs VALUES(?,?,?) ON CONFLICT(guild,user) DO UPDATE SET at=excluded.at',(str(guild),str(actor),self.clock()))

    def save_summary(self,event,text,version):
        from .companion_store import safe_subject_text
        if not safe_subject_text(text) or len(text)<20:return False
        if not re.search(r'나는|난\s|저는|내\s|내가',text) or re.search(r'친구|걔|그\s*사람|다른\s*사람',text):return False
        # Extractive digest: retain a bounded personal excerpt, no invented facts,
        # no messages authored by other group participants, no whole transcripts.
        excerpt=re.split(r'(?<=[.!?])\s+|\n',text)[0][:160]
        with self.db() as db:
            r=db.execute("SELECT version,at FROM consent_choices WHERE guild=? AND user=? AND category='summaries' AND enabled=1",(str(event.guild),str(event.author))).fetchone()
            cutoff=db.execute("SELECT MAX(at) FROM memory_cutoffs WHERE guild=? AND user IN (?, '*')",(str(event.guild),str(event.author))).fetchone()[0]
            if not r or r[0]!=version or event.timestamp.timestamp()<r[1] or cutoff and event.timestamp.timestamp()<=cutoff:return False
            if db.execute('SELECT 1 FROM tombstones WHERE guild=? AND source=?',(str(event.guild),str(event.id))).fetchone():return False
            if db.execute('SELECT COUNT(*) FROM conversation_summaries').fetchone()[0]>=5000:return False
            db.execute('INSERT OR IGNORE INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?,?)',(str(event.guild),str(event.author),str(event.channel),str(event.id),event.conversation_id or '',excerpt,json.dumps([str(event.author)]),self.clock(),self.clock()+30*86400))
        return True

    def summaries(self,guild,user,channel=None):
        sql='SELECT * FROM conversation_summaries WHERE guild=? AND user=? AND expires>?';args=[str(guild),str(user),self.clock()]
        if channel is not None:sql+=' AND channel=?';args.append(str(channel))
        with self.db() as db:return [dict(r) for r in db.execute(sql+' ORDER BY created DESC LIMIT 30',args)]
