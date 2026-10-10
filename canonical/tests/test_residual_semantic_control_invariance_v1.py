from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import ast
import unittest

from canonical.runtime import open_world_semantic_control_v1 as control
from canonical.runtime import residual_semantic_control_invariance_v1 as builder
from canonical.runtime import residual_semantic_control_invariance_verify_v1 as verifier

ROOT = Path(__file__).resolve().parents[2]


def problem(**overrides):
    value = {
        "environment_id": "R2::FINANCE_SEMANTIC_ADEQUACY_TAIL",
        "goal_id": "R2::SAFE_NEXT_CONTROL_ACTION",
        "semantic_state": "UNRESOLVED_OPEN_WORLD",
        "decision_relevant": True,
        "information_origin": {
            "context_value_bound": False,
            "information_owner": "UNKNOWN",
            "source_scope": {"kind": "UNBOUND_SOURCE"},
            "discovery_delegated": False,
            "clarification_key": "margin_context",
        },
    }
    value.update(overrides)
    return value


class ResidualSemanticControlTests(unittest.TestCase):
    def test_unknown_origin_routes_to_minimum_clarification(self):
        out = control.resolve(problem(), repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["control_sufficient"])
        self.assertEqual(out["action"], "ASK_USER_MINIMUM_CLARIFICATION")
        self.assertFalse(out["semantic_decision_sufficient"])
        self.assertFalse(out["open_world_semantics_closed"])
        self.assertFalse(out["intended_sense_identified"])

    def test_delegated_external_origin_routes_to_minimum_research(self):
        p = problem()
        p["information_origin"] = {
            "context_value_bound": False,
            "information_owner": "EXTERNAL_WORLD",
            "source_scope": {"kind": "UNBOUND_SOURCE"},
            "discovery_delegated": True,
        }
        out = control.resolve(p, repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["action"], "RESEARCH_MINIMUM_AUTHENTICATED_FACT")

    def test_bound_external_source_routes_only_to_bound_source(self):
        p = problem()
        p["information_origin"] = {
            "context_value_bound": False,
            "information_owner": "EXTERNAL_WORLD",
            "source_scope": {"kind": "BOUND_SOURCE", "source_id": "loan_contract"},
            "discovery_delegated": False,
        }
        out = control.resolve(p, repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["action"], "OBSERVE_BOUND_SOURCE_ONLY")

    def test_nested_semantic_identity_cannot_control_route(self):
        p = problem()
        p["information_origin"]["metadata"] = {
            "nested": {"sense_id": "margin%1:21:02::"}
        }
        out = control.resolve(p, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTIC_IDENTITY_MUST_NOT_CONTROL_ORIGIN_ROUTE", out["reason"])

    def test_residual_world_identity_cannot_control_route(self):
        p = problem()
        p["information_origin"]["residual_world"] = "profit-margin-world"
        out = control.resolve(p, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTIC_IDENTITY_MUST_NOT_CONTROL_ORIGIN_ROUTE", out["reason"])

    def test_already_bound_context_is_not_residual_control(self):
        p = problem()
        p["information_origin"]["context_value_bound"] = True
        out = control.resolve(p, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertIn("BOUND_CONTEXT_IS_NOT_RESIDUAL_UNRESOLVED_CONTROL", out["reason"])

    def test_decision_irrelevant_case_cannot_gain_control_authority(self):
        p = problem(decision_relevant=False)
        out = control.resolve(p, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertFalse(out["control_action_authority"])

    def test_verifier_recomputes_and_rejects_tampered_action(self):
        p = problem()
        candidate = builder.build_candidate(
            environment_id=p["environment_id"],
            goal_id=p["goal_id"],
            semantic_state=p["semantic_state"],
            decision_relevant=True,
            information_origin=p["information_origin"],
        )
        tampered = deepcopy(candidate)
        tampered["action"] = "BUY_ASSET"
        out = verifier.verify(tampered, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertFalse(out["independent_verified"])
        self.assertIn("CANDIDATE_RECOMPUTATION_MISMATCH:action", out["reason"])

    def test_verified_receipt_is_control_only(self):
        p = problem()
        candidate = builder.build_candidate(
            environment_id=p["environment_id"],
            goal_id=p["goal_id"],
            semantic_state=p["semantic_state"],
            decision_relevant=True,
            information_origin=p["information_origin"],
        )
        receipt = verifier.verify(candidate, repo_root=ROOT)
        self.assertTrue(receipt["pass"], receipt)
        self.assertTrue(
            receipt["all_unmodeled_decision_relevant_alternatives_imply_control_action"]
        )
        self.assertEqual(
            receipt["control_scope"],
            "NEXT_INFORMATION_ACQUISITION_CONTROL_ONLY",
        )
        self.assertFalse(receipt["semantic_truth_authority"])
        self.assertFalse(receipt["final_domain_action_authority"])
        self.assertTrue(receipt["control_action_authority"])

    def test_live_front_door_source_binds_new_control_mode(self):
        path = ROOT / "canonical/runtime/unified_cognitive_fabric_v1.py"
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn(
            "from canonical.runtime import open_world_semantic_control_v1 as open_world_semantic_control",
            source,
        )
        self.assertIn(
            '"OPEN_WORLD_SEMANTIC_CONTROL": "open_world_semantic_control_v1.resolve"',
            source,
        )
        self.assertIn('return "OPEN_WORLD_SEMANTIC_CONTROL"', source)
        self.assertIn('elif mode == "OPEN_WORLD_SEMANTIC_CONTROL":', source)
        self.assertIn("open_world_semantic_control.resolve(", source)

    def test_control_mode_is_learning_observable_without_terminal_authority(self):
        path = ROOT / "canonical/runtime/unified_cognitive_fabric_v1.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn('"OPEN_WORLD_SEMANTIC_CONTROL",', source)
        out = control.resolve(problem(), repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["final_domain_action_authority"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
