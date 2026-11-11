import unittest

from canonical.runtime.aa_briefcase_core_owner_attestation_v2 import (
    CoreOwnerAttestationError,
    verify_core_owner_attestation,
)
from canonical.tests.test_aa_briefcase_owner_signature_verifier_v1 import make_signed


def target(owner_key_binding=None):
    out = {
        "target": {
            "benchmark": "AA-Briefcase v1.1",
            "model": "Claude Opus 5.5 (Max, Default Fallback)",
            "current_owner_elo": 1807,
            "observed_date": "2026-10-08",
        },
        "epoch_rule": {"current_epoch_minimum_opus55_target_elo": 1807},
    }
    if owner_key_binding is not None:
        out["owner_attestation_trust_anchor"] = owner_key_binding
    return out


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


class T(unittest.TestCase):
    def test_core_without_private_roots_is_sufficient(self):
        s = statement()
        bundle, binding = make_signed(s)
        out = verify_core_owner_attestation(target(binding), s, bundle)
        self.assertEqual(out["status"], "PASS_CORE_OWNER_ATTESTATION")
        self.assertFalse(out["audit_commitments_present"])
        self.assertFalse(out["private_population_hashes_required_for_logical_sufficiency"])

    def test_optional_audit_commitments_are_accepted(self):
        s = statement(audit=True)
        bundle, binding = make_signed(s)
        out = verify_core_owner_attestation(target(binding), s, bundle)
        self.assertTrue(out["audit_commitments_present"])

    def test_missing_owner_trust_anchor_rejected(self):
        s = statement()
        bundle, _binding = make_signed(s)
        with self.assertRaisesRegex(CoreOwnerAttestationError, "OWNER_TRUST_ANCHOR_MISSING"):
            verify_core_owner_attestation(target(), s, bundle)

    def test_wrong_subject_digest_rejected(self):
        s = statement()
        s["subject"][0]["digest"]["sha256"] = "z" * 64
        bundle, binding = make_signed(s)
        with self.assertRaisesRegex(CoreOwnerAttestationError, "SUBJECT_SHA256_INVALID"):
            verify_core_owner_attestation(target(binding), s, bundle)

    def test_stale_epoch_rejected(self):
        s = statement()
        s["predicate"]["target_observed_date"] = "2026-10-07"
        bundle, binding = make_signed(s)
        with self.assertRaisesRegex(CoreOwnerAttestationError, "PREDICATE_EPOCH_MISMATCH"):
            verify_core_owner_attestation(target(binding), s, bundle)

    def test_scope_incomplete_rejected(self):
        s = statement()
        s["predicate"]["complete_current_scored_private_scope_used"] = False
        bundle, binding = make_signed(s)
        with self.assertRaisesRegex(CoreOwnerAttestationError, "PRIVATE_SCOPE_NOT_COMPLETE"):
            verify_core_owner_attestation(target(binding), s, bundle)

    def test_grading_relations_incomplete_rejected(self):
        s = statement()
        s["predicate"]["all_load_bearing_grading_relations_included"] = False
        bundle, binding = make_signed(s)
        with self.assertRaisesRegex(CoreOwnerAttestationError, "GRADING_RELATION_SCOPE_NOT_COMPLETE"):
            verify_core_owner_attestation(target(binding), s, bundle)

    def test_noninferiority_false_rejected(self):
        s = statement()
        s["predicate"]["brain_weakly_dominates_current_opus55"] = False
        bundle, binding = make_signed(s)
        with self.assertRaisesRegex(CoreOwnerAttestationError, "NONINFERIORITY_NOT_ATTESTED"):
            verify_core_owner_attestation(target(binding), s, bundle)

    def test_unverified_owner_identity_rejected(self):
        s = statement()
        bundle, binding = make_signed(s)
        binding["identity_verified"] = False
        with self.assertRaisesRegex(Exception, "OWNER_KEY_IDENTITY_UNVERIFIED"):
            verify_core_owner_attestation(target(binding), s, bundle)

    def test_modified_statement_signature_rejected(self):
        s = statement()
        bundle, binding = make_signed(s)
        s["predicate"]["brain_weakly_dominates_current_opus55"] = False
        with self.assertRaisesRegex(Exception, "CRYPTOGRAPHIC_SIGNATURE_INVALID"):
            verify_core_owner_attestation(target(binding), s, bundle)
