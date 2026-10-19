"""Windows system commit and current-process counters; never records content."""
from __future__ import annotations
import ctypes
import os
import threading
import time
from contextlib import contextmanager
from importlib import metadata

GIB = 1024**3
# Windows/Torch 2.9.1 + Transformers 5.20.1 measured pre-open private usage
# was 9.03 GiB (allocator warmup included); round up, keep 2 GiB margin.
# This is a conservative admission estimate, not a universal model peak bound.
LOADER_PREPARATION_BYTES = 10*GIB


def loading_reserve(entry):
    """Measured native pread profile only; unknown versions use full-file sum.

    Same 677 tensors in <=2 GiB shards peaked at 13.01 GiB private commit.
    Allow largest COW reservation + 12 GiB preparation, then the unchanged
    2 GiB margin in model_memory_budget. Monolithic admission is unchanged.
    No environment knobs, monkeypatches or reduced physical/GPU safety limits.
    """
    try:
        measured=(metadata.version('transformers')=='5.20.1' and metadata.version('safetensors')=='0.8.0' and metadata.version('torch').split('+')[0]=='2.9.1')
    except metadata.PackageNotFoundError:measured=False
    largest=getattr(entry,'largest_shard_bytes',0)
    if (os.name=='nt' and measured and getattr(entry,'memory_profile',None)=='gemma4-12b-sharded-2g'
            and 0<largest<=2*GIB and largest<entry.bytes):
        return largest,12*GIB
    return entry.bytes,LOADER_PREPARATION_BYTES


def release_idle_cuda(torch):
    """Only after our single GPU worker has drained and model refs are gone.

    Torch 2.9.1's global cuBLAS workspace can pin an otherwise empty multi-GiB
    allocator segment. Capability-check this private hook; never reset CUDA or
    change workspace/environment settings. No CUDA initialization for cleanup.
    """
    if not getattr(torch.cuda,'is_initialized',lambda:False)():return
    torch.cuda.synchronize()
    clear=getattr(getattr(torch,'_C',None),'_cuda_clearCublasWorkspaces',None)
    if callable(clear):clear()
    torch.cuda.empty_cache()


def memory_snapshot():
    if os.name != 'nt':
        raise OSError('Windows memory counters required')
    from ctypes import wintypes as w
    size = ctypes.c_size_t
    class Status(ctypes.Structure):
        _fields_ = [('length', w.DWORD), ('load', w.DWORD)] + [(n, ctypes.c_ulonglong) for n in
            ('total', 'available', 'page_total', 'page_available', 'virtual_total', 'virtual_available', 'extended')]
    class Performance(ctypes.Structure):
        _fields_ = [('cb', w.DWORD)] + [(n, size) for n in
            ('commit', 'limit', 'peak', 'physical', 'physical_available', 'cache', 'kernel', 'paged', 'nonpaged', 'page_size')] + [(n, w.DWORD) for n in ('handles', 'processes', 'threads')]
    class Counters(ctypes.Structure):
        _fields_ = [('cb', w.DWORD), ('faults', w.DWORD)] + [(n, size) for n in
            ('peak_ws', 'ws', 'peak_paged', 'paged', 'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile', 'private')]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(Status)]
    psapi.GetPerformanceInfo.argtypes = [ctypes.POINTER(Performance), w.DWORD]
    psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, ctypes.POINTER(Counters), w.DWORD]
    kernel.GetProcessHandleCount.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
    status = Status(); status.length = ctypes.sizeof(status)
    perf = Performance(); perf.cb = ctypes.sizeof(perf)
    proc = Counters(); proc.cb = ctypes.sizeof(proc)
    if not (kernel.GlobalMemoryStatusEx(ctypes.byref(status)) and
            psapi.GetPerformanceInfo(ctypes.byref(perf), perf.cb) and
            psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(proc), proc.cb)):
        raise ctypes.WinError(ctypes.get_last_error())
    handles=w.DWORD()
    handle_count=handles.value if kernel.GetProcessHandleCount(kernel.GetCurrentProcess(),ctypes.byref(handles)) else None
    # The OS high-water mark is since boot, NOT the peak of this test run.
    return dict(ram_available=status.available, commit_used=perf.commit*perf.page_size,
                commit_limit=perf.limit*perf.page_size, commit_available=(perf.limit-perf.commit)*perf.page_size,
                system_commit_peak_since_boot=perf.peak*perf.page_size,process_handles=handle_count,
                process_private=proc.private, process_peak_private=proc.peak_pagefile,
                process_ws=proc.ws, process_peak_ws=proc.peak_ws)


class MemoryRecorder:
    """Bounded 50ms samples plus synchronous stage markers. No GPU sync/import."""
    def __init__(self, sample=memory_snapshot, interval=.05, limit=20000):
        self.sample=sample; self.interval=interval; self.limit=limit
        self.rows=[]; self.peaks={}; self.dropped_samples=0; self.phase='start'; self.started=time.monotonic()
        self.stop=threading.Event(); self.thread=None; self.lock=threading.Lock()
    def mark(self, phase=None):
        with self.lock:
            if phase is not None:self.phase=phase
            try:row=dict(seconds=time.monotonic()-self.started, phase=self.phase, **self.sample())
            except OSError:row=dict(seconds=time.monotonic()-self.started,phase=self.phase,counters_unavailable=True)
            for key,value in row.items():
                if isinstance(value,(int,float)) and (key.startswith(('process_','gpu_')) or key=='commit_used'):
                    self.peaks[key]=max(self.peaks.get(key,0),value)
            if len(self.rows)<self.limit:self.rows.append(row)
            else:self.dropped_samples+=1
    def __enter__(self):
        self.mark()
        def sample():
            while not self.stop.wait(self.interval):self.mark()
        self.thread=threading.Thread(target=sample,name='loader-memory',daemon=True);self.thread.start()
        return self
    def __exit__(self,*args):
        self.stop.set()
        if self.thread:self.thread.join()
        self.mark('recorder_closed')
    def report(self):
        return dict(interval_seconds=self.interval,samples=self.rows,dropped_samples=self.dropped_samples,peaks=self.peaks)


def budget_requirement(weight_bytes, preparation_bytes=0):
    """Current monolithic COW mapping reserve plus provisional overhead margin.

    This is an admission bound, NOT a calibrated full-load peak prediction.
    Imports, model buffers and NF4 temporary allocations are measured separately.
    """
    if isinstance(weight_bytes,bool) or not isinstance(weight_bytes,int) or weight_bytes<0:
        raise ValueError('Invalid weight byte count')
    if type(preparation_bytes) is not int or preparation_bytes<0:raise ValueError('Invalid preparation byte count')
    return weight_bytes+preparation_bytes+2*GIB


@contextmanager
def native_loader_phases(recorder):
    """Opt-in, subprocess-only instrumentation of the installed native loader.

    Does not change tensors, arguments, backends or quantization configuration.
    Never install these process-global hooks in the running Discord application.
    """
    from unittest.mock import patch
    import transformers.modeling_utils as models
    from transformers.integrations.bitsandbytes import Bnb4bitQuantize
    original_open=models.safe_open
    original_convert=Bnb4bitQuantize.convert
    def opened(*args,**kwargs):
        recorder.mark('safetensors_open_start')
        result=original_open(*args,**kwargs)
        recorder.mark('safetensors_open_end')
        return result
    def converted(self,*args,**kwargs):
        recorder.mark('nf4_convert_start')
        try:return original_convert(self,*args,**kwargs)
        finally:recorder.mark('nf4_convert_end')
    with patch.object(models,'safe_open',opened),patch.object(Bnb4bitQuantize,'convert',converted):
        yield
