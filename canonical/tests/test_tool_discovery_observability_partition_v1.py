from __future__ import annotations

import unittest

from canonical.runtime.tool_discovery_observability_partition_v1 import classify


def tool(tid, cost, state="UNKNOWN", safe=()):
    return {
        "tool_id": tid,
        "cost": cost,
        "capability_evidence": {"CAP_A": state},
        "safe_probe_capabilities": list(safe),
    }


def base(*tools):
    return {
        "identity_scope_complete": True,
        "required_capabilities": ["CAP_A"],
        "admissible_tools": list(tools),
    }


class ToolDiscoveryObservabilityPartitionTests(unittest.TestCase):
    def test_unprobeable_cheaper_unknown_requires_matched_comparator(self):
        out = classify(base(
            tool("CHEAP", 1, "UNKNOWN", ()),
            tool("EXPENSIVE", 2, "SUPPORTED", ("CAP_A",)),
        ))
        self.assertTrue(out["matched_comparator_required"], out)
        self.assertFalse(out["universal_proof_eligible"])
        self.assertEqual(
            out["ambiguous_decision_relevant_routes"][0]["tool_id"], "CHEAP"
        )

    def test_probeable_cheaper_unknown_is_universal_region(self):
        out = classify(base(
            tool("CHEAP", 1, "UNKNOWN", ("CAP_A",)),
            tool("EXPENSIVE", 2, "SUPPORTED", ("CAP_A",)),
        ))
        self.assertFalse(out["matched_comparator_required"], out)
        self.assertTrue(out["universal_proof_eligible"])

    def test_negative_cheaper_evidence_removes_ambiguity(self):
        out = classify(base(
            tool("CHEAP", 1, "UNSUPPORTED", ()),
            tool("EXPENSIVE", 2, "SUPPORTED", ("CAP_A",)),
        ))
        self.assertTrue(out["universal_proof_eligible"], out)
        self.assertEqual(out["ruled_out_tool_ids"], ["CHEAP"])

    def test_unprobeable_more_expensive_unknown_cannot_change_least_cost(self):
        out = classify(base(
            tool("CHEAP_VERIFIED", 1, "SUPPORTED", ("CAP_A",)),
            tool("EXPENSIVE_UNKNOWN", 2, "UNKNOWN", ()),
        ))
        self.assertTrue(out["universal_proof_eligible"], out)
        row = out["resolvable_unknown_routes"][0]
        self.assertTrue(row["cannot_improve_current_best_verified_cost"])

    def test_no_verified_route_plus_unprobeable_unknown_requires_matched(self):
        out = classify(base(tool("ONLY", 1, "UNKNOWN", ())))
        self.assertTrue(out["matched_comparator_required"], out)

    def test_equal_cost_unobservable_is_conservatively_matched(self):
        out = classify(base(
            tool("A", 1, "SUPPORTED", ("CAP_A",)),
            tool("B", 1, "UNKNOWN", ()),
        ))
        self.assertTrue(out["matched_comparator_required"], out)

    def test_identity_scope_must_be_closed_first(self):
        state = base(tool("T", 1, "SUPPORTED", ("CAP_A",)))
        state["identity_scope_complete"] = False
        out = classify(state)
        self.assertEqual(out["status"], "FAIL_CLOSED__INVALID_PARTITION_INPUT")
        self.assertTrue(out["matched_comparator_required"])

    def test_zero_credit_and_no_authority(self):
        out = classify(base(tool("T", 1, "SUPPORTED", ("CAP_A",))))
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertEqual(out["terminal_results_replayed"], 0)
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
