import unittest
from pathlib import Path
from canonical.runtime.cad_t0_refreeze_v3_guard import validate

class CadT0RefreezeV3GuardTests(unittest.TestCase):
    def test_live_branch_v3_freeze_and_binding(self):
        out=validate(Path("."))
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["terminal_case_generation_performed"])
        self.assertEqual(out["terminal_results_observed"],0)
        self.assertEqual(out["fresh_terminal_evidence_consumed"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main()
