"""Opt-in offline QA copy using public HF splitting and Safetensors APIs.

Never edits, links over, downloads or selects the original model. Tensor hashes
are checked after serialization before publishing the new index. The original
monolithic admission guard is used for preparation as well as initial GPU QA.
"""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import shutil
import struct

from echomate_bot.settings import private_path,atomic_private_json
from echomate_bot.loader_memory import LOADER_PREPARATION_BYTES,MemoryRecorder
from echomate_bot.processes import model_memory_budget


def tensor_hash(tensor):
    import torch
    return hashlib.sha256(memoryview(tensor.reshape(-1).view(torch.uint8).numpy()).cast('B')).hexdigest()


def stage(source,output,max_shard_size=2*1024**3):
    supplied=Path(source);sidecars=supplied.parent;source=supplied.resolve();output=private_path(output)
    if not source.is_file() or supplied.suffix!='.safetensors' or output.exists():raise ValueError('Use an existing source and fresh private output')
    if not 1024<=max_shard_size<=2*1024**3:raise ValueError('Shard bound is 1 KiB..2 GiB')
    if shutil.disk_usage(output.parent if output.parent.exists() else Path.cwd()).free<source.stat().st_size+2*1024**3:raise OSError('Insufficient disk space for independent copy')
    with source.open('rb') as f:
        n=struct.unpack('<Q',f.read(8))[0]
        if n>16*1024**2:raise ValueError('Invalid source header')
        header=json.loads(f.read(n))
    specs={k:v for k,v in header.items() if k!='__metadata__'}
    # HF's splitter permits an oversized single tensor. Reject it instead of
    # silently exceeding this tool's advertised materialization/RAM bound.
    if any(v['data_offsets'][1]-v['data_offsets'][0]>max_shard_size for v in specs.values()):raise ValueError('Tensor exceeds safe shard budget')
    model_memory_budget(source.stat().st_size,preparation_bytes=LOADER_PREPARATION_BYTES)
    from huggingface_hub import split_state_dict_into_shards_factory
    from safetensors import safe_open
    from safetensors.torch import save_file
    split=split_state_dict_into_shards_factory(specs,get_storage_size=lambda x:x['data_offsets'][1]-x['data_offsets'][0],filename_pattern='model{suffix}.safetensors',max_shard_size=max_shard_size)
    output.mkdir(parents=True);expected={};files={}
    with safe_open(source,framework='pt',device='cpu',backend='pread') as original:
        for filename,names in split.filename_to_tensors.items():
            tensors={name:original.get_tensor(name) for name in names}
            expected.update({name:tensor_hash(t) for name,t in tensors.items()})
            save_file(tensors,output/filename,metadata=header.get('__metadata__') or {'format':'pt'})
            del tensors;gc.collect()
            with safe_open(output/filename,framework='pt',device='cpu',backend='pread') as written:
                for name in names:
                    t=written.get_tensor(name)
                    if tensor_hash(t)!=expected[name] or list(t.shape)!=specs[name]['shape']:raise ValueError('Serialized tensor mismatch')
                    del t
            files[filename]=(output/filename).stat().st_size
            atomic_private_json(output/'preparation-progress.json',dict(shards=len(files),total_shards=len(split.filename_to_tensors),verified_tensors=len(expected)))
    # Copy only model sidecars, never tokens/cache metadata or arbitrary files.
    for name in ('config.json','generation_config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','chat_template.jinja','preprocessor_config.json','processor_config.json','video_preprocessor_config.json','LICENSE','README.md'):
        p=sidecars/name
        if p.is_file():shutil.copyfile(p,output/name)
    index=dict(metadata=split.metadata,weight_map=split.tensor_to_filename)
    if split.is_sharded:atomic_private_json(output/'model.safetensors.index.json',index)
    result=dict(status='PASS',tensor_count=len(expected),shards=len(files),largest_shard_bytes=max(files.values()),total_bytes=sum(files.values()),tensor_sha256=expected,
        source_header_sha256=hashlib.sha256(json.dumps(header,sort_keys=True).encode()).hexdigest(),original_modified=False,selected_in_app=False)
    atomic_private_json(output/'preparation-verification.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--source')
    a=p.parse_args()
    if a.source:source=Path(a.source)
    else:
        from echomate_bot.model_registry import ModelRegistry
        source=Path(ModelRegistry().resolve('base').path)/'model.safetensors'
    with MemoryRecorder() as recorder:
        result=stage(source,a.output)
    atomic_private_json(private_path(a.output)/'preparation-memory.json',recorder.report())
    print(json.dumps({k:v for k,v in result.items() if k!='tensor_sha256'}))
