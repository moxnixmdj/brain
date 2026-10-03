from __future__ import annotations
import unittest

from canonical.runtime.tool_discovery_dynamic_refinement_counterexample_v1 import evaluate

class Tests(unittest.TestCase):
    def test_exact_v3_counterexample_reproduces(self):
        out = evaluate()
        self.assertTrue(out["counterexample_reproduced"], out)
        self.assertEqual(
            out["status"],
            "PASS__ACTIVE_V3_CONDITIONAL_REFINEMENT_FALSIFIED",
        )
        self.assertEqual(out["first_action"]["action"], "PROBE")
        self.assertEqual(
            out["second_action"],
            {"action": "SELECT", "tool_id": "VISIBLE_EXPENSIVE"},
        )
        self.assertFalse(out["discovery_called_before_selection"])
        self.assertLess(
            out["complete_interface_cheaper_sufficient_cost"],
            out["visible_selected_cost"],
        )

    def test_counterexample_grants_no_acceptance_credit(self):
        out = evaluate()
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
