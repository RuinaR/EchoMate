import unittest
from copy import deepcopy
from korean_claim_contract import corpus,score,validate,verdict,grouped_parts


class KoreanClaims(unittest.TestCase):
    def test_fixed_authored_ground_truth_and_evidence_variants(self):
        rows=corpus();report=score(rows)
        self.assertGreaterEqual(report['cases'],60);self.assertFalse(report['failures'])
        same=[r for r in rows if r['group']=='reminder-complete']
        self.assertEqual(len({r['text'] for r in same}),1)
        self.assertEqual({verdict(r) for r in same},{'pass','violation','uncertain'})

    def test_wrong_receipt_and_composite_do_not_get_good_clause_credit(self):
        rows={r['id']:r for r in corpus()}
        for key in ('wrong-owner','wrong-guild','wrong-feature','composite-false','cancelled-now'):
            self.assertEqual(verdict(rows[key]),'violation')
        self.assertEqual(verdict(rows['cancelled-past']),'pass')
        self.assertEqual(verdict(rows['composite-unknown']),'uncertain')

    def test_annotation_contract_rejects_unanchored_spans_and_unknown_enums(self):
        for field,value in [('span',[0,10000]),('actor','guessed-user'),('act','string-match'),('value',1)]:
            case=deepcopy(corpus()[0]);case['atoms'][0][field]=value
            with self.assertRaises(ValueError):validate(case)
        rows=corpus()
        with self.assertRaises(ValueError):score(rows+[deepcopy(rows[0])])

    def test_missing_receipt_fields_are_unknown_not_negative_evidence(self):
        case=deepcopy(next(r for r in corpus() if r['id']=='memory-complete-true'))
        del case['evidence']['memory']['receipt']['current']
        self.assertEqual(verdict(case),'uncertain')
        del case['evidence']['memory']['receipt']['owner']
        self.assertEqual(verdict(case),'uncertain')

    def test_utterance_groups_never_cross_development_and_review(self):
        parts=grouped_parts(corpus())
        a={r['group'] for r in parts['development']};b={r['group'] for r in parts['review']}
        self.assertFalse(a&b);self.assertEqual(sum(map(len,parts.values())),len(corpus()))
