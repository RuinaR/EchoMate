import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
from sampling_diagnosis import sampling,PARAMETERS


class SamplingBoundary(unittest.TestCase):
    def test_greedy_and_non_persona_contracts_keep_original_arguments(self):
        calls=[]
        class Backend:
            def _generate(self,*args):calls.append(args);return 'unchanged'
        backend=Backend();original=backend._generate
        for seed in (None,20261024):
            with sampling(backend,seed):
                self.assertEqual(backend._generate(['input'],None,8,'base',None,['choice']),'unchanged')
            self.assertEqual(backend._generate,original)
        self.assertEqual(len(calls),2)
        self.assertEqual(PARAMETERS,dict(do_sample=True,temperature=1.0,top_k=64,top_p=.95))
    def test_unknown_seed_cannot_silently_change_experiment(self):
        with self.assertRaises(ValueError):
            with sampling(object(),123):pass
    def test_sampling_parameters_rng_and_method_restore_after_failure(self):
        state=[];calls=[]
        @contextmanager
        def fork_rng(devices):
            prior=list(state)
            try:yield
            finally:state[:]=prior
        rng=SimpleNamespace(manual_seed=state.append)
        torch=SimpleNamespace(random=SimpleNamespace(fork_rng=fork_rng,default_generator=rng),
            cuda=SimpleNamespace(current_device=lambda:0,default_generators=[rng]))
        class Model:
            def generate(self,**kwargs):calls.append(kwargs);raise RuntimeError('synthetic failure')
        class Backend:
            model=Model()
            def _generate(self,*args):return self.model.generate(do_sample=False,max_new_tokens=7)
        backend=Backend();original=backend._generate;method=backend.model.generate
        with patch.dict('sys.modules',torch=torch):
            with self.assertRaises(RuntimeError):
                with sampling(backend,20261024):backend._generate([],None,7,'base',None,persona={})
        self.assertEqual(calls,[dict(max_new_tokens=7,**PARAMETERS)])
        self.assertEqual(state,[])
        self.assertEqual(backend._generate,original);self.assertEqual(backend.model.generate,method)
