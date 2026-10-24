"""Bounded research DPO primitives; no model loading or automatic training.

Completion log probabilities are SUMS (not length averages). Sequential
recomputation retains one policy graph; replayed RNG preserves dropout masks.
Reference scalars must come from a fixed, independently bound model snapshot.
"""
import math


def completion_logps(model,ids,labels):
    import torch
    from torch.nn import functional as F
    if ids.ndim!=2 or ids.shape[0]!=1 or ids.shape!=labels.shape:raise ValueError('Batch-one matching token arrays')
    positions=torch.nonzero(labels[0,1:]!=-100,as_tuple=False).flatten()
    if not positions.numel():raise ValueError('Completion needs supervised causal positions')
    logits=model(input_ids=ids,logits_to_keep=positions,use_cache=False).logits
    selected=F.log_softmax(logits[0].float(),dim=-1)
    return selected.gather(1,labels[0,positions+1,None]).sum()


def dpo_loss(chosen,rejected,reference_chosen,reference_rejected,*,beta=.1):
    from torch.nn import functional as F
    if type(beta) not in (int,float) or not math.isfinite(beta) or not 0<beta<=1:raise ValueError('Bounded positive beta')
    return F.softplus(-beta*((chosen-rejected)-(reference_chosen-reference_rejected)))


def sequential_pair_backward(model,chosen,rejected,reference,*,beta=.1,scale=1.,observe=None):
    """Exact chain-rule gradient with one graph resident; no optimizer step.

    Four forwards trade compute for memory. Capture train-mode no-grad policy
    values and their RNG states; replay each graph forward with the same RNG.
    Caller owns accumulation, finite-gradient checks and optimizer boundaries.
    """
    import torch
    if not math.isfinite(scale) or not 0<scale<=1:raise ValueError('Bounded accumulation scale')
    if len(reference)!=2 or not all(math.isfinite(float(x)) for x in reference):raise ValueError('Finite fixed reference pair required')
    model.train()
    def rng():return torch.get_rng_state(),torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else []
    def restore(state):
        torch.set_rng_state(state[0])
        if state[1]:torch.cuda.set_rng_state_all(state[1])
    states=[];values=[]
    for label,example in zip(('chosen','rejected'),(chosen,rejected)):
        states.append(rng())
        with torch.no_grad():value=completion_logps(model,*example)
        if not torch.isfinite(value):raise ValueError('Nonfinite policy probability')
        values.append(value.detach())
        if observe:observe('policy_'+label)
    after=rng();left,right=values
    loss=dpo_loss(left,right,*reference,beta=beta)
    weight=beta*torch.sigmoid(-beta*((left-right)-(reference[0]-reference[1])))
    if not torch.isfinite(loss) or not torch.isfinite(weight):raise ValueError('Nonfinite DPO objective')
    try:
        for sign,label,example,state,value in zip((-1,1),('chosen','rejected'),(chosen,rejected),states,values):
            restore(state);actual=completion_logps(model,*example)
            if not torch.equal(actual.detach(),value):raise ValueError('Dropout/recomputation policy probability differs')
            if observe:observe('forward_'+label)
            (actual*weight*sign*scale).backward()
            if observe:observe('backward_'+label)
    finally:restore(after)
    return dict(loss=float(loss),chosen_logp=float(left),rejected_logp=float(right),
                reference_margin=float(reference[0]-reference[1]),policy_margin=float(left-right),beta=beta)
