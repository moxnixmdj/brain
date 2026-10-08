from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.aa_briefcase_owner_signature_verifier_v1 import (
    verify_owner_signature,
)

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_CORE_OWNER_ATTESTATION_V2"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = "https://project-brain.local/attestation/aa-briefcase-current-epoch-noninferiority/v2"
EXPECTED_BENCHMARK = "AA-Briefcase v1.1"
EXPECTED_MODEL = "Claude Opus 5.5 (Max, Default Fallback)"
EXPECTED_TASK_COUNT = 91
EXPECTED_GRADING_PROTOCOL_BLOB_SHA = "5c77f294e09d4933e3a3175c46af225b414f4702"


class CoreOwnerAttestationError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _hex64(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise CoreOwnerAttestationError(label + "_INVALID")
    return value


def _subject(statement: Mapping[str, Any]) -> Mapping[str, Any]:
    subjects = statement.get("subject")
    if not isinstance(subjects, Sequence) or isinstance(subjects, (str, bytes)) or len(subjects) != 1:
        raise CoreOwnerAttestationError("EXACTLY_ONE_SUBJECT_REQUIRED")
    subject = subjects[0]
    if not isinstance(subject, Mapping):
        raise CoreOwnerAttestationError("SUBJECT_INVALID")
    digest = subject.get("digest")
    if not isinstance(digest, Mapping):
        raise CoreOwnerAttestationError("SUBJECT_DIGEST_INVALID")
    _hex64(digest.get("sha256"), "SUBJECT_SHA256")
    return subject


def verify_core_owner_attestation(
    current_target: Mapping[str, Any],
    statement: Mapping[str, Any],
    signature_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(current_target, Mapping):
        raise CoreOwnerAttestationError("TARGET_INVALID")
    target = current_target.get("target")
    epoch = current_target.get("epoch_rule")
    if not isinstance(target, Mapping) or not isinstance(epoch, Mapping):
        raise CoreOwnerAttestationError("TARGET_BINDING_MISSING")
    if target.get("benchmark") != EXPECTED_BENCHMARK:
        raise CoreOwnerAttestationError("TARGET_BENCHMARK_MISMATCH")
    if target.get("model") != EXPECTED_MODEL:
        raise CoreOwnerAttestationError("TARGET_MODEL_MISMATCH")
    if epoch.get("current_epoch_minimum_opus55_target_elo") != target.get("current_owner_elo"):
        raise CoreOwnerAttestationError("TARGET_REFERENCE_DRIFT")

    if not isinstance(statement, Mapping):
        raise CoreOwnerAttestationError("STATEMENT_INVALID")
    if statement.get("_type") != STATEMENT_TYPE:
        raise CoreOwnerAttestationError("STATEMENT_TYPE_MISMATCH")
    if statement.get("predicateType") != PREDICATE_TYPE:
        raise CoreOwnerAttestationError("PREDICATE_TYPE_MISMATCH")
    owner_key_binding = current_target.get("owner_attestation_trust_anchor")
    if not isinstance(owner_key_binding, Mapping):
        raise CoreOwnerAttestationError("OWNER_TRUST_ANCHOR_MISSING")
    if owner_key_binding.get("status") != "VERIFIED_OWNER_KEY_BINDING":
        raise CoreOwnerAttestationError("OWNER_TRUST_ANCHOR_NOT_VERIFIED")

    signature_verification = verify_owner_signature(
        statement,
        signature_bundle,
        owner_key_binding,
    )
    if signature_verification.get("statement_sha256") != _sha256(statement):
        raise CoreOwnerAttestationError("SIGNED_STATEMENT_DIGEST_MISMATCH")
    if signature_verification.get("attestor_is_benchmark_owner_or_authorized_operator") is not True:
        raise CoreOwnerAttestationError("ATTESTOR_AUTHORITY_NOT_VERIFIED")
    if signature_verification.get("identity_verified") is not True:
        raise CoreOwnerAttestationError("ATTESTOR_IDENTITY_NOT_VERIFIED")
    _hex64(signature_verification.get("verification_receipt_sha256"), "SIGNATURE_VERIFICATION_RECEIPT_SHA256")

    subject = _subject(statement)

    predicate = statement.get("predicate")
    if not isinstance(predicate, Mapping):
        raise CoreOwnerAttestationError("PREDICATE_INVALID")
    if predicate.get("benchmark") != EXPECTED_BENCHMARK:
        raise CoreOwnerAttestationError("PREDICATE_BENCHMARK_MISMATCH")
    if predicate.get("target_model") != EXPECTED_MODEL:
        raise CoreOwnerAttestationError("PREDICATE_TARGET_MODEL_MISMATCH")
    if predicate.get("target_observed_date") != target.get("observed_date"):
        raise CoreOwnerAttestationError("PREDICATE_EPOCH_MISMATCH")
    if predicate.get("grading_protocol_manifest_git_blob_sha") != EXPECTED_GRADING_PROTOCOL_BLOB_SHA:
        raise CoreOwnerAttestationError("GRADING_PROTOCOL_DRIFT")
    if predicate.get("task_count") != EXPECTED_TASK_COUNT:
        raise CoreOwnerAttestationError("TASK_COUNT_MISMATCH")

    if predicate.get("complete_current_scored_private_scope_used") is not True:
        raise CoreOwnerAttestationError("PRIVATE_SCOPE_NOT_COMPLETE")
    if predicate.get("all_load_bearing_grading_relations_included") is not True:
        raise CoreOwnerAttestationError("GRADING_RELATION_SCOPE_NOT_COMPLETE")
    if predicate.get("brain_weakly_dominates_current_opus55") is not True:
        raise CoreOwnerAttestationError("NONINFERIORITY_NOT_ATTESTED")
    if predicate.get("official_owner_elo_claimed") is not False:
        raise CoreOwnerAttestationError("DIRECT_ATTESTATION_MUST_NOT_CLAIM_OFFICIAL_ELO")
    if predicate.get("historical_1822_epoch_rewritten") is not False:
        raise CoreOwnerAttestationError("HISTORICAL_EPOCH_REWRITE_FORBIDDEN")

    audit = predicate.get("audit_commitments")
    audit_commitments_present = False
    if audit is not None:
        if not isinstance(audit, Mapping):
            raise CoreOwnerAttestationError("AUDIT_COMMITMENTS_INVALID")
        for key in (
            "private_task_population_sha256",
            "load_bearing_check_population_sha256",
            "opus_reference_subject_sha256",
        ):
            _hex64(audit.get(key), key.upper())
        audit_commitments_present = True

    material = {
        "schema": SCHEMA,
        "status": "PASS_CORE_OWNER_ATTESTATION",
        "subject_sha256": subject["digest"]["sha256"],
        "target_observed_date": target["observed_date"],
        "current_owner_reference_elo_context_only": target["current_owner_elo"],
        "scope_complete_current_epoch_noninferiority": True,
        "audit_commitments_present": audit_commitments_present,
        "private_task_or_check_contents_required": False,
        "private_population_hashes_required_for_logical_sufficiency": False,
        "numeric_elo_reconstruction_required": False,
        "official_owner_elo_claimed": False,
        "historical_1822_epoch_rewritten": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
    }
    return {**material, "verdict_sha256": _sha256(material)}
