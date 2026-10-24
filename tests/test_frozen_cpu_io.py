import unittest
import torch
from frozen_cpu_io import install,verify
from training_budget import estimate,GIB


class FrozenIO(unittest.TestCase):
    def model(self):
        from transformers import Gemma4UnifiedTextConfig,Gemma4UnifiedForCausalLM
        torch.set_num_threads(1);torch.manual_seed(17)
        cfg=Gemma4UnifiedTextConfig(vocab_size=16,hidden_size=32,intermediate_size=64,num_hidden_layers=2,
            num_attention_heads=2,num_key_value_heads=1,head_dim=16,global_head_dim=16,
            layer_types=['sliding_attention','full_attention'],max_position_embeddings=64,use_cache=False)
        return Gemma4UnifiedForCausalLM(cfg).to(torch.bfloat16).requires_grad_(False).eval()

    def test_scaled_embedding_and_full_logits_unchanged_on_cpu(self):
        m=self.model();ids=torch.tensor([[1,2,3]])
        before=m.get_input_embeddings()(ids).detach().clone()
        logits=m(input_ids=ids,use_cache=False).logits.detach().clone()
        info=install(m);verify(m)
        self.assertTrue(info['same_cpu_parameter'])
        torch.testing.assert_close(m.get_input_embeddings()(ids),before,atol=0,rtol=0)
        torch.testing.assert_close(m(input_ids=ids,use_cache=False).logits,logits,atol=0,rtol=0)
        with self.assertRaises(ValueError):install(m)

    def test_cpu_head_keeps_graph_to_hidden_and_weight_frozen(self):
        m=self.model();head=m.get_output_embeddings();x=torch.randn(2,32,dtype=torch.bfloat16,requires_grad=True)
        head(x).float().sum().backward();expected=x.grad.clone();x.grad=None
        install(m);m.get_output_embeddings()(x).float().sum().backward()
        torch.testing.assert_close(x.grad,expected,atol=0,rtol=0)
        self.assertFalse(m.get_output_embeddings().weight.requires_grad)

    def test_primary_device_anchor_is_zero_storage_and_frozen(self):
        m=self.model();original_device=m.device;install(m)
        anchor=m._research_execution_device
        self.assertEqual(anchor.numel(),0);self.assertFalse(anchor.requires_grad)
        self.assertEqual(m.device,original_device)
        m._research_execution_device=torch.nn.Parameter(torch.ones(1),requires_grad=False)
        with self.assertRaises(ValueError):verify(m)

    def test_untied_or_trainable_base_rejected(self):
        m=self.model();m.get_output_embeddings().weight=torch.nn.Parameter(m.get_output_embeddings().weight.clone(),requires_grad=False)
        with self.assertRaises(ValueError):install(m)
        m=self.model();m.get_input_embeddings().weight.requires_grad_(True)
        with self.assertRaises(ValueError):install(m)

    def test_io_budget_retains_full_gpu_load_peak_and_host_reserve(self):
        rows={'model.language_model.embed_tokens.weight':dict(shape=[100,32],dtype='BF16'),
            'model.language_model.layers.0.self_attn.q_proj.weight':dict(shape=[32,32],dtype='BF16')}
        cfg=dict(num_hidden_layers=2,hidden_size=32,vocab_size=100,tie_word_embeddings=True)
        base=estimate(rows,cfg,frozen_bf16=True);cpu=estimate(rows,cfg,frozen_bf16=True,cpu_tied_io=True)
        self.assertEqual(cpu['prepared_bytes'],base['prepared_bytes'])
        self.assertEqual(cpu['training_prepared_vram_bytes'],base['prepared_bytes']-6400)
        self.assertGreaterEqual(cpu['planning_required_vram'],cpu['prepared_bytes']+3*GIB)
        self.assertEqual(cpu['safety_bytes'],2*GIB)
        self.assertGreater(cpu['cpu_offload_reserve_bytes'],6400+GIB)
        for kwargs in ({'frozen_bf16':False},{'frozen_bf16':True}):
            with self.assertRaises(ValueError):estimate(rows,{**cfg,'tie_word_embeddings':False},cpu_tied_io=True,**kwargs)
