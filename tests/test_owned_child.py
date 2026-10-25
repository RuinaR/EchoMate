"""Only known, project-spawned children. Never enumerates host processes."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from echomate_bot.owned_child import OwnedChild
from echomate_bot.processes import background_options


@unittest.skipUnless(os.name=='nt','Windows ownership contract')
class NativeOwnership(unittest.TestCase):
    def test_closing_job_stops_only_assigned_owned_child(self):
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],**background_options())
        group=None
        try:
            group=OwnedChild(child)
            self.assertIsNotNone(group.handle)
            self.assertIsNone(child.poll())
            group.close()
            child.wait(5)
            self.assertIsNotNone(child.returncode)
            group.close()  # Idempotent.
        finally:
            if group:group.close()
            if child.poll() is None:child.terminate();child.wait(5)

    def test_parent_exit_closes_job_and_terminates_its_child(self):
        # Child inherits parent's stdout so use DEVNULL, not communicate().
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            marker=Path(folder).resolve()/'child-pid'
            code="""from echomate_bot.owned_child import OwnedChild
import subprocess,sys,os
from pathlib import Path
p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
job=OwnedChild(p)
Path(sys.argv[1]).write_text(str(p.pid))
input()
os._exit(0)
"""
            parent=subprocess.Popen([sys.executable,'-c',code,str(marker)],stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,**background_options())
            import time,ctypes as c
            from ctypes import wintypes as w
            handle=None
            kernel=c.WinDLL('kernel32',use_last_error=True)
            kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
            kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];kernel.WaitForSingleObject.restype=w.DWORD
            kernel.CloseHandle.argtypes=[w.HANDLE];kernel.CloseHandle.restype=w.BOOL
            try:
                deadline=time.monotonic()+10
                while not marker.exists():
                    if parent.poll() is not None:raise AssertionError(parent.stderr.read().decode())
                    if time.monotonic()>deadline:raise TimeoutError('Owned child did not start')
                    time.sleep(.01)
                # SYNCHRONIZE handle to the PID explicitly published by our
                # test parent; no memory read, process list or unrelated PID.
                handle=kernel.OpenProcess(0x100000,False,int(marker.read_text()))
                self.assertTrue(handle)
                self.assertEqual(kernel.WaitForSingleObject(handle,0),258)
                parent.communicate(b'\n',timeout=5)
                self.assertEqual(kernel.WaitForSingleObject(handle,5000),0)
            finally:
                if parent.poll() is None:parent.terminate();parent.wait(5)
                if handle:kernel.CloseHandle(handle)
                if parent.stderr:parent.stderr.close()
