from __future__ import annotations

import copy
import unittest
from unittest import mock

from canonical.runtime import adaptive_terminal_closure_controller_v2 as v2


class AdaptiveTerminalClosureControllerV2Tests(unittest.TestCase):
    def test_live_v13_v5_postdual_frontier_compiles(self):
        out = v2.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["live_world"]["unresolved_predicates"], 27)
        self.assertEqual(out["live_world"]["nondominated_certificates"], 14)
        self.assertEqual(out["live_world"]["verified_zero_reality_requirements"], 17)
        self.assertEqual(out["live_world"]["matched_primitive_child_facts"], 16)
        self.assertEqual(out["action_refinement"]["direct_nonmatched_work_units"], 15)
        self.assertEqual(out["action_refinement"]["primitive_acceptance_work_units"], 31)
        self.assertEqual(len(out["acceptance_work_units"]), 31)
        self.assertEqual(len(out["first_resource_priority_work_unit_ids"]), 16)

    def test_postdual_discharged_source_requirements_are_not_scheduled(self):
        out = v2.evaluate()
        ids = {row["work_unit_id"] for row in out["acceptance_work_units"]}
        self.assertTrue(v2.DISCHARGED.isdisjoint(ids))
        self.assertEqual(
            set(out["post_dual_transition"]["direct_reality_blocked_predicates"]),
            {
                "FINANCE_UNCOVERED_SCOPE_AUDIT",
                "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
            },
        )
        self.assertFalse(out["post_dual_transition"]["source_admission_is_acceptance"])

    def test_tool_discovery_uses_v5_gate_not_legacy_v3_label(self):
        out = v2.evaluate()
        rows = [
            row
            for row in out["acceptance_work_units"]
            if "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
            in row["target_predicates"]
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row["mandatory_tool_discovery_v5_gate"])
        self.assertNotIn("mandatory_tool_discovery_v3_gate", row)
        self.assertEqual(
            row["source_hints"][0],
            "MANDATORY_TOOL_DISCOVERY_V5_OVER_V4_OVER_V3_OVER_VERIFIED_V2_BASE_RETRIEVAL_GATE",
        )
        self.assertTrue(out["execution_policy"]["tool_discovery_v5_gate_mandatory"])

    def test_ownership_reconciliation_remains_parallel(self):
        out = v2.evaluate()
        families = {
            row["family"] for row in out["ownership_reconciliation_work_units"]
        }
        self.assertEqual(
            families,
            {
                "SUBAGENT_DELEGATION_AND_COORDINATION",
                "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
            },
        )
        self.assertTrue(out["execution_policy"]["ownership_reconciliation_runs_in_parallel"])

    def test_no_credit_or_reality_authority(self):
        out = v2.evaluate()
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertEqual(out["ownership_credit_delta"], 0)
        self.assertEqual(out["incremental_spend_usd"], 0)
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertFalse(out["compatibility"]["compatibility_projection_has_authority"])

    def test_pinned_v1_or_current_authority_drift_fails_closed(self):
        bad = dict(v2.PINNED)
        bad[v2.PATHS["v1"]] = "0" * 40
        with mock.patch.dict(v2.PINNED, bad, clear=True):
            out = v2.evaluate()
        self.assertFalse(out["pass"])
        self.assertTrue(
            any(x.startswith("PINNED_BLOB_DRIFT:") for x in out["errors"])
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
