"""Grounded fast path for a single established interlocutor's clear request.

Not an autonomous-entry rule. Real bot reply provenance, speaker continuity,
explicit request language and absence of a different addressee are all required.
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
