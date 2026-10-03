from __future__ import annotations
import unittest
from canonical.runtime import tool_discovery_acceptance_promotion_v1 as p

class ToolDiscoveryAcceptancePromotionV1Tests(unittest.TestCase):
    def test_exact_delta(self):
        out=p.evaluate()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["before"],{"proved_atomic":11,"unresolved_atomic":27,"accepted_families":4,"open_families":15,"verified_owned_families":2})
        self.assertEqual(out["after"],{"proved_atomic":12,"unresolved_atomic":26,"accepted_families":5,"open_families":14,"verified_owned_families":2})
        self.assertEqual(out["newly_proved_predicates"],[p.TARGET])
        self.assertEqual(out["newly_closed_families"],[p.FAMILY])
    def test_ownership_remains_separate(self):
        out=p.evaluate(); self.assertTrue(out["pass"],out)
        self.assertEqual(out["ownership_promotions"],[])
        self.assertEqual(out["after"]["verified_owned_families"],2)
    def test_zero_reality_and_no_authority(self):
        out=p.evaluate(); self.assertTrue(out["pass"],out)
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
