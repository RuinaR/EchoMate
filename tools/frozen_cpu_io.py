"""Opt-in research-only Gemma Unified frozen tied I/O on CPU.

Public nn modules, Tensor.to and Transformers embedding setters only. Never
dispatches an NF4 layer to CPU, changes installed libraries or app defaults.
"""
import torch


class FrozenCPUEmbedding(torch.nn.Module):
    def __init__(self,weight,original,output_device):
        super().__init__();self.weight=weight;self.padding_idx=original.padding_idx
        self.num_embeddings=original.num_embeddings;self.embedding_dim=original.embedding_dim
        self.output_device=output_device
        self.register_buffer('embed_scale',original.embed_scale.detach().cpu(),persistent=False)

    def forward(self,ids):
        result=torch.nn.functional.embedding(ids.to('cpu'),self.weight,padding_idx=self.padding_idx)
        # Gemma scales embeddings; omitting this changes the actual model.
        return (result*self.embed_scale.to(self.weight.dtype)).to(self.output_device)


class FrozenCPUHead(torch.nn.Module):
    def __init__(self,weight):
        super().__init__();self.weight=weight;self.in_features=weight.shape[1];self.out_features=weight.shape[0]

    def forward(self,hidden):
        # Floating device copies retain the graph back to the GPU LoRA layers.
        return torch.nn.functional.linear(hidden.to('cpu'),self.weight).to(hidden.device)


def install(model):
    embedding=model.get_input_embeddings();head=model.get_output_embeddings()
    if type(embedding).__name__!='Gemma4UnifiedTextScaledWordEmbedding' or not isinstance(head,torch.nn.Linear):
        raise ValueError('Only verified Gemma Unified scaled embedding and linear head')
    if (embedding.weight is not head.weight or embedding.weight.requires_grad or embedding.weight.dtype!=torch.bfloat16
            or head.bias is not None or embedding.max_norm is not None or embedding.scale_grad_by_freq or embedding.sparse):
        raise ValueError('Frozen tied BF16 default embedding/head required')
    if any(getattr(m,'_hf_hook',None) is not None for m in (embedding,head)):
        raise ValueError('Existing I/O dispatch hooks require separate proof')
    device=embedding.weight.device
    weight=torch.nn.Parameter(embedding.weight.detach().cpu(),requires_grad=False)
    model.set_input_embeddings(FrozenCPUEmbedding(weight,embedding,device))
    model.set_output_embeddings(FrozenCPUHead(weight))
    # Transformers infers the primary execution device from the first parameter.
    # A root-level empty frozen parameter reports the decoder device without
    # allocating weight storage. Otherwise generate moves position IDs to CPU.
    model.register_parameter('_research_execution_device',torch.nn.Parameter(
        torch.empty(0,device=device,dtype=torch.bfloat16),requires_grad=False))
    verify(model)
    return dict(policy='frozen_tied_cpu_io_v2',weight_bytes=weight.numel()*weight.element_size(),
                dtype='bfloat16',output_device=str(device),same_cpu_parameter=True,execution_anchor_numel=0)


def verify(model):
    embedding=model.get_input_embeddings();head=model.get_output_embeddings()
    if (not isinstance(embedding,FrozenCPUEmbedding) or not isinstance(head,FrozenCPUHead)
            or embedding.weight is not head.weight or embedding.weight.device.type!='cpu'
            or embedding.weight.requires_grad or embedding.weight.dtype!=torch.bfloat16):
        raise ValueError('CPU tied I/O invariant changed')
    anchor=getattr(model,'_research_execution_device',None)
    if anchor is None or anchor.numel()!=0 or anchor.requires_grad or anchor.device!=embedding.output_device or model.device!=embedding.output_device:
        raise ValueError('Primary decoder execution device changed')
