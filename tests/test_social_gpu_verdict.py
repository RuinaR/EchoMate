"""QA scores must not reward a classifier exception as successful silence."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from verify_social_gpu import result_health,decision_contract


class GPUVerdict(unittest.TestCase):
    def test_silence_does_not_prove_expected_end_or_rest_effect(self):
        trace={'outcome':'silence','calls':[],'decision':{'social':{'evidence':'social_no_response_expected'}}}
        case={'expected_evidence':'social_end','expected_state_effect':'rest_without_cancellation'}
        self.assertFalse(result_health(decision_contract(case,[trace]),[],[trace])['passed'])

    def test_actual_evidence_and_effect_must_both_match(self):
        case={'expected_evidence':'social_end','expected_state_effect':'rest_without_cancellation'}
        trace={'decision':{'social':{'evidence':'social_end','state_effect':'rest_without_cancellation'}}}
        self.assertTrue(decision_contract(case,[trace]))
        trace['decision']['social']['state_effect']='other'
        self.assertFalse(decision_contract(case,[trace]))
        trace['decision']['social'].pop('state_effect')
        self.assertFalse(decision_contract(case,[trace]))

    def test_missing_latest_observation_cannot_reuse_older_success(self):
        case={'expected_evidence':'social_end'}
        good={'decision':{'social':{'evidence':'social_end'}}}
        for latest in ({'decision':None},{'decision':{}},{'decision':{'social':None}}):
            self.assertFalse(decision_contract(case,[good,latest]))
        self.assertFalse(decision_contract(case,[]))

    def test_old_protocol_without_explicit_branch_contract_is_unchanged(self):
        self.assertTrue(decision_contract({'respond':False},[]))

    def test_failed_negative_case_is_not_pass(self):
        row=result_health(True,[{'method':'assess_social','error':'ValueError'}],
                          [{'outcome':'failed','calls':[{'outcome':'failed'}]}])
        self.assertFalse(row['passed']);self.assertTrue(row['behavior_ok'])
        self.assertEqual(row['physical_calls'],1);self.assertEqual(row['worker_failures'],1)

    def test_optional_link_fallback_preserves_behavior_but_not_model_success(self):
        row=result_health(True,[{'method':'link_direct','error':'ValueError'}],
                          [{'outcome':'sent','calls':[{'outcome':'failed'}]}])
        self.assertTrue(row['behavior_ok']);self.assertFalse(row['inference_ok'])
        self.assertFalse(row['passed'])

    def test_silent_metadata_path_is_valid_without_gpu_call(self):
        row=result_health(True,[],[{'outcome':'silence','calls':[]}])
        self.assertTrue(row['passed']);self.assertEqual(row['physical_calls'],0)

    def test_completed_and_cancelled_worker_attempts_count_separately(self):
        row=result_health(False,[],[{'outcome':'cancelled','calls':[{'outcome':'completed'},{'outcome':'cancelled'}]}])
        self.assertEqual(row['physical_calls'],2);self.assertEqual(row['worker_cancelled'],1)
        self.assertFalse(row['passed'])
