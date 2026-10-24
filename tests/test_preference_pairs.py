import copy
import hashlib
import json
from pathlib import Path
import unittest
from persona_dataset import audit
from preference_pairs import pair_audit


class PreferencePairContracts(unittest.TestCase):
    def setUp(self):
        self.raw=(Path(__file__).parent/'fixtures/persona_evidence_pilot.json').read_bytes()
        records,_=audit(json.loads(self.raw));r=next(x for x in records if x['split']=='train' and not x['case']['evidence']);self.independent=next(x for x in records if x['split']=='independent')
        self.row=dict(id=r['id'],source_family=r['group'],split=r['split'],eligible=True,justification='Explicit editorial reasoning about a contradictory current request.',reasons=['current_intent'],evidence_ids=[],rejected='I refuse to follow your current request.',rejected_issue_span=[0,8],rejected_issue='I refuse')
        self.pairs=dict(schema=1,source_sha256=hashlib.sha256(self.raw).hexdigest(),labeler='codex_editorial_not_human',automatic_judge_approval=False,rows=[self.row])

    def test_pair_contract_keeps_editorial_limit_and_excludes_ties(self):
        _,accepted,summary=pair_audit(self.raw,self.pairs);self.assertEqual(len(accepted),1)
        self.assertEqual(summary['human_validation'],'NOT_VERIFIED')
        self.row['eligible']=False;self.assertEqual(pair_audit(self.raw,self.pairs)[2]['eligible'],0)

    def test_independent_cannot_be_laundered_or_relabelled(self):
        self.row['id']=self.independent['id'];self.row['split']='train'
        with self.assertRaises(ValueError):pair_audit(self.raw,self.pairs)

    def test_facts_need_real_evidence_and_issue_span_must_match(self):
        self.row['reasons']=['factuality']
        with self.assertRaises(ValueError):pair_audit(self.raw,self.pairs)
        self.row['reasons']=['current_intent'];self.row['rejected_issue']='not in text'
        with self.assertRaises(ValueError):pair_audit(self.raw,self.pairs)
