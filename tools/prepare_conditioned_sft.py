"""CPU tokenizer/target-mask audit, not a trainer or production prompt switch.

Reuses character instruction/card compiler and public feature formatting.
Synthetic source states only; never accesses a personal store or final corpus.
"""
from collections.abc import Mapping
from copy import deepcopy
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from conditioned_curriculum import validate


async def compile_case(case,key,characters,tokenizer):
    from echomate_bot.character_profiles import presets,SHARED_FIELDS,validate_profile
    from echomate_bot.character_card import empty_card,augment
    from echomate_bot.settings import DEFAULTS,validate as validate_settings
    from echomate_bot.character import instruction
    from echomate_bot.capabilities import model_facts,public_state
    alias={'gentle':'supportive','playful':'playful','analytical':'analytical','dry':'dry'}
    person=characters[key];profile=deepcopy(presets()[alias[key]])
    profile.update(values=person['values'],habits=person['habit'],card=empty_card())
    profile['card']['background']=person['background'];validate_profile(profile)
    cfg=deepcopy(DEFAULTS);cfg['character_profile']=profile
    cfg.update({k:profile[k] for k in SHARED_FIELDS})
    cfg.update(enabled=True,guilds={'2':dict(enabled=True,channels={'3':dict(mode='mention',inherit=False)},threads={})})
    state=dict(case['evidence']);history=state.pop('previous',[])
    cfg['mood']=state.get('mood','평온');cfg['memory_auto']=state.get('memory')=='on'
    close=state.get('relationship')=='consented_close';memory_consent=state.get('consent') is True
    validate_settings(cfg)
    cfg['_familiarity']=80 if close else None
    consents=dict(memory=memory_consent,relationships=close,summaries=False)
    fixture=SimpleNamespace(settings=SimpleNamespace(get=lambda:deepcopy(cfg)),
        companion=SimpleNamespace(error=state.get('storage_available',True) is False,consent=lambda g,u:dict(consents)),
        backend=SimpleNamespace(failed=False,model=True,pending=0),note=lambda code:None)
    event=SimpleNamespace(guild=2,channel=3,author=4,parent=None)
    view=await public_state(fixture,event,dict(view=True,send=True,react=True))
    facts=model_facts(view)
    facts['content']='[합성 fixture 조건; 실제 실행 결과 아님] '+facts['content']
    messages=[dict(role='system',content=instruction(cfg)),facts,
        dict(role='user',content='[합성 fixture의 확인 근거; 현재 발언/실행 요청 아님] '+json.dumps(state,ensure_ascii=False)),
        *history,dict(role='user',content=case['user'])]
    return augment(messages,profile,80 if close else None,tokenizer,current_text=case['user'])[0]


def ids(tokenizer,messages,generation):
    encoded=tokenizer.apply_chat_template(messages,add_generation_prompt=generation,enable_thinking=False,tokenize=True,return_dict=True)
    value=encoded['input_ids'] if isinstance(encoded,Mapping) else encoded
    if not isinstance(value,list) or not all(type(n) is int for n in value):raise ValueError('Plain token IDs required')
    return value


def mask_target(prompt,full):
    if full[:len(prompt)]!=prompt or len(full)<=len(prompt):raise ValueError('Template prefix mismatch; no guessed mask')
    return [-100]*len(prompt)+full[len(prompt):]


