from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_scoped_evidence_overlay_v1 as scoped


class ProfessionalQualityScopedEvidenceOverlayV1Tests(unittest.TestCase):
    def test_current_overlay_admits_r2_semantic_scope_without_global_credit(self):
        out = scoped.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["admitted_scope_count"], 17, out)
        row = next(
            x for x in out["admitted_scopes"]
            if x["claim_kind"] == "FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS"
        )
        self.assertEqual(row["root_id"], "R2_CANDIDATE_SEARCH")
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R2_CANDIDATE_SEARCH::SEMANTIC"],
        )
        self.assertIn(
            "CANDIDATE_SCOPE_MEANS_THE_DECLARED_FINITE_POLICY_RELEVANT_REGION_AND_NOT_AN_OPEN_WORLD_UNIVERSE",
            row["claim_scope"]["guarantees"],
        )
        self.assertIn(
            "NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["global_leaf_credit"])
        self.assertFalse(out["global_leaf_closure"])
        self.assertFalse(out["domain_semantic_closure"])

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


if __name__ == "__main__":
    unittest.main()
