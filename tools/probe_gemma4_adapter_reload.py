"""Gemma4 cached baseline vs saved synthetic adapter deterministic loss probe."""
from __future__ import annotations
import argparse,json,math
from pathlib import Path

MODEL="google/gemma-4-12B-it"
PROMPTS=("오늘 게임 정말 재밌었어 ㅋㅋ","이거 왜 이렇게 어렵지? 그래도 다시 해보자")

def inspect_adapter(path):
    path=Path(path).resolve()
    if "local_data" not in path.parts or not (path/"adapter_model.safetensors").is_file() or not (path/"adapter_config.json").is_file():
        raise ValueError("private existing adapter required")
    cfg=json.loads((path/"adapter_config.json").read_text(encoding="utf-8"))
    if cfg.get("base_model_name_or_path") != MODEL or cfg.get("r")!=4 or set(cfg.get("target_modules",[]))!={"q_proj","v_proj"}:
        raise ValueError("adapter model or LoRA configuration mismatch")
    return path

def run(path):
    import torch
    from transformers import AutoTokenizer,AutoModelForMultimodalLM,BitsAndBytesConfig
    from peft import PeftModel
    if not torch.cuda.is_available():raise RuntimeError("CUDA unavailable")
    tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16)
    base=AutoModelForMultimodalLM.from_pretrained(MODEL,quantization_config=quant,device_map={"":0},dtype=torch.float16,attn_implementation="sdpa",local_files_only=True)
    model=PeftModel.from_pretrained(base,str(path),is_trainable=False)
    model.eval()
    def losses():
        result=[]
        with torch.inference_mode():
            for text in PROMPTS:
                ids=tok(text,return_tensors="pt",add_special_tokens=True)["input_ids"].to("cuda")
                labels=ids.clone();labels[:,:1]=-100
                v=float(model(input_ids=ids,attention_mask=torch.ones_like(ids),labels=labels,use_cache=False).loss.item())
                if not math.isfinite(v):raise RuntimeError("nonfinite loss")
                result.append(round(v,4))
        return result
    with model.disable_adapter():
        baseline=losses()
    adapted=losses()
    free,_=torch.cuda.mem_get_info(0)
    return {"status":"ok","synthetic_only":True,"base_model":MODEL,
            "sample_count":len(PROMPTS),"baseline_losses":baseline,"adapter_losses":adapted,
            "free_after_mib":round(free/1048576,1),
            "note":"Synthetic loss comparison only, not a quality or style evaluation."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--adapter",type=Path,default=Path("local_data/gemma4-synthetic-e2e/adapter"))
    p.add_argument("--run-gpu",action="store_true")
    p.add_argument("--output",type=Path,default=Path("local_data/gemma4-adapter-reload.json"))
    a=p.parse_args()
    if "local_data" not in a.output.resolve().parts:p.error("output must remain private")
    path=inspect_adapter(a.adapter)
    report=run(path) if a.run_gpu else {"status":"preflight_ok","synthetic_only":True,"gpu_not_run":True}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Adapter reload:",report["status"],"report:",a.output)
    return 0

if __name__=="__main__":raise SystemExit(main())
