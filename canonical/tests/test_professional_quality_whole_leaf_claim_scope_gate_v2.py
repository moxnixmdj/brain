from __future__ import annotations
from copy import deepcopy
import unittest

from canonical.runtime import professional_quality_whole_leaf_claim_scope_gate_v2 as gate

LEAF = "PQ::R1_TARGET_SPECIFICATION::SEMANTIC"
ROOT = "R1_TARGET_SPECIFICATION"
CLAIM_BLOB = "a" * 40
CERT_BLOB = "b" * 40
CLAIM_VERIFIER_BLOB = "c" * 40
CLAIM_TESTS_BLOB = "d" * 40
CERT_VERIFIER_BLOB = "e" * 40
CERT_TESTS_BLOB = "f" * 40
TRANSCRIPT = "1" * 64

def manifest():
    return {
        "roots": [{
            "root_id": ROOT,
            "contract": "Freeze objective, audience and decision-relevant target semantics.",
            "semantic_leaf": {
                "id": LEAF,
                "obligation": "PROVE_DOMAIN_SEMANTIC_SUFFICIENCY_FOR_R1_TARGET_SPECIFICATION",
                "acceptance": "ALL_ADMISSIBLE_R1_TARGET_SPECIFICATION_INPUTS_ARE_GROUNDED_AND_DECISION_RELEVANT_AMBIGUITY_IS_RESOLVED",
            },
            "execution_leaf": {
                "id": "PQ::R1_TARGET_SPECIFICATION::EXECUTION",
                "obligation": "VERIFY_DOMAIN_EXECUTION_FOR_R1_TARGET_SPECIFICATION",
                "acceptance": "EXECUTION_ACCEPTANCE",
            },
        }]
    }

def scope_definition():
    return {
        "domain_schema_id": "TEST_R1_WHOLE_DOMAIN_V1",
        "entire_admissible_leaf_domain": True,
        "domain_definition": {
            "input_kinds": ["TARGET_SPEC"],
            "boundary": "ALL_INPUTS_SATISFYING_FROZEN_TEST_DOMAIN_SCHEMA",
        },
    }

def claim_scope():
    meta = gate._manifest_leaf(manifest(), LEAF)
    sd = scope_definition()
    claim = gate.build_claim(meta, sd, epoch="2026-10-10T15:30:00Z")
    return {
        "schema": gate.CLAIM_SCOPE_SCHEMA,
        "leaf_id": LEAF,
        "root_id": ROOT,
        "kind": "SEMANTIC",
        "behavior_id": "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
        "subject_kind": gate.SUBJECT_KIND,
        "subject_id": gate.SUBJECT_ID,
        "subject_sha256": gate.SUBJECT_SHA256,
        "leaf_acceptance": meta["acceptance"],
        "scope_definition": sd,
        "epoch": "2026-10-10T15:30:00Z",
        "claim": claim,
    }

