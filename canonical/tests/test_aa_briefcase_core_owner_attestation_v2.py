import unittest

from canonical.runtime.aa_briefcase_core_owner_attestation_v2 import (
    CoreOwnerAttestationError,
    _sha256,
    verify_core_owner_attestation,
)


def target():
    return {
        "target": {
            "benchmark": "AA-Briefcase v1.1",
            "model": "Claude Opus 5.5 (Max, Default Fallback)",
            "current_owner_elo": 1807,
            "observed_date": "2026-10-08",
        },
        "epoch_rule": {"current_epoch_minimum_opus55_target_elo": 1807},
    }


def statement(audit=False):
    predicate = {
        "benchmark": "AA-Briefcase v1.1",
        "target_model": "Claude Opus 5.5 (Max, Default Fallback)",
        "target_observed_date": "2026-10-08",
        "grading_protocol_manifest_git_blob_sha": "5c77f294e09d4933e3a3175c46af225b414f4702",
        "task_count": 91,
        "complete_current_scored_private_scope_used": True,
        "all_load_bearing_grading_relations_included": True,
        "brain_weakly_dominates_current_opus55": True,
        "official_owner_elo_claimed": False,
        "historical_1822_epoch_rewritten": False,
    }
    if audit:
        predicate["audit_commitments"] = {
            "private_task_population_sha256": "b" * 64,
            "load_bearing_check_population_sha256": "c" * 64,
            "opus_reference_subject_sha256": "d" * 64,
        }
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": "brain-aa-briefcase-candidate", "digest": {"sha256": "a" * 64}}],
        "predicateType": "https://project-brain.local/attestation/aa-briefcase-current-epoch-noninferiority/v2",
        "predicate": predicate,
    }


def sig(s):
    return {
        "status": "VERIFIED",
        "statement_sha256": _sha256(s),
        "attestor_is_benchmark_owner_or_authorized_operator": True,
        "identity_verified": True,
        "verification_receipt_sha256": "e" * 64,
    }


class T(unittest.TestCase):
    def test_core_without_private_roots_is_sufficient(self):
        s = statement()
        out = verify_core_owner_attestation(target(), s, sig(s))
        self.assertEqual(out["status"], "PASS_CORE_OWNER_ATTESTATION")
        self.assertFalse(out["audit_commitments_present"])
        self.assertFalse(out["private_population_hashes_required_for_logical_sufficiency"])

    def test_optional_audit_commitments_are_accepted(self):
        s = statement(audit=True)
        out = verify_core_owner_attestation(target(), s, sig(s))
        self.assertTrue(out["audit_commitments_present"])

    def test_wrong_subject_digest_rejected(self):
        s = statement()
        s["subject"][0]["digest"]["sha256"] = "z" * 64
        with self.assertRaisesRegex(CoreOwnerAttestationError, "SUBJECT_SHA256_INVALID"):
            verify_core_owner_attestation(target(), s, sig(s))

    def test_stale_epoch_rejected(self):
        s = statement()
        s["predicate"]["target_observed_date"] = "2026-10-07"
        with self.assertRaisesRegex(CoreOwnerAttestationError, "PREDICATE_EPOCH_MISMATCH"):
            verify_core_owner_attestation(target(), s, sig(s))

    def test_scope_incomplete_rejected(self):
        s = statement()
        s["predicate"]["complete_current_scored_private_scope_used"] = False
        with self.assertRaisesRegex(CoreOwnerAttestationError, "PRIVATE_SCOPE_NOT_COMPLETE"):
            verify_core_owner_attestation(target(), s, sig(s))

    def test_grading_relations_incomplete_rejected(self):
        s = statement()
        s["predicate"]["all_load_bearing_grading_relations_included"] = False
        with self.assertRaisesRegex(CoreOwnerAttestationError, "GRADING_RELATION_SCOPE_NOT_COMPLETE"):
            verify_core_owner_attestation(target(), s, sig(s))

    def test_noninferiority_false_rejected(self):
        s = statement()
        s["predicate"]["brain_weakly_dominates_current_opus55"] = False
        with self.assertRaisesRegex(CoreOwnerAttestationError, "NONINFERIORITY_NOT_ATTESTED"):
            verify_core_owner_attestation(target(), s, sig(s))

    def test_unverified_signer_rejected(self):
        s = statement()
        v = sig(s)
        v["identity_verified"] = False
        with self.assertRaisesRegex(CoreOwnerAttestationError, "ATTESTOR_IDENTITY_NOT_VERIFIED"):
            verify_core_owner_attestation(target(), s, v)

    def test_tampered_statement_rejected(self):
        s = statement()
        v = sig(s)
        s["predicate"]["task_count"] = 90
        with self.assertRaises(CoreOwnerAttestationError):
            verify_core_owner_attestation(target(), s, v)
