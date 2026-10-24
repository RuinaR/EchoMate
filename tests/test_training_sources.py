import copy
import io
import json
from pathlib import Path
import tarfile
import unittest
from unittest.mock import patch

from acquire_training_situations import select, episodes
from curate_training_situations import build, lineage
from persona_dataset import audit
from run_persona_pilot import pilot_protocol


def ep(seed, other, family='convai2'):
    return dict(personas=[['fictional A'],['fictional B']],context_dataset=family,
        free_turker_utterance=seed,guided_turker_utterance=other,
        dialog=[[0,'What should I try this weekend?'],[1,'Perhaps something unfamiliar.']])


class TrainingSources(unittest.TestCase):
    def test_transitive_seed_closure_excludes_prior_evaluation(self):
        rows=[ep('old seed','middle seed'),ep('middle seed','next seed'),ep('next seed','last seed'),ep('fresh start','new reply')]
        selected,summary=select(rows,{0})
        self.assertEqual([r['source_index'] for r in selected],[3])
        self.assertEqual(summary['excluded']['prior_evaluation_or_shared_seed'],3)
    def test_connected_sources_never_cross_split(self):
        selected,_=select([ep('shared seed','reply one'),ep('shared seed','reply two')],set())
        self.assertEqual(len({r['component'] for r in selected}),1)
        self.assertEqual(len({r['split'] for r in selected}),1)
    def test_nc_family_and_private_contact_excluded(self):
        selected,summary=select([ep('a','b','empathetic_dialogues'),ep('mail user@example.invalid','hi')],set())
        self.assertFalse(selected);self.assertEqual(sum(summary['excluded'].values()),2)
    def test_duplicate_source_dialogue_is_not_new_situation(self):
        selected,summary=select([ep('a','b'),ep('a','b')],set())
        self.assertEqual(len(selected),1);self.assertEqual(summary['excluded']['exact_dialogue_duplicate'],1)
    def test_archive_checksum_checked_before_parse(self):
        with self.assertRaisesRegex(ValueError,'checksum'):episodes(b'not an archive')
    def test_link_member_rejected_without_extraction(self):
        import hashlib
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode='w:gz') as tar:
            member=tarfile.TarInfo('train.json');member.type=tarfile.SYMTYPE;member.linkname='../private';tar.addfile(member)
        raw=stream.getvalue()
        with patch('acquire_training_situations.ARCHIVE_SHA',hashlib.sha256(raw).hexdigest()):
            with self.assertRaisesRegex(ValueError,'regular'):episodes(raw)
    def setUp(self):
        self.original=json.loads((Path(__file__).parent/'fixtures/persona_evidence_pilot.json').read_text('utf-8'))
        self.queue=[dict(source_index=1,split='train',component='a'*64,dialogue_sha256='b'*64,license='CC-BY-4.0',source_family='convai2')]
        self.tsv='1|전시회에 혼자 가도 괜찮을까?|네 속도로 둘러볼 수 있겠어. 편하게 가 봐.|혼자만의 전시 투어라니 좋네. 발길 가는 대로 가자.|관람 시간과 안내 규칙만 먼저 확인해.|같이 갈 사람 없다고 네 일정까지 접진 마.|outing'
    def test_private_targets_require_bound_attribution(self):
        data,summary=build(self.original,self.queue,self.tsv)
        self.assertEqual(summary['new_conditional_responses'],4)
        self.assertEqual(data['cases'][-1]['license'],'CC-BY-4.0')
        del data['source_manifest']['attribution']
        with self.assertRaises(ValueError):audit(data)
    def test_source_split_change_rejected(self):
        data,_=build(self.original,self.queue,self.tsv);data['cases'][-1]['split']='independent'
        with self.assertRaisesRegex(ValueError,'reserved split'):lineage(data,self.queue,self.original)
    def test_derivative_cannot_be_laundered_into_mit(self):
        data,_=build(self.original,self.queue,self.tsv);data['cases'][-1]['license']='MIT'
        with self.assertRaisesRegex(ValueError,'relabeled'):lineage(data,self.queue,self.original)
    def test_unannotated_high_risk_response_rejected(self):
        with self.assertRaisesRegex(ValueError,'bounded claim'):build(self.original,self.queue,self.tsv.replace('outing','unread_memory'))
    def test_nc_license_or_unknown_source_rejected(self):
        q=copy.deepcopy(self.queue);q[0]['license']='CC-BY-NC-4.0'
        with self.assertRaises(ValueError):build(self.original,q,self.tsv)
        with self.assertRaises(ValueError):build(self.original,[],self.tsv)
    def test_complete_dataset_protocol_no_silent_128_row_truncation(self):
        self.assertEqual(pilot_protocol(264,56,[1e-4]),dict(optimizer_steps=66,learning_rates=(1e-4,)))
        for train,dev,rates in [(513,56,[1e-4]),(264,55,[1e-4]),(264,56,[1e-4,1e-4]),(264,56,[.01])]:
            with self.assertRaises(ValueError):pilot_protocol(train,dev,rates)
    def test_original_card_cannot_be_rewritten(self):
        data,_=build(self.original,self.queue,self.tsv);data['characters']['gentle']['values']='fabricated'
        with self.assertRaises(ValueError):lineage(data,self.queue,self.original)
