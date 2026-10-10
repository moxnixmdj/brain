from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_scoped_evidence_v1 as scoped


class ProfessionalQualityScopedEvidenceV1Tests(unittest.TestCase):
    def test_current_r7_single_edit_scope_is_admitted_without_global_credit(self):
        out = scoped.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["admitted_scope_count"], 1, out)
        self.assertEqual(out["rejected_scope_count"], 0, out)
        self.assertFalse(out["global_leaf_closure"])
        self.assertFalse(out["global_root_closure"])
        self.assertFalse(out["domain_semantic_closure"])
        self.assertFalse(out["domain_execution_closure"])
        self.assertFalse(out["terminal_authority"])

    def test_registry_cannot_claim_global_leaf_closure(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        registry["entries"][0]["global_leaf_closure"] = True
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        self.assertIn(
            "GLOBAL_LEAF_CLOSURE_FORBIDDEN",
            out["rejected_scopes"][0]["errors"],
            out,
        )

    def test_stale_source_receipt_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        registry["entries"][0]["source_receipt"]["git_blob_sha"] = "0" * 40
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        self.assertIn(
            "SOURCE_RECEIPT_STALE",
            out["rejected_scopes"][0]["errors"],
            out,
        )

    def test_wrong_leaf_binding_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        registry["entries"][0]["contributes_to_leaf_ids"] = [
            "PQ::R1_TARGET_SPECIFICATION::SEMANTIC"
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        self.assertIn(
            "R7_LEAF_BINDING_INVALID",
            out["rejected_scopes"][0]["errors"],
            out,
        )

    def test_scoped_result_preserves_exact_claim_kind(self):
        out = scoped.evaluate()
        row = out["admitted_scopes"][0]
        self.assertEqual(
            row["claim_scope"]["kind"],
            "EXACT_SINGLE_EDIT_PROFESSIONAL_CODE_INTERVENTION_INSTANCE",
        )
        self.assertEqual(
            set(row["contributes_to_leaf_ids"]),
            {
                "PQ::R7_CAUSAL_PRESCRIPTIVE::SEMANTIC",
                "PQ::R7_CAUSAL_PRESCRIPTIVE::EXECUTION",
            },
        )
        self.assertFalse(row["global_leaf_credit"])
        self.assertFalse(row["global_root_credit"])


if __name__ == "__main__":
    unittest.main()
