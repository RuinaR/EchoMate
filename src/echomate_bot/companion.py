"""Deterministic private requests; successful acknowledgement follows DB commit."""
import re
from .companion_store import safe_subject_text
from .temporal import parse_when,duration,display_time


def request_kind(text):
    from .routing import prose
    text=prose(text)
    timed=bool(re.search(r'(?:\d+|한|두|세|네|반)\s*(?:분|시간|일)\s*(?:후|뒤|있다가|더|전)|\d+\s*시(?!간)',text))
    if re.search(r'알림|불러\s*줘|깨워\s*줘',text) or timed and re.search(r'알려\s*줘|라고\s*해\s*줘|늦춰|미뤄|취소',text):return 'reminder'
    if re.search(r'(?:내|나의).*(?:기억|정보).*(?:삭제|지워|잊어|목록|보여)|기억해\s*줘',text):return 'memory'
    return None


def handle_request(store,event,cfg,bot_id):
    text=re.sub(r'<@!?'+str(bot_id)+r'>','',event.content).strip()
    kind=request_kind(text)
    if not kind:return None
    tz=cfg['guilds'].get(str(event.guild),{}).get('timezone','Asia/Seoul')
    if kind=='memory':
        if re.search(r'삭제|지워|잊어',text):
            store.forget_memories(event.guild,event.author)
            return '이 서버에서 네 기억을 지웠어. 다시 자동 저장하지 않도록 막아 뒀어.'
        if re.search(r'목록|보여',text):
            rows=store.memories(event.guild,event.author,event.channel)
            return '이 채널에서 사용할 수 있는 네 기억이 없어.' if not rows else '\n'.join(r['summary'] for r in rows[:5])
        key=store.extract(event,tz,text=text,policy=cfg)
        return '네가 직접 말한 내용을 이 채널에서 참고하도록 저장했어.' if key else '민감한 정보나 다른 사람의 정보는 저장하지 않아. 네가 기억시키려는 내용을 명확하게 알려 줘.'
    if not cfg.get('reminders_enabled',True):return '지금은 알림 예약 기능이 꺼져 있어.'
    if re.search(r'<@|@everyone|@here',text) or re.search(r'(?:친구|다른\s*사람|걔).*(?:불러|깨워|알려)',text):return '알림은 부탁한 본인에게만 예약할 수 있어.'
    rows=[r for r in store.reminders(event.guild,event.author,active=True) if r['channel']==str(event.channel)]
    if re.search(r'뭐\s*있|목록|조회|보여',text):
        return '이 채널에 예약한 알림은 없어.' if not rows else '\n'.join(f"{r['reminder_id'][:8]} · {display_time(r['due_at'],tz)} · {r['text'][:70]}" for r in rows[:10])
    cancel=bool(re.search(r'취소|지워|삭제',text));postpone=bool(re.search(r'늦춰|미뤄|연기|변경',text))
    if cancel or postpone:
        if (m:=re.search(r'\b([a-f0-9]{8,24})\b',text)):rows=[r for r in rows if r['reminder_id'].startswith(m[1])]
        if '내일' in text and cancel:
            when=parse_when(text,event.timestamp,tz)
            if when.start:rows=[r for r in rows if when.start.timestamp()<=r['due_at']<when.end.timestamp()]
        elif cancel and (delta:=duration(text)):
            rows=[r for r in rows if abs((r['due_at']-r['created_at'])-delta.total_seconds())<90]
        if not rows:return '일치하는 예약이 없어. 알림 목록을 확인해 줘.'
        if len(rows)>1 and not(cancel and re.search(r'모두|전부',text)):return '어느 알림인지 구분이 필요해. 알림 목록의 앞 8자리 번호도 알려 줘.'
        for row in rows:
            if cancel:store.change_reminder(event.guild,event.author,row['reminder_id'],cancel=True)
            else:
                delta=duration(text)
                when=parse_when(text,event.timestamp,tz,exact=True)
                due=row['due_at']+delta.total_seconds() if delta and re.search(r'더|늦춰',text) else when.start.timestamp() if when.start else None
                if due is None:return '변경할 날짜와 시각을 알려 줘.'
                store.change_reminder(event.guild,event.author,row['reminder_id'],due=due)
        return '예약을 취소했어.' if cancel else f'예약 시간을 변경했어. {display_time(due,tz)}에 알려줄게.'
    when=parse_when(text,event.timestamp,tz,exact=True)
    if not when.start:return when.reason
    if when.start.timestamp()<=store.clock():return '그 시각은 이미 지났어. 알림을 받을 날짜와 시각을 다시 알려 줘.'
    if not safe_subject_text(text):return '민감하거나 사적인 내용은 공개 채널 알림에 저장하지 않아. 개인정보 없는 짧은 내용으로 다시 부탁해 줘.'
    row=store.reserve_reminder(event,when.start.timestamp(),tz,text[:300])
    lead='좋아' if cfg['mood'] in ('기쁨','신남') else '응'
    return f"{lead}, {display_time(row['due_at'],tz)}에 이 채널에서 너를 부를게. (예약 {row['reminder_id'][:8]})"
