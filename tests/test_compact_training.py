import json
from pathlib import Path
import tempfile
import unittest


class CompactData(unittest.TestCase):
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
