"""Conservative Korean civil time parsing; no LLM arithmetic or guessed hours."""
from dataclasses import dataclass
from datetime import datetime,date,time,timedelta,timezone
import calendar
import re
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

UTC=timezone.utc


def zone(name):
    try:return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        # Modern Korean dates have no DST. Other zones require IANA tzdata.
        if name=='Asia/Seoul':return timezone(timedelta(hours=9),name)
        if name in ('UTC','Etc/UTC'):return UTC
        raise ValueError('Install tzdata for this timezone') from None


@dataclass(frozen=True)
class When:
    start:datetime|None=None
    end:datetime|None=None
    precision:str='unknown'
    reason:str='날짜와 시간을 조금 더 정확히 알려 줘.'


def duration(text):
    match=re.search(r'((?:(?:\d+|한|두|세|네|반)\s*(?:분|시간|일)\s*)+)(?:후|뒤|있다가|더|전)',text)
    if not match:return None
    seconds=0
    for number,unit in re.findall(r'(\d+|한|두|세|네|반)\s*(분|시간|일)',match[1]):
        value={'한':1,'두':2,'세':3,'네':4,'반':.5}.get(number)
        if value is None:value=int(number)
        seconds+=value*{'분':60,'시간':3600,'일':86400}[unit]
    return timedelta(seconds=seconds) if 0<seconds<=366*86400 else None


def parse_when(text,observed,timezone_name='Asia/Seoul',*,exact=False):
    if observed.tzinfo is None:raise ValueError('Timezone-aware source timestamp required')
    tz=zone(timezone_name);local=observed.astimezone(tz);day=local.date();has_date=False
    relative=duration(text)
    if len(re.findall(r'(?:분|시간|일)\s*(?:후|뒤|있다가|더|전)',text))>1:return When(reason='알림 하나에 날짜와 시각을 하나씩 정해 줘.')
    before=bool(re.search(r'(?:분|시간)\s*전에',text))
    has_absolute=bool(re.search(r'오늘|내일|모레|이번\s*주|다음\s*주|다음\s*달|\d+\s*월|\d{4}-\d\d-\d\d|\d+\s*일\s*(?:후|뒤).*\d+\s*시',text))
    if relative and not before and not has_absolute:
        start=(observed.astimezone(UTC)+relative)
        return When(start,start,'minute','')
    if re.search(r'쯤|주말|저녁에|아침에|나중에|언젠가',text):return When()
    try:
        if (m:=re.search(r'(\d{4})-(\d{2})-(\d{2})',text)):
            day=date(*map(int,m.groups()));has_date=True
        elif (m:=re.search(r'다음\s*달\s*(\d{1,2})일',text)):
            year=day.year+(day.month==12);month=day.month%12+1;day=date(year,month,int(m[1]));has_date=True
        elif (m:=re.search(r'(\d{1,2})월\s*(\d{1,2})일',text)):
            day=date(day.year,int(m[1]),int(m[2]));has_date=True
        elif (m:=re.search(r'(이번|다음)\s*주\s*([월화수목금토일])요일',text)):
            offset='월화수목금토일'.index(m[2])-day.weekday()+(7 if m[1]=='다음' else 0)
            day+=timedelta(days=offset);has_date=True
        elif '이번 주' in text or '이번주' in text:
            day+=timedelta(days=6-day.weekday());has_date=True
        elif '모레' in text:day+=timedelta(days=2);has_date=True
        elif '내일' in text:day+=timedelta(days=1);has_date=True
        elif '오늘' in text:has_date=True
        elif (m:=re.search(r'(\d+)\s*일\s*(?:후|뒤)',text)):
            day+=timedelta(days=int(m[1]));has_date=True
        elif (m:=re.search(r'(\d{1,2})월\s*말',text)):
            month=int(m[1]);day=date(day.year,month,calendar.monthrange(day.year,month)[1]);has_date=True
    except ValueError:return When(reason='존재하는 날짜인지 확인해 줘.')
    clock_pattern=r'(?:(오전|오후|저녁|아침)\s*)?(\d{1,2})\s*시(?!간)(?:\s*(\d{1,2})\s*분)?'
    if len(re.findall(clock_pattern,text))>1:return When(reason='알림 하나에 날짜와 시각을 하나씩 정해 줘.')
    clock=re.search(clock_pattern,text)
    if clock:
        hour=int(clock[2]);minute=int(clock[3] or 0)
        if clock[1]:
            if not 1<=hour<=12:return When(reason='시각을 다시 확인해 줘.')
            hour=hour%12+(12 if clock[1] in ('오후','저녁') else 0)
        elif 1<=hour<=12:return When(reason='오전인지 오후인지도 알려 줘.')
        if hour>23 or minute>59:return When(reason='시각을 다시 확인해 줘.')
        naive=datetime.combine(day,time(hour,minute));start=naive.replace(tzinfo=tz)
        # Reject nonexistent and repeated civil times rather than selecting a fold.
        if start.astimezone(UTC).astimezone(tz).replace(tzinfo=None)!=naive or start.utcoffset()!=start.replace(fold=1).utcoffset():
            return When(reason='시간대 전환과 겹치는 시간이야. UTC 시각을 확인해 줘.')
        start=start.astimezone(UTC)
        if before:
            if not relative:return When()
            start-=relative
        return When(start,start,'minute','')
    if exact:return When(reason='알림을 보낼 날짜와 오전·오후 시각을 알려 줘.')
    if has_date:
        start=datetime.combine(day,time.min,tz).astimezone(UTC)
        end=datetime.combine(day+timedelta(days=1),time.min,tz).astimezone(UTC)
        return When(start,end,'date','')
    return When()


def display_time(timestamp,name='Asia/Seoul'):
    return datetime.fromtimestamp(timestamp,UTC).astimezone(zone(name)).strftime('%Y-%m-%d %H:%M')


def editor_timestamp(value,name):
    if not value.strip():return None
    try:naive=datetime.strptime(value.strip(),'%Y-%m-%d %H:%M')
    except ValueError:raise ValueError('Use YYYY-MM-DD HH:MM') from None
    local=naive.replace(tzinfo=zone(name))
    if local.astimezone(UTC).astimezone(zone(name)).replace(tzinfo=None)!=naive or local.utcoffset()!=local.replace(fold=1).utcoffset():raise ValueError('Ambiguous local timestamp')
    return local.timestamp()
