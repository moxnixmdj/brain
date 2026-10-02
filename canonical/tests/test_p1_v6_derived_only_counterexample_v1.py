from __future__ import annotations
import unittest
from canonical.runtime.p1_v6_derived_only_counterexample_v1 import evaluate

class Tests(unittest.TestCase):
    def test_v6_overclaims_derived_only_failure_and_its_repair_does_not_rescue(self):
        out=evaluate()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertTrue(out["derived_only_visible_failure"])
        self.assertEqual(out["candidate_output"]["status"],"IDENTIFIED")
        self.assertEqual(out["candidate_output"]["cause_action_id"],"A1")
        self.assertEqual(out["candidate_output"]["repair_targets"],["restore:A1:SCOPE"])
        self.assertFalse(out["forward_intervention"]["terminal_rescued"])
        self.assertTrue(out["v6_scope_transport_falsified"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
