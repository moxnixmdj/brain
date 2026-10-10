from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_whole_leaf_scope_cover_v1 as s

LEAF = "PQ::R10_ANALYSIS_DECISION::EXECUTION"
CLAIM_ID = "2" * 64
CLAIM_SCOPE_BLOB = "a" * 40
CLAIM_VERIFY_BLOB = "b" * 40
ROOT = Path(__file__).resolve().parents[2]


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest()


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


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
        "scope_certificate": {
            "id": LEAF + "::WHOLE_LEAF_SCOPE_V1",
            "target_scope_id": "scope://professional-quality/whole-leaf/" + CLAIM_ID,
            "claim_id": CLAIM_ID,
            "basis": s.UNIVERSAL,
            "verified": True,
            "independent": True,
            "scope_relation": "EXACT",
            "formal_completeness": True,
            "all_admissible_target_inputs_proved": True,
            "premise_set_id": "claim-verification:" + CLAIM_VERIFY_BLOB,
        },
        "evidence_refs": [{
            "path": "canonical/verification/CLAIM_VERIFY.json",
            "git_blob_sha": CLAIM_VERIFY_BLOB,
        }],
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

    def test_missing_exact_claim_verification_evidence_fails(self):
        cert = certificate()
        cert["evidence_refs"][0]["git_blob_sha"] = "0" * 40
        self.assertEqual(evaluate(cert=cert)["reason"], "CERT_EXACT_CLAIM_VERIFICATION_EVIDENCE_REQUIRED")

    def test_scope_target_narrowing_fails(self):
        cert = certificate()
        cert["scope_certificate"]["target_scope_id"] = "scope://professional-quality/whole-leaf/narrow"
        self.assertEqual(evaluate(cert=cert)["reason"], "SCOPE_CERTIFICATE_BINDING_MISMATCH:target_scope_id")

    def test_scope_basis_tamper_fails(self):
        cert = certificate()
        cert["scope_certificate"]["basis"] = "EXACT_COMPLETE_TARGET_CASE_UNIVERSE"
        self.assertEqual(evaluate(cert=cert)["reason"], "SCOPE_CERTIFICATE_BINDING_MISMATCH:basis")

    def test_premise_rebinding_fails(self):
        cert = certificate()
        cert["scope_certificate"]["premise_set_id"] = "claim-verification:" + ("0" * 40)
        self.assertEqual(evaluate(cert=cert)["reason"], "SCOPE_CERTIFICATE_BINDING_MISMATCH:premise_set_id")

    def test_authority_overclaim_fails(self):
        cert = certificate()
        cert["quality_authority"] = True
        self.assertEqual(evaluate(cert=cert)["reason"], "CERT_SELF_AUTHORITY_FORBIDDEN:quality_authority")

    def test_claim_id_mismatch_fails(self):
        cert = certificate()
        cert["claim_id"] = "3" * 64
        self.assertEqual(evaluate(cert=cert)["reason"], "CERT_IDENTITY_MISMATCH")

    def test_current_r10_execution_certificate_exact_bytes_pass(self):
        claim_path = "canonical/governance/PROFESSIONAL_QUALITY_R10_EXECUTION_WHOLE_LEAF_CLAIM_SCOPE_20261010_V1.json"
        verify_path = "canonical/verification/PROFESSIONAL_QUALITY_R10_EXECUTION_WHOLE_LEAF_CLAIM_SCOPE_VERIFY_20261010_V1.json"
        cert_path = "canonical/governance/PROFESSIONAL_QUALITY_R10_EXECUTION_WHOLE_LEAF_SCOPE_CERTIFICATE_20261010_V1.json"
        cs = load_json(claim_path)
        cv = load_json(verify_path)
        cert = load_json(cert_path)
        out = s.evaluate(
            claim_scope=cs,
            claim_verification=cv,
            certificate=cert,
            claim_scope_blob=git_blob(ROOT / claim_path),
            claim_verification_blob=git_blob(ROOT / verify_path),
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["scope_complete"])
        self.assertEqual(out["verified_basis"], s.UNIVERSAL)
        self.assertFalse(out["leaf_property_truth_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
