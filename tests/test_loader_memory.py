"""Admission, transient accounting and failed-load lifetime regressions."""
import asyncio
import gc
import os
import sys
import unittest
import weakref
from types import SimpleNamespace
from unittest.mock import patch

from echomate_bot.loader_memory import GIB,MemoryRecorder,budget_requirement,memory_snapshot
from echomate_bot.processes import model_memory_budget,ResourceLimitError,resource_message


class LoaderMemory(unittest.TestCase):
    def test_admission_bound_is_not_lowered_and_invalid_sizes_rejected(self):
        self.assertEqual(budget_requirement(22*GIB),24*GIB)
        for bad in (-1,True,1.5):
            with self.assertRaises(ValueError):budget_requirement(bad)

    @unittest.skipUnless(os.name=='nt','Windows counters')
    def test_actual_counters_have_consistent_units_and_process_peaks(self):
        s=memory_snapshot()
        self.assertEqual(s['commit_limit'],s['commit_used']+s['commit_available'])
        self.assertGreater(s['process_private'],0)
        self.assertGreaterEqual(s['process_peak_private'],s['process_private'])
        self.assertGreaterEqual(s['process_peak_ws'],s['process_ws'])

    @unittest.skipUnless(os.name=='nt','Windows guard')
    def test_headroom_and_ram_are_separate_and_deficit_is_explained(self):
        with patch('echomate_bot.loader_memory.memory_snapshot',return_value=dict(ram_available=8*GIB,commit_available=10*GIB)):
            with self.assertRaises(ResourceLimitError) as got:model_memory_budget(22*GIB)
            self.assertEqual(got.exception.reason,'commit')
            self.assertIn('deficit 14.00 GiB',str(got.exception))
        with patch('echomate_bot.loader_memory.memory_snapshot',return_value=dict(ram_available=2*GIB,commit_available=30*GIB)):
            with self.assertRaises(ResourceLimitError) as got:model_memory_budget(22*GIB)
            self.assertEqual(got.exception.reason,'ram')

    @unittest.skipUnless(os.name=='nt','Windows guard')
    def test_query_failure_fails_closed_and_exact_bound_is_accepted(self):
        with patch('echomate_bot.loader_memory.memory_snapshot',side_effect=OSError('synthetic')):
            with self.assertRaises(ResourceLimitError):model_memory_budget(GIB)
        with patch('echomate_bot.loader_memory.memory_snapshot',return_value=dict(ram_available=3*GIB,commit_available=24*GIB)):
            self.assertIsNotNone(model_memory_budget(22*GIB))

    def test_sampler_is_bounded_and_stops_even_on_failure(self):
        r=MemoryRecorder(sample=lambda:dict(process_private=7),limit=3)
        with self.assertRaises(ValueError):
            with r:
                for _ in range(10):r.mark('weights')
                raise ValueError('synthetic')
        self.assertFalse(r.thread.is_alive());self.assertEqual(len(r.rows),3)
        self.assertEqual(r.report()['peaks']['process_private'],7)

    def test_owner_resource_message_shows_only_validated_numeric_details(self):
        error=ResourceLimitError('synthetic private text','commit',dict(available=10*GIB,required=24*GIB))
        message=resource_message(error,'fallback')
        self.assertIn('10.00 GiB',message);self.assertNotIn('private',message)
        error.details['available']='synthetic private text'
        self.assertEqual(resource_message(error,'fallback'),'fallback')

    def test_failed_load_releases_partial_model_owned_by_traceback(self):
        from echomate_bot.inference import LocalBackend
        backend=LocalBackend();refs=[]
        class Partial:pass
        def fail():
            partial=Partial();refs.append(weakref.ref(partial))
            backend.processor=Partial()
            raise OSError(1455,'synthetic commit failure')
        backend._load_impl=fail
        with patch.dict(sys.modules,torch=None):
            try:
                backend.load()
            except OSError as exc:
                self.assertEqual(exc.errno,1455);gc.collect()
                self.assertIsNone(refs[0]())
            self.assertIsNone(backend.processor);self.assertIsNone(backend.model)
            self.assertFalse(backend.capabilities_verified)
            asyncio.run(backend.close())

    def test_admission_failure_precedes_framework_import_and_cleanup_does_not_import_it(self):
        from echomate_bot.inference import LocalBackend
        backend=LocalBackend()
        with patch('echomate_bot.model_registry.ModelRegistry.resolve',return_value=SimpleNamespace(bytes=22*GIB,path='synthetic-local')):
            with patch('echomate_bot.processes.model_memory_budget',side_effect=ResourceLimitError('synthetic','commit')):
                with patch.dict(sys.modules,torch=None):
                    with self.assertRaises(ResourceLimitError):backend.load()
                    asyncio.run(backend.close())
        self.assertIsNone(backend.model)

    def test_loaded_model_is_reused_and_unload_clears_verification(self):
        from echomate_bot.inference import LocalBackend
        backend=LocalBackend();backend.model=object();backend.capabilities_verified=True
        backend._load_impl=lambda:self.fail('must not reload resident model')
        backend.load()
        with patch.dict(sys.modules,torch=None):asyncio.run(backend.close())
        self.assertFalse(backend.capabilities_verified);self.assertIsNone(backend.loaded_path)

    def test_admission_is_rechecked_after_imports_and_after_processor_before_weights(self):
        from echomate_bot.inference import LocalBackend
        from unittest.mock import Mock
        fake_torch=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:False))
        for fail_at in (2,3):
            with self.subTest(fail_at=fail_at):
                processor=SimpleNamespace(from_pretrained=Mock(return_value=object()))
                weights=SimpleNamespace(from_pretrained=Mock())
                transformers=SimpleNamespace(AutoModelForMultimodalLM=weights,AutoProcessor=processor,
                    AutoConfig=object(),AutoTokenizer=object(),BitsAndBytesConfig=object())
                b=LocalBackend();b.health=lambda:None
                checks=[None]*(fail_at-1)+[ResourceLimitError('synthetic headroom changed','commit')]
                with patch.dict(sys.modules,torch=fake_torch,transformers=transformers),patch.dict(os.environ,{}):
                    with patch('echomate_bot.model_registry.ModelRegistry.resolve',return_value=SimpleNamespace(bytes=22*GIB,path='synthetic')):
                        with patch('echomate_bot.processes.model_memory_budget',side_effect=checks) as guard:
                            with self.assertRaises(ResourceLimitError):b.load()
                            self.assertEqual(guard.call_count,fail_at)
                    weights.from_pretrained.assert_not_called()
                    self.assertIsNone(b.processor);asyncio.run(b.close())
