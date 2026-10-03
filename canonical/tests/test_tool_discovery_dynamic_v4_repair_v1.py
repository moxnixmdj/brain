from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_dynamic_v4_repair_v1 as repair


class ToolDiscoveryDynamicV4RepairVerifierTests(unittest.TestCase):
    def test_live_sources_reproduce_v3_counterexample_and_v4_repair(self):
        out=repair.verify()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertFalse(out["v3_conditional_implication_sound"])
        self.assertTrue(out["v4_repair_candidate_pass"])
        self.assertEqual(out["counterexample"]["v3_first_action"],{"action":"SELECT","tool_id":"T0"})
        self.assertEqual(out["counterexample"]["v4_first_action"]["action"],"DISCOVER")
        self.assertEqual(out["counterexample"]["v4_after_positive_probe"],{"action":"SELECT","tool_id":"T1"})
        self.assertTrue(out["v4_existing_dynamic_grid"]["pass"])
        self.assertEqual(out["v4_existing_dynamic_grid"]["failed"],0)
        self.assertFalse(out["universal_target_proved"])
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
