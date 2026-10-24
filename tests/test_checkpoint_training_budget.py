import copy
import functools
import unittest
from training_budget import estimate,GIB


class CheckpointInputsBudget(unittest.TestCase):
    def setUp(self):
        self.rows={'model.language_model.embed_tokens.weight':dict(shape=[100,32],dtype='BF16')}
        for part in ('q','k','v'):
            self.rows[f'model.language_model.layers.0.self_attn.{part}_proj.weight']=dict(shape=[32,32],dtype='BF16')
        self.cfg=dict(model_type='gemma4_unified_text',num_hidden_layers=2,hidden_size=32,vocab_size=100,intermediate_size=64,head_dim=16,global_head_dim=16)

    def test_explicit_checkpoint_storage_bounds_keep_driver_and_safety(self):
        old=estimate(self.rows,self.cfg,frozen_bf16=True,sequence=64,supervised_tokens=16)
        new=estimate(self.rows,self.cfg,frozen_bf16=True,sequence=64,supervised_tokens=16,checkpoint_inputs=True)
        bound=2*64*32*4+2*64*(32+32)*4+2*64*16*2*4+2*64*64*4
        self.assertEqual(sum(new['checkpoint_input_bounds'].values()),bound)
        self.assertEqual(new['components']['checkpoint_activations'],bound)
        self.assertEqual(new['allocator_driver_bytes'],GIB);self.assertEqual(new['safety_bytes'],2*GIB)
        self.assertLess(new['planning_required_vram'],old['planning_required_vram'])
        self.assertEqual(new['prepared_bytes'],old['prepared_bytes'])

    def test_unknown_or_combined_geometry_cannot_reuse_reduced_activation_plan(self):
        for args in ({'sequence':513},{'rank':8},{'last_layers':1},{'cpu_tied_io':True}):
            with self.assertRaises(ValueError):estimate(self.rows,{**self.cfg,'tie_word_embeddings':True},frozen_bf16=True,checkpoint_inputs=True,**args)
        for cfg in ({**self.cfg,'model_type':'unknown'},{**self.cfg,'hidden_size':4096},{**self.cfg,'head_dim':None}):
            with self.assertRaises(ValueError):estimate(self.rows,cfg,frozen_bf16=True,checkpoint_inputs=True)

    def test_global_query_heads_use_global_head_dimension(self):
        rows=copy.deepcopy(self.rows)
        rows['model.language_model.layers.0.self_attn.q_proj.weight']['shape']=[8192,32]
        cfg={**self.cfg,'head_dim':256,'global_head_dim':512}
        estimate(rows,cfg,frozen_bf16=True,checkpoint_inputs=True)
        rows['model.language_model.layers.0.self_attn.q_proj.weight']['shape']=[8193,32]
        with self.assertRaises(ValueError):estimate(rows,cfg,frozen_bf16=True,checkpoint_inputs=True)

    def test_eval_flag_is_not_active_checkpointing_and_reentrant_is_rejected(self):
        import torch
        from torch.utils.checkpoint import checkpoint
        from transformers import Gemma4UnifiedTextConfig,Gemma4UnifiedForCausalLM
        from peft import get_peft_model,LoraConfig
        from qlora_recipe import training_checkpoint_mode
        torch.set_num_threads(1)
        cfg=Gemma4UnifiedTextConfig(vocab_size=16,hidden_size=32,intermediate_size=64,num_hidden_layers=2,num_attention_heads=2,num_key_value_heads=1,head_dim=16,global_head_dim=16,layer_types=['sliding_attention','full_attention'],max_position_embeddings=64,use_cache=False)
        base=Gemma4UnifiedForCausalLM(cfg).to(torch.bfloat16).eval().requires_grad_(False)
        base.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
        model=get_peft_model(base,LoraConfig(r=4,lora_alpha=8,lora_dropout=.05,target_modules=r'model\.layers\.\d+\.self_attn\.(q_proj|v_proj)',task_type='CAUSAL_LM'))
        self.assertTrue(base.is_gradient_checkpointing);self.assertFalse(base.model.layers[0].training)
        result=training_checkpoint_mode(model)
        self.assertEqual(result['checkpointed_layers'],2);self.assertTrue(base.model.layers[0].training)
        base.model.layers[0]._gradient_checkpointing_func=functools.partial(checkpoint,use_reentrant=True)
        with self.assertRaises(ValueError):training_checkpoint_mode(model)
