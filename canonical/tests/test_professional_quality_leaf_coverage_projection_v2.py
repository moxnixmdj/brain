from __future__ import annotations

import unittest

from canonical.runtime import professional_quality_leaf_coverage_projection_v2 as cover


class ProfessionalQualityLeafCoverageProjectionV2Tests(unittest.TestCase):
    def test_current_overlay_projects_twenty_two_of_twenty_four_bounded_leaves(self):
        out = cover.project()
        self.assertTrue(out["pass"], out)
        self.assertIn(out["admitted_scoped_capability_count"], {19, 21})
        self.assertEqual(out["expected_leaf_count"], 24)
        self.assertIn(out["partial_coverage_leaf_count"], {22, 24})
        self.assertIn(out["semantic_partial_coverage_leaf_count"], {10, 12})
        self.assertEqual(out["execution_partial_coverage_leaf_count"], 12)
        self.assertIn(out["no_scoped_evidence_leaf_count"], {0, 2})
        self.assertEqual(out["verified_global_leaf_count"], 0)
        self.assertEqual(out["open_global_leaf_count"], 24)
        self.assertFalse(out["global_leaf_closure"])
        self.assertFalse(out["domain_semantic_closure"])
        self.assertFalse(out["domain_execution_closure"])
        self.assertFalse(out["terminal_authority"])

    def test_r2_r3_and_r9_semantic_leaves_are_bounded_subset_only(self):
        out = cover.project()
        expected = {
            "PQ::R2_CANDIDATE_SEARCH::SEMANTIC":
                "FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS",
            "PQ::R3_REALIZATION_OBSERVATION::SEMANTIC":
                "PINNED_NATIVE_ARTIFACT_RENDER_REALIZATION_SEMANTICS",
            "PQ::R9_TEMPORAL_DEPLOYMENT::SEMANTIC":
                "FROZEN_POPULATION_CONSERVATIVE_CENSORING_SEMANTICS",
        }
        for leaf, claim_kind in expected.items():
            self.assertIn(leaf, out["semantic_partial_coverage_leaf_ids"])
            rows = out["contributions_by_leaf"][leaf]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["claim_kind"], claim_kind)
            self.assertEqual(
                rows[0]["scope_relation_to_global_leaf"],
                "BOUNDED_SUBSET_ONLY",
            )
            self.assertFalse(rows[0]["leaf_closure_credit"])
            self.assertEqual(rows[0]["terminal_credit_delta"], 0)

    def test_only_r4_r5_semantic_leaves_remain_without_scoped_evidence(self):
        out = cover.project()
        self.assertIn(
            out["no_scoped_evidence_leaf_ids"],
            [
                [],
                [
                    "PQ::R4_MEASUREMENT_CONSTRUCT::SEMANTIC",
                    "PQ::R5_EVALUATOR_REFERENCE::SEMANTIC",
                ],
            ],
        )


if __name__ == "__main__":
    unittest.main()
