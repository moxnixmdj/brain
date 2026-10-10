from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import ast
import json
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
        path = ROOT / "canonical/runtime/unified_cognitive_fabric_v2.py"
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn(
            "from canonical.runtime import open_world_semantic_control_v1 as open_world_control",
            source,
        )
        self.assertIn(
            'OPEN_WORLD_MODE = "OPEN_WORLD_SEMANTIC_CONTROL"',
            source,
        )
        self.assertIn("_is_open_world_control_payload(payload)", source)
        self.assertIn("requested == OPEN_WORLD_MODE", source)
        self.assertIn("open_world_control.resolve(", source)

    def test_control_mode_is_learning_observable_without_terminal_authority(self):
        path = ROOT / "canonical/runtime/unified_cognitive_fabric_v1.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn('"OPEN_WORLD_SEMANTIC_CONTROL",', source)
        out = control.resolve(problem(), repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["final_domain_action_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_governance_activation_preserves_semantic_residual(self):
        activation = json.loads(
            (
                ROOT
                / "canonical/governance/R2_OPEN_WORLD_SEMANTIC_CONTROL_ACTIVATION_20261010_V1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            activation["status"],
            "ACTIVE_LIVE_OPEN_WORLD_SEMANTIC_CONTROL_PROGRESS_ROUTE",
        )
        authority = activation["authority"]
        self.assertTrue(authority["control_progress_closed_when_preconditions_hold"])
        self.assertFalse(authority["semantic_identity_closed"])
        self.assertFalse(authority["semantic_truth_authority"])
        self.assertFalse(authority["final_domain_action_authority"])
        self.assertEqual(activation["live_surface"]["front_door_path"], "canonical/runtime/unified_cognitive_fabric_v2.py")
        self.assertEqual(activation["live_surface"]["mode"], "OPEN_WORLD_SEMANTIC_CONTROL")

    def test_current_r2_v72_binds_control_capability_without_tail_closure(self):
        current = json.loads(
            (
                ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIn("__V72__", current["status"])
        self.assertIn(
            "OPEN_WORLD_SEMANTIC_CONTROL_PROGRESS_BOUND",
            current["status"],
        )
        bound = current["open_world_semantic_control_progress"]
        self.assertTrue(bound["control_progress_closed"])
        self.assertFalse(bound["semantic_identity_closed"])
        self.assertFalse(bound["finance_semantic_tail_closed"])
        self.assertEqual(bound["live_mode"], "OPEN_WORLD_SEMANTIC_CONTROL")
        self.assertEqual(current["live_front_door"]["path"], "canonical/runtime/unified_cognitive_fabric_v2.py")
        self.assertEqual(bound["complementary_nonidentifiability_git_blob_sha"], "e358eeecc45868c91d22009cc57c624e9a210037")

    def test_scheduler_deduplicates_generic_control_work_only(self):
        scheduler = json.loads(
            (
                ROOT / "canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json"
            ).read_text(encoding="utf-8")
        )
        row = scheduler["open_world_semantic_control_progress"]
        self.assertIn("DO_NOT_REBUILD_GENERIC_OPEN_WORLD_INFORMATION_ORIGIN_CONTROL", row["scheduler_rule"])
        self.assertFalse(row["semantic_closure_claimed"])
        self.assertIn("SEMANTIC_IDENTITY_RESIDUAL_STILL_OPEN", row["status"])

    def test_context_meaning_v4_composes_nonidentifiability_then_control(self):
        intent = json.loads(
            (
                ROOT
                / "canonical/action_intents/ACTION_INTENT_CONTEXT_DEPENDENT_MEANING_POSITIVE_COVERAGE_20261010_V4.json"
            ).read_text(encoding="utf-8")
        )
        law = intent["general_control_law"]
        self.assertTrue(any("NONIDENTIFIABILITY" in row for row in law))
        self.assertTrue(any("MINIMUM_INFORMATION_ACQUISITION_CONTROL_ACTION" in row for row in law))
        self.assertFalse(intent["exact_margin_instance"]["semantic_identity_selected"])
        self.assertIn("ACQUIRE_MINIMUM_POLICY_CHANGING_INFORMATION", intent["exact_margin_instance"]["safe_next_class"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
