import json
from pathlib import Path
import unittest

from canonical.runtime.terminal_proof_solver_v1 import evaluate
from canonical.runtime.terminal_next_action_compiler_v1 import compile_next_frontier

ROOT = Path(__file__).resolve().parents[2]


class TerminalProofSolverTests(unittest.TestCase):
    def test_exact_minimum_bundle_with_dependency(self):
        out = evaluate({
            "facts": ["BASE"],
            "goals": ["G1", "G2"],
            "rules": [
                {"id": "R1", "requires": ["P1"], "proves": ["G1"]},
                {"id": "R2", "requires": ["P2"], "proves": ["G2"]},
            ],
            "actions": [
                {"id": "A1", "requires": ["BASE"], "proves": ["P1"], "declared_cost": 1},
                {"id": "A2", "requires": ["P1"], "proves": ["P2"], "declared_cost": 1},
                {"id": "A3", "requires": ["BASE"], "proves": ["P2"], "declared_cost": 5},
            ],
            "learned_clauses": [],
        })
        self.assertEqual(out["status"], "SAT_DECLARED_MODEL", out)
        self.assertTrue(out["terminal_sat"])
        self.assertEqual(out["minimum_action_bundle"]["action_ids"], ["A1", "A2"])
        self.assertEqual(out["minimum_action_bundle"]["declared_cost"], 2.0)

    def test_learned_clause_prunes_impossible_route(self):
        out = evaluate({
            "facts": ["TB4_FROZEN_NO_REPLAY", "TB4_MAX_180", "TB4_NEEDS_220"],
            "goals": ["TB4_PASS"],
            "rules": [],
            "actions": [
                {"id": "RUN_CURRENT_TB4", "requires": [], "proves": ["TB4_PASS"], "declared_cost": 1},
            ],
            "learned_clauses": [
                {
                    "id": "TB4_180_LT_220",
                    "when_all": ["TB4_FROZEN_NO_REPLAY", "TB4_MAX_180", "TB4_NEEDS_220"],
                    "blocks_actions": ["RUN_CURRENT_TB4"],
                    "reason": "Verified attainability upper bound is below threshold.",
                }
            ],
        })
        self.assertEqual(out["status"], "UNSAT_CURRENT_DECLARED_MODEL", out)
        self.assertEqual(out["blocked_action_ids"], ["RUN_CURRENT_TB4"])
        self.assertEqual(out["minimal_unsatisfied_cores"], [["TB4_PASS"]])
        self.assertFalse(out["execution_authority"])

    def test_invalid_model_fails_closed(self):
        out = evaluate({"facts": [], "goals": [], "actions": [], "rules": []})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertFalse(out["execution_authority"])

    def test_live_next_action_projection_matches_current_authority(self):
        registry = json.loads((ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json").read_text())
        evidence = json.loads((ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json").read_text())
        hypergraph = json.loads((ROOT / "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json").read_text())
        authority = json.loads((ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json").read_text())

        fresh = compile_next_frontier(registry, evidence, hypergraph)
        projected = authority["compiled_next_frontier"]

        self.assertEqual(fresh["proved_predicate_count"], 7, fresh)
        self.assertEqual(fresh["unresolved_predicate_count"], 31, fresh)
        self.assertNotEqual(fresh["primary_action_id"], "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA")
        self.assertNotIn(
            "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA",
            fresh["available_zero_reality_critical_actions"],
        )
        self.assertIn(
            "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA",
            [x["id"] for x in fresh["blocked_critical_actions"]],
        )

        keys = [
            "primary_action_id",
            "primary_action_state",
            "unresolved_target_count",
            "primary_unsatisfied_preconditions",
            "highest_leverage_blocked_action_id",
            "highest_leverage_blocked_action_target_count",
            "highest_leverage_blocked_action_preconditions",
            "available_zero_reality_critical_actions",
        ]
        # Authority uses unresolved_target_count for the primary while the runtime
        # output uses primary_unresolved_target_count.
        self.assertEqual(projected["primary_action_id"], fresh["primary_action_id"])
        self.assertEqual(projected["primary_action_state"], fresh["primary_action_state"])
        self.assertEqual(projected["unresolved_target_count"], fresh["primary_unresolved_target_count"])
        self.assertEqual(projected["primary_unsatisfied_preconditions"], fresh["primary_unsatisfied_preconditions"])
        self.assertEqual(projected["highest_leverage_blocked_action_id"], fresh["highest_leverage_blocked_action_id"])
        self.assertEqual(projected["highest_leverage_blocked_action_target_count"], fresh["highest_leverage_blocked_action_target_count"])
        self.assertEqual(projected["highest_leverage_blocked_action_preconditions"], fresh["highest_leverage_blocked_action_preconditions"])
        self.assertEqual(projected["available_zero_reality_critical_actions"], fresh["available_zero_reality_critical_actions"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
