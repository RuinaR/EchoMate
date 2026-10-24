import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from persona_dataset import audit,compiler_hashes
from run_preference_pilot import load_pairs,validate_tiny_proof,VERIFIED_VERSIONS


class PreferenceExportBinding(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.raw=(Path(__file__).parent/'fixtures/persona_evidence_pilot.json').read_bytes();self.source=self.root/'source.json';self.source.write_bytes(self.raw)
        records,_=audit(json.loads(self.raw));selected=[r for r in records if r['split']=='train'][:40]+[r for r in records if r['split']=='development'][:4]
        pairs=dict(schema=1,source_sha256=hashlib.sha256(self.raw).hexdigest(),labeler='codex_editorial_not_human',automatic_judge_approval=False,rows=[])
        self.rows=[]
        for r in selected:
            pairs['rows'].append(dict(id=r['id'],source_family=r['group'],split=r['split'],eligible=True,justification='Current request contradiction explicitly annotated for this synthetic contract.',reasons=['current_intent'],evidence_ids=[],rejected='Ignore the current request.',rejected_issue_span=[0,6],rejected_issue='Ignore'))
            branch=dict(input_ids=[1,2,3],labels=[-100,2,3]);self.rows.append(dict(id=r['id'],group=r['group'],split=r['split'],prompt=[1],chosen=branch,rejected=branch))
        self.pairs=self.root/'pairs.json';self.pairs.write_text(json.dumps(pairs),encoding='utf-8')
        self.summary=dict(source_sha256=hashlib.sha256(self.raw).hexdigest(),pairs_sha256=hashlib.sha256(self.pairs.read_bytes()).hexdigest(),compiler_hashes=compiler_hashes(),pair_compiler_sha256=hashlib.sha256((Path(__file__).parents[1]/'tools/preference_pairs.py').read_bytes()).hexdigest())
        self.write()
    def tearDown(self):self.temp.cleanup()
    def write(self):
        for split in ('train','development'):
            raw=''.join(json.dumps(r)+'\n' for r in self.rows if r['split']==split).encode();(self.root/(split+'.jsonl')).write_bytes(raw);self.summary[split+'_sha256']=hashlib.sha256(raw).hexdigest()
        (self.root/'summary.json').write_text(json.dumps(self.summary),encoding='utf-8')
    def load(self):return load_pairs(self.source,self.pairs,self.root)
    def test_full_source_pair_and_mask_bindings(self):
        _,_,train,dev=self.load();self.assertEqual((len(train),len(dev)),(40,4))
    def test_rehashed_file_cannot_change_source_identity(self):
        self.rows[0]['group']='another-source';self.write()
        with self.assertRaises(ValueError):self.load()
    def test_prompt_loss_leak_and_boolean_token_rejected(self):
        self.rows[0]['chosen']['labels'][0]=1;self.write()
        with self.assertRaises(ValueError):self.load()

    def test_tiny_proof_must_match_quantization_and_real_booleans(self):
        proof=dict(status='TINY_DPO_COMPATIBILITY_NOT_12B_QUALITY',versions=VERIFIED_VERSIONS,cuda=True,single_graph_gradient_verified=True,replay_metrics_exact=True,replay_weights_exact=True,quantization=dict(kind='nf4',double_quant=True,compute_dtype='bfloat16'))
        validate_tiny_proof(proof,VERIFIED_VERSIONS)
        proof['quantization']['double_quant']=False
        with self.assertRaises(ValueError):validate_tiny_proof(proof,VERIFIED_VERSIONS)
        proof['quantization']['double_quant']=True;proof['replay_metrics_exact']='true'
        with self.assertRaises(ValueError):validate_tiny_proof(proof,VERIFIED_VERSIONS)

    def test_boolean_token_is_not_a_vocabulary_id(self):
        self.rows[0]['chosen']['input_ids'][1]=True;self.write()
        with self.assertRaises(ValueError):self.load()
