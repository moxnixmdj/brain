from __future__ import annotations
import json
import unittest
from pathlib import Path

from canonical.runtime.abductive_residual_theorem_v1 import evaluate as abductive_evaluate
from canonical.runtime.terminal_next_action_compiler_v2 import compile_next_frontier_v2

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class CurrentExecutableFrontierV2Tests(unittest.TestCase):
    def test_historical_v1_projection_stays_quarantined(self):
        authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        historical = authority["compiled_next_frontier"]
        self.assertTrue(historical["status"].startswith("SUPERSEDED_FOR_EXECUTION"))
        self.assertFalse(historical["execution_authority"])
        self.assertFalse(historical["promotion_authority"])
        self.assertEqual(
            historical["historical_projection"]["primary_action_id"],
            "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA",
        )

    def test_current_executable_frontier_matches_v2_compiler_exactly(self):
        authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
        evidence = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
        receipt = load("canonical/verification/TERMINAL_NEXT_ACTION_COMPILER_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        exhaustion = load("canonical/governance/OPUS55_SYNTHESIS_ZERO_REALITY_DISCHARGE_EXHAUSTION_V1.json")

        out = compile_next_frontier_v2(registry, evidence, hypergraph)
        live = authority["current_executable_frontier_v2"]

        self.assertTrue(receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"))
        self.assertEqual(receipt["public_runner"]["conclusion"], "success")
        self.assertFalse(exhaustion["current_zero_reality_discharge_available"])
        for key in (
            "schema",
            "status",
            "source_hypergraph",
            "proved_predicate_count",
            "unresolved_predicate_count",
            "primary_action_id",
            "primary_action_state",
            "primary_unresolved_target_count",
            "primary_unresolved_targets",
            "primary_unsatisfied_preconditions",
            "highest_leverage_blocked_action_id",
            "highest_leverage_blocked_action_target_count",
            "highest_leverage_blocked_action_preconditions",
            "available_zero_reality_critical_actions",
            "blocked_critical_actions",
        ):
            self.assertEqual(live[key], out[key], key)

        self.assertNotIn(
            "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA",
            live["available_zero_reality_critical_actions"],
        )
        self.assertEqual(
            live["primary_action_id"],
            "BUILD_DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE",
        )

    def test_matched_child_abductive_residual_is_exact_and_unshared(self):
        authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        inp = load("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V1.json")
        receipt = load("canonical/verification/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        out = abductive_evaluate(inp)
        projected = authority["matched_scope_abductive_residual"]

        self.assertEqual(receipt["public_runner"]["conclusion"], "success")
        self.assertEqual(out["target_count"], 11)
        self.assertEqual(out["verified_rule_count"], 11)
        self.assertEqual(len(out["primitive_residual_facts"]), 22)
        self.assertEqual(out["shared_residual_groups"], [])
        self.assertEqual(out["minimum_joint_residual_size"], 22)
        self.assertEqual(projected["primitive_residual_fact_count"], 22)
        self.assertEqual(projected["shared_residual_group_count"], 0)
        self.assertFalse(projected["exact_further_compression_found"])

    def test_terminal_truth_remains_fail_closed(self):
        authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        self.assertEqual(authority["truth"]["opus55_acceptance"], "2/19_PASS__17/19_OPEN")
        self.assertFalse(authority["truth"]["achieved"])
        self.assertEqual(authority["atomic_acceptance_frontier"]["proved"], 7)
        self.assertEqual(authority["atomic_acceptance_frontier"]["unresolved"], 31)
        live = authority["current_executable_frontier_v2"]
        self.assertEqual(live["capability_credit_delta"], 0)
        self.assertEqual(live["family_credit_delta"], 0)
        self.assertFalse(live["execution_authority"])
        self.assertFalse(live["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
