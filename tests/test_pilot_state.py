import copy
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch
import torch
from pilot_state import cosine,train_window,save,inspect,restore


class Toy(torch.nn.Module):
    def __init__(self):
        super().__init__();self.embedding=torch.nn.Embedding(16,4);self.drop=torch.nn.Dropout(.05);self.head=torch.nn.Linear(4,16)
    def forward(self,ids):return self.head(self.drop(self.embedding(ids)))
    def save_pretrained(self,path,**kwargs):
        from safetensors.torch import save_file
        path.mkdir();(path/'adapter_config.json').write_text('{}');save_file(self.state_dict(),path/'adapter_model.safetensors')


def loss(model,ids,labels):
    return torch.nn.functional.cross_entropy(model(ids)[:,:-1].reshape(-1,16),labels[:,1:].reshape(-1),ignore_index=-100)


class PilotState(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1);torch.manual_seed(32);random.seed(32)
        self.model=Toy();self.opt=torch.optim.AdamW(self.model.parameters(),lr=.0001);self.sched=cosine(self.opt,4)
        self.batches=[([1,2,3],[-100,2,3]),([4,5,6,7],[-100,-100,6,7])]
    def test_dropout_rng_optimizer_scheduler_resume_matches_uninterrupted(self):
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            p=Path(folder)/'step1';train_window(self.model,self.batches,self.opt,self.sched,loss)
            save(p,self.model,self.opt,self.sched,step=1,data_hash='fixed',config=dict(rank=4,dropout=.05))
            rng=random.random();expected=train_window(self.model,self.batches,self.opt,self.sched,loss);weights=copy.deepcopy(self.model.state_dict())
            other=Toy();from safetensors.torch import load_file
            other.load_state_dict(load_file(p/'adapter/adapter_model.safetensors'));opt=torch.optim.AdamW(other.parameters(),lr=.0001);sched=cosine(opt,4)
            self.assertEqual(restore(p,opt,sched,data_hash='fixed',config=dict(rank=4,dropout=.05)),1)
            self.assertEqual(random.random(),rng);actual=train_window(other,self.batches,opt,sched,loss)
            self.assertEqual(actual,expected)
            for name,v in other.state_dict().items():torch.testing.assert_close(v,weights[name],atol=0,rtol=0)
    def test_accumulation_is_token_weighted_not_microbatch_weighted(self):
        self.model.drop.p=0;other=copy.deepcopy(self.model)
        opt=torch.optim.SGD(self.model.parameters(),lr=.01);sched=cosine(opt,2)
        batches=[([1,2,3],[-100,-100,3]),([4,5,6,7],[-100,5,6,7])]
        train_window(self.model,batches,opt,sched,loss,max_norm=100)
        opt2=torch.optim.SGD(other.parameters(),lr=.01);total=sum(loss(other,torch.tensor([ids]),torch.tensor([labels]))*n/4 for (ids,labels),n in zip(batches,(1,3)))
        total.backward();opt2.step()
        for a,b in zip(self.model.parameters(),other.parameters()):torch.testing.assert_close(a,b)

    def test_phase_observer_does_not_change_dropout_metrics_or_updates(self):
        rng=torch.get_rng_state();other=copy.deepcopy(self.model);events=[]
        expected=train_window(self.model,self.batches,self.opt,self.sched,loss)
        torch.set_rng_state(rng);opt=torch.optim.AdamW(other.parameters(),lr=.0001);sched=cosine(opt,4)
        actual=train_window(other,self.batches,opt,sched,loss,observe=events.append)
        self.assertEqual(events,['forward_1','backward_1','forward_2','backward_2','optimizer_step'])
        self.assertEqual(actual,expected)
        for a,b in zip(self.model.parameters(),other.parameters()):torch.testing.assert_close(a,b,atol=0,rtol=0)

    def test_observer_guard_stops_before_optimizer_and_scheduler(self):
        from unittest.mock import Mock
        optimizer=Mock();scheduler=Mock()
        with self.assertRaisesRegex(RuntimeError,'reserve'):
            train_window(self.model,self.batches,optimizer,scheduler,loss,observe=Mock(side_effect=RuntimeError('reserve')))
        optimizer.step.assert_not_called();scheduler.step.assert_not_called()
    def test_corruption_extra_file_or_wrong_binding_rejected_before_load(self):
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            p=Path(folder)/'saved';save(p,self.model,self.opt,self.sched,step=0,data_hash='a',config={})
            with self.assertRaises(ValueError):inspect(p,data_hash='b',config={})
            (p/'state.pt').write_bytes(b'corrupt')
            with patch('torch.load',side_effect=AssertionError('must not load')):
                with self.assertRaises(ValueError):restore(p,self.opt,self.sched,data_hash='a',config={})
    def test_failed_save_preserves_prior_checkpoint_and_cleans_own_temp(self):
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            p=Path(folder)/'good';save(p,self.model,self.opt,self.sched,step=0,data_hash='a',config={});old=(p/'state.pt').read_bytes()
            with patch('torch.save',side_effect=OSError('disk write')):
                with self.assertRaises(OSError):save(Path(folder)/'failed',self.model,self.opt,self.sched,step=1,data_hash='a',config={})
            self.assertEqual((p/'state.pt').read_bytes(),old);self.assertEqual(list(Path(folder).iterdir()),[p])
            with self.assertRaises(FileExistsError):save(p,self.model,self.opt,self.sched,step=0,data_hash='a',config={})

    def test_transient_windows_publish_lock_retries_without_rewriting(self):
        import os
        original=os.rename
        denied=PermissionError('Synthetic sharing lock');denied.winerror=32
        calls=[]
        def publish(source,target):
            calls.append((source,target))
            if len(calls)==1:raise denied
            return original(source,target)
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            p=Path(folder)/'saved'
            with patch('pilot_state.os.rename',side_effect=publish),patch('pilot_state.time.sleep') as sleep:
                save(p,self.model,self.opt,self.sched,step=0,data_hash='a',config={})
            self.assertEqual(len(calls),2);sleep.assert_called_once_with(.02)
            inspect(p,data_hash='a',config={})
            self.assertEqual(list(Path(folder).iterdir()),[p])

    def test_persistent_windows_publish_lock_is_bounded_and_cleans_partial(self):
        denied=PermissionError('Synthetic persistent sharing lock');denied.winerror=5
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            p=Path(folder)/'saved'
            with patch('pilot_state.os.rename',side_effect=denied) as rename,patch('pilot_state.time.sleep') as sleep:
                with self.assertRaises(PermissionError):
                    save(p,self.model,self.opt,self.sched,step=0,data_hash='a',config={})
            self.assertEqual(rename.call_count,5);self.assertEqual(sleep.call_count,4)
            self.assertEqual(list(Path(folder).iterdir()),[])

    def test_unified_checkpointing_with_dropout_accumulation(self):
        from transformers import Gemma4UnifiedTextConfig,Gemma4UnifiedForCausalLM
        from peft import get_peft_model,LoraConfig
        from qlora_recipe import supervised_loss
        cfg=Gemma4UnifiedTextConfig(vocab_size=16,hidden_size=32,intermediate_size=64,num_hidden_layers=2,
            num_attention_heads=2,num_key_value_heads=1,head_dim=16,global_head_dim=16,
            layer_types=['sliding_attention','full_attention'],max_position_embeddings=64,use_cache=False)
        base=Gemma4UnifiedForCausalLM(cfg).to(torch.bfloat16);base.requires_grad_(False)
        model=get_peft_model(base,LoraConfig(r=4,lora_alpha=8,lora_dropout=.05,target_modules=r'model\.layers\.\d+\.self_attn\.(q_proj|v_proj)',task_type='CAUSAL_LM'))
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
        frozen=[(p,p.detach().clone()) for p in model.parameters() if not p.requires_grad]
        opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=.0001);sched=cosine(opt,2)
        row=train_window(model,self.batches,opt,sched,supervised_loss)
        self.assertGreater(row['gradient_norm'],0);self.assertEqual(row['supervised_tokens'],4)
        self.assertTrue(all(torch.equal(p,v) for p,v in frozen))

    def test_12b_runner_rejects_unproven_recipe_before_model_or_network(self):
        from run_persona_pilot import run
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            root=Path(folder);tiny=root/'tiny.json';proof=root/'proof.json'
            tiny.write_text(json.dumps(dict(status='TINY_NEW_RECIPE_PASS_NOT_12B_QUALITY',replay={'loss':1})))
            proof.write_text(json.dumps(dict(deterministic=False,repeat_metrics_equal=True,repeat_max_adapter_difference=0)))
            with patch('echomate_bot.model_registry.ModelValidator.validate',side_effect=AssertionError('must not open model')):
                with self.assertRaisesRegex(ValueError,'backward replay proof'):run('unused','unused','unused',root/'denied',tiny,proof)
    def test_checkpoint_extra_file_and_wrong_config_are_rejected(self):
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            p=Path(folder)/'saved';save(p,self.model,self.opt,self.sched,step=0,data_hash='a',config={'rank':4})
            with self.assertRaises(ValueError):inspect(p,data_hash='a',config={'rank':8})
            (p/'extra.txt').write_text('unbound extra')
            with self.assertRaises(ValueError):inspect(p,data_hash='a',config={'rank':4})