def claim_verify(cs=None):
    cs = cs or claim_scope()
    return {
        "schema": gate.CLAIM_VERIFY_SCHEMA,
        "status": "PASS__WHOLE_LEAF_DOMAIN_EQUIVALENCE_INDEPENDENTLY_VERIFIED",
        "leaf_id": LEAF,
        "claim_id": cs["claim"]["claim_id"],
        "claim_scope_git_blob_sha": CLAIM_BLOB,
        "leaf_manifest_git_blob_sha": gate.MANIFEST_BLOB,
        "subject_git_blob_sha": gate.SUBJECT_BLOB,
        "mission_authority_git_blob_sha": gate.MISSION_BLOB,
        "claim_guard_git_blob_sha": gate.CLAIM_GUARD_BLOB,
        "semantic_verifier_git_blob_sha": CLAIM_VERIFIER_BLOB,
        "semantic_tests_git_blob_sha": CLAIM_TESTS_BLOB,
        "whole_leaf_domain_equivalence_proved": True,
        "scope_definition_sha256": gate._canon_sha(cs["scope_definition"]),
        "leaf_acceptance_sha256": gate._text_sha(cs["leaf_acceptance"]),
        "independent_replay": {"pass": True, "transcript_sha256": TRANSCRIPT},
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

def certificate(cs=None):
    cs = cs or claim_scope()
    cid = cs["claim"]["claim_id"]
    return {
        "schema": gate.CERT_SCHEMA,
        "leaf_id": LEAF,
        "claim_id": cid,
        "claim_scope_git_blob_sha": CLAIM_BLOB,
        "scope_certificate": {
            "id": "TEST_SCOPE_CERT",
            "target_scope_id": "scope://professional-quality/whole-leaf/" + cid,
            "claim_id": cid,
            "basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
            "verified": True,
            "independent": True,
            "scope_relation": "EXACT",
            "formal_completeness": True,
            "all_admissible_target_inputs_proved": True,
            "premise_set_id": "test-premise-set",
        },
        "evidence_refs": [{"path": "canonical/verification/x.json", "git_blob_sha": "2" * 40}],
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

def cert_verify(cs=None, cert=None):
    cs = cs or claim_scope()
    cert = cert or certificate(cs)
    return {
        "schema": gate.CERT_VERIFY_SCHEMA,
        "status": "PASS__WHOLE_LEAF_SCOPE_COVER_INDEPENDENTLY_VERIFIED",
        "leaf_id": LEAF,
        "claim_id": cs["claim"]["claim_id"],
        "claim_scope_git_blob_sha": CLAIM_BLOB,
        "certificate_git_blob_sha": CERT_BLOB,
        "scope_compiler_git_blob_sha": gate.SCOPE_COMPILER_BLOB,
        "semantic_verifier_git_blob_sha": CERT_VERIFIER_BLOB,
        "semantic_tests_git_blob_sha": CERT_TESTS_BLOB,
        "scope_complete": True,
        "verified_basis": cert["scope_certificate"]["basis"],
        "independent_replay": {"pass": True, "transcript_sha256": TRANSCRIPT},
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

def evaluate(cs=None, cv=None, cert=None, sv=None):
    cs = cs or claim_scope()
    cv = cv or claim_verify(cs)
    cert = cert or certificate(cs)
    sv = sv or cert_verify(cs, cert)
    return gate.evaluate_documents(
        manifest=manifest(),
        claim_scope=cs,
        claim_verification=cv,
        certificate=cert,
        certificate_verification=sv,
        claim_scope_blob=CLAIM_BLOB,
        certificate_blob=CERT_BLOB,
        claim_semantic_verifier_blob=CLAIM_VERIFIER_BLOB,
        claim_semantic_tests_blob=CLAIM_TESTS_BLOB,
        certificate_semantic_verifier_blob=CERT_VERIFIER_BLOB,
        certificate_semantic_tests_blob=CERT_TESTS_BLOB,
    )

class WholeLeafClaimScopeGateV2Tests(unittest.TestCase):
    def test_valid_claim_scoped_certificate_passes_scope_only(self):
        out = evaluate()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["whole_leaf_domain_equivalence_proved"])
        self.assertTrue(out["whole_leaf_scope_complete"])
        self.assertFalse(out["leaf_property_truth_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_domain_shrinkage_fails_closed(self):
        cs = claim_scope()
        cs["scope_definition"]["entire_admissible_leaf_domain"] = False
        cs["claim"] = gate.build_claim(gate._manifest_leaf(manifest(), LEAF), cs["scope_definition"], epoch=cs["epoch"])
        out = evaluate(cs=cs, cv=claim_verify(cs), cert=certificate(cs), sv=cert_verify(cs, certificate(cs)))
        self.assertEqual(out["reason"], "ENTIRE_LEAF_DOMAIN_ASSERTION_REQUIRED")

    def test_missing_domain_definition_fails_closed(self):
        cs = claim_scope()
        cs["scope_definition"].pop("domain_definition")
        cs["claim"] = gate.build_claim(gate._manifest_leaf(manifest(), LEAF), cs["scope_definition"], epoch=cs["epoch"])
        out = evaluate(cs=cs, cv=claim_verify(cs), cert=certificate(cs), sv=cert_verify(cs, certificate(cs)))
        self.assertEqual(out["reason"], "DOMAIN_DEFINITION_REQUIRED")

    def test_acceptance_drift_fails_closed(self):
        cs = claim_scope()
        cs["leaf_acceptance"] = "weaker"
        out = evaluate(cs=cs)
        self.assertEqual(out["reason"], "CLAIM_SCOPE_ACCEPTANCE_DRIFT")

    def test_subject_drift_fails_closed(self):
        cs = claim_scope()
        cs["subject_sha256"] = "0" * 64
        out = evaluate(cs=cs)
        self.assertEqual(out["reason"], "CLAIM_SCOPE_SUBJECT_DRIFT")

    def test_claim_id_substitution_fails_closed(self):
        cs = claim_scope()
        cs["claim"]["claim_id"] = "0" * 64
        out = evaluate(cs=cs)
        self.assertEqual(out["reason"], "CLAIM_SCOPE_CONTENT_ADDRESS_MISMATCH")

    def test_claim_verifier_must_prove_whole_domain_equivalence(self):
        cv = claim_verify()
        cv["whole_leaf_domain_equivalence_proved"] = False
        out = evaluate(cv=cv)
        self.assertEqual(out["reason"], "WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED")

    def test_claim_verifier_must_bind_scope_digest(self):
        cv = claim_verify()
        cv["scope_definition_sha256"] = "0" * 64
        out = evaluate(cv=cv)
        self.assertEqual(out["reason"], "CLAIM_VERIFY_SCOPE_DEFINITION_DIGEST_MISMATCH")

    def test_claim_verifier_must_bind_exact_scope_blob(self):
        cv = claim_verify()
        cv["claim_scope_git_blob_sha"] = "0" * 40
        out = evaluate(cv=cv)
        self.assertEqual(out["reason"], "CLAIM_VERIFY_SCOPE_BLOB_MISMATCH")

    def test_certificate_must_bind_claim_scope_blob(self):
        cert = certificate()
        cert["claim_scope_git_blob_sha"] = "0" * 40
        out = evaluate(cert=cert, sv=cert_verify(cert=cert))
        self.assertEqual(out["reason"], "CERT_CLAIM_SCOPE_BLOB_MISMATCH")

    def test_certificate_target_scope_is_claim_specific(self):
        cert = certificate()
        cert["scope_certificate"]["target_scope_id"] = LEAF
        out = evaluate(cert=cert, sv=cert_verify(cert=cert))
        self.assertEqual(out["reason"], "SCOPE_CERTIFICATE_TARGET_MISMATCH")

    def test_incomplete_scope_certificate_fails_closed(self):
        cert = certificate()
        cert["scope_certificate"]["all_admissible_target_inputs_proved"] = False
        out = evaluate(cert=cert, sv=cert_verify(cert=cert))
        self.assertEqual(out["reason"], "UNIVERSAL_SCOPE_COMPILER_REJECTED")

    def test_certificate_verification_must_bind_exact_certificate(self):
        sv = cert_verify()
        sv["certificate_git_blob_sha"] = "0" * 40
        out = evaluate(sv=sv)
        self.assertEqual(out["reason"], "CERT_VERIFY_CERTIFICATE_BLOB_MISMATCH")

    def test_claim_verification_authority_overclaim_fails(self):
        cv = claim_verify()
        cv["quality_authority"] = True
        out = evaluate(cv=cv)
        self.assertEqual(out["reason"], "CLAIM_VERIFY_AUTHORITY_OVERCLAIM:quality_authority")

    def test_certificate_authority_overclaim_fails(self):
        cert = certificate()
        cert["quality_authority"] = True
        out = evaluate(cert=cert, sv=cert_verify(cert=cert))
        self.assertEqual(out["reason"], "CERT_SELF_AUTHORITY_FORBIDDEN:quality_authority")

    def test_certificate_verification_authority_overclaim_fails(self):
        sv = cert_verify()
        sv["terminal_authority"] = True
        out = evaluate(sv=sv)
        self.assertEqual(out["reason"], "CERT_VERIFY_AUTHORITY_OVERCLAIM:terminal_authority")

if __name__ == "__main__":
    unittest.main(verbosity=2)
