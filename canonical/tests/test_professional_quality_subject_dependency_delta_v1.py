from __future__ import annotations

import unittest

from canonical.runtime.professional_quality_subject_dependency_delta_v1 import (
    evaluate,
)


class ProfessionalQualitySubjectDependencyDeltaV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = evaluate()

    def test_current_candidate_and_v6_runtime_closure_pass(self):
        self.assertTrue(self.out["pass"], self.out)
        self.assertTrue(self.out["candidate_subject_current"])
        self.assertGreater(self.out["runtime_closure_file_count"], 0)
        self.assertTrue(
            self.out["v6_minimal_goal_binding_kernel_in_runtime_closure"]
        )

    def test_v6_replacement_removes_broad_controller_and_v5_from_runtime_cone(self):
        self.assertFalse(self.out["general_r2_controller_in_v6_replacement_closure"])
        self.assertFalse(self.out["router_v5_in_v6_replacement_closure"])
        paths = {x["path"] for x in self.out["runtime_closure"]["files"]}
        for required in {
            "canonical/runtime/professional_quality_p1_router_v6.py",
            "canonical/runtime/goal_to_decision_binding_authority_v1.py",
            "canonical/runtime/professional_quality_p1_router_v4.py",
            "canonical/runtime/professional_quality_p1_router_v3.py",
            "canonical/runtime/professional_quality_p1_router_v2.py",
            "canonical/runtime/professional_artifact_hard_defect_preflight_v1.py",
            "canonical/runtime/professional_target_semantic_certificate_v1.py",
            "canonical/runtime/professional_quality_scoped_evidence_v1.py",
        }:
            self.assertIn(required, paths)

    def test_known_hidden_config_dependencies_are_exposed(self):
        missing = set(self.out["known_missing_config_components"])
        self.assertIn(
            "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V1.json",
            missing,
        )
        self.assertIn(
            "canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json",
            missing,
        )
        self.assertIn(
            "canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json",
            missing,
        )

    def test_no_authority_is_minted_by_dependency_diagnostics(self):
        self.assertFalse(self.out["subject_dependency_closure_complete"])
        self.assertFalse(self.out["subject_refresh_authority"])
        self.assertFalse(self.out["root_subject_binding_authority"])
        self.assertFalse(self.out["quality_authority"])
        self.assertFalse(self.out["acceptance_authority"])
        self.assertFalse(self.out["promotion_authority"])
        self.assertFalse(self.out["terminal_authority"])
        self.assertEqual(self.out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()
