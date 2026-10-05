from __future__ import annotations
import unittest
from canonical.runtime.astra_legacy_target_crosswalk_verifier_v1 import verify

class AstraLegacyTargetCrosswalkVerifierV1Tests(unittest.TestCase):
    def test_crosswalk_is_exact_and_fail_closed(self):
        out=verify()
        self.assertTrue(out["valid"],out)
        self.assertEqual(out["legacy_family_count"],19)
        self.assertEqual(out["astra_target_count"],13)
        self.assertFalse(out["set_equivalent"])
        self.assertEqual(out["dedicated_legacy_gaps"],["CYBERSECURITY_PROBLEM_SOLVING"])
        self.assertEqual(out["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
