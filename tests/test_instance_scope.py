import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name=='nt','Windows session ownership')
class SessionOwnership(unittest.TestCase):
    def test_different_data_homes_cannot_own_models_at_once(self):
        from echomate_bot.instance import InstanceLease
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            root=Path(folder)
            with patch('echomate_bot.instance.ROOT',root/'a'):first=InstanceLease()
            try:
                with patch('echomate_bot.instance.ROOT',root/'b'):
                    with self.assertRaises(RuntimeError):InstanceLease()
            finally:first.close()
            with patch('echomate_bot.instance.ROOT',root/'b'):
                second=InstanceLease();second.close();second.close()

    def test_initialization_error_releases_session_ownership(self):
        from echomate_bot.instance import InstanceLease
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            root=Path(folder);bad=root/'file';bad.write_text('fixture')
            with patch('echomate_bot.instance.ROOT',bad):
                with self.assertRaises(OSError):InstanceLease()
            with patch('echomate_bot.instance.ROOT',root/'valid'):
                lease=InstanceLease();lease.close()

    def test_owner_process_exit_releases_kernel_object_without_process_scans(self):
        from echomate_bot.instance import InstanceLease
        from echomate_bot.processes import background_options
        with tempfile.TemporaryDirectory(dir='local_data') as folder:
            code='import os;from pathlib import Path;import echomate_bot.instance as i;i.ROOT=Path(os.environ["OWNED_FIXTURE"]);lease=i.InstanceLease();os._exit(2)'
            result=subprocess.run([sys.executable,'-c',code],env=dict(os.environ,OWNED_FIXTURE=folder),
                capture_output=True,timeout=15,**background_options())
            self.assertEqual(result.returncode,2,result.stderr)
            with patch('echomate_bot.instance.ROOT',Path(folder)/'new'):
                lease=InstanceLease();lease.close()
