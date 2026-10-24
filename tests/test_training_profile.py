import copy
import unittest
from unittest.mock import Mock
from training_profile import audit_report,PhasePeaks,GIB,MIB
from training_budget import estimate


class ProfileAccounting(unittest.TestCase):
    def report(self):
        return dict(budget=dict(planning_required_vram=14*GIB),health=dict(free_vram_mib=15020),
            stages=[dict(health=dict(free_vram_mib=2266),gpu_allocated=11*GIB,
                gpu_reserved=12*GIB,gpu_peak_allocated=11*GIB,gpu_peak_reserved=12*GIB)])

    def test_reserved_contains_allocated_not_two_additive_reserves(self):
        v=audit_report(self.report())
        self.assertEqual(v['aggregate_envelope_plus_safety_bytes'],(15020-2266)*MIB+2*GIB)
        self.assertEqual(v['reserved_plus_safety_bytes'],14*GIB)
        self.assertLess(v['static_minus_observed_envelope_bytes'],0)
        self.assertFalse(v['reusable_admission'])

    def test_bad_or_missing_measurements_never_authorize_execution(self):
        for value in (-1,True,float('nan')):
            r=self.report();r['stages'][0]['health']['free_vram_mib']=value
            with self.assertRaises(ValueError):audit_report(r)
        r=self.report();r['stages']=[]
        with self.assertRaises(ValueError):audit_report(r)

    def test_failed_stage_is_not_safe_even_if_allocated_is_small(self):
        r=self.report();r['stages'][0]['health']['free_vram_mib']=2047
        self.assertFalse(audit_report(r)['safe_stage_samples'])
        r['stages'][0]['health']['free_vram_mib']=2048
        self.assertTrue(audit_report(r)['safe_stage_samples'])

    def test_component_breakdown_reconciles_without_changing_old_formula(self):
        rows={'model.language_model.embed_tokens.weight':dict(shape=[100,32],dtype='BF16'),
              'model.language_model.layers.0.self_attn.q_proj.weight':dict(shape=[32,32],dtype='BF16')}
        for frozen in (True,False):
            r=estimate(rows,dict(num_hidden_layers=2,hidden_size=32,vocab_size=100),frozen_bf16=frozen)
            c=r['components']
            self.assertEqual(sum(c[k] for k in ('nf4_with_scales','frozen_embedding','other_floating')),r['prepared_bytes'])
            self.assertEqual(sum(c[k] for k in ('adapter_parameters','adapter_gradients','optimizer_moments','adapter_save_copy')),r['adapter_state_bytes'])
            self.assertEqual(c['checkpoint_activations']+c['selected_logits_workspace']+c['backward_workspace'],r['backward_planning_bytes'])
            self.assertEqual(r['planning_required_vram'],max(r['prepared_bytes']+r['upcast_overlap_bytes'],r['prepared_bytes']+r['adapter_state_bytes']+r['backward_planning_bytes'])+3*GIB)

    def test_phase_reset_preserves_lifetime_peak_and_never_clears_cache(self):
        t=Mock();t.cuda.max_memory_allocated.return_value=100;t.cuda.max_memory_reserved.return_value=200
        t.cuda.memory_allocated.return_value=90;t.cuda.memory_reserved.return_value=190
        p=PhasePeaks(t,True);v=p.boundary('first_forward')
        self.assertEqual(v['peak_reserved'],200)
        t.cuda.max_memory_allocated.return_value=50;t.cuda.max_memory_reserved.return_value=60
        self.assertEqual(p.peaks(),(100,200))
        t.cuda.reset_peak_memory_stats.assert_called_once();t.cuda.empty_cache.assert_not_called()

    def test_profiling_disabled_has_no_cuda_side_effect(self):
        t=Mock();p=PhasePeaks(t)
        self.assertIsNone(p.boundary('anything'));self.assertFalse(t.mock_calls)
