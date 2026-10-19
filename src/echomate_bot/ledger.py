"""At-most-once event ledger and observational statistics; no speech quota."""
from contextlib import contextmanager,closing
from datetime import datetime,timezone,timedelta
import sqlite3
import time
from .settings import private_path

class Ledger:
    def __init__(self,path,clock=time.time):
        self.path=private_path(path);self.clock=clock;self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS sent(event TEXT PRIMARY KEY,channel TEXT,day TEXT,at REAL,status TEXT,action TEXT DEFAULT \'legacy\')')
            if 'action' not in {r[1] for r in db.execute('PRAGMA table_info(sent)')}:db.execute("ALTER TABLE sent ADD COLUMN action TEXT DEFAULT 'legacy'")
    @contextmanager
    def db(self):
        with closing(sqlite3.connect(self.path,timeout=.5)) as db:
            with db:yield db
    def last(self,channel):
        with self.db() as db:row=db.execute('SELECT MAX(at) FROM sent WHERE channel=?',(str(channel),)).fetchone()
        return row[0] or 0
    def contains(self,event):
        with self.db() as db:return db.execute('SELECT 1 FROM sent WHERE event=?',(str(event.response_to or event.id),)).fetchone() is not None
    def block_reason(self,event,cooldown):
        if self.contains(event):return 'duplicate_request'
        if self.clock()-self.last(event.channel)<cooldown:return 'response_cooldown'
        return None
    def reserve(self,event,cooldown=0,*,action='TEXT'):
        if action not in ('TEXT','REACTION','TEXT_REACTION'):raise ValueError('Unsupported ledger action')
        now=self.clock();day=datetime.fromtimestamp(now,timezone.utc).date().isoformat()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            last=db.execute('SELECT MAX(at) FROM sent WHERE channel=?',(str(event.channel),)).fetchone()[0] or 0
            if now-last<cooldown:return False
            try:db.execute('INSERT INTO sent(event,channel,day,at,status,action) VALUES(?,?,?,?,?,?)',(str(event.response_to or event.id),str(event.channel),day,now,'reserved',action))
            except sqlite3.IntegrityError:return False
        return True
    def completed(self,event,status):
        if status not in ('sent','failed_or_uncertain'):raise ValueError('Unsupported delivery state')
        with self.db() as db:db.execute('UPDATE sent SET status=? WHERE event=?',(status,str(event.response_to or event.id)))
    def statistics(self):return self.read_statistics(self.path,self.clock())
    @staticmethod
    def read_statistics(path,now=None):
        now=time.time() if now is None else now
        today=datetime.fromtimestamp(now,timezone(timedelta(hours=9))).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
        result=dict(responses_today=0,reactions_today=0,legacy_today=0,reserved=0,uncertain=0,total=0,successful=0)
        if not path.exists():return result
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.1)) as db:
            columns={r[1] for r in db.execute('PRAGMA table_info(sent)')}
            action='action' if 'action' in columns else "'legacy'"
            values=db.execute(f"SELECT COUNT(*),COALESCE(SUM(status='sent'),0),COALESCE(SUM(status='reserved'),0),COALESCE(SUM(status='failed_or_uncertain'),0),COALESCE(SUM(status='sent' AND at>=? AND {action} IN ('TEXT','TEXT_REACTION')),0),COALESCE(SUM(status='sent' AND at>=? AND {action} IN ('REACTION','TEXT_REACTION')),0),COALESCE(SUM(status='sent' AND at>=? AND {action}='legacy'),0) FROM sent",(today,today,today)).fetchone()
            result.update(zip(('total','successful','reserved','uncertain','responses_today','reactions_today','legacy_today'),values))
        return result
