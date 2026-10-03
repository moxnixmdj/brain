from __future__ import annotations

import unittest

from canonical.runtime.tool_discovery_observability_partition_v2 import classify


def tool(tid, cost, evidence, safe=()):
    return {
        "tool_id": tid,
        "cost": cost,
        "capability_evidence": dict(evidence),
        "safe_probe_capabilities": list(safe),
    }


def state(required, *tools):
    return {
        "identity_scope_complete": True,
        "required_capabilities": list(required),
        "admissible_tools": list(tools),
    }


class ToolDiscoveryObservabilityPartitionV2Tests(unittest.TestCase):
    def test_mixed_safe_and_unsafe_unknown_must_probe_before_comparator(self):
        out = classify(state(
            ["A", "B"],
            tool("CHEAP", 1, {"A": "UNKNOWN", "B": "UNKNOWN"}, safe=["B"]),
            tool("KNOWN", 2, {"A": "SUPPORTED", "B": "SUPPORTED"}, safe=["A", "B"]),
        ))
        self.assertEqual(out["minimum_reality_action"], "SAFE_PROBE", out)
        self.assertEqual(out["recommended_safe_probe"]["tool_id"], "CHEAP")
        self.assertEqual(out["recommended_safe_probe"]["capability"], "B")
        self.assertFalse(out["matched_comparator_required_now"])

    def test_negative_safe_probe_can_remove_irreducible_branch_entirely(self):
        out = classify(state(
            ["A", "B"],
            tool("CHEAP", 1, {"A": "UNKNOWN", "B": "UNSUPPORTED"}, safe=["B"]),
            tool("KNOWN", 2, {"A": "SUPPORTED", "B": "SUPPORTED"}, safe=["A", "B"]),
        ))
        self.assertEqual(out["minimum_reality_action"], "UNIVERSAL_PROOF", out)
        self.assertTrue(out["universal_proof_eligible"])

    def test_positive_safe_probe_then_exposes_true_irreducible_fact(self):
        out = classify(state(
            ["A", "B"],
            tool("CHEAP", 1, {"A": "UNKNOWN", "B": "SUPPORTED"}, safe=["B"]),
            tool("KNOWN", 2, {"A": "SUPPORTED", "B": "SUPPORTED"}, safe=["A", "B"]),
        ))
        self.assertEqual(out["minimum_reality_action"], "MATCHED_COMPARATOR", out)
        self.assertTrue(out["matched_comparator_required_now"])
        self.assertEqual(out["irreducible_routes"][0]["unsafe_unknown_capabilities"], ["A"])

    def test_fully_probeable_cheapest_unknown_is_safe_progress_not_comparator(self):
        out = classify(state(
            ["A"],
            tool("CHEAP", 1, {"A": "UNKNOWN"}, safe=["A"]),
            tool("KNOWN", 2, {"A": "SUPPORTED"}, safe=["A"]),
        ))
        self.assertEqual(out["minimum_reality_action"], "SAFE_PROBE", out)

    def test_equal_cost_unknown_does_not_require_comparator_when_verified_peer_exists(self):
        out = classify(state(
            ["A"],
            tool("VERIFIED", 1, {"A": "SUPPORTED"}, safe=[]),
            tool("UNKNOWN_PEER", 1, {"A": "UNKNOWN"}, safe=[]),
        ))
        self.assertEqual(out["minimum_reality_action"], "UNIVERSAL_PROOF", out)
        self.assertEqual(out["best_verified_sufficient_cost"], 1.0)

    def test_strictly_cheaper_unobservable_unknown_is_irreducible(self):
        out = classify(state(
            ["A"],
            tool("CHEAP", 1, {"A": "UNKNOWN"}, safe=[]),
            tool("KNOWN", 2, {"A": "SUPPORTED"}, safe=[]),
        ))
        self.assertEqual(out["minimum_reality_action"], "MATCHED_COMPARATOR", out)

    def test_cheaper_safe_frontier_can_be_probed_before_more_expensive_irreducible_route(self):
        out = classify(state(
            ["A"],
            tool("CHEAP_SAFE", 1, {"A": "UNKNOWN"}, safe=["A"]),
            tool("MID_UNSAFE", 2, {"A": "UNKNOWN"}, safe=[]),
            tool("KNOWN", 3, {"A": "SUPPORTED"}, safe=[]),
        ))
        self.assertEqual(out["minimum_reality_action"], "SAFE_PROBE", out)
        self.assertEqual(out["recommended_safe_probe"]["tool_id"], "CHEAP_SAFE")

    def test_after_cheapest_route_is_disproved_next_frontier_becomes_load_bearing(self):
        out = classify(state(
            ["A"],
            tool("CHEAP", 1, {"A": "UNSUPPORTED"}, safe=[]),
            tool("MID_UNSAFE", 2, {"A": "UNKNOWN"}, safe=[]),
            tool("KNOWN", 3, {"A": "SUPPORTED"}, safe=[]),
        ))
        self.assertEqual(out["minimum_reality_action"], "MATCHED_COMPARATOR", out)
        self.assertEqual(out["decision_frontier_cost"], 2.0)

    def test_all_routes_disproved_is_universal_no_route_region(self):
        out = classify(state(
            ["A"],
            tool("A", 1, {"A": "UNSUPPORTED"}, safe=[]),
            tool("B", 2, {"A": "UNSUPPORTED"}, safe=[]),
        ))
        self.assertEqual(out["minimum_reality_action"], "UNIVERSAL_PROOF", out)
        self.assertIsNone(out["best_verified_sufficient_cost"])

    def test_identity_scope_incomplete_fails_closed(self):
        x = state(["A"], tool("A", 1, {"A": "SUPPORTED"}))
        x["identity_scope_complete"] = False
        out = classify(x)
        self.assertEqual(out["status"], "FAIL_CLOSED__INVALID_PARTITION_INPUT")
        self.assertTrue(out["matched_comparator_required_now"])

    def test_zero_credit(self):
        out = classify(state(["A"], tool("A", 1, {"A": "SUPPORTED"})))
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
