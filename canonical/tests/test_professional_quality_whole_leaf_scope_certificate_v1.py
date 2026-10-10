from __future__ import annotations

from copy import deepcopy
import unittest

from canonical.runtime import professional_quality_whole_leaf_scope_certificate_v1 as s

CLAIM_ID = "2" * 64
LEAF = "PQ::R10_ANALYSIS_DECISION::EXECUTION"
SCOPE_BLOB = "3" * 40
VERIFY_BLOB = "4" * 40
VERIFY_PATH = "canonical/verification/r10-claim-verify.json"


def claim_scope():
    return {
        "schema": s.CLAIM_SCOPE_SCHEMA,
        "leaf_id": LEAF,
        "claim": {"claim_id": CLAIM_ID},
    }


def claim_verify():
    return {
        "schema": s.CLAIM_VERIFY_SCHEMA,
        "status": "PASS__WHOLE_LEAF_DOMAIN_EQUIVALENCE",
        "leaf_id": LEAF,
        "claim_id": CLAIM_ID,
        "claim_scope_git_blob_sha": SCOPE_BLOB,
        "whole_leaf_domain_equivalence_proved": True,
    }


def cert():
    return {
        "schema": s.CERT_SCHEMA,
        "leaf_id": LEAF,
        "claim_id": CLAIM_ID,
        "claim_scope_git_blob_sha": SCOPE_BLOB,
        "scope_certificate": {
            "id": "R10_SCOPE_CERT",
            "target_scope_id": "scope://professional-quality/whole-leaf/" + CLAIM_ID,
            "claim_id": CLAIM_ID,
            "basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
            "verified": True,
            "independent": True,
            "scope_relation": "EXACT",
            "formal_completeness": True,
            "all_admissible_target_inputs_proved": True,
            "premise_set_id": "claim-verification:" + VERIFY_BLOB,
        },
        "evidence_refs": [{"path": VERIFY_PATH, "git_blob_sha": VERIFY_BLOB}],
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def evaluate(cv=None, c=None):
    return s.evaluate(
        claim_scope(),
        cv or claim_verify(),
        c or cert(),
        claim_scope_blob=SCOPE_BLOB,
        claim_verification_blob=VERIFY_BLOB,
        claim_verification_path=VERIFY_PATH,
    )


class WholeLeafScopeCertificateV1Tests(unittest.TestCase):
    def test_valid_claim_bound_universal_scope_passes_scope_only(self):
        out = evaluate()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["whole_leaf_scope_complete"])
        self.assertFalse(out["leaf_property_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_domain_equivalence_receipt_required(self):
        cv = claim_verify()
        cv["whole_leaf_domain_equivalence_proved"] = False
        self.assertEqual(evaluate(cv=cv)["reason"], "WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED")

    def test_claim_verification_must_match_scope_blob(self):
        cv = claim_verify()
        cv["claim_scope_git_blob_sha"] = "0" * 40
        self.assertEqual(evaluate(cv=cv)["reason"], "CLAIM_VERIFICATION_SCOPE_BLOB_MISMATCH")

    def test_claim_verification_evidence_ref_required(self):
        c = cert()
        c["evidence_refs"] = []
        self.assertEqual(evaluate(c=c)["reason"], "CLAIM_VERIFICATION_EVIDENCE_REF_REQUIRED")

    def test_scope_target_must_be_claim_specific(self):
        c = cert()
        c["scope_certificate"]["target_scope_id"] = LEAF
        self.assertEqual(evaluate(c=c)["reason"], "SCOPE_TARGET_MISMATCH")

    def test_premise_set_must_bind_exact_claim_verification(self):
        c = cert()
        c["scope_certificate"]["premise_set_id"] = "claim-verification:" + "f" * 40
        self.assertEqual(evaluate(c=c)["reason"], "PREMISE_SET_NOT_BOUND_TO_CLAIM_VERIFICATION")

    def test_incomplete_universal_scope_fails(self):
        c = cert()
        c["scope_certificate"]["all_admissible_target_inputs_proved"] = False
        self.assertEqual(evaluate(c=c)["reason"], "UNIVERSAL_SCOPE_COMPILER_REJECTED")

    def test_authority_overclaim_fails(self):
        c = cert()
        c["execution_authority"] = True
        self.assertEqual(evaluate(c=c)["reason"], "CERTIFICATE_AUTHORITY_OVERCLAIM:execution_authority")


if __name__ == "__main__":
    unittest.main(verbosity=2)
