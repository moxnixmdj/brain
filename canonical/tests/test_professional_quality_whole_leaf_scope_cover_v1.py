from __future__ import annotations

from copy import deepcopy
import unittest

from canonical.runtime import professional_quality_whole_leaf_scope_cover_v1 as s

LEAF = "PQ::R10_ANALYSIS_DECISION::EXECUTION"
CLAIM_ID = "2" * 64
CLAIM_SCOPE_BLOB = "a" * 40
CLAIM_VERIFY_BLOB = "b" * 40


def claim_scope():
    return {
        "schema": s.CLAIM_SCOPE_SCHEMA,
        "leaf_id": LEAF,
        "claim": {"claim_id": CLAIM_ID},
    }


def claim_verify():
    return {
        "schema": s.CLAIM_VERIFY_SCHEMA,
        "status": "PASS__EXACT_WHOLE_LEAF_DOMAIN_EQUIVALENCE",
        "leaf_id": LEAF,
        "claim_id": CLAIM_ID,
        "claim_scope_git_blob_sha": CLAIM_SCOPE_BLOB,
        "whole_leaf_domain_equivalence_proved": True,
        "independent_replay": {"pass": True, "transcript_sha256": "c" * 64},
    }


def certificate():
    return {
        "schema": s.CERT_SCHEMA,
        "leaf_id": LEAF,
        "claim_id": CLAIM_ID,
        "claim_scope_git_blob_sha": CLAIM_SCOPE_BLOB,
        "claim_verification_git_blob_sha": CLAIM_VERIFY_BLOB,
        "scope_certificate": s.expected_scope_certificate(CLAIM_ID, CLAIM_VERIFY_BLOB),
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def evaluate(cs=None, cv=None, cert=None):
    return s.evaluate(
        claim_scope=cs or claim_scope(),
        claim_verification=cv or claim_verify(),
        certificate=cert or certificate(),
        claim_scope_blob=CLAIM_SCOPE_BLOB,
        claim_verification_blob=CLAIM_VERIFY_BLOB,
    )


class ScopeCoverV1Tests(unittest.TestCase):
    def test_exact_independent_domain_equivalence_composes_to_scope_cover(self):
        out = evaluate()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["scope_complete"])
        self.assertFalse(out["leaf_property_truth_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_nonindependent_domain_equivalence_fails(self):
        cv = claim_verify()
        cv["independent_replay"]["pass"] = False
        self.assertEqual(evaluate(cv=cv)["reason"], "INDEPENDENT_DOMAIN_REPLAY_REQUIRED")

    def test_domain_equivalence_false_fails(self):
        cv = claim_verify()
        cv["whole_leaf_domain_equivalence_proved"] = False
        self.assertEqual(evaluate(cv=cv)["reason"], "WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED")

    def test_claim_scope_blob_drift_fails(self):
        cv = claim_verify()
        cv["claim_scope_git_blob_sha"] = "0" * 40
        self.assertEqual(evaluate(cv=cv)["reason"], "CLAIM_VERIFY_SCOPE_BLOB_MISMATCH")

    def test_certificate_claim_verify_blob_drift_fails(self):
        cert = certificate()
        cert["claim_verification_git_blob_sha"] = "0" * 40
        self.assertEqual(evaluate(cert=cert)["reason"], "CERT_CLAIM_VERIFY_BLOB_MISMATCH")

    def test_scope_target_narrowing_fails(self):
        cert = certificate()
        cert["scope_certificate"]["target_scope_id"] = "scope://professional-quality/whole-leaf/narrow"
        self.assertEqual(evaluate(cert=cert)["reason"], "SCOPE_CERTIFICATE_NOT_EXACT")

    def test_scope_basis_tamper_fails(self):
        cert = certificate()
        cert["scope_certificate"]["basis"] = "EXACT_COMPLETE_TARGET_CASE_UNIVERSE"
        self.assertEqual(evaluate(cert=cert)["reason"], "SCOPE_CERTIFICATE_NOT_EXACT")

    def test_authority_overclaim_fails(self):
        cert = certificate()
        cert["quality_authority"] = True
        self.assertEqual(evaluate(cert=cert)["reason"], "CERT_SELF_AUTHORITY_FORBIDDEN:quality_authority")

    def test_claim_id_mismatch_fails(self):
        cert = certificate()
        cert["claim_id"] = "3" * 64
        self.assertEqual(evaluate(cert=cert)["reason"], "CERT_IDENTITY_MISMATCH")


if __name__ == "__main__":
    unittest.main(verbosity=2)
