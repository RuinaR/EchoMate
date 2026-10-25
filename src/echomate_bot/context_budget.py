"""Native-token selection for structured social evidence, never summary JSON."""
from copy import deepcopy
import json
from .social_evidence import trim_frame


def current_last(messages):
    """Preserve JSON values while placing the actual event after its history."""
    result=deepcopy(messages)
    if len(result)!=2:return result
    try:data=json.loads(result[1]['content'])
    except (ValueError,TypeError,KeyError):return result
    if isinstance(data,dict) and 'current' in data:
        current=data.pop('current');data['current']=current
        result[1]['content']=json.dumps(data,ensure_ascii=False)
    return result


def compact_minimum(data):
    """Reversible text references only after all permitted history trimming.

    Never reference a source with conflicting copies; retain the pending
    human text itself. Epoch/version authority remains in Runtime guards.
    """
    result=deepcopy(data);current=result['current'];identity=current.get('bot_identity',{})
    identity.pop('name_version',None);identity.pop('character_epoch',None)
    if 'id' in identity and identity['id']==result.get('bot_id'):identity.pop('id')
    current.get('roles',{}).pop('identity_actions_allowed',None)
    pending=(result.get('pending_human_exchange') or {}).get('source');groups={}
    for row in [r for f in result['frames'] for r in f['turns']]+list(result.get('surrounding',())):
        if row.get('id') is not None:groups.setdefault(row['id'],[]).append(row)
    for key,group in groups.items():
        if key==pending or len(group)<2 or not isinstance(group[0].get('text'),str):continue
        first=group[0]
        if not all(all(row.get(k)==first.get(k) for k in ('speaker','text','reply')) and
                   all(row[k]==first[k] for k in set(row)&set(first)) for row in group):continue
        for row in group[1:]:row['text_source']=key;del row['text']
    return result


async def fit_social(messages,limit,count):
    result=deepcopy(messages);tokens=await count(result);removed=0
    if tokens<=limit:return result,tokens,removed
    if len(result)!=2 or result[0].get('role')!='system' or result[1].get('role')!='user':
        raise ValueError('Native context exceeds budget')
    try:data=json.loads(result[1]['content'])
    except (ValueError,TypeError):raise ValueError('Native context exceeds budget') from None
    if not isinstance(data,dict) or not isinstance(data.get('current'),dict) or not isinstance(data.get('frames'),list):
        raise ValueError('Native context exceeds budget')
    # Keep every candidate index and membership; preserve original current,
    # pending human exchange, surrounding and requested/latest reply pairs.
    reply=data['current'].get('reply')
    for _ in range(32):
        frames=sorted(data['frames'],key=lambda f:-len(f.get('turns',())))
        if not any(trim_frame(frame,reply) for frame in frames):break
        removed+=1;data['older_context_omitted']=True
        result[1]['content']=json.dumps(data,ensure_ascii=False,separators=(',',':'))
        tokens=await count(result)
        if tokens<=limit:return result,tokens,removed
    # No subsequent source pruning is allowed: every text_source reference
    # must still resolve to the complete retained original in this request.
    result[1]['content']=json.dumps(compact_minimum(data),ensure_ascii=False,separators=(',',':'))
    tokens=await count(result)
    if tokens<=limit:return result,tokens,removed
    raise ValueError('Current social evidence and protected reply pairs exceed native context')
