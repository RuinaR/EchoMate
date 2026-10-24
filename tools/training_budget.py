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


def estimate(rows,cfg,*,rank=4,sequence=64,frozen_bf16=False,supervised_tokens=None,last_layers=None,cpu_tied_io=False,checkpoint_inputs=False):
    if rank not in (2,4,8) or type(sequence) is not int or not 8<=sequence<=2048:raise ValueError('Bounded probe sizes required')
    if supervised_tokens is not None and (type(supervised_tokens) is not int or not 1<=supervised_tokens<sequence):raise ValueError('Invalid supervised positions')
    if last_layers is not None and (type(last_layers) is not int or not 1<=last_layers<=cfg['num_hidden_layers']):raise ValueError('Invalid trainable suffix')
    quantized=0;floating=0;embedding_parameters=0;largest_cast=0;targets=[]
    for name,value in rows.items():
        shape=value['shape'];n=math.prod(shape)
        if len(shape)==2 and any(name.endswith('.'+part+'.weight') for part in LINEARS):quantized+=n
        else:
            floating+=n
            if name.endswith('.embed_tokens.weight'):embedding_parameters+=n
            if value['dtype'] in ('BF16','F16'):largest_cast=max(largest_cast,n*2)
        if '.language_model.' in name and name.endswith(('.q_proj.weight','.v_proj.weight')):
            if len(shape)!=2:raise ValueError('Invalid linear target')
            if last_layers is not None:
                layer=int(name.split('.language_model.layers.')[1].split('.')[0])
                if layer<cfg['num_hidden_layers']-last_layers:continue
            targets.append(dict(name=name,shape=shape,adapter_parameters=rank*sum(shape)))
    if not targets:raise ValueError('No text q/v adapter targets')
    # 4.5 bits/linear parameter includes a conservative NF4 scale allowance.
    # Only embedding BF16 is a required observed contract of this recipe.
    # Reserve FP32 for other floating weights, including loader keep-fp32 lists.
    prepared=math.ceil(quantized*9/16)+floating*4-(embedding_parameters*2 if frozen_bf16 else 0)
    if cpu_tied_io and (not frozen_bf16 or not embedding_parameters or cfg.get('tie_word_embeddings') is not True):
        raise ValueError('CPU I/O budget requires frozen tied BF16 embedding')
    if frozen_bf16:largest_cast=0
    adapter=sum(x['adapter_parameters'] for x in targets)
    adapter_state=adapter*20 # fp32 parameters, grads, Adam moments, save copy
    checkpoint=(last_layers or cfg['num_hidden_layers'])*sequence*cfg['hidden_size']*4*8
    checkpoint_detail=None
    if checkpoint_inputs:
        # Isolated, opt-in non-reentrant train-mode recipe. Keep FP32 upper
        # bounds even though observed checkpoint inputs are BF16. Count every
        # layer's K/V and rotary separately even when actual storage is shared.
        k=[v['shape'][0] for n,v in rows.items() if '.language_model.layers.' in n and n.endswith('.self_attn.k_proj.weight')]
        v=[v['shape'][0] for n,v in rows.items() if '.language_model.layers.' in n and n.endswith('.self_attn.v_proj.weight')]
        q=[v['shape'][0] for n,v in rows.items() if '.language_model.layers.' in n and n.endswith('.self_attn.q_proj.weight')]
        heads=[cfg.get('head_dim'),cfg.get('global_head_dim') or cfg.get('head_dim')]
        largest=max(math.prod(v['shape']) for n,v in rows.items() if '.language_model.layers.' in n and len(v['shape'])==2)
        if (not frozen_bf16 or cpu_tied_io or last_layers is not None or rank!=4 or sequence>512 or cfg.get('model_type')!='gemma4_unified_text'
                or not k or not v or not q or any(type(h) is not int or h<=0 for h in heads)
                or cfg['num_hidden_layers']>48 or cfg['hidden_size']>3840 or cfg['vocab_size']>262144
                or (cfg.get('hidden_size_per_layer_input') or 0)!=0
                or cfg.get('intermediate_size',0)>15360 or largest>2**26 or max(k+v)>2048 or max(heads)>512 or max(q)>16*max(heads)):
            raise ValueError('Checkpoint-input budget requires separately verified bounded Unified train-mode geometry')
        layers=cfg['num_hidden_layers']
        checkpoint_detail=dict(hidden_fp32=layers*sequence*cfg['hidden_size']*4,
            kv_fp32_all_layers=layers*sequence*(max(k)+max(v))*4,
            rotary_fp32_all_layers=layers*sequence*max(heads)*2*4,causal_masks_fp32=2*sequence*sequence*4)
        checkpoint=sum(checkpoint_detail.values())
    logits=(supervised_tokens or sequence)*cfg['vocab_size']*4*4
    backward_workspace=GIB+checkpoint+logits
    allocator_driver=GIB;safety=2*GIB
    cpu_weight=embedding_parameters*2 if cpu_tied_io else 0
    gpu_prepared=prepared-cpu_weight
    cpu_reserve=cpu_weight+logits+GIB if cpu_tied_io else 0
    return dict(rank=rank,sequence=sequence,batch=1,checkpointing=True,frozen_bf16=frozen_bf16,supervised_tokens=supervised_tokens,last_layers=last_layers,
        cpu_tied_io=cpu_tied_io,training_prepared_vram_bytes=gpu_prepared,cpu_offload_reserve_bytes=cpu_reserve,
        activation_policy='checkpoint_train_inputs_v1' if checkpoint_inputs else 'legacy_saved8_fp32',checkpoint_input_bounds=checkpoint_detail,
        frozen_prefix_gradient_proof_required=last_layers is not None,quantized_parameters=quantized,
        non_quantized_parameters=floating,fp32_parameters=floating-(embedding_parameters if frozen_bf16 else 0),
        bf16_parameters=embedding_parameters if frozen_bf16 else 0,adapter_parameters=adapter,target_count=len(targets),targets=targets,
        prepared_bytes=prepared,upcast_overlap_bytes=largest_cast,adapter_state_bytes=adapter_state,
        backward_planning_bytes=backward_workspace,allocator_driver_bytes=allocator_driver,safety_bytes=safety,
        components=dict(nf4_with_scales=math.ceil(quantized*9/16),
            frozen_embedding=embedding_parameters*2 if frozen_bf16 else 0,
            other_floating=floating*4-(embedding_parameters*4 if frozen_bf16 else 0),
            adapter_parameters=adapter*4,adapter_gradients=adapter*4,
            optimizer_moments=adapter*8,adapter_save_copy=adapter*4,
            checkpoint_activations=checkpoint,selected_logits_workspace=logits,
            backward_workspace=GIB,allocator_driver=allocator_driver,safety=safety),
        lifetime_formula='max(full_GPU_load_prepared + upcast_overlap, training_GPU_prepared + adapter_state + backward_planning) + allocator_driver + safety',
        planning_required_vram=max(prepared+largest_cast,gpu_prepared+adapter_state+backward_workspace)+allocator_driver+safety,
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
