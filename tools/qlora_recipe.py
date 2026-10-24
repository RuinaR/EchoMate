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
