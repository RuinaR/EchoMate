import unittest
from training_budget import estimate,GIB


class TrainingBudget(unittest.TestCase):
    def test_suffix_budget_is_explicitly_conditional_on_prefix_gradient_proof(self):
        rows={f'model.language_model.layers.{i}.self_attn.q_proj.weight':dict(shape=[32,32],dtype='BF16') for i in range(3)}
        cfg=dict(num_hidden_layers=3,hidden_size=32,vocab_size=100)
        result=estimate(rows,cfg,last_layers=1,frozen_bf16=True)
        self.assertEqual(result['target_count'],1)
        self.assertIn('.layers.2.',result['targets'][0]['name'])
        self.assertTrue(result['frozen_prefix_gradient_proof_required'])
        self.assertFalse(estimate(rows,cfg)['frozen_prefix_gradient_proof_required'])
        for value in (0,4,True):
            with self.assertRaises(ValueError):estimate(rows,cfg,last_layers=value)

    def test_embedding_upcast_and_only_text_adapter_targets_are_counted(self):
        rows={
            'model.language_model.embed_tokens.weight':dict(shape=[100,32],dtype='BF16'),
            'model.language_model.layers.0.self_attn.q_proj.weight':dict(shape=[32,32],dtype='BF16'),
            'model.embed_vision.q_proj.weight':dict(shape=[32,32],dtype='BF16')}
        r=estimate(rows,dict(num_hidden_layers=2,hidden_size=32,vocab_size=100))
        self.assertEqual(r['fp32_parameters'],3200);self.assertEqual(r['upcast_overlap_bytes'],6400)
        self.assertEqual(r['target_count'],1);self.assertEqual(r['adapter_parameters'],256)
        self.assertGreater(r['planning_required_vram'],4*GIB)
    def test_longer_sequences_cost_more_and_probe_bounds_are_strict(self):
        rows={'model.language_model.x.q_proj.weight':dict(shape=[32,32],dtype='BF16')}
        c=dict(num_hidden_layers=2,hidden_size=32,vocab_size=100)
        self.assertGreater(estimate(rows,c,sequence=128)['planning_required_vram'],estimate(rows,c)['planning_required_vram'])
        with self.assertRaises(ValueError):estimate(rows,c,sequence=100000)
