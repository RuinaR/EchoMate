"""Tiny NF4 test of the new dropout/accumulation/RNG checkpoint recipe."""
import argparse
import gc
import json
import os
from pathlib import Path
from unittest.mock import patch


def run(base_path,output,*,cache_hygiene=False):
    from pilot_state import private_path,train_window,cosine,save,restore,inspect
    out=private_path(output);out.mkdir(parents=True,exist_ok=False)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.loader_memory import memory_snapshot,release_idle_cuda
    from echomate_bot.instance import InstanceLease
    health=check_resources();model_memory_budget(128*1024**2)
    if health['free_vram_mib']<2048:raise ValueError('Tiny reserve not met')
    import torch
    from transformers import AutoModelForMultimodalLM,BitsAndBytesConfig
    from peft import get_peft_model,LoraConfig,PeftModel
    from qlora_recipe import prepare_frozen_bf16,supervised_loss
    lease=InstanceLease();base=None;model=None;opt=None;sched=None;weights=None;torch.set_num_threads(1);torch.manual_seed(881)
    report=dict(status='NOT_STARTED',before=memory_snapshot(),health=health)
    from run_persona_pilot import clear_unused_before_phase
    report['cache_events']=[]
    def before_phase():
        event=clear_unused_before_phase(torch,cache_hygiene)
        if event is not None:report['cache_events'].append(event)
    try:
        base=prepare_frozen_bf16(AutoModelForMultimodalLM.from_pretrained(base_path,local_files_only=True,trust_remote_code=False,
            dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa',quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16)))
        model=get_peft_model(base,LoraConfig(r=4,lora_alpha=8,lora_dropout=.05,target_modules=r'.*language_model\.layers\.\d+\.self_attn\.(q_proj|v_proj)',task_type='CAUSAL_LM'))
        opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=.0001);sched=cosine(opt,4)
        batches=[([2,4,6,8,10],[-100,-100,6,8,10]),([3,5,7,9],[-100,-100,7,9])]*2
        before_phase();train_window(model,batches,opt,sched,supervised_loss)
        save(out/'step1',model,opt,sched,step=1,data_hash='tiny-api-only',config=dict(dropout=.05,accumulation=4))
        before_phase();expected=train_window(model,batches,opt,sched,supervised_loss);weights=[p.detach().cpu().clone() for p in model.parameters() if p.requires_grad]
        base=model.unload();model=None;opt=None;sched=None;gc.collect();release_idle_cuda(torch)
        inspect(out/'step1',data_hash='tiny-api-only',config=dict(dropout=.05,accumulation=4))
        model=PeftModel.from_pretrained(base,out/'step1/adapter',is_trainable=True,local_files_only=True)
        opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=.0001);sched=cosine(opt,4)
        restore(out/'step1',opt,sched,data_hash='tiny-api-only',config=dict(dropout=.05,accumulation=4))
        before_phase();actual=train_window(model,batches,opt,sched,supervised_loss)
        assert actual==expected
        assert all(torch.equal(p.detach().cpu(),v) for p,v in zip((p for p in model.parameters() if p.requires_grad),weights))
        assert torch.cuda.max_memory_reserved()<512*1024**2
        report.update(status='TINY_NEW_RECIPE_PASS_NOT_12B_QUALITY',replay=actual,peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved(),health_after=check_resources())
        report['cache_hygiene_verified']=cache_hygiene and len(report['cache_events'])==3
    finally:
        model=None;base=None;opt=None;sched=None;weights=None;gc.collect();release_idle_cuda(torch);lease.close()
        report['after']=memory_snapshot();(out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(report['status'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--output',required=True);p.add_argument('--cache-hygiene',action='store_true');a=p.parse_args()
    import faulthandler
    faulthandler.dump_traceback_later(180,exit=True)
    with patch('socket.socket.connect',side_effect=AssertionError('Offline')),patch('socket.getaddrinfo',side_effect=AssertionError('Offline')):run(a.base,a.output,cache_hygiene=a.cache_hygiene)
