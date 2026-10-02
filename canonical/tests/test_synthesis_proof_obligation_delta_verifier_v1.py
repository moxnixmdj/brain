from __future__ import annotations

import copy
import json
import unittest

from canonical.runtime.synthesis_proof_obligation_delta_verifier_v1 import (
    BINDING_RECEIPT,
    COMPILER,
    COMPILER_RECEIPT,
    INPUT,
    TARGET_SCOPE_SOURCE,
    WITNESS_SCOPE_SOURCE,
    blob_sha,
    evaluate,
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def docs(self):
        return (
            load(INPUT),
            load(COMPILER_RECEIPT),
            load(BINDING_RECEIPT),
            {
                "compiler": blob_sha(COMPILER),
                "binding_receipt": blob_sha(BINDING_RECEIPT),
                "target_scope": blob_sha(TARGET_SCOPE_SOURCE),
                "witness_scope": blob_sha(WITNESS_SCOPE_SOURCE),
            },
        )

    def test_live_application_verifies_exact_open_residual(self):
        out = evaluate(*self.docs())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["verified_atom_binding_count"], 7)
        self.assertEqual(
            out["missing_scope_components"],
            ["population:frozen_matched_synthesis_portfolio"],
        )
        self.assertEqual(out["missing_atoms"], ["metric:matched_quality"])
        self.assertEqual(
            out["missing_metric_bindings"],
            ["matched_quality_noninferiority", "required_claim_coverage_noninferiority"],
        )
        self.assertFalse(out["acceptance_predicate_closed"])

    def test_invented_scope_binding_is_rejected(self):
        doc, compiler_receipt, binding_receipt, blobs = self.docs()
        doc = copy.deepcopy(doc)
        doc["scope_bindings"] = [{
            "witness_component": "population:p3_t1_t3_terminal_observations",
            "target_component": "population:frozen_matched_synthesis_portfolio",
            "relation": "COVERS",
            "verified": True,
            "independent": True,
            "receipt": {
                "path": "canonical/verification/fake.json",
                "git_blob_sha": "a" * 40,
            },
        }]
        out = evaluate(doc, compiler_receipt, binding_receipt, blobs)
        self.assertFalse(out["pass"])
        self.assertIn("UNVERIFIED_SCOPE_BINDING_FORBIDDEN", out["errors"])

    def test_invented_metric_binding_is_rejected(self):
        doc, compiler_receipt, binding_receipt, blobs = self.docs()
        doc = copy.deepcopy(doc)
        doc["metric_bindings"] = [{
            "witness_metric": "invented",
            "target_metric": "matched_quality_noninferiority",
            "verified": True,
            "independent": True,
            "receipt": {
                "path": "canonical/verification/fake.json",
                "git_blob_sha": "b" * 40,
            },
        }]
        out = evaluate(doc, compiler_receipt, binding_receipt, blobs)
        self.assertFalse(out["pass"])
        self.assertIn("UNVERIFIED_METRIC_BINDING_FORBIDDEN", out["errors"])

    def test_wrong_atom_receipt_blob_is_rejected(self):
        doc, compiler_receipt, binding_receipt, blobs = self.docs()
        doc = copy.deepcopy(doc)
        doc["atom_bindings"][0]["receipt"]["git_blob_sha"] = "c" * 40
        out = evaluate(doc, compiler_receipt, binding_receipt, blobs)
        self.assertFalse(out["pass"])
        self.assertIn("ATOM_BINDING_RECEIPT_IDENTITY_MISMATCH:0", out["errors"])

    def test_wrong_scope_source_blob_is_rejected(self):
        doc, compiler_receipt, binding_receipt, blobs = self.docs()
        doc = copy.deepcopy(doc)
        doc["target"]["scope_components"][0]["source_sha"] = "d" * 40
        out = evaluate(doc, compiler_receipt, binding_receipt, blobs)
        self.assertFalse(out["pass"])
        self.assertIn("TARGET_SCOPE_PROVENANCE_MISMATCH", out["errors"])

    def test_stale_compiler_receipt_cannot_authorize_application(self):
        doc, compiler_receipt, binding_receipt, blobs = self.docs()
        compiler_receipt = copy.deepcopy(compiler_receipt)
        compiler_receipt["exact_brain_blobs"][
            "canonical/runtime/proof_obligation_delta_compiler_v1.py"
        ] = "e" * 40
        out = evaluate(doc, compiler_receipt, binding_receipt, blobs)
        self.assertFalse(out["pass"])
        self.assertIn("COMPILER_BLOB_NOT_BOUND_TO_INDEPENDENT_RECEIPT", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
