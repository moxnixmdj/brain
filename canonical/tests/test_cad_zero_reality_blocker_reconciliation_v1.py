import unittest
from pathlib import Path
from canonical.runtime.verify_cad_zero_reality_blocker_reconciliation_v1 import verify

class Tests(unittest.TestCase):
    def test_live_tree_reconciliation_passes_fail_closed_validator(self):
        out=verify(Path("."))
        self.assertEqual(out["status"],"PASS",out)
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["capability_credit_delta"],0)

if __name__=="__main__":
    unittest.main()
