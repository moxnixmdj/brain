from __future__ import annotations

import unittest

from canonical.runtime.contract_native_actual_brain_policy_v1 import solve


class ContractNativeActualBrainPolicyV1Tests(unittest.TestCase):
    def test_structured_keeps_only_required_and_sorts(self):
        case = {"contract": "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001", "task": {
            "requirements": [
                {"id": "z", "coefficient": 2, "required": True},
                {"id": "ignored", "coefficient": 9, "required": False},
                {"id": "a", "coefficient": -1, "required": True},
            ]}}
        self.assertEqual(solve(case), {"graph": [
            {"factor": "a", "coefficient": -1},
            {"factor": "z", "coefficient": 2},
        ]})

    def test_trajectory_uses_earliest_visible_failure_and_unique_repair(self):
        case = {"contract": "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001", "task": {
            "trajectory": [
                {"step": 4, "invariant_pass": False},
                {"step": 2, "invariant_pass": False},
            ],
            "repair_candidates": [
                {"id": "late", "targets_step": 4},
                {"id": "right", "targets_step": 2},
            ],
        }}
        self.assertEqual(solve(case), {"cause_step": 2, "repair_id": "right", "evidence_steps": [2]})

    def test_trajectory_fails_closed_when_repair_is_not_unique(self):
        case = {"contract": "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001", "task": {
            "trajectory": [{"step": 1, "invariant_pass": False}],
            "repair_candidates": [{"id": "a", "targets_step": 1}, {"id": "b", "targets_step": 1}],
        }}
        with self.assertRaisesRegex(ValueError, "REPAIR_NOT_UNIQUE"):
            solve(case)

    def test_synthesis_preserves_selected_conflicted_uncertainty_and_provenance(self):
        case = {"contract": "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001", "task": {"evidence": [
            {"claim_id": "r", "role": "required", "support": "conflicted", "provenance": ["p1"]},
            {"claim_id": "o", "role": "optional", "support": "supported", "provenance": ["p2"]},
            {"claim_id": "f", "role": "forbidden", "support": "conflicted", "provenance": ["p3"]},
        ]}}
        self.assertEqual(solve(case), {
            "selected_claims": ["r", "o"],
            "uncertainty_claims": ["r"],
            "claim_provenance": {"r": ["p1"], "o": ["p2"]},
        })

    def test_professional_maximizes_weighted_score_subject_to_support_hardness_and_budget(self):
        case = {"contract": "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001", "task": {
            "rubric_weights": {"q": 3},
            "edit_budget": 2,
            "edit_candidates": [
                {"id": "a", "supported": True, "hard_violation": False, "cost": 1, "scores": {"q": 2}},
                {"id": "b", "supported": True, "hard_violation": False, "cost": 2, "scores": {"q": 3}},
                {"id": "c", "supported": False, "hard_violation": False, "cost": 0, "scores": {"q": 99}},
            ],
        }}
        self.assertEqual(solve(case), {"selected_edits": ["b"]})

    def test_unknown_contract_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_CONTRACT"):
            solve({"contract": "NOPE", "task": {}})


if __name__ == "__main__":
    unittest.main()
