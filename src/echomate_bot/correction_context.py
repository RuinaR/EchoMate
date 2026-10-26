"""A provenance view, not a fact extractor or a DB correction operation."""
import re


def correction_requested(text):
    # Quoted/conditional corrections are not current user corrections.
    value=re.sub(r'"[^"\n]*"|“[^”\n]*”|`[^`\n]*`','',text)
    if re.search(r'만약|라면|다면',value):return False
    return bool(re.search(r'정정할게(?:요)?(?:[.!?\s]|$)|바로잡을게|말한\s*적(?:이)?\s*없|말하지\s*않았|'
                          r'(?:방금|아까|네가|그거|그건).{0,50}(?:틀렸|사실|아니라)|'
                          r'(?:어제|내일|라고|다고).{0,25}아니라|(?:라고|다고).{0,35}사실|가정이었.{0,25}실제',value))


def correction_view(messages,current,*,local_history=False):
    """Preserve roles, user sources and stored history; down-rank model claims.

    Only known LOCAL history may supply past correction markers. Runtime
    excerpts/summary metadata are never treated as new user corrections.
    """
    boundary=len(messages) if correction_requested(current) else -1
    if local_history:
        boundary=max([boundary,*[i for i,m in enumerate(messages)
                     if m.get('role')=='user' and correction_requested(m.get('content',''))]])
    count=0;result=[]
    for i,m in enumerate(messages):
        row=dict(m)
        if i<boundary and m.get('role')=='assistant':
            row['content']='[정정 전 모델 응답: 사실·조회·실행의 근거로 사용하지 않음]'
            count+=1
        result.append(row)
    return result,count
