"""Actual source retention is independent of text meaning, time and activity."""
import unittest
from echomate_bot.social_evidence import evidence_window,source_ids,trim_frame,reply_recipient


class SourceWindows(unittest.TestCase):
    def rows(self):
        return [dict(id='1',speaker='4',bot=False,text='original request',reply=None),
                dict(id='2',speaker='999',bot=True,text='actual answer',reply='1'),
                *[dict(id=str(i),speaker='4',bot=False,text='extra condition',reply=None) for i in range(3,12)]]

    def test_many_supplements_cannot_remove_actual_bot_and_original_request(self):
        rows=self.rows();window=evidence_window(rows)
        self.assertEqual([r['id'] for r in window],['1','2','8','9','10','11'])
        self.assertEqual(len(rows),11)

    def test_explicit_old_reply_and_latest_bot_each_keep_actual_parent(self):
        rows=self.rows()+[dict(id='12',bot=False,text='new request'),dict(id='13',bot=True,reply='12',text='new answer')]
        window=evidence_window(rows,limit=4,reply='2')
        self.assertEqual([r['id'] for r in window],['1','2','12','13'])

    def test_missing_parent_or_reply_is_never_invented(self):
        rows=self.rows()[1:]
        self.assertEqual(source_ids(rows,reply='absent'),{'2'})
        self.assertFalse(any(r['id']=='1' for r in evidence_window(rows,reply='absent')))

    def test_budget_trimming_preserves_protected_sources_or_stops(self):
        frame={'turns':evidence_window(self.rows())}
        for _ in range(4):self.assertTrue(trim_frame(frame))
        self.assertEqual([r['id'] for r in frame['turns']],['1','2'])
        self.assertFalse(trim_frame(frame))
        frame={'turns':[dict(id='1'),dict(id='2',bot=True,reply='1'),dict(id='3'),dict(id='4',bot=True,reply='3')]}
        self.assertFalse(trim_frame(frame,reply='2'))

    def test_short_existing_packets_have_identical_order_and_fields(self):
        rows=self.rows()[:2]
        self.assertEqual(evidence_window(rows),rows)
        with self.assertRaises(ValueError):evidence_window(rows,limit=3)

    def test_recipient_follows_actual_reply_parent_not_historical_membership(self):
        rows=self.rows()+[dict(id='12',speaker='5',bot=False),dict(id='13',speaker='999',bot=True,reply='12')]
        self.assertEqual(reply_recipient(evidence_window(rows)),'5')
        self.assertIsNone(reply_recipient([dict(id='13',speaker='999',bot=True,reply='missing')]))
