"""Research-only optimizer-boundary checkpoints, hash validated before load.

One immutable directory per step. Failed writes leave earlier checkpoints
untouched. No untrusted pickle, operating adapter selection or global RNG use
outside the explicitly controlled training process.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import tempfile


def private_path(path):
    value=Path(path).resolve()
    if not value.is_relative_to(Path(__file__).resolve().parents[1]/'local_data'):raise ValueError('Private research checkpoint only')
    return value


def cosine(optimizer,total,warmup_ratio=.05):
    import torch
    if type(total) is not int or total<1 or not 0<=warmup_ratio<=.1:raise ValueError('Bounded scheduler')
    warmup=max(1,math.ceil(total*warmup_ratio))
    def multiplier(step):
        if step<warmup:return (step+1)/warmup
        return .5*(1+math.cos(math.pi*min(1,(step-warmup)/max(1,total-warmup))))
    return torch.optim.lr_scheduler.LambdaLR(optimizer,multiplier)


def train_window(model,examples,optimizer,scheduler,loss_fn,*,max_norm=1.):
    """Batch1 microsteps; mean by supervised TOKEN count across the window.

    Normalizing each microbatch equally overweights short answers. Keep only
    one graph resident and scale each exact selected-token loss by its count.
    """
    import torch
    if not 1<=len(examples)<=4:raise ValueError('One to four microbatches')
    counts=[sum(x!=-100 for x in labels[1:]) for ids,labels in examples]
    if not all(counts):raise ValueError('Every microbatch needs supervised next tokens')
    total=sum(counts);optimizer.zero_grad(set_to_none=True);model.train();losses=[]
    for (ids,labels),n in zip(examples,counts):
        device=next(model.parameters()).device
        loss=loss_fn(model,torch.tensor([ids],device=device),torch.tensor([labels],device=device))
        if not torch.isfinite(loss):raise ValueError('Non-finite loss')
        (loss*n/total).backward();losses.append(float(loss.detach()))
    parameters=[p for p in model.parameters() if p.requires_grad]
    if any(p.grad is None or not torch.isfinite(p.grad).all() for p in parameters):raise ValueError('Missing/non-finite gradient')
    norm=torch.nn.utils.clip_grad_norm_(parameters,max_norm,error_if_nonfinite=True)
    optimizer.step();scheduler.step();optimizer.zero_grad(set_to_none=True)
    return dict(loss=sum(v*n for v,n in zip(losses,counts))/total,supervised_tokens=total,gradient_norm=float(norm),learning_rate=optimizer.param_groups[0]['lr'])


def save(path,model,optimizer,scheduler,*,step,data_hash,config):
    import torch
    path=private_path(path)
    if path.exists():raise FileExistsError('Immutable checkpoint')
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.writing-',dir=path.parent))
    try:
        model.save_pretrained(temp/'adapter',safe_serialization=True)
        torch.save(dict(optimizer=optimizer.state_dict(),scheduler=scheduler.state_dict(),torch_rng=torch.get_rng_state(),
            cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else []),temp/'state.pt')
        manifest=dict(schema=1,step=step,data_hash=data_hash,config=config,python_rng=random.getstate(),files={})
        for p in sorted(temp.rglob('*')):
            if p.is_file():manifest['files'][p.relative_to(temp).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        (temp/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
        os.rename(temp,path)
    finally:
        if temp.exists():
            assert temp.resolve().is_relative_to(path.parent) and temp.name.startswith('.writing-')
            shutil.rmtree(temp)


def inspect(path,*,data_hash,config):
    path=private_path(path);manifest=json.loads((path/'manifest.json').read_text('utf-8'))
    if manifest['schema']!=1 or manifest['data_hash']!=data_hash or manifest['config']!=config or type(manifest['step']) is not int or manifest['step']<0:raise ValueError('Checkpoint binding mismatch')
    files=manifest['files'];actual={p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file() and p.name!='manifest.json'}
    if set(files)!=actual or not {'state.pt','adapter/adapter_config.json','adapter/adapter_model.safetensors'}.issubset(files):raise ValueError('Checkpoint membership mismatch')
    for name,digest in files.items():
        target=(path/name).resolve()
        if not target.is_relative_to(path.resolve()) or target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('Checkpoint integrity mismatch')
    return manifest


def restore(path,optimizer,scheduler,*,data_hash,config):
    import torch
    manifest=inspect(path,data_hash=data_hash,config=config)
    state=torch.load(Path(path)/'state.pt',map_location='cpu',weights_only=True)
    optimizer.load_state_dict(state['optimizer']);scheduler.load_state_dict(state['scheduler'])
    torch.set_rng_state(state['torch_rng'])
    if state['cuda_rng']:
        if not torch.cuda.is_available() or len(state['cuda_rng'])!=torch.cuda.device_count():raise ValueError('RNG device mismatch')
        torch.cuda.set_rng_state_all(state['cuda_rng'])
    def tuples(v):return tuple(map(tuples,v)) if isinstance(v,list) else v
    random.setstate(tuples(manifest['python_rng']))
    return manifest['step']
