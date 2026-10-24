import unittest


class SelectedLoss(unittest.TestCase):
    def test_frozen_prefix_has_no_graph_when_only_suffix_adapters_train(self):
        import torch
        from transformers import Gemma4UnifiedTextConfig,Gemma4UnifiedForCausalLM
        from peft import get_peft_model,LoraConfig
        from qlora_recipe import supervised_loss,prepare_suffix_inputs
        cfg=Gemma4UnifiedTextConfig(vocab_size=32,hidden_size=32,intermediate_size=64,num_hidden_layers=3,
            num_attention_heads=2,num_key_value_heads=1,head_dim=16,global_head_dim=16,
            layer_types=['sliding_attention','sliding_attention','full_attention'],max_position_embeddings=64,use_cache=False)
        base=Gemma4UnifiedForCausalLM(cfg).to(torch.bfloat16)
        base.requires_grad_(False)
        model=get_peft_model(base,LoraConfig(r=2,lora_alpha=4,lora_dropout=0,target_modules=r'model\.layers\.2\.self_attn\.(q_proj|v_proj)',task_type='CAUSAL_LM'))
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
        prepare_suffix_inputs(model,2)
        flags={}
        def observer(index):
            def observed(module,args,result):flags[index]=result.requires_grad
            return observed
        handles=[layer.register_forward_hook(observer(i)) for i,layer in enumerate(base.model.layers)]
        try:
            ids=torch.tensor([[2,4,6,8,1]]);loss=supervised_loss(model,ids,ids)
            self.assertEqual(flags,{0:False,1:False,2:True})
            loss.backward()
            self.assertTrue(any(p.grad is not None and p.grad.abs().sum()>0 for p in model.parameters() if p.requires_grad))
            self.assertFalse(base.get_input_embeddings().weight.requires_grad)
        finally:
            for handle in handles:handle.remove()

    def test_selected_causal_positions_equal_full_loss_and_gradients(self):
        import torch
        from transformers import Gemma4UnifiedTextConfig,Gemma4UnifiedForCausalLM
        from qlora_recipe import supervised_loss
        torch.manual_seed(20261024)
        cfg=Gemma4UnifiedTextConfig(vocab_size=32,hidden_size=32,intermediate_size=64,num_hidden_layers=2,
            num_attention_heads=2,num_key_value_heads=1,head_dim=16,global_head_dim=16,
            layer_types=['sliding_attention','full_attention'],max_position_embeddings=64,use_cache=False)
        model=Gemma4UnifiedForCausalLM(cfg).eval()
        ids=torch.tensor([[2,4,6,8,10,12,14,1]]);labels=ids.clone();labels[:,:4]=-100;labels[:,5]=-100
        full=model(input_ids=ids,labels=labels).loss;full.backward()
        expected={n:p.grad.clone() for n,p in model.named_parameters() if p.grad is not None}
        model.zero_grad(set_to_none=True)
        selected=supervised_loss(model,ids,labels);selected.backward()
        torch.testing.assert_close(full,selected)
        for name,p in model.named_parameters():
            if name in expected:torch.testing.assert_close(p.grad,expected[name],atol=1e-6,rtol=1e-4)
        with self.assertRaises(ValueError):supervised_loss(model,ids,torch.full_like(ids,-100))

    def test_bf16_plan_removes_conversion_overlap_but_retains_reserves(self):
        from training_budget import estimate,GIB
        rows={'model.language_model.embed_tokens.weight':dict(shape=[100,32],dtype='BF16'),
              'model.language_model.layers.0.self_attn.q_proj.weight':dict(shape=[32,32],dtype='BF16')}
        cfg=dict(num_hidden_layers=2,hidden_size=32,vocab_size=100)
        baseline=estimate(rows,cfg);candidate=estimate(rows,cfg,frozen_bf16=True,supervised_tokens=8)
        self.assertEqual(candidate['prepared_bytes'],baseline['prepared_bytes']-6400)
        self.assertEqual(candidate['upcast_overlap_bytes'],0)
        self.assertEqual(candidate['safety_bytes'],2*GIB)
        self.assertEqual(candidate['allocator_driver_bytes'],GIB)
        with self.assertRaises(ValueError):estimate(rows,cfg,supervised_tokens=64)
