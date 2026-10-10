from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_r12_semantic_root_cut_v1 as r

ROOT = Path(__file__).resolve().parents[2]

PATHS = {
    "domain": "canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json",
    "scope": "canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json",
    "identity": "canonical/verification/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_VERIFY_20261010_V1.json",
    "bounded": "canonical/verification/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_VERIFY_20261010_V12.json",
}

def docs():
    return {k: json.loads((ROOT / p).read_text()) for k, p in PATHS.items()}

class R12SemanticRootCutV1Tests(unittest.TestCase):
    def evaluate(self, d=None):
        d = d or docs()
        return r.evaluate(
            domain_verification=d["domain"],
            scope_batch_verification=d["scope"],
            identity_verification=d["identity"],
            bounded_r12_verification=d["bounded"],
        )

    def test_current_cut_is_exactly_two_open_semantic_roots(self):
        out = self.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["open_semantic_root_ids"]),
            {"CC_R2_MISSION_SOUNDNESS_V1", "CC_R3_TERMINAL_CLOSURE_V1"},
        )
        self.assertEqual(out["open_semantic_root_count"], 2)
        self.assertEqual(
            out["root_states"]["CC_R1_REALITY_CONTAINMENT_V1"]["state"],
            "MATERIALIZABLE_FROM_VERIFIED_EXISTING_PROOFS",
        )
        self.assertEqual(
            out["root_states"]["CC_R4_PROOF_AUTHORITY_V1"]["state"],
            "DEPENDENCY_BLOCKED",
        )
        self.assertFalse(out["semantic_property_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_r12_claim_substitution_fails_closed(self):
        d = docs()
        d["identity"] = copy.deepcopy(d["identity"])
        d["identity"]["independent_replay"]["r12_claim_id"] = "0" * 64
        out = self.evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "R12_CLAIM_ID_DRIFT")

    def test_finite_sample_carrier_cannot_support_cut(self):
        d = docs()
        d["identity"] = copy.deepcopy(d["identity"])
        d["identity"]["theorem"]["finite_witness_set_used"] = True
        out = self.evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "IDENTITY_CARRIER_FINITE_SAMPLE_FORBIDDEN")

    def test_bounded_semantic_evidence_cannot_self_promote(self):
        d = docs()
        d["bounded"] = copy.deepcopy(d["bounded"])
        d["bounded"]["r12_projection"]["semantic_leaf_credit"] = True
        out = self.evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "R12_BOUNDED_EVIDENCE_SELF_PROMOTION")

    def test_scope_batch_property_self_promotion_fails(self):
        d = docs()
        d["scope"] = copy.deepcopy(d["scope"])
        d["scope"]["property_truth_count"] = 1
        out = self.evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SCOPE_BATCH_PROPERTY_SELF_PROMOTION")

if __name__ == "__main__":
    unittest.main(verbosity=2)
