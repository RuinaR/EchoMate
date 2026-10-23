"""Sequential evaluation-only adapter for the already verified Qwen QA copy.

Never registered with the app, never simultaneous with its generation model.
No downloads, authentication, operating changes or unconstrained file roots.
"""
import gc,json,time,hashlib
from pathlib import Path
from dialogue_eval_core import private_root


class LocalJudge:
    def __init__(self,path):self.path=private_root(path);self.model=None;self.metrics=[]
    async def ready(self):
        from echomate_bot.processes import check_resources,model_memory_budget
        from echomate_bot.loader_memory import GIB
        if check_resources()['free_vram_mib']<10240:raise RuntimeError('Need 10GiB free VRAM')
        meta=json.loads((self.path/'acquisition.json').read_text('utf-8'))
        if meta['model']!='Qwen/Qwen3-8B':raise ValueError('Only existing official comparison copy')
        model_memory_budget(sum(p.stat().st_size for p in self.path.glob('*.safetensors')),10*GIB)
        for row in meta['files']:
            p=self.path/row['name']
            if not p.resolve().is_relative_to(self.path):raise ValueError('Model path escape')
            h=hashlib.sha256()
            with p.open('rb') as stream:
                while block:=stream.read(8*1024**2):h.update(block)
            if h.hexdigest()!=row['sha256']:raise ValueError('Model changed')
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM,BitsAndBytesConfig
        self.tokenizer=AutoTokenizer.from_pretrained(self.path,local_files_only=True,trust_remote_code=False)
        self.model=AutoModelForCausalLM.from_pretrained(self.path,local_files_only=True,trust_remote_code=False,device_map={'':'cuda:0'},dtype=torch.bfloat16,
            quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16))
    async def probe(self):await self._job([dict(role='user',content='Reply OK only')],budget=16)
    async def _job(self,messages,budget=384,**kwargs):
        import torch
        from transformers import StoppingCriteria,StoppingCriteriaList
        from echomate_bot.processes import check_resources
        check_resources()
        class Bound(StoppingCriteria):
            def __init__(self):self.at=time.monotonic();self.steps=0
            def __call__(self,input_ids,scores,**kw):
                self.steps+=1
                if self.steps%16==0:check_resources()
                return time.monotonic()-self.at>90
        inputs=self.tokenizer.apply_chat_template(messages,add_generation_prompt=True,enable_thinking=False,return_dict=True,return_tensors='pt').to('cuda:0')
        if inputs['input_ids'].shape[-1]>6000:raise ValueError('Audit input budget')
        torch.cuda.reset_peak_memory_stats();t=time.monotonic()
        with torch.inference_mode():out=self.model.generate(**inputs,max_new_tokens=budget,do_sample=False,stopping_criteria=StoppingCriteriaList([Bound()]))
        ids=out[0,inputs['input_ids'].shape[-1]:].tolist()
        self.metrics.append(dict(seconds=time.monotonic()-t,input_tokens=inputs['input_ids'].shape[-1],output_tokens=len(ids),
            peak_allocated_mib=torch.cuda.max_memory_allocated()/1048576,peak_reserved_mib=torch.cuda.max_memory_reserved()/1048576))
        self.metrics=self.metrics[-200:]
        if not ids or ids[-1]!=self.tokenizer.eos_token_id:raise ValueError('Incomplete audit output; stop instead of retry')
        return self.tokenizer.decode(ids,skip_special_tokens=True)
    async def close(self):
        import torch
        self.model=None;gc.collect()
        if torch.cuda.is_initialized():torch.cuda.synchronize();torch.cuda.empty_cache()
