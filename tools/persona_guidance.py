"""Evaluation-only contrastive persona decoding on one resident model.

No app/settings imports this module. Both branches keep the same upper policy,
current dialogue and runtime evidence. Neutralization removes character data,
not safety. Two cached forwards per token increase cost; never call it free.
"""
from contextlib import contextmanager
from copy import deepcopy
from functools import wraps
from unittest.mock import patch


def neutral_messages(messages,profile):
    from echomate_bot.character_profiles import compile_profile,DEFAULT_PROFILE
    original=compile_profile(profile)
    if not messages or messages[0]['role']!='system' or messages[0]['content'].count(original)!=1:
        raise ValueError('Exact character compiler boundary required')
    neutral=deepcopy(messages)
    neutral[0]['content']=neutral[0]['content'].replace(original,compile_profile(deepcopy(DEFAULT_PROFILE)),1)
    return neutral


@contextmanager
def guidance(backend,scale,records):
    if scale not in (1.0,1.5):raise ValueError('Sealed scales only')
    original=backend._generate
    def generate(messages,images,budget,weight,stop,choices=None,persona=None):
        if persona is None:return original(messages,images,budget,weight,stop,choices,persona)
        if images or choices:raise ValueError('Only free text persona generation')
        # Called by the existing single GPU Worker, not a second executor/model.
        model=backend.model;forward=model.forward;sample=model.generate;forwards=[]
        negative=neutral_messages(messages,persona[0]) if scale!=1 else None
        @wraps(forward)
        def counted(*args,**kwargs):
            forwards.append(1)
            return forward(*args,**kwargs)
        def sampled(*args,**kwargs):
            if negative is not None:
                encoded=backend.processor.tokenizer.apply_chat_template(negative,add_generation_prompt=True,enable_thinking=False,
                    tokenize=True,return_dict=True,return_tensors='pt')
                if encoded['input_ids'].shape[-1]>6000:raise ValueError('Neutral context limit')
                device=kwargs['input_ids'].device
                kwargs.update(guidance_scale=scale,negative_prompt_ids=encoded['input_ids'].to(device),
                              negative_prompt_attention_mask=encoded['attention_mask'].to(device))
            return sample(*args,**kwargs)
        error=None
        try:
            with patch.object(model,'forward',new=counted),patch.object(model,'generate',new=sampled):
                return original(messages,images,budget,weight,stop,choices,persona)
        except Exception as exc:
            error=type(exc).__name__+': '+str(exc);raise
        finally:records.append(dict(scale=scale,model_instances=1,forward_calls=len(forwards),error=error))
    with patch.object(backend,'_generate',new=generate):yield
