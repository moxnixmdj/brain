from __future__ import annotations

import copy
import json
import unittest

from canonical.runtime.synthesis_implication_residual_verifier_v2 import (
    ALGEBRA, BINDING, INPUT, RECEIPT, TARGETS, blob_sha, evaluate
)

def load(p):
    return json.loads(p.read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
    def docs(self):
        return (
            load(INPUT), load(TARGETS), load(BINDING), load(RECEIPT),
            {
                "targets": blob_sha(TARGETS),
                "binding": blob_sha(BINDING),
                "receipt": blob_sha(RECEIPT),
                "algebra": blob_sha(ALGEBRA),
            },
        )

    def test_live_scope_safe_residual(self):
        out = evaluate(*self.docs())
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["missing_scope_relation"])
        self.assertEqual(out["missing_atoms"], ["metric:matched_quality"])
        self.assertEqual(
            out["missing_metric_bounds"],
            ["matched_quality_noninferiority", "required_claim_coverage_noninferiority"],
        )
        self.assertFalse(out["implies_target"])

    def test_unverified_scope_relation_cannot_be_inserted(self):
        doc, targets, binding, receipt, shas = self.docs()
        doc = copy.deepcopy(doc)
        doc["algebra_input"]["verified_scope_relations"] = [{
            "witness_scope": doc["algebra_input"]["witness"]["scope_ref"],
            "target_scope": doc["algebra_input"]["target"]["scope_ref"],
            "relation": "SUPERSET",
            "verified": True,
            "independent": True,
            "receipt": "invented://scope",
        }]
        out = evaluate(doc, targets, binding, receipt, shas)
        self.assertFalse(out["pass"])
        self.assertIn("UNVERIFIED_SCOPE_RELATION_FORBIDDEN", out["errors"])

    def test_v1_algebra_authority_is_rejected(self):
        doc, targets, binding, receipt, shas = self.docs()
        doc = copy.deepcopy(doc)
        doc["authority"]["algebra_runtime"]["path"] = "canonical/runtime/protocol_implication_scope_algebra_v1.py"
        out = evaluate(doc, targets, binding, receipt, shas)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_MISMATCH:algebra_runtime", out["errors"])

    def test_numeric_bound_invention_is_rejected(self):
        doc, targets, binding, receipt, shas = self.docs()
        doc = copy.deepcopy(doc)
        doc["algebra_input"]["witness"]["metric_bounds"] = {
            "matched_quality_noninferiority": {"lower": 0}
        }
        out = evaluate(doc, targets, binding, receipt, shas)
        self.assertFalse(out["pass"])
        self.assertIn("WITNESS_METRIC_BOUND_INVENTION", out["errors"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
