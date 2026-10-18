import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.topic_qa import evaluate, CASES

class TopicQATests(unittest.TestCase):
    def test_six_synthetic_scenarios_and_expected_labels(self):
        def fake(turns, *, model):
            case=turns[-1].message_id.removesuffix("_h")
            return next(expected for name,_,_,_,expected in CASES if name==case)
        results=evaluate(judge=fake)
        self.assertEqual(len(results),6)
        self.assertTrue(all(row["correct"] for row in results))
    def test_wrong_prediction_reported(self):
        results=evaluate(judge=lambda turns,*,model:False)
        self.assertTrue(any(not row["correct"] for row in results))
        self.assertFalse(any("메이플" in str(row) for row in results))
