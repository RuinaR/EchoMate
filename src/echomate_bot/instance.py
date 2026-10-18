"""Process-wide exclusive GPU serving lease, released automatically on exit."""
from .settings import ROOT


class InstanceLease:
    def __init__(self):
        import os
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
        except OSError:
            self.file.close();raise RuntimeError('Another EchoMate bot is already running') from None
    def close(self):self.file.close()
