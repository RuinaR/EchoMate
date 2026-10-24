import copy
import unittest
from unittest.mock import Mock
from run_persona_pilot import observed_admission_floor,clear_unused_before_phase


class ObservedAdmission(unittest.TestCase):
    def setUp(self):
        self.plan=dict(rank=4,sequence=399,supervised_tokens=44,frozen_bf16=True,last_layers=None,planning_required_vram=14000*1024**2)
        self.proof=dict(status='STOPPED',reason='vram',data_hash='data',headers={'shard':'hash'},budget=copy.deepcopy(self.plan),health=dict(free_vram_mib=15004),resource_details=dict(health=dict(free_vram_mib=2020)))
    def floor(self):return observed_admission_floor(self.proof,data_hash='data',headers={'shard':'hash'},plan=self.plan)
    def test_real_guard_shortfall_raises_floor(self):self.assertEqual(self.floor(),15032*1024**2)
    def test_proof_never_reduces_static_reserve(self):
        self.plan['planning_required_vram']=16000*1024**2
        self.assertEqual(self.floor(),16000*1024**2)
    def test_changed_workload_or_nonfailure_rejected(self):
        self.proof['budget']['sequence']=320
        with self.assertRaises(ValueError):self.floor()
        self.proof['budget']['sequence']=399;self.proof['resource_details']['health']['free_vram_mib']=2048
        with self.assertRaises(ValueError):self.floor()
    def test_allocator_policy_not_interchangeable(self):
        with self.assertRaises(ValueError):observed_admission_floor(self.proof,data_hash='data',headers={'shard':'hash'},plan=self.plan,cache_hygiene=True)
    def test_public_cleanup_preserves_live_allocations(self):
        torch=Mock();torch.cuda.memory_allocated.return_value=100;torch.cuda.memory_reserved.side_effect=[200,150]
        self.assertEqual(clear_unused_before_phase(torch,True),dict(allocated_unchanged=100,reserved_before=200,reserved_after=150))
        torch.cuda.empty_cache.assert_called_once();torch.cuda.synchronize.assert_called_once()
    def test_cleanup_never_silently_changes_live_memory(self):
        torch=Mock();self.assertIsNone(clear_unused_before_phase(torch,False));torch.cuda.empty_cache.assert_not_called()
        torch.cuda.memory_allocated.side_effect=[100,90]
        with self.assertRaises(ValueError):clear_unused_before_phase(torch,True)
