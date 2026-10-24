"""Read-only Safetensors header planning for text q/v QLoRA.

No weights, GPU tensors, downloads, model construction or automatic training.
Reserve estimates reject unsafe experiments; they never certify trainability.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

GIB=1024**3
LINEARS=('q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj','gate_up_proj')


def estimate(rows,cfg,*,rank=4,sequence=64):
    if rank not in (2,4,8) or sequence not in (32,64,128,256):raise ValueError('Bounded probe sizes required')
    quantized=0;floating=0;largest_cast=0;targets=[]
    for name,value in rows.items():
        shape=value['shape'];n=math.prod(shape)
        if len(shape)==2 and any(name.endswith('.'+part+'.weight') for part in LINEARS):quantized+=n
        else:
            floating+=n
            if value['dtype'] in ('BF16','F16'):largest_cast=max(largest_cast,n*2)
        if '.language_model.' in name and name.endswith(('.q_proj.weight','.v_proj.weight')):
            if len(shape)!=2:raise ValueError('Invalid linear target')
            targets.append(dict(name=name,shape=shape,adapter_parameters=rank*sum(shape)))
    if not targets:raise ValueError('No text q/v adapter targets')
    # 4.5 bits/linear parameter includes a conservative NF4 scale allowance.
    prepared=math.ceil(quantized*9/16)+floating*4
    adapter=sum(x['adapter_parameters'] for x in targets)
    adapter_state=adapter*20 # fp32 parameters, grads, Adam moments, save copy
    checkpoint=cfg['num_hidden_layers']*sequence*cfg['hidden_size']*4*8
    logits=sequence*cfg['vocab_size']*4*4
    backward_workspace=GIB+checkpoint+logits
    allocator_driver=GIB;safety=2*GIB
    return dict(rank=rank,sequence=sequence,batch=1,checkpointing=True,quantized_parameters=quantized,
        fp32_parameters=floating,adapter_parameters=adapter,target_count=len(targets),targets=targets,
        prepared_bytes=prepared,upcast_overlap_bytes=largest_cast,adapter_state_bytes=adapter_state,
        backward_planning_bytes=backward_workspace,allocator_driver_bytes=allocator_driver,safety_bytes=safety,
        planning_required_vram=max(prepared+largest_cast,prepared+adapter_state+backward_workspace)+allocator_driver+safety,
        caveat='Planning reserve, not a proven activation peak; sufficient headroom requires actual stage checks. No admission relaxation.')


def run(model,output):
    from echomate_bot.model_registry import ModelValidator
    from echomate_bot.processes import check_resources,model_memory_budget
    from echomate_bot.loader_memory import memory_snapshot,loading_reserve
    repo=Path(__file__).resolve().parents[1];out=Path(output).resolve()
    if not out.is_relative_to(repo/'local_data') or out.exists():raise ValueError('Fresh private output required')
    entry=ModelValidator().validate(model)
    if not entry.compatible:raise ValueError('Validated existing Gemma required')
    root=Path(entry.path);cfg=json.loads((root/'config.json').read_text('utf-8'))
    idx=json.loads((root/'model.safetensors.index.json').read_text('utf-8'));rows={};headers={}
    for name in sorted(set(idx['weight_map'].values())):
        with (root/name).open('rb') as f:
            length=struct.unpack('<Q',f.read(8))[0];raw=f.read(length)
        headers[name]=hashlib.sha256(raw).hexdigest()
        rows.update({k:v for k,v in json.loads(raw).items() if k!='__metadata__'})
    result=estimate(rows,cfg['text_config']);health=check_resources();memory=memory_snapshot()
    model_memory_budget(*loading_reserve(entry)) # original host loading gate
    required=result['planning_required_vram'];available=health['free_vram_mib']*1024**2
    result.update(status='BLOCKED_STATIC_VRAM' if required>available else 'REQUIRES_ACTUAL_STAGE_CHECK',
        free_vram_bytes=available,health=health,memory=memory,header_hashes=headers,
        config_sha256=hashlib.sha256((root/'config.json').read_bytes()).hexdigest(),
        library_versions={n:__import__('importlib.metadata',fromlist=['version']).version(n) for n in ('torch','transformers','peft','bitsandbytes')})
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('targets','header_hashes','memory')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    run(a.model,a.output)
