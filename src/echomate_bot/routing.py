"""Prose isolation plus legacy grounded helpers for compatibility tests.

Production Runtime uses structured semantic speech-act/addressee inference;
these legacy punctuation/request shortcuts no longer grant participation.
"""
import re


def prose(text):
    return re.sub(r'```[\s\S]*?```|`[^`\n]*`|https?://\S+|["“][^"”]*["”]|[\'‘][^\'’\n]*[\'’]','',text)


def grounded_followup(turns,event):
    prior=[(i,t) for i,t in enumerate(turns[:-1]) if t.is_bot]
    if not prior:return False
    bot_index,bot=prior[-1]
    source=next((i for i,t in enumerate(turns[:bot_index]) if t.message_id==bot.reply_to and not t.is_bot and t.author_id==str(event.author)),None)
    if source is None:return False
    humans=[t for t in turns[source:] if not t.is_bot]
    if any(t.author_id!=str(event.author) for t in humans):return False
    text=prose(event.content)
    if re.search(r'<@!?\d+>|<@&|@everyone|@here',text):return False
    if re.search(r'\S+(?:한테|에게).*(?:질문|물어|묻)',text):return False
    if re.search(r'^[가-힣A-Za-z]{1,16}[아야][,\s]',text):return False
    if any(re.search(r'여기까지|그만\s*하자|대화\s*끝|이제\s*다른|다른\s*친구랑|너\s*말고|봇\s*말고',prose(t.content)) for t in humans):return False
    return bool(re.search(r'\?|알려\s*줘|설명해\s*줘|말해\s*줘|추천해\s*줘|확인해\s*줘|기억해\s*줘|불러\s*줘|깨워\s*줘|알림|늦춰|미뤄|숫자만|답만|하나만|얼마야|어때|뭐였지|어디였지',text))


def grounded_group_followup(turns,event,participants):
    """Only an explicitly joined group and a substantive link to the last reply."""
    if len(participants)<2 or event.author not in participants:return False
    bots=[t for t in turns[:-1] if t.is_bot]
    if not bots:return False
    if event.reply_to and not any(t.message_id==str(event.reply_to) for t in bots):return False
    source=next((t for t in turns if t.message_id==bots[-1].reply_to and not t.is_bot),None)
    if not source:return False
    text=prose(event.content)
    if re.search(r'<@|@everyone|@here|너\s*말고|봇\s*말고|우리끼리|다른\s*사람|\S+(?:한테|에게)|^[가-힣A-Za-z]{1,16}[아야][,\s]',text):return False
    if not re.search(r'\?|알려\s*줘|확인해\s*줘|뭐였지|어디였지|얼마야',text):return False
    from .context import terms
    generic={'그건','그게','이건','이게','설명','질문','답변','단어','문장','한문','자세','정확','계속','아까','이번','조금','더알','한번','오늘','최종','추천','계산','내용','지금','언제','누구','알려','말해','하나','숫자'}
    return bool((terms(text)-generic)&(terms(source.content+' '+bots[-1].content)-generic))
