from __future__ import annotations

import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_scoped_evidence_v1 as scoped
from canonical.runtime import professional_quality_leaf_coverage_projection_v1 as projection

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


class CurrentProfessionalQualityReconciliationV1Tests(unittest.TestCase):
    def test_current_professional_pointer_matches_live_registry_and_projection(self):
        current = load("canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json")
        scoped_out = scoped.evaluate()
        projected = projection.project()

        self.assertTrue(scoped_out["pass"], scoped_out)
        self.assertTrue(projected["pass"], projected)
        self.assertEqual(scoped_out["admitted_scope_count"], 16)
        self.assertEqual(projected["partial_coverage_leaf_count"], 19)
        self.assertEqual(projected["semantic_partial_coverage_leaf_count"], 7)
        self.assertEqual(projected["execution_partial_coverage_leaf_count"], 12)
        self.assertEqual(projected["no_scoped_evidence_leaf_count"], 5)

        self.assertEqual(
            current["scoped_evidence"]["admitted_scope_count"],
            scoped_out["admitted_scope_count"],
        )
        for key in (
            "partial_coverage_leaf_count",
            "semantic_partial_coverage_leaf_count",
            "execution_partial_coverage_leaf_count",
            "no_scoped_evidence_leaf_count",
            "verified_global_leaf_count",
            "open_global_leaf_count",
        ):
            self.assertEqual(current["leaf_coverage_projection"][key], projected[key])

        self.assertIn(
            "PQ::R8_POPULATION_CONTEXT_OPERATOR::SEMANTIC",
            current["scoped_evidence"]["bounded_semantic_leaf_ids"],
        )
        self.assertFalse(current["live_default"])
        self.assertFalse(current["promotion_authority"])
        self.assertFalse(current["quality_authority"])
        self.assertFalse(current["terminal_authority"])
        self.assertEqual(current["terminal_credit_delta"], 0)

    def test_assurance_pointer_matches_same_live_frontier_without_promoting_it(self):
        assurance = load("canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json")
        scoped_out = scoped.evaluate()
        projected = projection.project()

        self.assertEqual(
            assurance["professional_quality_scoped_evidence"]["admitted_scope_count"],
            scoped_out["admitted_scope_count"],
        )
        for key in (
            "partial_coverage_leaf_count",
            "semantic_partial_coverage_leaf_count",
            "execution_partial_coverage_leaf_count",
            "no_scoped_evidence_leaf_count",
            "verified_global_leaf_count",
            "open_global_leaf_count",
        ):
            self.assertEqual(
                assurance["professional_quality_leaf_coverage_projection"][key],
                projected[key],
            )
        self.assertIn(
            "PQ::R8_POPULATION_CONTEXT_OPERATOR::SEMANTIC",
            assurance["professional_quality_scoped_evidence"]["bounded_semantic_leaf_ids"],
        )
        self.assertFalse(assurance["live_default"])
        self.assertFalse(assurance["terminal_authority"])
        self.assertEqual(assurance["terminal_credit_delta"], 0)

    def test_r8_delta_is_independently_verified_but_remains_bounded(self):
        receipt = load(
            "canonical/verification/PROFESSIONAL_QUALITY_R8_POPULATION_SEMANTIC_VERIFY_20261010_V1.json"
        )
        scope = load(
            "canonical/governance/PROFESSIONAL_QUALITY_R8_POPULATION_SEMANTIC_SCOPE_20261010_V1.json"
        )

        self.assertTrue(receipt["status"].startswith("PASS__"))
        self.assertEqual(receipt["replay"]["tests_run"], 6)
        self.assertEqual(receipt["replay"]["tests_passed"], 6)
        self.assertEqual(receipt["replay"]["tests_failed"], 0)
        self.assertFalse(receipt["global_leaf_closure"])
        self.assertFalse(receipt["terminal_authority"])
        self.assertFalse(scope["global_leaf_closure"])
        self.assertFalse(scope["global_root_closure"])
        self.assertFalse(scope["terminal_authority"])

    def test_reuse_classifier_cannot_reopen_professional_primitive_from_stale_counts(self):
        current = load(
            "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"
        )
        row = next(
            x
            for x in current["classifications"]
            if x["residual_id"] == "PROFESSIONAL_QUALITY_BROAD_EXECUTION"
        )
        self.assertIn("16_CLAIM_SCOPED_CAPABILITIES_CURRENT", row["current_truth"])
        self.assertIn("19_PARTIAL_LEAVES", row["current_truth"])
        self.assertIn("5_NO_SCOPED_EVIDENCE", row["current_truth"])
        self.assertTrue(row["new_primitive_status"].startswith("NOT_ESTABLISHED"))
        self.assertEqual(current["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()
