from __future__ import annotations
import json
import unittest
from pathlib import Path

from canonical.runtime.abductive_residual_theorem_v1 import evaluate as abductive_evaluate
from canonical.runtime.terminal_next_action_compiler_v2 import compile_next_frontier_v2

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class LiveProofSchedulerReconciliationTests(unittest.TestCase):
    def test_current_authority_matches_verified_v2_scheduler(self):
        authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
        evidence = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
        receipt = load("canonical/verification/TERMINAL_NEXT_ACTION_COMPILER_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        exhaustion = load("canonical/governance/OPUS55_SYNTHESIS_ZERO_REALITY_DISCHARGE_EXHAUSTION_V1.json")
        out = compile_next_frontier_v2(registry, evidence, hypergraph)
        projected = authority["compiled_next_frontier"]

        self.assertTrue(receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"))
        self.assertEqual(receipt["public_runner"]["conclusion"], "success")
        self.assertFalse(exhaustion["current_zero_reality_discharge_available"])

        self.assertEqual(projected["schema"], out["schema"])
        self.assertEqual(projected["proved_predicate_count"], out["proved_predicate_count"])
        self.assertEqual(projected["unresolved_predicate_count"], out["unresolved_predicate_count"])
        self.assertEqual(projected["primary_action_id"], out["primary_action_id"])
        self.assertEqual(projected["primary_action_state"], out["primary_action_state"])
        self.assertEqual(
            projected["available_zero_reality_critical_actions"],
            out["available_zero_reality_critical_actions"],
        )
        self.assertEqual(
            projected["highest_leverage_blocked_action_id"],
            out["highest_leverage_blocked_action_id"],
        )
        self.assertEqual(
            projected["highest_leverage_blocked_action_preconditions"],
            out["highest_leverage_blocked_action_preconditions"],
        )
        self.assertEqual(
            projected["blocked_critical_actions"],
            out["blocked_critical_actions"],
        )
        self.assertNotIn(
            "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA",
            projected["available_zero_reality_critical_actions"],
        )

    def test_matched_abductive_projection_matches_live_input(self):
        authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        inp = load("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V1.json")
        receipt = load("canonical/verification/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        out = abductive_evaluate(inp)
        projected = authority["matched_scope_abductive_residual"]

        self.assertEqual(out["target_count"], 11)
        self.assertEqual(out["verified_rule_count"], 11)
        self.assertEqual(len(out["primitive_residual_facts"]), 22)
        self.assertEqual(out["shared_residual_groups"], [])
        self.assertEqual(out["minimum_joint_residual_size"], 22)
        self.assertEqual(projected["child_target_count"], out["target_count"])
        self.assertEqual(projected["verified_child_edge_count"], out["verified_rule_count"])
        self.assertEqual(projected["primitive_residual_fact_count"], len(out["primitive_residual_facts"]))
        self.assertEqual(projected["shared_residual_group_count"], len(out["shared_residual_groups"]))
        self.assertEqual(projected["minimum_joint_residual_size"], out["minimum_joint_residual_size"])
        self.assertFalse(projected["exact_further_compression_found"])
        self.assertEqual(receipt["public_runner"]["conclusion"], "success")

    def test_terminal_truth_unchanged_and_fail_closed(self):
        authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        self.assertEqual(authority["truth"]["opus55_acceptance"], "2/19_PASS__17/19_OPEN")
        self.assertFalse(authority["truth"]["achieved"])
        self.assertEqual(authority["atomic_acceptance_frontier"]["proved"], 7)
        self.assertEqual(authority["atomic_acceptance_frontier"]["unresolved"], 31)
        self.assertEqual(authority["compiled_next_frontier"]["capability_credit_delta"], 0)
        self.assertEqual(authority["compiled_next_frontier"]["family_credit_delta"], 0)
        self.assertFalse(authority["compiled_next_frontier"]["execution_authority"])
        self.assertFalse(authority["compiled_next_frontier"]["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
