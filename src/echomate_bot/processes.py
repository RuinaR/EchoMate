"""Options for noninteractive child commands launched by the desktop app."""
import os
import subprocess

class ResourceLimitError(RuntimeError):
    def __init__(self,message,reason,details=None):
        super().__init__(message);self.reason=reason;self.details=details


def resource_message(error,fallback):
    """Owner UI: allowlisted numeric counters only, never arbitrary exception text."""
    details=getattr(error,'details',None)
    if error.reason=='commit' and isinstance(details,dict):
        available=details.get('available');required=details.get('required')
        if all(type(v) is int and v>=0 for v in (available,required)):
            return ('Windows 메모리 할당 여유 %.2f GiB / 로딩 전 검사 기준 %.2f GiB. '
                    '다른 작업을 직접 마친 뒤 다시 시도해 주세요. 전체 로딩 피크는 아직 검증되지 않았어요') % (available/1024**3,required/1024**3)
    return fallback


def background_options():
    # Capturing stdout alone does not suppress a console under pythonw on Windows.
    return {'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}

def model_memory_budget(weight_bytes,preparation_bytes=0,baseline_private=None):
    """Conservative Windows commit guard before opening large weight mappings.

    Does not change page-file/system settings or terminate other processes.
    """
    if os.name!='nt':return
    from .loader_memory import memory_snapshot,budget_requirement,GIB
    try:status=memory_snapshot()
    except OSError:raise ResourceLimitError('Memory query unavailable','ram') from None
    # Imports/warmup already present in this process must not be counted twice.
    consumed=max(0,status['process_private']-baseline_private) if baseline_private is not None else 0
    required=budget_requirement(weight_bytes,max(0,preparation_bytes-consumed))
    if status['ram_available']<3*GIB:raise ResourceLimitError('Insufficient RAM for model preparation','ram')
    if status['commit_available']<required:
        # Safe aggregate only: no model path, message, user ID or credentials.
        raise ResourceLimitError('Windows commit headroom %.2f GiB; model-loading admission estimate %.2f GiB; deficit %.2f GiB. Full-load peak remains environment-dependent' %
            (status['commit_available']/GIB,required/GIB,(required-status['commit_available'])/GIB),'commit',
            dict(available=status['commit_available'],required=required))
    return status


def check_resources():
    """Hardware bounds without importing a GPU inference framework."""
    try:
        line=subprocess.check_output(['nvidia-smi','--query-gpu=temperature.gpu,memory.free',
            '--format=csv,noheader,nounits'],text=True,stderr=subprocess.PIPE,timeout=5,**background_options()).splitlines()[0]
        temperature,free=map(int,line.split(','))
    except (subprocess.SubprocessError,OSError,ValueError,IndexError):
        raise ResourceLimitError('GPU health query unavailable','gpu_query') from None
    if temperature>=85:raise ResourceLimitError('GPU resource safety stop','temperature')
    if free<512:raise ResourceLimitError('GPU resource safety stop','vram')
    available=None
    if os.name=='nt':
        import ctypes
        class Memory(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in
                ('total','available','page_total','page_available','virtual_total','virtual_available','extended')]
        status=Memory();status.length=ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)) or status.available<2*1024**3:
            raise ResourceLimitError('RAM resource safety stop','ram')
        available=round(status.available/1048576,1)
    return dict(temperature_c=temperature,free_vram_mib=free,available_ram_mib=available)
