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
