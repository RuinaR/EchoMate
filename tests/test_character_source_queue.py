import copy
import unittest
from character_source_queue import select_topical,mixed_reference_index


class EditorialSourceQueue(unittest.TestCase):
    def row(self,article,text):
        return dict(article_url=article,content=[dict(agent='agent_'+str(i%2+1),message=text+str(i),sentiment='Curious') for i in range(4)])

    def test_shared_article_is_one_family_and_never_training_approval(self):
        data={'a':self.row('https://example.org/article','A question '),'b':self.row('https://example.org/article','A different question '),'c':self.row('','Another topic ')}
        rows,summary=select_topical(data)
        self.assertEqual(len(rows),2);self.assertEqual(summary['training_approved'],0)
        self.assertTrue(all(r['status']=='UNREVIEWED_NOT_TRAINING' for r in rows))
        self.assertEqual(select_topical(dict(reversed(list(data.items())))),(rows,summary))

    def test_exact_duplicate_and_identifier_screen(self):
        original=self.row('','Normal question ');bad=self.row('','Contact person@example.org ')
        rows,summary=select_topical({'a':original,'b':copy.deepcopy(original),'c':bad})
        self.assertEqual(len(rows),1);self.assertEqual(summary['excluded']['exact_dialogue'],1)
        self.assertEqual(summary['excluded']['privacy_or_length'],1)

    def test_invalid_bounds_and_lineage_rejected(self):
        with self.assertRaises(ValueError):select_topical({},maximum=True)
        with self.assertRaises(ValueError):select_topical({'a':self.row(None,'Question ')})

    def test_explicit_unspecified_mix_preserves_rights_and_source_family(self):
        source=dict(dataset='unlicensed-example',license='UNSPECIFIED',sha256='a'*64,revision='pinned',records=[dict(index=0,family='same-persona',dimensions=['emotion']),dict(index=1,family='same-persona',dimensions=['relationship'])])
        with self.assertRaises(ValueError):mixed_reference_index([source])
        rows=mixed_reference_index([source],allow_unspecified_local_research=True)
        self.assertEqual(rows[0]['license'],'UNSPECIFIED');self.assertEqual(rows[0]['split'],rows[1]['split'])
        self.assertTrue(all(not r['raw_training_approved'] and not r['redistribution_approved'] for r in rows))
        for row in source['records']:row['split']='development'
        self.assertTrue(all(r['split']=='development' for r in mixed_reference_index([source],allow_unspecified_local_research=True)))
        source['records'][1]['split']='train'
        with self.assertRaises(ValueError):mixed_reference_index([source],allow_unspecified_local_research=True)
