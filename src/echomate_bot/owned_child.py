"""Windows kill-on-owner-exit group for an explicitly spawned EchoMate child.

Never enumerates or opens unrelated processes. No limits/settings are applied
to the host or to another application. The job handle is not inherited.
"""
import ctypes as c
from ctypes import wintypes as w
import os


class BasicLimits(c.Structure):
    _fields_=[('process_time',c.c_longlong),('job_time',c.c_longlong),('flags',w.DWORD),
              ('minimum_ws',c.c_size_t),('maximum_ws',c.c_size_t),('active',w.DWORD),
              ('affinity',c.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]


class IOCounters(c.Structure):
    _fields_=[(name,c.c_ulonglong) for name in
              ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]


class ExtendedLimits(c.Structure):
    _fields_=[('basic',BasicLimits),('io',IOCounters),('process_memory',c.c_size_t),
              ('job_memory',c.c_size_t),('peak_process_memory',c.c_size_t),('peak_job_memory',c.c_size_t)]


_api=None


def api():
    global _api
    if _api is None:
        dll=c.WinDLL('kernel32',use_last_error=True)
        for name,args,result in (
            ('CreateJobObjectW',[c.c_void_p,w.LPCWSTR],w.HANDLE),
            ('SetInformationJobObject',[w.HANDLE,c.c_int,c.c_void_p,w.DWORD],w.BOOL),
            ('AssignProcessToJobObject',[w.HANDLE,w.HANDLE],w.BOOL),
            ('CloseHandle',[w.HANDLE],w.BOOL)):
            fn=getattr(dll,name);fn.argtypes=args;fn.restype=result
        _api=dll
    return _api


class OwnedChild:
    def __init__(self, process):
        self.handle=None
        if os.name!='nt':
            return  # Other platforms retain explicit terminate/wait behavior.
        kernel=api()
        handle=kernel.CreateJobObjectW(None,None)
        if not handle:
            raise c.WinError(c.get_last_error())
        try:
            info=ExtendedLimits();info.basic.flags=0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not kernel.SetInformationJobObject(handle,9,c.byref(info),c.sizeof(info)):
                raise c.WinError(c.get_last_error())
            # Popen's owned handle, not a PID lookup or a process scan.
            if not kernel.AssignProcessToJobObject(handle,w.HANDLE(int(process._handle))):
                raise c.WinError(c.get_last_error())
        except BaseException:
            kernel.CloseHandle(handle)
            raise
        self.handle=handle

    def close(self):
        if self.handle is not None:
            if not api().CloseHandle(self.handle):
                raise c.WinError(c.get_last_error())
            self.handle=None
