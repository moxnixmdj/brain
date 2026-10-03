from __future__ import annotations

import copy
import importlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = "canonical.runtime.adaptive_terminal_closure_controller_v1"


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def live_docs():
    return [
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
        load("canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json"),
        load("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"),
        load("canonical/verification/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"),
        load("canonical/verification/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
        load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"),
        load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
        load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"),
    ]


class AdaptiveTerminalClosureV13Tests(unittest.TestCase):
    def m(self):
        return importlib.import_module(MODULE)

    def test_current_v13_world_compiles_exact_31_unit_frontier(self):
        out = self.m().evaluate(*live_docs())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["live_world"]["proved_predicates"], 11)
        self.assertEqual(out["live_world"]["unresolved_predicates"], 27)
        self.assertEqual(out["live_world"]["active_zero_reality_requirements"], 17)
        self.assertEqual(out["live_world"]["active_nondominated_certificates"], 14)
        self.assertEqual(out["live_world"]["zero_reality_covered_predicates"], 25)
        self.assertEqual(out["live_world"]["primitive_zero_reality_work_units"], 31)
        self.assertEqual(out["live_world"]["matched_primitive_child_facts"], 16)
        self.assertEqual(len(out["acceptance_work_units"]), 31)
        self.assertEqual(len(out["first_resource_priority_work_unit_ids"]), 16)

    def test_two_direct_reality_blocked_predicates_are_not_zero_reality_targets(self):
        out = self.m().evaluate(*live_docs())
        blocked = {
            "FINANCE_UNCOVERED_SCOPE_AUDIT",
            "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        }
        targets = {
            p for row in out["acceptance_work_units"]
            for p in row.get("target_predicates", [])
        }
        self.assertTrue(blocked.isdisjoint(targets))
        self.assertEqual(len(targets), 25)

    def test_tool_discovery_is_bound_to_v5(self):
        out = self.m().evaluate(*live_docs())
        rows = [
            row for row in out["acceptance_work_units"]
            if "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" in row.get("target_predicates", [])
        ]
        self.assertEqual(len(rows), 1, rows)
        row = rows[0]
        self.assertTrue(row["mandatory_tool_discovery_v5_gate"])
        self.assertIn(
            "MANDATORY_TOOL_DISCOVERY_V5_OVER_V4_OVER_V3_OVER_VERIFIED_V2_RETRIEVAL_GATE",
            row["source_hints"],
        )
        self.assertTrue(out["execution_policy"]["tool_discovery_v5_gate_mandatory"])

    def test_tb4_is_search_only(self):
        out = self.m().evaluate(*live_docs())
        row = next(
            x for x in out["acceptance_work_units"]
            if x["requirement"] == "MACHINE_VERIFIED_TB4_ROUTE_UPPER_BOUND_GE_220"
        )
        self.assertEqual(row["execution_mode"], "ROUTE_SEARCH_ONLY__CURRENT_DIRECT_EXECUTION_FORBIDDEN")

    def test_ownership_reconciliation_remains_parallel(self):
        out = self.m().evaluate(*live_docs())
        families = {x["family"] for x in out["ownership_reconciliation_work_units"]}
        self.assertEqual(
            families,
            {
                "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
                "SUBAGENT_DELEGATION_AND_COORDINATION",
            },
        )
        self.assertTrue(out["execution_policy"]["ownership_reconciliation_runs_in_parallel"])

    def test_unknown_probabilities_are_not_invented(self):
        out = self.m().evaluate(*live_docs())
        self.assertTrue(all(x["empirical_posterior"] is None for x in out["acceptance_work_units"]))
        self.assertEqual(out["probability_policy"]["empirically_scored_work_unit_count"], 0)

    def test_empirical_history_changes_scheduling_only(self):
        docs = live_docs()
        req = "GDPVAL_AA_ROUTE_BOUND"
        out = self.m().evaluate(
            *docs,
            attempt_history={
                req: {
                    "verified_successes": 3,
                    "verified_failures": 1,
                    "total_wall_seconds": 40,
                }
            },
        )
        row = next(x for x in out["acceptance_work_units"] if x["requirement"] == req)
        self.assertIsNotNone(row["empirical_posterior"])
        self.assertAlmostEqual(
            row["empirical_posterior"]["posterior_mean_verified_discharge_probability"],
            4 / 6,
        )
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["acceptance_credit_delta"], 0)

    def test_stale_v12_pointer_fails_closed(self):
        docs = copy.deepcopy(live_docs())
        docs[-1]["status"] = "ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V12_CURRENT"
        out = self.m().evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn("SCHEDULING_AUTHORITY_NOT_CURRENT_V13_INDEPENDENT_PASS", out["errors"])

    def test_failed_or_partial_v5_epoch_consumption_fails_closed(self):
        docs = copy.deepcopy(live_docs())
        docs[-1]["mandatory_tool_discovery_retrieval"]["failed_or_partial_source_cell_consumes_epoch"] = True
        out = self.m().evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn(
            "RETRIEVAL_FAIL_CLOSED_FLAG_NOT_FALSE:failed_or_partial_source_cell_consumes_epoch",
            out["errors"],
        )


    def test_v5_consumed_cell_replay_fails_closed(self):
        docs = copy.deepcopy(live_docs())
        docs[-1]["mandatory_tool_discovery_retrieval"]["consumed_cell_replay_allowed"] = True
        out = self.m().evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn(
            "RETRIEVAL_FAIL_CLOSED_FLAG_NOT_FALSE:consumed_cell_replay_allowed",
            out["errors"],
        )

    def test_v5_empty_or_failed_attempt_cannot_prove_nonexistence(self):
        docs = copy.deepcopy(live_docs())
        docs[-1]["mandatory_tool_discovery_retrieval"]["empty_or_failed_attempt_proves_nonexistence"] = True
        out = self.m().evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn(
            "RETRIEVAL_FAIL_CLOSED_FLAG_NOT_FALSE:empty_or_failed_attempt_proves_nonexistence",
            out["errors"],
        )

    def test_controller_never_grants_credit_or_reality_authority(self):
        out = self.m().evaluate(*live_docs())
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertEqual(out["ownership_credit_delta"], 0)
        self.assertEqual(out["incremental_spend_usd"], 0)
        self.assertEqual(out["new_reality_units_consumed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
