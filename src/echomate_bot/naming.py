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


def name_address(text,name,aliases=(),partial=True,other_names=()):
    """Deterministic address evidence, separate from semantic speech intention.

    Only registered bounded forms; never fuzzy spelling. Quoted/code/link text
    cannot grant an invitation. Bare collisions need semantic disambiguation.
    """
    from .routing import prose
    clean=prose(text).strip()
    forms=address_forms(name,aliases,partial)
    pattern=r'(?<![가-힣A-Za-z0-9_])(?P<name>'+'|'.join(re.escape(n) for n in sorted(forms,key=len,reverse=True))+r')'
    match=re.search(pattern+r'(?P<call>아|야|님)?(?=$|[\s,!.?~…:])',clean,re.I)
    if not match:return 'none'
    if any(match['name'].casefold() in {n.casefold() for n in address_forms(other)} for other in other_names):return 'ambiguous'
    before=clean[:match.start()].strip();after=clean[match.end():].lstrip(' ,!.?~…:')
    # Korean indirect speech reports a past call; the registered spelling alone
    # does not turn that quoted speech act into a fresh invitation.
    if re.search(r'(?:냐고|라고|다고|자고)\s*(?:물|말|전|했|하더|부르)',after):return 'ambiguous'
    if re.search(r'<@!?\d+>|너\s*말고|봇\s*말고|(?:저|그|다른)\s*사람(?:한테|에게)',after):return 'ambiguous'
    if not before:
        if not after or match['call'] in ('아','야'):return 'direct'
        # A noun-headed third-person statement remains a semantic candidate.
        if re.match(r'(?:얘기|이야기|이름|라는|라고|때문|관련|말고|대신|아닌)',after):return 'ambiguous'
        return 'direct' if re.search(r'(?:해|하라|해라|줘|세요|십시오)[.!?~ ]*$',after) else 'ambiguous'
    if not after and re.search(r'(?:해|하라|줘|와|봐|니|냐|어|야)\s*[,!.?~…]*$',before):return 'direct'
    return 'ambiguous'
