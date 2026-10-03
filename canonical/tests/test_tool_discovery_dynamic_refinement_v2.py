from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_dynamic_refinement_v2 as ref


class Tests(unittest.TestCase):
    def test_current_v2_refinement_passes_truthfully(self):
        out=ref.evaluate()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertEqual(out["source_blob_drift"],[])
        self.assertFalse(out["v1_conditional_implication_valid"])
        self.assertTrue(out["v3_least_cost_counterexample_confirmed"])
        self.assertTrue(out["v4_discovery_first_invariant_pass"])
        self.assertTrue(out["v4_source_ordering_invariant_pass"])
        self.assertFalse(out["universal_target_proved"])

    def test_v3_failure_is_load_bearing_and_exact(self):
        out=ref.evaluate()
        self.assertEqual(
            out["v3_observed_action"],
            {"action":"SELECT","tool_id":"EXPENSIVE"},
        )
        self.assertEqual(
            out["v4_observed_first_action"],
            {"action":"DISCOVER","source_id":"S0","query":"CAP_A"},
        )
        self.assertIn("FALSIFIED",out["v1_disposition"])

    def test_regression_to_select_before_discovery_fails_closed(self):
        def bad_policy(public):
            return {"action":"SELECT","tool_id":"EXPENSIVE"}
        out=ref.evaluate(v4_policy=bad_policy)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("V4_DOES_NOT_DISCOVER_BEFORE_SELECT",out["errors"])

    def test_regression_to_probe_before_discovery_fails_closed(self):
        def bad_policy(public):
            return {"action":"PROBE","tool_id":"EXPENSIVE","capability":"CAP_A"}
        out=ref.evaluate(v4_policy=bad_policy)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("V4_DOES_NOT_DISCOVER_BEFORE_SELECT",out["errors"])

    def test_remaining_burden_is_not_hidden(self):
        out=ref.evaluate()
        self.assertEqual(len(out["minimum_missing_facts"]),2)
        self.assertIn(
            "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V2",
            out["minimum_missing_facts"],
        )
        self.assertIn(
            "INDEPENDENT_SCOPE_COMPLETE_FORMAL_OR_EXHAUSTIVE_ACCEPTANCE_PROOF_FOR_DISCOVERY_EXHAUSTIVE_V4_OVER_THE_FROZEN_TOOL_DISCOVERY_TARGET",
            out["minimum_missing_facts"],
        )
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
