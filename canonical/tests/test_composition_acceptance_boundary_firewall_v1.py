from __future__ import annotations

import unittest

from canonical.runtime.composition_acceptance_boundary_firewall_v1 import evaluate


def complete_candidate():
    head = "a" * 64
    return {
        "planning_mode": "DETERMINISTIC_CAPABILITY_GRAPH",
        "composition_state_capsule": {
            "status": "PASS",
            "scope": "DETERMINISTIC_CAPABILITY_GRAPH_DECLARED_CROSS_CAPABILITY_STATE",
            "capsule_schema": "PROJECT_BRAIN_COMPOSITION_STATE_CAPSULE_V2",
            "head_hash": head,
            "declared_cross_capability_state_no_bypass": True,
            "content_bound_action_result_provenance": True,
            "semantic_declaration_completeness": True,
            "external_evidence_channel_completeness": True,
            "broader_runtime_channel_totality": True,
            "rollback_scope_complete": True,
        },
        "independent_system_verification": {
            "status": "PASS",
            "c1_closed_world_mediation_totality": True,
            "subject_capsule_head_hash": head,
        },
    }


class Tests(unittest.TestCase):
    def test_current_partial_v1_style_receipt_fails_closed(self):
        candidate = {
            "planning_mode": "DETERMINISTIC_CAPABILITY_GRAPH",
            "composition_state_capsule": {
                "status": "PASS",
                "scope": "DETERMINISTIC_CAPABILITY_GRAPH_DECLARED_CROSS_CAPABILITY_STATE",
                "declared_cross_capability_state_no_bypass": True,
                "semantic_declaration_completeness": "UNVERIFIED",
                "external_evidence_channel_completeness": "UNVERIFIED",
                "head_hash": "x",
            },
        }
        out = evaluate(candidate)
        self.assertFalse(out["promotion_allowed"])
        self.assertIn(
            "STRICT_CAPSULE_V2_SCHEMA_REQUIRED",
            out["errors"],
        )
        self.assertIn(
            "SEMANTIC_DECLARATION_COMPLETENESS_NOT_PROVED",
            out["errors"],
        )

    def test_partial_v2_declared_channel_still_fails_closed(self):
        candidate = complete_candidate()
        candidate["composition_state_capsule"]["external_evidence_channel_completeness"] = "UNVERIFIED"
        out = evaluate(candidate)
        self.assertFalse(out["promotion_allowed"])
        self.assertIn(
            "EXTERNAL_EVIDENCE_CHANNEL_COMPLETENESS_NOT_PROVED",
            out["errors"],
        )

    def test_independent_receipt_must_bind_same_capsule_head(self):
        candidate = complete_candidate()
        candidate["independent_system_verification"]["subject_capsule_head_hash"] = "b" * 64
        out = evaluate(candidate)
        self.assertFalse(out["promotion_allowed"])
        self.assertIn(
            "INDEPENDENT_VERIFICATION_CAPSULE_HEAD_MISMATCH",
            out["errors"],
        )

    def test_only_complete_synthetic_boundary_passes(self):
        out = evaluate(complete_candidate())
        self.assertTrue(out["promotion_allowed"], out)
        self.assertEqual(
            out["status"],
            "PASS__C1_PROMOTION_BOUNDARY_SATISFIED",
        )
        self.assertEqual(out["acceptance_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
