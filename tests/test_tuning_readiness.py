import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from echomate_studio.tuning_readiness import assess_readiness

class TuningReadinessTests(unittest.TestCase):
    def test_official_export_requires_verification(self):
        report=assess_readiness(source_kind="official-personal-data-package",
                                permission_confirmed=False,owner_reviewed=True)
        self.assertEqual(report["status"],"not_ready")
        self.assertIn("rights_reviewed",report["blocking_checks"])
    def test_api_export_cannot_be_cleared_by_user_toggle(self):
        report=assess_readiness(source_kind="api-export",permission_confirmed=True,owner_reviewed=True)
        self.assertFalse(report["checks"]["rights_reviewed"])
    def test_even_confirmed_rights_do_not_start_training(self):
        report=assess_readiness(source_kind="official-personal-data-package",
                                permission_confirmed=True,owner_reviewed=True,gpu_vram_gb=12)
        self.assertEqual(report["status"],"not_ready")
        self.assertIn("training_data_screened",report["blocking_checks"])
    def test_invalid_source_and_vram(self):
        with self.assertRaises(ValueError):
            assess_readiness(source_kind="wrong",permission_confirmed=False,owner_reviewed=False)
        with self.assertRaises(ValueError):
            assess_readiness(source_kind="unknown",permission_confirmed=False,owner_reviewed=False,gpu_vram_gb=0)
