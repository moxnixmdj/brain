from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_leaf_coverage_projection_v1 as cover
from canonical.runtime import professional_quality_scoped_evidence_v1 as scoped


class ProfessionalQualityLeafCoverageProjectionV1Tests(unittest.TestCase):
    def test_current_twelve_scopes_project_without_global_leaf_credit(self):
        out = cover.project()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["admitted_scoped_capability_count"], 12)
        self.assertEqual(out["expected_leaf_count"], 24)
        self.assertEqual(out["partial_coverage_leaf_count"], 13)
        self.assertEqual(out["semantic_partial_coverage_leaf_count"], 1)
        self.assertEqual(out["execution_partial_coverage_leaf_count"], 12)
        self.assertEqual(out["no_scoped_evidence_leaf_count"], 11)
        self.assertEqual(out["verified_global_leaf_count"], 0)
        self.assertEqual(out["open_global_leaf_count"], 24)
        self.assertFalse(out["global_leaf_closure"])
        self.assertFalse(out["domain_semantic_closure"])
        self.assertFalse(out["domain_execution_closure"])
        self.assertFalse(out["terminal_authority"])

    def test_only_r7_semantic_leaf_has_bounded_semantic_contribution(self):
        out = cover.project()
        self.assertEqual(
            out["semantic_partial_coverage_leaf_ids"],
            ["PQ::R7_CAUSAL_PRESCRIPTIVE::SEMANTIC"],
        )

    def test_all_twelve_execution_leaves_have_bounded_contributions(self):
        out = cover.project()
        self.assertEqual(len(out["execution_partial_coverage_leaf_ids"]), 12)
        self.assertTrue(
            all(
                x.endswith("::EXECUTION")
                for x in out["execution_partial_coverage_leaf_ids"]
            )
        )

    def test_every_contribution_is_subset_only_and_zero_credit(self):
        out = cover.project()
        for items in out["contributions_by_leaf"].values():
            for item in items:
                self.assertEqual(
                    item["scope_relation_to_global_leaf"],
                    "BOUNDED_SUBSET_ONLY",
                )
                self.assertFalse(item["leaf_closure_credit"])
                self.assertEqual(item["terminal_credit_delta"], 0)

    def test_scoped_global_credit_attempt_fails_projection_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        registry["entries"][0]["global_leaf_closure"] = True
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = cover.project(scoped_registry_path=p)
        self.assertFalse(out["pass"], out)
        self.assertIn(
            "SCOPED_EVIDENCE_NOT_ADMITTED",
            out["structural_errors"],
        )

    def test_unknown_contribution_leaf_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        registry["entries"][0]["contributes_to_leaf_ids"] = [
            "PQ::UNKNOWN::EXECUTION"
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = cover.project(scoped_registry_path=p)
        self.assertFalse(out["pass"], out)
        self.assertTrue(
            "SCOPED_EVIDENCE_NOT_ADMITTED" in out["structural_errors"]
            or "UNKNOWN_CONTRIBUTION_LEAF_IDS" in out["structural_errors"]
        )

    def test_promotion_rule_requires_verified_scope_transport_or_complete_union(self):
        out = cover.project()
        rule = out["promotion_rule"]
        self.assertTrue(rule["partial_scope_never_closes_leaf"])
        self.assertIn(
            "INDEPENDENTLY_VERIFIED_PROVEN_SUPERSET_WITH_STRUCTURAL_MATCH_V1",
            rule["allowed_whole_leaf_routes"],
        )
        self.assertIn(
            "CERTIFIED_COMPLETE_UNION_OF_SCOPED_REGIONS",
            rule["allowed_whole_leaf_routes"],
        )
        self.assertEqual(
            rule["required_superset_scope_predicate"],
            "STRUCTURAL_MATCH_V1",
        )


if __name__ == "__main__":
    unittest.main()
