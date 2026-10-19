"""Deterministic, single Unicode reaction requests; model output grants no API rights."""
import re
import unicodedata
from .routing import prose

def requested_reaction(text):
    text=prose(text)
    if re.search(r'<a?:\w+:\d+>',text):return None
    if not reaction_intent(text):return None
    import regex
    emoji=next((g for g in regex.findall(r'\X',text) if len(g)<=16 and regex.search(r'\p{Extended_Pictographic}|\p{Regional_Indicator}',g) and all(unicodedata.category(c) in ('So','Sk','Mn','Cf') for c in g)),None)
    if not emoji:
        for expression,value in (('하트','❤️'),('축하','🎉'),('좋아요','👍'),('엄지','👍'),('웃는','😄'),('웃음','😄')):
            if expression in text:emoji=value;break
    return (emoji,reaction_target_hint(text)!='current') if emoji else None

def reaction_intent(text):
    text=prose(text)
    return bool(re.search(r'(?:달아|눌러|붙여|반응해|표시\s*해|올려)\s*(?:줘|주세요|주라|줄래)?[.!?~\s]*$',text) and
                re.search(r'이모지|반응|좋아요|하트|엄지|축하|[\U0001f000-\U0001ffff❤]',text))

def reaction_target_hint(text):
    if re.search(r'답장한|이전\s*메시지',text):return 'reply'
    if re.search(r'내가.*(?:방금|쓴\s*글)',text):return 'own_previous'
    if re.search(r'위[에의]?\s*(?:메시지|글)|방금\s*(?:그\s*)?(?:말|메시지|글)',text):return 'previous'
    if re.search(r'아까|저\s*메시지',text):return 'ambiguous'
    return 'current'
