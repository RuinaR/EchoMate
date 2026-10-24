"""A calibration gate must fail even with a superficially high score."""
import json
import unittest
from operation_verifier_probe import calibration,messages,gate


class CalibrationContract(unittest.TestCase):
    def records(self):
        return [dict(case=c['id'],order=o,gold=c['gold'],predicted=c['gold'])
                for c in calibration() for o in (0,1)]

    def test_gold_and_case_id_are_not_model_input(self):
        c=calibration()[0];ms,mapping=messages(c)
        payload=json.loads(ms[-1]['content'])
        self.assertEqual(set(payload),{'evidence','answer'})
        self.assertNotIn('gold',ms[-1]['content'])
        _,rotated=messages(c,1);self.assertNotEqual(mapping,rotated)

    def test_one_unsafe_miss_or_false_veto_blocks_high_accuracy(self):
        self.assertTrue(gate(self.records())['eligible'])
        for gold,predicted in [('violation','pass'),('violation','uncertain'),('pass','violation')]:
            rows=self.records();next(r for r in rows if r['gold']==gold)['predicted']=predicted
            self.assertFalse(gate(rows)['eligible'])

    def test_incomplete_duplicated_and_changed_gold_are_rejected(self):
        rows=self.records()
        self.assertFalse(gate(rows[:-1])['eligible'])
        self.assertFalse(gate(rows[:-1]+[rows[0]])['eligible'])
        rows[0]['gold']='violation';self.assertFalse(gate(rows)['eligible'])
