"""Evaluation-only native sampling. No application imports or setting writes."""
from contextlib import contextmanager
from unittest.mock import patch

SEEDS=(20261024,20261025)
PARAMETERS=dict(do_sample=True,temperature=1.0,top_k=64,top_p=0.95)


@contextmanager
def sampling(backend,seed):
    if seed is not None and (type(seed) is not int or seed not in SEEDS):raise ValueError('Sealed seeds only')
    original=backend._generate
    def generate(messages,images,budget,weight,stop,choices=None,persona=None):
        if seed is None or persona is None or choices is not None:
            return original(messages,images,budget,weight,stop,choices,persona)
        if images:raise ValueError('Text-only sampling experiment')
        import torch
        model=backend.model;method=model.generate;device=torch.cuda.current_device()
        def sampled(*args,**kwargs):
            # Random state is local to this worker process, not a GPU setting.
            with torch.random.fork_rng(devices=[device]):
                torch.random.default_generator.manual_seed(seed)
                torch.cuda.default_generators[device].manual_seed(seed)
                return method(*args,**dict(kwargs,**PARAMETERS))
        with patch.object(model,'generate',new=sampled):
            return original(messages,images,budget,weight,stop,choices,persona)
    with patch.object(backend,'_generate',new=generate):yield
