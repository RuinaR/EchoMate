"""Options for noninteractive child commands launched by the desktop app."""
import os
import subprocess

class ResourceLimitError(RuntimeError):
    def __init__(self,message,reason):super().__init__(message);self.reason=reason


def background_options():
    # Capturing stdout alone does not suppress a console under pythonw on Windows.
    return {'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}


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
