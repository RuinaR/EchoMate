"""Replay a failed research checkpoint twice, without additional quality tuning."""
import argparse
import gc
import json
import os
from pathlib import Path
import random
from unittest.mock import patch


def run(model_path,previous,export,output,deterministic=False):
    from pilot_state import private_path,inspect,restore,cosine,train_window
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.loader_memory import memory_snapshot,loading_reserve,release_idle_cuda
    from echomate_bot.model_registry import ModelValidator
    from echomate_bot.instance import InstanceLease
    out=private_path(output);out.mkdir(parents=True,exist_ok=False);old=json.loads((Path(previous)/'report.json').read_text('utf-8'))
    if old['status']!='STOPPED' or old.get('error')!='ValueError' or len(old['trials'])!=1:raise ValueError('Specific failed pilot only')
    trial=old['trials'][0];lr=trial['lr'];config={k:trial[k] for k in ('lr','rank','alpha','dropout','accumulation','max_grad_norm','epochs','warmup_ratio','scheduler')}
    checkpoint=Path(previous)/('lr-'+str(lr))/'step8';inspect(checkpoint,data_hash=old['data_hash'],config=config)
    train=[json.loads(l) for l in (Path(export)/'train.jsonl').read_bytes().splitlines()];order=list(range(len(train)));random.Random(881).shuffle(order)
    batches=[(train[i]['input_ids'],train[i]['labels']) for i in order[32:36]]
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    if deterministic:os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8' # this child only, not Windows/global settings
    entry=ModelValidator().validate(model_path);health=check_resources();model_memory_budget(*loading_reserve(entry))
    if old['budget']['planning_required_vram']>health['free_vram_mib']*1024**2:raise ValueError('Static reserve changed')
    import torch
    if deterministic:torch.use_deterministic_algorithms(True)
    from transformers import AutoModelForMultimodalLM,BitsAndBytesConfig
    from peft import PeftModel
    from qlora_recipe import prepare_frozen_bf16,supervised_loss
    torch.set_num_threads(2);lease=InstanceLease();base=None;model=None;opt=None;sched=None;weights=None
    report=dict(status='NOT_STARTED',before=memory_snapshot(),health=health,old_expected=trial['steps'][8],replays=[],deterministic=deterministic)
    try:
        base=prepare_frozen_bf16(AutoModelForMultimodalLM.from_pretrained(model_path,local_files_only=True,trust_remote_code=False,
            dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa',quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16)))
        for repeat in range(2):
            model=PeftModel.from_pretrained(base,checkpoint/'adapter',is_trainable=True,local_files_only=True)
            report['adapter_dtypes']=sorted(set(str(p.dtype) for p in model.parameters() if p.requires_grad))
            opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=lr);sched=cosine(opt,16,.05)
            restore(checkpoint,opt,sched,data_hash=old['data_hash'],config=config)
            metrics=train_window(model,batches,opt,sched,supervised_loss);report['replays'].append(metrics)
            current=[p.detach().cpu().clone() for p in model.parameters() if p.requires_grad]
            if repeat==0:weights=current
            else:report['repeat_max_adapter_difference']=max(float((a-b).abs().max()) for a,b in zip(weights,current))
            memory=memory_snapshot();h=check_resources();report.setdefault('stages',[]).append(dict(memory=memory,health=h,peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved()))
            (out/'progress.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            if memory['ram_available']<3*1024**3 or memory['commit_available']<2*1024**3 or h['free_vram_mib']<2048:raise ValueError('Resource reserve')
            base=model.unload();model=None;opt=None;sched=None;current=None;gc.collect();release_idle_cuda(torch)
        report.update(status='REPLAY_DIAGNOSIS_COMPLETE_NOT_QUALITY',repeat_metrics_equal=report['replays'][0]==report['replays'][1],old_delta={k:report['replays'][0][k]-report['old_expected'][k] for k in report['old_expected']})
    except BaseException as e:
        report.update(status='STOPPED',error=type(e).__name__,message=str(e));raise
    finally:
        model=None;base=None;opt=None;sched=None;weights=None;current=None;gc.collect();release_idle_cuda(torch);lease.close()
        report['after']=memory_snapshot();(out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=report['status'],replays=report['replays'],old_delta=report['old_delta'],repeat_metrics_equal=report['repeat_metrics_equal'],repeat_max_adapter_difference=report['repeat_max_adapter_difference'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--previous',required=True);p.add_argument('--export',required=True);p.add_argument('--output',required=True);p.add_argument('--deterministic',action='store_true');a=p.parse_args()
    import faulthandler
    faulthandler.dump_traceback_later(300,exit=True)
    with patch('socket.socket.connect',side_effect=AssertionError('Offline')),patch('socket.getaddrinfo',side_effect=AssertionError('Offline')):run(a.model,a.previous,a.export,a.output,a.deterministic)
