"""Native-token selection for structured social evidence, never summary JSON."""
from copy import deepcopy
import json
from .social_evidence import trim_frame


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
    raise ValueError('Current social evidence and protected reply pairs exceed native context')
