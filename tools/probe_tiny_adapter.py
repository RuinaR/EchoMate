"""CPU-only Gemma4 text/PEFT API feasibility, NOT 12B training or quality.

Fresh random tiny weights and integer tokens only. Never reads a base model,
operating settings, private conversations or existing adapters. No downloads.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from importlib.metadata import version
from unittest.mock import patch


def run(output):
    repo=Path(__file__).resolve().parents[1];root=Path(output).resolve()
    if not root.is_relative_to(repo/'local_data'):raise ValueError('Private project output required')
    root.mkdir(parents=True,exist_ok=False)
    # Only this explicitly CPU test process; no system environment/settings.
    os.environ['CUDA_VISIBLE_DEVICES']=''
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    import torch
    from transformers import Gemma4UnifiedTextConfig,Gemma4UnifiedForCausalLM
    from peft import LoraConfig,get_peft_model,PeftModel
    torch.set_num_threads(1)
    seed=20261024
    def fresh():
        torch.manual_seed(seed)
        cfg=Gemma4UnifiedTextConfig(vocab_size=64,hidden_size=32,intermediate_size=64,
            num_hidden_layers=2,num_attention_heads=4,num_key_value_heads=2,head_dim=8,
            global_head_dim=8,layer_types=['sliding_attention','full_attention'],
            max_position_embeddings=64,sliding_window=16,use_cache=False)
        cfg._attn_implementation='eager'
        return Gemma4UnifiedForCausalLM(cfg).cpu()
    base=fresh();refs=[(p,p.detach().clone()) for p in base.parameters()]
    model=get_peft_model(base,LoraConfig(r=2,lora_alpha=4,lora_dropout=0,
        target_modules=['q_proj','v_proj'],task_type='CAUSAL_LM'))
    trainable=[p for n,p in model.named_parameters() if p.requires_grad]
    assert trainable and all('lora_' in n for n,p in model.named_parameters() if p.requires_grad)
    ids=torch.tensor([[2,4,7,9,12,15,19,1]],device='cpu')
    optimizer=torch.optim.AdamW(trainable,lr=.001)
    model.train();loss=model(input_ids=ids,labels=ids).loss
    assert torch.isfinite(loss)
    loss.backward()
    assert any(p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().sum()>0 for p in trainable)
    optimizer.step();optimizer.zero_grad();model.eval()
    assert all(torch.equal(p.detach(),original) for p,original in refs)
    with torch.no_grad():expected=model(input_ids=ids).logits
    model.save_pretrained(root/'adapter',safe_serialization=True)
    restored=PeftModel.from_pretrained(fresh(),root/'adapter',local_files_only=True).eval()
    with torch.no_grad():actual=restored(input_ids=ids).logits
    assert torch.allclose(expected,actual,atol=1e-6,rtol=1e-5)
    report=dict(status='CPU_API_PASS_NOT_TRAINING_QUALITY',versions={n:version(n) for n in ('torch','transformers','peft')},
        parameters=sum(p.numel() for p in model.parameters()),trainable=sum(p.numel() for p in trainable),
        finite_loss=float(loss.detach()),base_unchanged=True,adapter_roundtrip=True,steps=1,device='cpu',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        not_verified=['12B','NF4 backward','multimodal wrapper','VRAM/commit training peak','persona/factual quality'])
    (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    with patch('socket.socket.connect',side_effect=AssertionError('No network')),\
         patch('socket.getaddrinfo',side_effect=AssertionError('No network')):
        run(args.output)
