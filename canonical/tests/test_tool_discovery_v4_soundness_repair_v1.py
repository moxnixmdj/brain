from __future__ import annotations
import unittest
from canonical.runtime import tool_discovery_v4_soundness_repair_v1 as repair

class Tests(unittest.TestCase):
    def test_v3_refinement_is_falsified(self):
        out=repair.evaluate()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertTrue(out["v3_falsified"])
        self.assertFalse(out["prior_residual_reduction_to_interface_instance_only_sound"])
        self.assertEqual(
            out["counterexample"]["v3_action"],
            {"action":"SELECT","tool_id":"EXPENSIVE"},
        )
        self.assertEqual(
            out["counterexample"]["v4_action_before_discovery"],
            {"action":"DISCOVER","source_id":"S0","query":"CAP_A"},
        )

    def test_v4_repair_checks(self):
        out=repair.evaluate()
        self.assertTrue(out["v4_repair_checks_pass"])
        self.assertEqual(
            out["counterexample"]["v4_action_after_complete_discovery"],
            {"action":"SELECT","tool_id":"CHEAP"},
        )
        self.assertEqual(out["v4_safe_probe_gate_check"],{"action":"SELECT","tool_id":"SAFE"})
        self.assertEqual(out["v4_stale_discovery_receipt_check"],{"action":"DISCOVER","source_id":"S0","query":"CAP_A"})
        self.assertEqual(out["v4_unauthorized_source_check"],{"action":"SELECT","tool_id":"SAFE"})

    def test_no_credit(self):
        out=repair.evaluate()
        self.assertFalse(out["universal_target_proved"])
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
