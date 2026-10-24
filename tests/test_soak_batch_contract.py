import unittest
from verify_stability_soak import batch_matches


class ConcurrentBatch(unittest.TestCase):
    def test_completion_order_is_not_identity_or_queue_admission(self):
        rows=[dict(source=11,author=5,kind='TEXT'),dict(source=10,author=4,kind='TEXT')]
        self.assertTrue(batch_matches(rows,{10:4,11:5}))
        for bad in ([rows[0],rows[0]],rows[:1],[dict(rows[0],author=4),dict(rows[1],author=5)],[dict(rows[0],kind='REACTION'),rows[1]]):
            self.assertFalse(batch_matches(bad,{10:4,11:5}))