def supervised_pair(tokenizer,messages,target):
    """Keep the exact inference prefix, derive the terminator from the template.

    Gemma's non-thinking generation prefix includes an empty thought channel;
    ordinary assistant rendering omits it. Never mask by a guessed offset.
    """
    if any(t and t in target for t in tokenizer.all_special_tokens):raise ValueError('Reserved control token in target')
    marker='ECHOMATE_TARGET_BOUNDARY_7f6e'
    if any(marker in m.get('content','') for m in messages):raise ValueError('Sentinel collision')
    def render(ms,generation):return tokenizer.apply_chat_template(ms,add_generation_prompt=generation,
        enable_thinking=False,tokenize=False)
    probe=render([*messages,dict(role='assistant',content=marker)],False)
    if probe.count(marker)!=1:raise ValueError('Unsupported assistant rendering')
    plain_prefix,suffix=probe.split(marker)
    expected=render([*messages,dict(role='assistant',content=target)],False)
    if not suffix or expected!=plain_prefix+target+suffix:raise ValueError('Template changed target content')
    inference_prefix=render(messages,True)
    if not inference_prefix.startswith(plain_prefix):raise ValueError('Template changed preceding context')
    prompt=ids(tokenizer,messages,True)
    if tokenizer.encode(inference_prefix,add_special_tokens=False)!=prompt:raise ValueError('Prompt encoding mismatch')
    full=tokenizer.encode(inference_prefix+target+suffix,add_special_tokens=False)
    labels=mask_target(prompt,full)
    return prompt,full,labels


async def run(model,source,output):
    repo=Path(__file__).resolve().parents[1];root=Path(output).resolve()
    if not root.is_relative_to(repo/'local_data'):raise ValueError('Fresh private output required')
    raw=Path(source).read_bytes();data=json.loads(raw);summary=validate(data);root.mkdir(parents=True,exist_ok=False)
    os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
    from echomate_bot.model_registry import ModelValidator
    from echomate_bot.processes import model_memory_budget
    entry=ModelValidator().validate(model)
    if not entry.compatible:raise ValueError('Existing validated Gemma tokenizer required')
    model_memory_budget(128*1024**2)
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(entry.path,local_files_only=True,trust_remote_code=False)
    records=[]
    for case in data['scenarios']:
        for key in data['characters']:
            messages=await compile_case(case,key,data['characters'],tokenizer)
            prompt,full,labels=supervised_pair(tokenizer,messages,case['responses'][key])
            records.append(dict(id=case['id']+'-'+key,split=case['split'],group=case['source_group'],
                input_ids=full,labels=labels,prompt_tokens=len(prompt),target_tokens=len(full)-len(prompt)))
    from echomate_bot.telemetry import distribution
    summary.update(status='TOKENIZER_MASK_PASS_NOT_TRAINING',source_sha256=hashlib.sha256(raw).hexdigest(),
        prompt_tokens=distribution([r['prompt_tokens'] for r in records]),target_tokens=distribution([r['target_tokens'] for r in records]),
        total_tokens=distribution([len(r['input_ids']) for r in records]),
        max_total_tokens=max(len(r['input_ids']) for r in records),empty_target_records=sum(r['target_tokens']<=0 for r in records),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        tokenizer_artifact_hashes={name:hashlib.sha256((Path(entry.path)/name).read_bytes()).hexdigest()
            for name in ('config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja')},
        largest_dense_logits_bf16_bytes=max(len(r['input_ids']) for r in records)*tokenizer.vocab_size*2,
        largest_dense_logits_fp32_bytes=max(len(r['input_ids']) for r in records)*tokenizer.vocab_size*4,
        caveat='Gold synthetic states, existing generation compilers, CPU tokenization only. Dense logits shape sizes are not peak memory.')
    for split in ('train','validation'):
        payload=''.join(json.dumps(r)+'\n' for r in records if r['split']==split).encode()
        (root/(split+'.jsonl')).write_bytes(payload);summary[split+'_sha256']=hashlib.sha256(payload).hexdigest()
    (root/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--source',default='tests/fixtures/conditioned_curriculum.json');p.add_argument('--output',required=True);a=p.parse_args()
    async def isolated():
        # Windows Proactor creates a local socketpair before entering this body.
        # All application/tokenizer work then runs with external connects blocked.
        with patch('socket.socket.connect',side_effect=AssertionError('No network')),patch('socket.getaddrinfo',side_effect=AssertionError('No network')):
            await run(a.model,a.source,a.output)
    asyncio.run(isolated())
