import json
import hashlib
from pathlib import Path
import tempfile
import unittest


class CompactData(unittest.TestCase):
    def test_full_export_rejects_duplicate_source_and_prompt_label_training(self):
        from compact_training import load_full_records
        source=Path('tests/fixtures/conditioned_curriculum.json');data=json.loads(source.read_text('utf-8'))
        with tempfile.TemporaryDirectory(dir='local_data') as temp:
            root=Path(temp);summary=dict(status='TOKENIZER_MASK_PASS_NOT_TRAINING',source_schema=2,
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),tokenizer_artifact_hashes={})
            for n in ('config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja'):
                (root/n).write_bytes(b'synthetic');summary['tokenizer_artifact_hashes'][n]=hashlib.sha256(b'synthetic').hexdigest()
            train=[]
            def save(split,rows):
                raw=''.join(json.dumps(r)+'\n' for r in rows).encode();(root/(split+'.jsonl')).write_bytes(raw)
                summary[split+'_sha256']=hashlib.sha256(raw).hexdigest();(root/'summary.json').write_text(json.dumps(summary),encoding='utf-8')
            for split in ('train','validation'):
                rows=[dict(id=c['id']+'-'+k,group=c['source_group'],split=split,input_ids=[2,3,4,5,1],labels=[-100,-100,-100,5,1],prompt_tokens=3)
                    for c in data['scenarios'] if c['split']==split for k in data['characters']]
                save(split,rows)
                if split=='train':train=rows
            self.assertEqual(len(load_full_records(root,source,root)),60)
            train[1]['id']=train[0]['id'];save('train',train)
            with self.assertRaisesRegex(ValueError,'source binding'):load_full_records(root,source,root)
            train[1]['id']=data['scenarios'][0]['id']+'-playful';train[0]['labels'][0]=2;save('train',train)
            with self.assertRaisesRegex(ValueError,'boundary'):load_full_records(root,source,root)

    def test_compact_sources_keep_original_pilot_and_final_corpus_separate(self):
        from compact_training import compile_records
        class Tokenizer:
            all_special_tokens=['<control>']
            def encode(self,text,**kwargs):return list(text.encode('utf-8'))
            def apply_chat_template(self,messages,add_generation_prompt=False,tokenize=False,**kwargs):
                text='prompt:' if add_generation_prompt else 'prompt:'+messages[-1]['content']+'!'
                return dict(input_ids=self.encode(text)) if tokenize else text
        source=Path('tests/fixtures/compact_training.json')
        records=compile_records(Tokenizer(),source)
        train={r['group'] for r in records if r['split']=='train'}
        val={r['group'] for r in records if r['split']=='validation'}
        self.assertFalse(train&val);self.assertEqual(len(train),4);self.assertEqual(len(val),2)
        data=json.loads(source.read_text('utf-8'));data['cases'][0]['responses']['gentle']='가'*100
        with tempfile.TemporaryDirectory(dir='local_data') as temp:
            p=Path(temp)/'fixture.json';p.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'128-token'):compile_records(Tokenizer(),p)
