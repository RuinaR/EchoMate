import copy
import unittest
from run_persona_pilot import complete_group_curriculum


class CompleteGroupCurriculum(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(id=str(i),group='a' if i<2 else 'b',split='train',input_ids=list(range(n))) for i,n in enumerate((200,321,300,301))]
    def test_long_variant_defers_entire_family_without_truncation(self):
        before=copy.deepcopy(self.rows);selected,m=complete_group_curriculum(self.rows,320)
        self.assertEqual([r['id'] for r in selected],['2','3']);self.assertEqual(m['deferred_ids'],['0','1'])
        self.assertEqual(self.rows,before);self.assertEqual(len(selected[-1]['input_ids']),301)
    def test_default_uses_all_records(self):
        selected,m=complete_group_curriculum(self.rows)
        self.assertEqual(selected,self.rows);self.assertEqual(m['deferred_ids'],[])
    def test_manifest_binds_selection(self):
        _,a=complete_group_curriculum(self.rows,320);_,b=complete_group_curriculum(self.rows,384)
        self.assertNotEqual(a['sha256'],b['sha256'])
    def test_evaluation_and_arbitrary_threshold_rejected(self):
        self.rows[0]['split']='independent'
        with self.assertRaises(ValueError):complete_group_curriculum(self.rows,320)
        with self.assertRaises(ValueError):complete_group_curriculum([],319)
