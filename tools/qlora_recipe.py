"""Experimental frozen-BF16 recipe and exact supervised-position loss.

Uses public torch/Transformers/PEFT APIs; never patches installed libraries.
Not connected to the app's model loader or operating adapter selection.
"""


def prepare_frozen_bf16(model):
    import torch
    if not getattr(model,'is_loaded_in_4bit',False):raise ValueError('NF4 base required')
    for p in model.parameters():p.requires_grad_(False)
    embedding=model.get_input_embeddings().weight
    if embedding.dtype!=torch.bfloat16:raise ValueError('Preserve loaded BF16 embedding')
    model.config.use_cache=False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
    return model


def training_checkpoint_mode(model):
    """A true property alone does not activate checkpointing in eval mode."""
    model.train()
    base=model.get_base_model() if hasattr(model,'get_base_model') else model
    layers=getattr(base.model,'language_model',base.model).layers
    if not layers or not all(l.training and getattr(l,'gradient_checkpointing',False) for l in layers):
        raise ValueError('Every decoder layer must actually checkpoint in train mode')
    if not all(getattr(getattr(l,'_gradient_checkpointing_func',None),'keywords',{}).get('use_reentrant') is False for l in layers):
        raise ValueError('Verified non-reentrant checkpoint implementation required')
    return dict(training=True,checkpointed_layers=len(layers),non_reentrant=True)


def checkpoint_mode_proof(model,loss_fn,*,length=32,supervised=8):
    """Bounded NF4 probe: matching train-mode grads with/without checkpointing.

    Saved-storage counts are forward-only upper bounds, excluding parameters.
    Opaque custom-autograd ctx and CUDA workspace are outside this hook's scope.
    No activations or values are retained in diagnostics.
    """
    import torch
    base=model.get_base_model();device=next(p for p in model.parameters() if p.requires_grad).device
    cpu_rng=torch.get_rng_state();cuda_rng=torch.cuda.get_rng_state_all()
    if not 8<=length<=128 or not 1<=supervised<length:raise ValueError('Bounded checkpoint comparison')
    ids=(torch.arange(length,device=device)%16+2).unsqueeze(0);labels=ids.clone();labels[:,:-supervised]=-100
    def key(t):return (str(t.device),t.untyped_storage().data_ptr(),t.untyped_storage().nbytes())
    static={key(p) for p in list(model.parameters())+list(model.buffers())};result={};gradients={}
    try:
        for name,training,checkpoint in (('eval_checkpoint_flag_only',False,True),('train_without_checkpoint',True,False),('train_checkpoint',True,True)):
            if checkpoint:base.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
            else:base.gradient_checkpointing_disable()
            model.train(training);model.zero_grad(set_to_none=True);torch.manual_seed(808);torch.cuda.manual_seed_all(808)
            seen={}
            def pack(t):
                k=key(t)
                if k not in static:seen[k]=dict(shape=list(t.shape),dtype=str(t.dtype),storage_bytes=k[2])
                return t.detach()
            with torch.autograd.graph.saved_tensors_hooks(pack,lambda t:t):
                loss=loss_fn(model,ids,labels)
                observed=dict(training=training,checkpoint_flag=base.is_gradient_checkpointing,loss=float(loss.detach()),
                    forward_saved_storage_upper_bytes=sum(k[2] for k in seen),saved_shapes=list(seen.values())[:128])
                loss.backward()
            gradients[name]=[p.grad.detach().cpu().clone() for p in model.parameters() if p.requires_grad]
            if not all(torch.isfinite(g).all() for g in gradients[name]):raise ValueError('Nonfinite checkpoint proof gradient')
            result[name]=observed
        left=gradients['train_without_checkpoint'];right=gradients['train_checkpoint']
        maximum=max(float((a-b).abs().max()) for a,b in zip(left,right))
        exact=maximum==0 and result['train_without_checkpoint']['loss']==result['train_checkpoint']['loss']
        result.update(train_mode_loss_gradients_exact=exact,gradient_max_abs_delta=maximum,
            train_mode_loss_abs_delta=abs(result['train_without_checkpoint']['loss']-result['train_checkpoint']['loss']),
            diagnostic_scope='Forward saved-storage upper bounds only; not complete activation/workspace lifetimes')
        return result
    finally:
        model.zero_grad(set_to_none=True);base.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False});model.train()
        torch.set_rng_state(cpu_rng);torch.cuda.set_rng_state_all(cuda_rng)


def prepare_suffix_inputs(model,first_layer):
    """Only non-reentrant, frozen-embedding suffix experiments may use this.

    Transformers enables embedding-output grads during checkpoint setup.
    Remove that via its public API, then callers must prove the prefix has
    no graph on an actual forward before accepting a suffix-only budget.
    """
    import re
    if type(first_layer) is not int or first_layer<1:raise ValueError('Strict suffix required')
    trainable=[n for n,p in model.named_parameters() if p.requires_grad]
    if not trainable or any('lora_' not in n or not (m:=re.search(r'\.layers\.(\d+)\.',n)) or int(m[1])<first_layer for n in trainable):
        raise ValueError('Only suffix LoRA parameters may train')
    if model.get_input_embeddings().weight.requires_grad:raise ValueError('Frozen embedding required')
    model.get_base_model().disable_input_require_grads()
    return model


def prove_suffix_graph(model,first_layer,ids):
    """Bounded real forward/backward proof before using the suffix budget."""
    base=model.get_base_model();layers=getattr(base.model,'language_model',base.model).layers
    flags={}
    def observe(key):
        def record(module,args,result):flags[key]=bool(result.requires_grad)
        return record
    handles=[layers[first_layer-1].register_forward_hook(observe('prefix')),
             layers[first_layer].register_forward_hook(observe('suffix'))]
    try:
        model.train();loss=supervised_loss(model,ids,ids)
        if flags!={'prefix':False,'suffix':True}:raise ValueError('Frozen prefix has a graph; reject suffix budget')
        loss.backward()
        import torch
        trainable=[p for p in model.parameters() if p.requires_grad]
        if not trainable or not any(p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().sum()>0 for p in trainable):raise ValueError('Missing suffix gradient')
        return dict(prefix_requires_grad=False,suffix_requires_grad=True,nonzero_gradient=True)
    finally:
        model.zero_grad(set_to_none=True)
        for handle in handles:handle.remove()


def supervised_loss(model,ids,labels):
    """Exactly the non-ignored causal positions; never truncate the prompt.

    Batch-one experiment only. Position t predicts label t+1. Supplying
    labels with sliced logits to the built-in loss would misalign targets.
    """
    import torch
    from torch.nn import functional as F
    if ids.ndim!=2 or ids.shape[0]!=1 or ids.shape!=labels.shape:raise ValueError('Batch-one matching labels required')
    positions=torch.nonzero(labels[0,1:]!=-100,as_tuple=False).flatten()
    if not positions.numel():raise ValueError('No supervised next token')
    logits=model(input_ids=ids,logits_to_keep=positions,use_cache=False).logits
    return F.cross_entropy(logits[0].float(),labels[0,positions+1])
