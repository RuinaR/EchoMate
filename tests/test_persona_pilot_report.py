import copy
import unittest
from review_persona_pilot import summarize,render,operation_coverage


class PairedPilotReport(unittest.TestCase):
    def setUp(self):
        row=dict(id='synthetic/card',seconds=2,ttft=.2,output_tokens=20,format_status='visible',text='<script>alert(1)</script>',raw='PRIVATE_RAW_CHANNEL')
        self.report=dict(status='PILOT_COMPLETE_REQUIRES_QUALITY_REVIEW',development_generation_ids=['synthetic/card'],baseline=[row],trials=[dict(lr=.0001,generation=[copy.deepcopy(row)],optimizer_steps=2,development_loss=3,resume_metrics_match=True,resume_weights_match=True,base_sentinels_versions_unchanged=True)])
    def test_metrics_do_not_grant_semantic_quality(self):
        s=summarize(self.report);self.assertEqual(s['arms']['baseline']['seconds']['p50'],2)
        self.assertIn('NOT_VERIFIED',s['automated_quality'])
    def test_previous_adapter_is_also_paired_and_never_auto_approved(self):
        self.report['previous']=copy.deepcopy(self.report['baseline'])
        self.assertIn('previous',summarize(self.report)['arms'])
        self.assertIn('<th>previous</th>',render(self.report))
        self.report['previous'][0]['id']='other'
        with self.assertRaises(ValueError):summarize(self.report)
    def test_partial_or_unpaired_run_rejected(self):
        self.report['trials'][0]['generation'][0]['id']='different'
        with self.assertRaises(ValueError):summarize(self.report)
        self.report['status']='STOPPED'
        with self.assertRaises(ValueError):summarize(self.report)
        self.report['status']='RESOURCE_TRAINING_COMPLETE_NOT_QUALITY'
        with self.assertRaises(ValueError):summarize(self.report)
    def test_html_escapes_visible_text_and_omits_raw(self):
        text=render(self.report);self.assertIn('&lt;script&gt;',text);self.assertNotIn('<script>',text);self.assertNotIn('PRIVATE_RAW_CHANNEL',text)
        self.report['baseline'][0]['format_status']='incomplete'
        self.report['baseline'][0]['text']='INCOMPLETE_PRIVATE_PROSE'
        self.assertNotIn('INCOMPLETE_PRIVATE_PROSE',render(self.report))
    def test_operation_coverage_counts_situations_not_responses(self):
        source=dict(cases=[dict(split='train',relevant_features=['memory'],features={'memory':dict(operation='read',status='success')},responses={str(i):{} for i in range(4)})])
        self.assertEqual(operation_coverage(source)['train'],[dict(feature='memory',operation='read',status='success',situations=1)])
    def test_failed_list_coverage_is_not_inferred_from_memory(self):
        source=dict(cases=[dict(split='development',relevant_features=['reminder'],features={'reminder':dict(operation='list',status='failed')})])
        self.assertEqual(operation_coverage(source)['train'],[])
        self.assertEqual(operation_coverage(source)['development'][0]['status'],'failed')
