import copy
from types import SimpleNamespace
import unittest
import torch
from preference_learning import completion_logps,dpo_loss,sequential_pair_backward


class TinyPolicy(torch.nn.Module):
    def __init__(self):
        super().__init__();self.embedding=torch.nn.Embedding(13,8);self.dropout=torch.nn.Dropout(.2);self.head=torch.nn.Linear(8,13)
    def forward(self,input_ids,logits_to_keep,use_cache):
        return SimpleNamespace(logits=self.head(self.dropout(self.embedding(input_ids)))[:,logits_to_keep])


class PreferenceMath(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1);torch.manual_seed(92);self.model=TinyPolicy()
        self.chosen=(torch.tensor([[1,2,3,4]]),torch.tensor([[-100,-100,3,4]]))
        self.rejected=(torch.tensor([[1,2,8,9,10]]),torch.tensor([[-100,-100,8,9,10]]))

    def test_selected_causal_sum_masks_prompt_and_not_length_averaged(self):
        self.model.eval();ids,labels=self.chosen
        logits=self.model.head(self.model.embedding(ids))[0]
        expected=logits[1].log_softmax(0)[3]+logits[2].log_softmax(0)[4]
        self.assertTrue(torch.equal(completion_logps(self.model,ids,labels),expected))

    def test_sequential_replay_equals_two_graph_dropout_gradient(self):
        original=copy.deepcopy(self.model);rng=torch.get_rng_state()
        left=completion_logps(original,*self.chosen);right=completion_logps(original,*self.rejected)
        expected=dpo_loss(left,right,-5.,-7.);expected.backward();after=torch.get_rng_state()
        torch.set_rng_state(rng)
        actual=sequential_pair_backward(self.model,self.chosen,self.rejected,(-5.,-7.))
        self.assertAlmostEqual(actual['loss'],float(expected.detach()),places=7)
        for a,b in zip(original.parameters(),self.model.parameters()):torch.testing.assert_close(a.grad,b.grad,rtol=1e-6,atol=1e-7)
        self.assertTrue(torch.equal(after,torch.get_rng_state()))

    def test_invalid_reference_mask_and_beta_rejected(self):
        with self.assertRaises(ValueError):dpo_loss(torch.tensor(0.),torch.tensor(0.),0.,0.,beta=0)
        with self.assertRaises(ValueError):completion_logps(self.model,self.chosen[0],torch.full_like(self.chosen[1],-100))
        with self.assertRaises(ValueError):sequential_pair_backward(self.model,self.chosen,self.rejected,(float('nan'),0.))

    def test_resource_observer_failure_aborts_before_any_backward(self):
        def stop(phase):raise RuntimeError('synthetic resource guard')
        with self.assertRaisesRegex(RuntimeError,'resource guard'):
            sequential_pair_backward(self.model,self.chosen,self.rejected,(-5.,-7.),observe=stop)
        self.assertTrue(all(p.grad is None for p in self.model.parameters()))
