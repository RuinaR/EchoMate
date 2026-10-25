"""Process-wide exclusive GPU serving lease, released automatically on exit."""
from .settings import ROOT

_windows_api=None


def windows_api():
    global _windows_api
    if _windows_api is None:
        import ctypes as c
        from ctypes import wintypes as w
        api=c.WinDLL('kernel32',use_last_error=True)
        api.CreateEventW.argtypes=[c.c_void_p,w.BOOL,w.BOOL,w.LPCWSTR]
        api.CreateEventW.restype=w.HANDLE
        api.CloseHandle.argtypes=[w.HANDLE];api.CloseHandle.restype=w.BOOL
        _windows_api=api
    return _windows_api


def claim_windows_session():
    """Lifetime-owned object, not a process/window scan or a system setting."""
    import ctypes as c
    api=windows_api()
    c.set_last_error(0)
    handle=api.CreateEventW(None,True,False,'Local\\RuinaR.EchoMate.Serving.Owner.v1')
    if not handle:raise c.WinError(c.get_last_error())
    if c.get_last_error()==183:  # ERROR_ALREADY_EXISTS, including another data home.
        api.CloseHandle(handle)
        raise RuntimeError('Another EchoMate bot is already running')
    return handle


class InstanceLease:
    def __init__(self):
        import os
        self.file=None;self.session_handle=None
        try:
            if os.name=='nt':self.session_handle=claim_windows_session()
            ROOT.mkdir(parents=True,exist_ok=True)
            self.file=(ROOT/'runtime.lock').open('a+b')
            self.file.seek(0);self.file.write(b'0');self.file.flush();self.file.seek(0)
            try:
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError('Another EchoMate bot is already running') from exc
        except BaseException:
            self.close();raise
    def close(self):
        try:
            if self.file is not None:self.file.close()
        finally:
            if self.session_handle is not None:
                import ctypes as c
                handle=self.session_handle;self.session_handle=None
                if not windows_api().CloseHandle(handle):raise c.WinError(c.get_last_error())
