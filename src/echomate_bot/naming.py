"""Guild-local display names and bounded Korean forms of address."""
import re
import unicodedata


def validate_name(value):
    if not isinstance(value,str) or value!=value.strip() or not 2<=len(value)<=32:
        raise ValueError('Name must be 2..32 characters')
    if any(unicodedata.category(c).startswith('C') or c in '<>@`\\"' for c in value):
        raise ValueError('Invalid name')
    return value


def guild_name(cfg,guild):
    return cfg['guilds'].get(str(guild),{}).get('name','EchoMate')


def name_candidate(text,name):
    """A candidate only. Semantic addressee assessment still decides participation."""
    # Names quoted as examples, code and URLs are not calls to the bot.
    text=re.sub(r'```[\s\S]*?```|`[^`\n]*`|https?://\S+|["“][^"”]*["”]|\'[^\'\n]*\'', '',text)
    forms={name}
    for suffix in ('봇','bot','이'):
        if name.lower().endswith(suffix) and len(name)-len(suffix)>=2:forms.add(name[:-len(suffix)])
    return bool(re.search(r'(?<![가-힣A-Za-z0-9_])(?:'+ '|'.join(re.escape(n) for n in sorted(forms,key=len,reverse=True))+
                          r')(?:아|야|님)?(?=$|[\s,!.?~…:])',text,re.I))
