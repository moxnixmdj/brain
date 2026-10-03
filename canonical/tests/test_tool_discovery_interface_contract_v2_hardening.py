from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_interface_contract_v2_hardening_proof as proof


class ToolDiscoveryInterfaceV2HardeningTests(unittest.TestCase):
    def test_current_hardening_proof_passes_without_acceptance_credit(self):
        out=proof.evaluate()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertEqual(out["source_blob_drift"],[])
        self.assertTrue(out["scope_preserved_without_brain_only_narrowing"])
        self.assertFalse(out["universal_target_proved"])
        self.assertFalse(out["complete_interface_instance_verified"])
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_duplicate_source_id_alias_is_load_bearing(self):
        row=proof.duplicate_source_id_countermodel()
        self.assertEqual(row["observed"],{"action":"SELECT","tool_id":"EXPENSIVE"})
        self.assertEqual(
            row["required_property"],
            "AUTHORITATIVE_DISCOVERY_SOURCE_IDS_ARE_CANONICAL_NONEMPTY_AND_UNIQUE_WITHIN_EPOCH",
        )

    def test_result_must_be_visible_before_source_is_marked_queried(self):
        row=proof.non_atomic_incorporation_countermodel()
        self.assertEqual(row["observed"],{"action":"SELECT","tool_id":"EXPENSIVE"})
        self.assertEqual(
            row["required_property"],
            "DISCOVERY_RESULT_IS_ATOMICALLY_INCORPORATED_INTO_VISIBLE_TOOL_STATE_BEFORE_SOURCE_IS_MARKED_QUERIED",
        )

    def test_duplicate_tool_id_alias_makes_route_identity_ambiguous(self):
        row=proof.duplicate_tool_id_countermodel()
        self.assertEqual(row["observed"],{"action":"SELECT","tool_id":"DUP"})
        self.assertEqual(
            row["required_property"],
            "VISIBLE_TOOL_IDS_ARE_CANONICAL_NONEMPTY_AND_UNIQUE_WITHIN_EPOCH",
        )

    def test_nonfinite_cost_has_no_total_least_cost_semantics(self):
        row=proof.nonfinite_cost_countermodel()
        self.assertTrue(row["nan_is_nonfinite"])
        self.assertEqual(row["observed"]["action"],"SELECT")
        self.assertEqual(
            row["required_property"],
            "DECLARED_SOURCE_AND_TOOL_COSTS_ARE_FINITE_NUMERIC_VALUES_WITH_DETERMINISTIC_ID_TIEBREAKS",
        )

    def test_v2_exposes_real_remaining_facts(self):
        out=proof.evaluate()
        self.assertEqual(len(out["remaining_irreducible_facts"]),3)
        self.assertIn(
            "INDEPENDENT_EVIDENCE_THAT_AVAILABLE_AUTHORITATIVE_DISCOVERY_SOURCE_UNION_IS_COMPLETE_FOR_COMMON_FROZEN_BRAIN_OPUS_TOOL_AUTHORITY_IN_THE_DECISION_EPOCH",
            out["remaining_irreducible_facts"],
        )
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertEqual(out["new_reality_units_consumed"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
