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


def address_forms(name,aliases=(),partial=True):
    forms={name,*aliases}
    if partial:
        for candidate in list(forms):
            for suffix in ('봇','bot','이'):
                if candidate.lower().endswith(suffix) and len(candidate)-len(suffix)>=2:forms.add(candidate[:-len(suffix)])
            stem=re.sub(r'(?:[A-Za-z]+\d*|\d+)$','',candidate)
            if len(stem)>=2 and re.search('[가-힣]',stem):forms.add(stem)
    return forms


def name_candidate(text,name,aliases=(),partial=True):
    """A candidate only. Semantic addressee assessment still decides participation."""
    text=re.sub(r'```[\s\S]*?```|`[^`\n]*`|https?://\S+|["“][^"”]*["”]|\'[^\'\n]*\'', '',text)
    forms=address_forms(name,aliases,partial)
    return bool(re.search(r'(?<![가-힣A-Za-z0-9_])(?:'+ '|'.join(re.escape(n) for n in sorted(forms,key=len,reverse=True))+
                          r')(?:아|야|님)?(?=$|[\s,!.?~…:])',text,re.I))
