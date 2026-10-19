"""No screen automation: verify subprocess flags and Windows child console state."""
import os
import shutil
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from echomate_bot.processes import background_options
from echomate_bot.inference import LocalBackend


class BackgroundProcesses(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt' and shutil.which('cscript.exe'),'Windows Script Host')
    def test_launcher_parses_without_opening_app_or_dialog(self):
        result=subprocess.run([shutil.which('cscript.exe'),'//nologo','EchoMate.vbs','/check'],
            capture_output=True,text=True,timeout=10,**background_options())
        self.assertEqual(result.returncode,0)
        self.assertEqual(result.stdout.strip(),'')
        self.assertEqual(result.stderr.strip(),'')

    def test_non_windows_does_not_receive_windows_only_flags(self):
        with patch('echomate_bot.processes.os.name','posix'):
            self.assertEqual(background_options(),{})

    @unittest.skipUnless(os.name=='nt','Windows process creation semantics')
    def test_windows_child_has_no_console_and_captured_output_still_works(self):
        self.assertEqual(background_options()['creationflags'],subprocess.CREATE_NO_WINDOW)
        answer=subprocess.check_output([sys.executable,'-c',
            'import ctypes; print(int(ctypes.windll.kernel32.GetConsoleWindow() != 0))'],
            text=True,stderr=subprocess.PIPE,timeout=10,**background_options())
        self.assertEqual(answer.strip(),'0')

    def test_health_query_hides_console_and_keeps_safety_limits(self):
        import torch
        with patch.object(torch.cuda,'is_available',return_value=True),patch('subprocess.check_output',return_value='90, 2000\n') as query:
            with self.assertRaisesRegex(RuntimeError,'resource safety'):LocalBackend.health()
            self.assertEqual(query.call_args.kwargs['timeout'],5)
            self.assertEqual(query.call_args.kwargs['stderr'],subprocess.PIPE)
            if os.name=='nt':self.assertEqual(query.call_args.kwargs['creationflags'],subprocess.CREATE_NO_WINDOW)

    def test_health_timeout_fails_closed_without_exposing_command_details(self):
        import torch
        with patch.object(torch.cuda,'is_available',return_value=True),patch('subprocess.check_output',side_effect=subprocess.TimeoutExpired('private-detail',5)):
            with self.assertRaisesRegex(RuntimeError,'^GPU health query unavailable$'):LocalBackend.health()

    def test_only_reclaimable_cache_is_released_without_weakening_safety(self):
        import torch
        from echomate_bot.processes import ResourceLimitError
        with patch.object(torch.cuda,'is_available',return_value=True),patch.object(torch.cuda,'memory_reserved',return_value=2048*1048576),patch.object(torch.cuda,'memory_allocated',return_value=1024*1048576),patch.object(torch.cuda,'empty_cache') as release:
            with patch('echomate_bot.inference.check_resources',side_effect=[ResourceLimitError('GPU resource safety stop','vram'),dict(free_vram_mib=1500)]):
                self.assertTrue(LocalBackend.health()['allocator_cache_reclaimed']);release.assert_called_once()
            release.reset_mock()
            with patch('echomate_bot.inference.check_resources',side_effect=ResourceLimitError('RAM resource safety stop','ram')):
                with self.assertRaises(RuntimeError):LocalBackend.health()
                release.assert_not_called()

    def test_windowless_entry_does_not_invoke_cmd_or_expose_secrets(self):
        source=Path('EchoMate.vbs').read_text(encoding='ascii')
        self.assertIn('pythonw.exe',source)
        self.assertIn('WScript.ScriptFullName',source)
        self.assertIn(', 0, False',source)
        for value in ('cmd.exe','powershell.exe','bootstrap.json','token','signing_key'):
            self.assertNotIn(value,source)
