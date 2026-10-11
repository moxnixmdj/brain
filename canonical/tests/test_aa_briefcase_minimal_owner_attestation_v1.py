import copy
import unittest

from canonical.runtime.aa_briefcase_minimal_owner_attestation_v1 import (
    OwnerAttestationError,
    verify_minimal_owner_attestation,
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


def statement():
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": "brain-aa-briefcase-candidate", "digest": {"sha256": "a" * 64}}],
        "predicateType": "https://project-brain.local/attestation/aa-briefcase-current-epoch-noninferiority/v1",
        "predicate": {
            "benchmark": "AA-Briefcase v1.1",
            "target_model": "Claude Opus 5.5 (Max, Default Fallback)",
            "target_observed_date": "2026-10-08",
            "grading_protocol_manifest_git_blob_sha": "5c77f294e09d4933e3a3175c46af225b414f4702",
            "task_count": 91,
            "private_task_population_sha256": "b" * 64,
            "load_bearing_check_population_sha256": "c" * 64,
            "opus_reference_subject_sha256": "d" * 64,
            "private_scope_complete": True,
            "all_load_bearing_checks_included": True,
            "brain_weakly_dominates_current_opus55": True,
            "official_owner_elo_claimed": False,
            "historical_1822_epoch_rewritten": False,
        },
    }



class T(unittest.TestCase):
    def test_minimal_private_attestation_passes_without_private_bytes(self):
        s = statement()
        bundle, binding = make_signed(s)
        out = verify_minimal_owner_attestation(target(binding), s, bundle)
        self.assertEqual(out["status"], "PASS_MINIMAL_OWNER_ATTESTATION")
        self.assertTrue(out["scope_complete_current_epoch_noninferiority"])
        self.assertFalse(out["private_task_or_check_contents_required_for_brain_verification"])
        self.assertFalse(out["numeric_elo_reconstruction_required"])

    def test_missing_owner_trust_anchor_fails(self):
        s = statement()
        bundle, _binding = make_signed(s)
        with self.assertRaisesRegex(OwnerAttestationError, "OWNER_TRUST_ANCHOR_MISSING"):
            verify_minimal_owner_attestation(target(), s, bundle)

    def test_stale_epoch_fails(self):
        s = statement()
        s["predicate"]["target_observed_date"] = "2026-10-07"
        with self.assertRaisesRegex(OwnerAttestationError, "PREDICATE_EPOCH_MISMATCH"):
            bundle, binding = make_signed(s)
            verify_minimal_owner_attestation(target(binding), s, bundle)

    def test_protocol_drift_fails(self):
        s = statement()
        s["predicate"]["grading_protocol_manifest_git_blob_sha"] = "0" * 40
        with self.assertRaisesRegex(OwnerAttestationError, "GRADING_PROTOCOL_DRIFT"):
            bundle, binding = make_signed(s)
            verify_minimal_owner_attestation(target(binding), s, bundle)

    def test_incomplete_private_scope_fails(self):
        s = statement()
        s["predicate"]["private_scope_complete"] = False
        with self.assertRaisesRegex(OwnerAttestationError, "PRIVATE_SCOPE_NOT_COMPLETE"):
            bundle, binding = make_signed(s)
            verify_minimal_owner_attestation(target(binding), s, bundle)

    def test_missing_check_scope_fails(self):
        s = statement()
        s["predicate"]["all_load_bearing_checks_included"] = False
        with self.assertRaisesRegex(OwnerAttestationError, "CHECK_SCOPE_NOT_COMPLETE"):
            bundle, binding = make_signed(s)
            verify_minimal_owner_attestation(target(binding), s, bundle)

    def test_negative_attestation_fails(self):
        s = statement()
        s["predicate"]["brain_weakly_dominates_current_opus55"] = False
        with self.assertRaisesRegex(OwnerAttestationError, "NONINFERIORITY_NOT_ATTESTED"):
            bundle, binding = make_signed(s)
            verify_minimal_owner_attestation(target(binding), s, bundle)

    def test_modified_statement_signature_fails(self):
        s = statement()
        bundle, binding = make_signed(s)
        s["predicate"]["brain_weakly_dominates_current_opus55"] = False
        with self.assertRaisesRegex(Exception, "CRYPTOGRAPHIC_SIGNATURE_INVALID"):
            verify_minimal_owner_attestation(target(binding), s, bundle)

    def test_unverified_owner_key_identity_fails(self):
        s = statement()
        bundle, binding = make_signed(s)
        binding["identity_verified"] = False
        with self.assertRaisesRegex(Exception, "OWNER_KEY_IDENTITY_UNVERIFIED"):
            verify_minimal_owner_attestation(target(binding), s, bundle)
