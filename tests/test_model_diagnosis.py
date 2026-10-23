"""Protocol fairness and private diagnostic/download boundaries, no GPU/network."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from diagnose_persona_pipeline import minimal_messages
from echomate_bot.character_profiles import presets
from dialogue_eval_core import save


class DiagnosisContracts(unittest.TestCase):
    def test_minimal_keeps_all_numeric_traits_and_excludes_retrieval_material(self):
        for profile in presets().values():
            messages=minimal_messages(profile,'지금의 실제 질문')
            payload=json.loads(messages[0]['content'].split('코드를 출력하지 마. ',1)[1])
            self.assertEqual(set(payload),set(profile)-{'name'})
            for key,value in profile.items():
                if key not in ('name','card'):self.assertEqual(payload[key],value)
            self.assertEqual(payload['card'],{k:v for k,v in profile['card'].items() if k not in ('lore','examples')})
            self.assertEqual(messages[-1],dict(role='user',content='지금의 실제 질문'))
    def test_incomplete_alternative_is_visible_as_failure_not_blind_complete_answer(self):
        from report_model_diagnosis import report
        with tempfile.TemporaryDirectory(dir='local_data') as tmp:
            root=Path(tmp);(root/'alternative').mkdir()
            save(root/'alternative/results-private.json',[dict(arm='C',case='x',profile='supportive',output='UNFINISHED_PRIVATE_MARKER',
                seconds=1,input_tokens=20,output_tokens=768,complete=False)])
            result=report(root)
            self.assertEqual(result['conditions']['C']['incomplete'],1)
            self.assertEqual(result['conditions']['C']['blind_eligible'],0)
            self.assertIn('UNFINISHED_PRIVATE_MARKER',(root/'report.html').read_text('utf-8'))
            self.assertNotIn('UNFINISHED_PRIVATE_MARKER',(root/'blind-C/review.html').read_text('utf-8'))
    def test_remote_metadata_cannot_write_nested_model_path(self):
        from acquire_diagnostic_model import acquire
        metadata=dict(sha='a'*40,siblings=[dict(rfilename='../outside.safetensors',size=1)])
        with tempfile.TemporaryDirectory(dir='local_data') as tmp,patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(metadata).encode())):
            with self.assertRaisesRegex(ValueError,'Nested'):acquire(Path(tmp)/'candidate')
            self.assertFalse((Path(tmp)/'outside.safetensors').exists())


if __name__=='__main__':unittest.main()
