from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_scoped_evidence_overlay_v1 as scoped


class ProfessionalQualityScopedEvidenceOverlayV1Tests(unittest.TestCase):
    def test_current_overlay_admits_r2_and_r9_semantic_scopes_without_global_credit(self):
        out = scoped.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["admitted_scope_count"], 18, out)

        r2 = next(
            x for x in out["admitted_scopes"]
            if x["claim_kind"] == "FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS"
        )
        self.assertEqual(r2["root_id"], "R2_CANDIDATE_SEARCH")
        self.assertEqual(
            r2["contributes_to_leaf_ids"],
            ["PQ::R2_CANDIDATE_SEARCH::SEMANTIC"],
        )
        self.assertIn(
            "NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS",
            r2["claim_scope"]["limitations"],
        )

        r9 = next(
            x for x in out["admitted_scopes"]
            if x["claim_kind"] == "FROZEN_POPULATION_CONSERVATIVE_CENSORING_SEMANTICS"
        )
        self.assertEqual(r9["root_id"], "R9_TEMPORAL_DEPLOYMENT")
        self.assertEqual(
            r9["contributes_to_leaf_ids"],
            ["PQ::R9_TEMPORAL_DEPLOYMENT::SEMANTIC"],
        )
        self.assertIn(
            "THE_EVALUATION_UNIVERSE_IS_ONE_FROZEN_SET_OF_EXACTLY_210_UNIQUE_SLOTS",
            r9["claim_scope"]["guarantees"],
        )
        self.assertIn(
            "NO_MULTIHORIZON_DEPLOYMENT_VALIDITY",
            r9["claim_scope"]["limitations"],
        )

        for row in (r2, r9):
            self.assertFalse(row["semantic_leaf_credit"])
            self.assertFalse(row["global_leaf_credit"])
        self.assertFalse(out["global_leaf_closure"])
        self.assertFalse(out["domain_semantic_closure"])

    def test_claim_scope_list_order_is_not_semantic(self):
        left = {
            "kind": "K",
            "guarantees": ["A", "B"],
            "limitations": ["X", "Y"],
        }
        right = {
            "kind": "K",
            "guarantees": ["B", "A"],
            "limitations": ["Y", "X"],
        }
        self.assertTrue(scoped._claim_scope_equivalent(left, right))
        right["limitations"] = ["Y"]
        self.assertFalse(scoped._claim_scope_equivalent(left, right))

    def test_r2_semantic_global_credit_attempt_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r2 = next(
            x for x in registry["entries"]
            if x.get("claim_kind") == "FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS"
        )
        r2["global_root_closure"] = True
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        row = next(
            x for x in out["rejected_scopes"]
            if x.get("claim_kind") == "FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS"
        )
        self.assertIn("GLOBAL_ROOT_CLOSURE_FORBIDDEN", row["errors"])

    def test_r2_semantic_stale_source_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r2 = next(
            x for x in registry["entries"]
            if x.get("claim_kind") == "FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS"
        )
        r2["source_receipt"]["git_blob_sha"] = "0" * 40
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        row = next(
            x for x in out["rejected_scopes"]
            if x.get("claim_kind") == "FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS"
        )
        self.assertIn("SOURCE_STALE", row["errors"])

    def test_r9_semantic_global_credit_attempt_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r9 = next(
            x for x in registry["entries"]
            if x.get("claim_kind") == "FROZEN_POPULATION_CONSERVATIVE_CENSORING_SEMANTICS"
        )
        r9["global_leaf_closure"] = True
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        row = next(
            x for x in out["rejected_scopes"]
            if x.get("claim_kind") == "FROZEN_POPULATION_CONSERVATIVE_CENSORING_SEMANTICS"
        )
        self.assertIn("GLOBAL_LEAF_CLOSURE_FORBIDDEN", row["errors"])

    def test_r9_semantic_stale_scope_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r9 = next(
            x for x in registry["entries"]
            if x.get("claim_kind") == "FROZEN_POPULATION_CONSERVATIVE_CENSORING_SEMANTICS"
        )
        r9["scope_governance"]["git_blob_sha"] = "0" * 40
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        row = next(
            x for x in out["rejected_scopes"]
            if x.get("claim_kind") == "FROZEN_POPULATION_CONSERVATIVE_CENSORING_SEMANTICS"
        )
        self.assertIn("SCOPE_STALE", row["errors"])


if __name__ == "__main__":
    unittest.main()
