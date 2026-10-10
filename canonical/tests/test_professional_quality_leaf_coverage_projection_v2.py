from __future__ import annotations

import unittest

from canonical.runtime import professional_quality_leaf_coverage_projection_v2 as cover


class ProfessionalQualityLeafCoverageProjectionV2Tests(unittest.TestCase):
    def test_current_overlay_projects_twenty_of_twenty_four_bounded_leaves(self):
        out = cover.project()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["admitted_scoped_capability_count"], 17)
        self.assertEqual(out["expected_leaf_count"], 24)
        self.assertEqual(out["partial_coverage_leaf_count"], 20)
        self.assertEqual(out["semantic_partial_coverage_leaf_count"], 8)
        self.assertEqual(out["execution_partial_coverage_leaf_count"], 12)
        self.assertEqual(out["no_scoped_evidence_leaf_count"], 4)
        self.assertEqual(out["verified_global_leaf_count"], 0)
        self.assertEqual(out["open_global_leaf_count"], 24)
        self.assertFalse(out["global_leaf_closure"])
        self.assertFalse(out["domain_semantic_closure"])
        self.assertFalse(out["domain_execution_closure"])
        self.assertFalse(out["terminal_authority"])

    def test_r2_semantic_leaf_is_bounded_subset_only(self):
        out = cover.project()
        leaf = "PQ::R2_CANDIDATE_SEARCH::SEMANTIC"
        self.assertIn(leaf, out["semantic_partial_coverage_leaf_ids"])
        rows = out["contributions_by_leaf"][leaf]
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["claim_kind"],
            "FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS",
        )
        self.assertEqual(rows[0]["scope_relation_to_global_leaf"], "BOUNDED_SUBSET_ONLY")
        self.assertFalse(rows[0]["leaf_closure_credit"])
        self.assertEqual(rows[0]["terminal_credit_delta"], 0)

    def test_only_r3_r4_r5_r9_semantic_leaves_remain_without_scoped_evidence(self):
        out = cover.project()
        self.assertEqual(
            out["no_scoped_evidence_leaf_ids"],
            [
                "PQ::R3_REALIZATION_OBSERVATION::SEMANTIC",
                "PQ::R4_MEASUREMENT_CONSTRUCT::SEMANTIC",
                "PQ::R5_EVALUATOR_REFERENCE::SEMANTIC",
                "PQ::R9_TEMPORAL_DEPLOYMENT::SEMANTIC",
            ],
        )


if __name__ == "__main__":
    unittest.main()
