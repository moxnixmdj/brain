from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.terminal_proof_route_autocompiler import compile_routes


def contract():
    return {
        "schema": "PROJECT_BRAIN_OBJECTIVE_ORACLE_DOMINANCE_INPUT_V1",
        "contracts": [
            {
                "behavior_id": "B1",
                "required_dimensions": ["D1", "D2"],
                "dimensions": [
                    {
                        "id": "D1",
                        "mechanism": "m1",
                        "objective": True,
                        "falsifiable": True,
                        "hidden_from_candidate": True,
                        "terminal_load_bearing": True,
                        "existing_evidence": "canonical/runtime/shared.py",
                    },
                    {
                        "id": "D2",
                        "mechanism": "m2",
                        "objective": True,
                        "falsifiable": True,
                        "hidden_from_candidate": True,
                        "terminal_load_bearing": True,
                        "existing_evidence": "canonical/runtime/shared.py",
                    },
                ],
                "candidate_receives_hidden_oracle": False,
                "weaker_comparator_dependency": "OLD",
                "route_gates": {
                    "candidate_package_frozen": True,
                    "executable_evaluator_bound": True,
                    "population_or_source_pool_frozen": False,
                    "information_boundary_frozen": True,
                    "post_freeze_selector_frozen": False,
                    "terminal_parent_binding_frozen": False,
                    "independent_verification_pass": False,
                },
            }
        ],
    }


class TerminalProofRouteAutocompilerTests(unittest.TestCase):
    def test_compiles_only_open_gates(self):
        out = compile_routes(contract())
        self.assertTrue(out["pass"])
        actions = [x["gate"] for x in out["zero_reality_materialization_actions"]]
        self.assertEqual(
            actions,
            [
                "population_or_source_pool_frozen",
                "post_freeze_selector_frozen",
                "terminal_parent_binding_frozen",
                "independent_verification_pass",
            ],
        )
        self.assertEqual(out["fresh_terminal_evidence_consumed"], 0)

    def test_exact_evidence_reuse_is_exposed_without_semantic_projection(self):
        out = compile_routes(contract())
        self.assertEqual(len(out["shared_evaluator_basis"]), 1)
        self.assertEqual(out["shared_evaluator_basis"][0]["reuse_count"], 2)
        self.assertEqual(
            out["shared_evaluator_basis"][0]["reuse_authority"],
            "EXACT_EVIDENCE_REFERENCE_ONLY__NO_SEMANTIC_PROJECTION",
        )

    def test_missing_evaluator_blocks_evaluator_binding_action(self):
        p = contract()
        p["contracts"][0]["dimensions"][1][
            "existing_evidence"
        ] = "NEW_TERMINAL_OBJECTIVE_ORACLE_COMPONENT_REQUIRED"
        p["contracts"][0]["route_gates"]["executable_evaluator_bound"] = False
        out = compile_routes(p)
        row = out["contracts"][0]
        self.assertFalse(row["evaluator_coverage_complete"])
        self.assertEqual(row["evaluator_gaps"], ["D2"])
        self.assertNotIn(
            "executable_evaluator_bound",
            [x["gate"] for x in out["zero_reality_materialization_actions"]],
        )

    def test_semantic_unknown_is_not_invented(self):
        p = contract()
        p["contracts"][0]["dimensions"][0]["objective"] = False
        out = compile_routes(p)
        self.assertEqual(out["status"], "SEMANTIC_GAPS_BLOCK_AUTOCOMPILE")
        self.assertGreater(out["semantic_gap_count"], 0)
        self.assertEqual(out["zero_reality_materialization_actions"], [])

    def test_hidden_oracle_leak_fails_closed(self):
        p = contract()
        p["contracts"][0]["candidate_receives_hidden_oracle"] = True
        out = compile_routes(p)
        self.assertFalse(out["pass"])
        self.assertIn("B1:HIDDEN_ORACLE_BOUNDARY_INVALID", out["errors"])

    def test_ready_route_gets_no_execution_or_promotion_authority(self):
        p = contract()
        for k in p["contracts"][0]["route_gates"]:
            p["contracts"][0]["route_gates"][k] = True
        out = compile_routes(p)
        self.assertEqual(out["route_ready_behavior_ids"], ["B1"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["capability_credit_delta"], 0)

    def test_live_objective_input_has_no_semantic_or_evaluator_gaps(self):
        p = json.loads(
            Path(
                "canonical/governance/OBJECTIVE_ORACLE_DOMINANCE_LIVE_INPUT_V1.json"
            ).read_text(encoding="utf-8")
        )
        out = compile_routes(p)
        self.assertTrue(out["pass"])
        self.assertEqual(out["semantic_gap_count"], 0)
        self.assertEqual(out["evaluator_gap_count"], 0)
        self.assertEqual(out["fresh_terminal_evidence_consumed"], 0)


if __name__ == "__main__":
    unittest.main()
