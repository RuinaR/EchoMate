"""Deterministic, single Unicode reaction requests; model output grants no API rights."""
import re
import unicodedata
from .routing import prose

def requested_reaction(text):
    text=prose(text)
    if re.search(r'<a?:\w+:\d+>',text):return None
    if not re.search(r'(?:달아|눌러|붙여|반응해)\s*(?:줘|주세요)?[.!?~\s]*$',text):return None
    import regex
    emoji=next((g for g in regex.findall(r'\X',text) if len(g)<=16 and regex.search(r'\p{Extended_Pictographic}|\p{Regional_Indicator}',g) and all(unicodedata.category(c) in ('So','Sk','Mn','Cf') for c in g)),None)
    if not emoji:emoji='🎉' if '축하' in text and '이모지' in text else '👍' if '좋아요' in text else None
    return (emoji,bool(re.search(r'답장한|저\s*메시지|이전\s*메시지',text))) if emoji else None
