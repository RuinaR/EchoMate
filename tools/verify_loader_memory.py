"""Isolated loader/mapping probes. Offline; reports contain counters, never prompts.

Run one mode per fresh process. Mapping mode defaults to 64 MiB synthetic U8.
Full mode respects the unchanged admission guard and the operating GPU lease.
"""
import argparse
import asyncio
import gc
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
from contextlib import ExitStack

from echomate_bot.loader_memory import MemoryRecorder,budget_requirement,native_loader_phases,memory_snapshot,LOADER_PREPARATION_BYTES,loading_reserve


def probe(args):
    output=Path(args.output).resolve()
    root=Path(__file__).resolve().parents[1]
    if not output.is_relative_to(root/'local_data') or output.exists():
        raise ValueError('Use a new output below local_data')
    output.parent.mkdir(parents=True,exist_ok=True)
    result=dict(mode=args.mode,status='NOT VERIFIED',gpu_load_attempts=0)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    def sample():
        row=memory_snapshot()
        torch=sys.modules.get('torch')
        if args.mode=='full' and torch is not None and torch.cuda.is_initialized():
            row.update(gpu_allocated=torch.cuda.memory_allocated(0),gpu_reserved=torch.cuda.memory_reserved(0),
                       gpu_peak_allocated=torch.cuda.max_memory_allocated(0))
        return row
    with MemoryRecorder(sample=sample) as recorder:
        try:
            if args.mode=='mapping':
                # Isolated synthetic tensors demonstrate transient reservation
                # without touching user weights or initiating CUDA.
                if not 1<=args.mib<=512:raise ValueError('Synthetic probe limited to 512 MiB')
                import torch
                from safetensors import safe_open
                recorder.mark('imports_complete')
                shards=getattr(args,'shards',1)
                if not 1<=shards<=8:raise ValueError('Shard count limited to 1..8')
                size=args.mib*1024**2
                from echomate_bot.processes import model_memory_budget
                model_memory_budget(size)
                with tempfile.TemporaryDirectory(dir=output.parent) as temp:
                    paths=[]
                    for i in range(shards):
                        path=Path(temp)/f'synthetic-{i}.safetensors';part=size//shards
                        header=json.dumps({'sample':dict(dtype='U8',shape=[part],data_offsets=[0,part])}).encode()
                        header+=b' '*((-len(header))%8)
                        with path.open('wb') as f:
                            f.write(struct.pack('<Q',len(header))+header);f.truncate(8+len(header)+part)
                        paths.append(path)
                    recorder.mark('before_open')
                    with ExitStack() as stack:
                        handles=[]
                        for path in paths:
                            handles.append(stack.enter_context(safe_open(path,framework='pt',device='cpu',backend=args.backend)))
                            recorder.mark('shard_opened')
                        weights=handles[-1]
                        recorder.mark('open_returned')
                        view=weights.get_slice('sample');result['shape']=view.get_shape()
                        recorder.mark('lazy_slice')
                        # Bounded materialization, not the entire synthetic file.
                        tensor=view[:min(size,1024**2)]
                        recorder.mark('materialized_1mib')
                        del tensor,view,weights,handles
                    gc.collect();recorder.mark('mapping_closed')
                result.update(status='PASS',backend=args.backend,shards=shards,weight_bytes=size,torch=torch.__version__)
            elif args.mode=='imports':
                recorder.mark('torch_import');import torch
                recorder.mark('transformers_import')
                from transformers import AutoModelForMultimodalLM,AutoProcessor,BitsAndBytesConfig
                if args.legacy_imports:
                    recorder.mark('peft_import');import peft
                recorder.mark('imports_complete')
                result.update(status='PASS',torch=torch.__version__,legacy_peft_imported=args.legacy_imports)
            else:
                from echomate_bot.model_registry import ModelRegistry
                from echomate_bot.processes import model_memory_budget
                if getattr(args,'model_path',None):
                    from echomate_bot.model_registry import ModelValidator
                    entry=ModelValidator().validate(args.model_path)
                    if not entry.compatible:raise ValueError('QA model structure invalid')
                else:entry=ModelRegistry().resolve('base')
                reserve,preparation=loading_reserve(entry)
                result.update(weight_bytes=entry.bytes,admission_bytes=budget_requirement(reserve,preparation),memory_profile=entry.memory_profile)
                model_memory_budget(reserve,preparation_bytes=preparation)
                from echomate_bot.instance import InstanceLease
                lease=InstanceLease()
                try:
                    from echomate_bot.inference import LocalBackend
                    backend=LocalBackend(model_id=entry.id,model_roots=[entry.path])
                    def observe(phase):
                        if phase=='model_init_weights_nf4':result['gpu_load_attempts']+=1
                        recorder.mark(phase)
                    backend.load_observer=observe
                    async def run():
                        try:
                            await backend.ready();recorder.mark('minimum_inference')
                            await backend.probe();result['status']='PASS'
                            result['load_seconds']=backend.load_seconds
                            answers=[]
                            for prompt in ('8 더하기 7의 답을 숫자로만 말해 줘','캐시의 목적을 한국어 두 문장으로 설명해 줘'):
                                answers.append(await backend._job([dict(role='system',content='정확한 한국어로 간결하게 답해.'),dict(role='user',content=prompt)],budget=128,weight='base'))
                            result['synthetic_outputs_private']=answers
                            result['generation_metrics']=backend.metrics
                        finally:
                            recorder.mark('unload');await backend.close();recorder.mark('unloaded')
                    recorder.mark('instrumentation_imports')
                    with native_loader_phases(recorder):asyncio.run(run())
                finally:lease.close()
        except Exception as exc:
            result.update(status='BLOCKED',error_type=type(exc).__name__,reason=getattr(exc,'reason',None),winerror=getattr(exc,'winerror',None))
            # Resource messages contain safe aggregate amounts, not paths.
            if getattr(exc,'reason',None):result['resource_message']=str(exc)
            recorder.mark('blocked')
    result['memory']=recorder.report()
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('memory','synthetic_outputs_private','generation_metrics')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['mapping','imports','full'],required=True)
    p.add_argument('--mib',type=int,default=64);p.add_argument('--backend',choices=['pread','mmap'],default='pread')
    p.add_argument('--shards',type=int,default=1,help='Synthetic simultaneously open shards; original model is untouched')
    p.add_argument('--legacy-imports',action='store_true')
    p.add_argument('--model-path',help='Optional validated private sharded QA copy; never selects it in the app')
    p.add_argument('--output',required=True);probe(p.parse_args())
