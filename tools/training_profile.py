"""Research-only accounting. Never infer free VRAM from Torch allocated alone.

Legacy reports lack phase peaks, GPU identity and complete weight digests: they
are audit evidence, NOT reusable admission authorization. No threshold override.
"""
import time

MIB=1024**2
GIB=1024**3


def audit_report(report):
    plan=report['budget'];stages=report['stages']
    if not stages:raise ValueError('Measured stages required')
    before=report['health']['free_vram_mib']
    if type(before) is not int or before<0:raise ValueError('Invalid initial free VRAM')
    for row in stages:
        free=row['health']['free_vram_mib']
        if type(free) is not int or free<0:raise ValueError('Invalid stage free VRAM')
        for k in ('gpu_allocated','gpu_reserved','gpu_peak_allocated','gpu_peak_reserved'):
            if type(row[k]) is not int or row[k]<0:raise ValueError('Invalid GPU counters')
        if row['gpu_allocated']>row['gpu_reserved']:raise ValueError('Allocated exceeds reserved')
    allocated=max(s['gpu_peak_allocated'] for s in stages)
    reserved=max(s['gpu_peak_reserved'] for s in stages)
    minimum=min(s['health']['free_vram_mib'] for s in stages)
    delta=(before-minimum)*MIB
    if delta<0:raise ValueError('Aggregate workload delta negative; host changed')
    # max, NOT sum: reserved already contains allocated and unused cache.
    observed_envelope=max(reserved,delta)+2*GIB
    return dict(schema=1,static_required_bytes=plan['planning_required_vram'],
        peak_allocated_bytes=allocated,peak_reserved_bytes=reserved,
        minimum_stage_free_mib=minimum,aggregate_free_delta_bytes=delta,
        reserved_plus_safety_bytes=reserved+2*GIB,
        aggregate_envelope_plus_safety_bytes=observed_envelope,
        static_minus_observed_envelope_bytes=plan['planning_required_vram']-observed_envelope,
        safe_stage_samples=minimum>=2048,
        reusable_admission=False,
        missing=['Full phase peaks and within-phase free-VRAM samples',
                 'Complete model/host/library/workload binding',
                 'Multiple independent successful executions under matched load'],
        caveat='Aggregate free delta includes host variation; not attributable to this process. '
               'Reserved contains allocated: never add them. Stage samples are not continuous minima.')


class PhasePeaks:
    """Opt-in synchronization/counter reset only; no cache/tensor mutation.

    Boundaries reset CUDA peak counters, so sample() must retain lifetime maxima
    for the existing recorder. Within-phase aggregate minima remain unmeasured.
    """
    def __init__(self,torch,enabled=False):
        self.torch=torch;self.enabled=enabled;self.rows=[]
        self.allocated=0;self.reserved=0;self.phase='initial';self.tick=time.monotonic()

    def peaks(self):
        cuda=self.torch.cuda
        return max(self.allocated,cuda.max_memory_allocated()),max(self.reserved,cuda.max_memory_reserved())

    def boundary(self,name):
        if not self.enabled:return None
        if len(self.rows)>=512:raise ValueError('Bounded phase profiling')
        cuda=self.torch.cuda;cuda.synchronize()
        a=cuda.max_memory_allocated();r=cuda.max_memory_reserved()
        self.allocated=max(self.allocated,a);self.reserved=max(self.reserved,r)
        now=time.monotonic()
        row=dict(phase=self.phase,until=name,seconds=now-self.tick,
                 peak_allocated=a,peak_reserved=r,allocated=cuda.memory_allocated(),reserved=cuda.memory_reserved())
        self.rows.append(row);cuda.reset_peak_memory_stats();self.phase=name;self.tick=now
        return row


if __name__=='__main__':
    import argparse
    import json
    from pathlib import Path
    p=argparse.ArgumentParser(description='Offline report audit; never grants admission')
    p.add_argument('--report',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    out=Path(a.output).resolve();root=Path(__file__).resolve().parents[1]/'local_data'
    if not out.is_relative_to(root) or out.exists():raise ValueError('Fresh private report required')
    result=audit_report(json.loads(Path(a.report).read_text(encoding='utf-8')))
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
