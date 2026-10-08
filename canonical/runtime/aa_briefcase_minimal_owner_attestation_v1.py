from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.aa_briefcase_owner_signature_verifier_v1 import (
    verify_owner_signature,
)

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_MINIMAL_OWNER_ATTESTATION_V1"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = "https://project-brain.local/attestation/aa-briefcase-current-epoch-noninferiority/v1"
EXPECTED_BENCHMARK = "AA-Briefcase v1.1"
EXPECTED_MODEL = "Claude Opus 5.5 (Max, Default Fallback)"
EXPECTED_TASK_COUNT = 91
EXPECTED_GRADING_PROTOCOL_BLOB_SHA = "5c77f294e09d4933e3a3175c46af225b414f4702"


class OwnerAttestationError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _hex(value: Any, n: int, label: str) -> str:
    if not isinstance(value, str) or len(value) != n or any(c not in "0123456789abcdef" for c in value):
        raise OwnerAttestationError(label + "_INVALID")
    return value


def _one_subject(statement: Mapping[str, Any]) -> Mapping[str, Any]:
    subjects = statement.get("subject")
    if not isinstance(subjects, Sequence) or isinstance(subjects, (str, bytes)) or len(subjects) != 1:
        raise OwnerAttestationError("EXACTLY_ONE_SUBJECT_REQUIRED")
    subject = subjects[0]
    if not isinstance(subject, Mapping):
        raise OwnerAttestationError("SUBJECT_INVALID")
    digest = subject.get("digest")
    if not isinstance(digest, Mapping):
        raise OwnerAttestationError("SUBJECT_DIGEST_INVALID")
    _hex(digest.get("sha256"), 64, "SUBJECT_SHA256")
    return subject


def verify_minimal_owner_attestation(
    current_target: Mapping[str, Any],
    statement: Mapping[str, Any],
    signature_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(current_target, Mapping):
        raise OwnerAttestationError("TARGET_INVALID")
    target = current_target.get("target")
    epoch = current_target.get("epoch_rule")
    if not isinstance(target, Mapping) or not isinstance(epoch, Mapping):
        raise OwnerAttestationError("TARGET_BINDING_MISSING")
    if target.get("benchmark") != EXPECTED_BENCHMARK:
        raise OwnerAttestationError("TARGET_BENCHMARK_MISMATCH")
    if target.get("model") != EXPECTED_MODEL:
        raise OwnerAttestationError("TARGET_MODEL_MISMATCH")
    observed_date = target.get("observed_date")
    reference = target.get("current_owner_elo")
    if epoch.get("current_epoch_minimum_opus55_target_elo") != reference:
        raise OwnerAttestationError("TARGET_REFERENCE_DRIFT")

    owner_key_binding = current_target.get("owner_attestation_trust_anchor")
    if not isinstance(owner_key_binding, Mapping):
        raise OwnerAttestationError("OWNER_TRUST_ANCHOR_MISSING")
    if owner_key_binding.get("status") != "VERIFIED_OWNER_KEY_BINDING":
        raise OwnerAttestationError("OWNER_TRUST_ANCHOR_NOT_VERIFIED")

    if not isinstance(statement, Mapping):
        raise OwnerAttestationError("STATEMENT_INVALID")
    if statement.get("_type") != STATEMENT_TYPE:
        raise OwnerAttestationError("STATEMENT_TYPE_MISMATCH")
    if statement.get("predicateType") != PREDICATE_TYPE:
        raise OwnerAttestationError("PREDICATE_TYPE_MISMATCH")

    signature_verification = verify_owner_signature(
        statement,
        signature_bundle,
        owner_key_binding,
    )
    if signature_verification.get("statement_sha256") != _sha256(statement):
        raise OwnerAttestationError("SIGNED_STATEMENT_DIGEST_MISMATCH")
    if signature_verification.get("attestor_is_benchmark_owner_or_authorized_operator") is not True:
        raise OwnerAttestationError("ATTESTOR_AUTHORITY_NOT_VERIFIED")
    if signature_verification.get("identity_verified") is not True:
        raise OwnerAttestationError("ATTESTOR_IDENTITY_NOT_VERIFIED")
    _hex(signature_verification.get("verification_receipt_sha256"), 64, "SIGNATURE_VERIFICATION_RECEIPT_SHA256")

    subject = _one_subject(statement)

    predicate = statement.get("predicate")
    if not isinstance(predicate, Mapping):
        raise OwnerAttestationError("PREDICATE_INVALID")
    if predicate.get("benchmark") != EXPECTED_BENCHMARK:
        raise OwnerAttestationError("PREDICATE_BENCHMARK_MISMATCH")
    if predicate.get("target_model") != EXPECTED_MODEL:
        raise OwnerAttestationError("PREDICATE_TARGET_MODEL_MISMATCH")
    if predicate.get("target_observed_date") != observed_date:
        raise OwnerAttestationError("PREDICATE_EPOCH_MISMATCH")
    if predicate.get("grading_protocol_manifest_git_blob_sha") != EXPECTED_GRADING_PROTOCOL_BLOB_SHA:
        raise OwnerAttestationError("GRADING_PROTOCOL_DRIFT")
    if predicate.get("task_count") != EXPECTED_TASK_COUNT:
        raise OwnerAttestationError("TASK_COUNT_MISMATCH")

    _hex(predicate.get("private_task_population_sha256"), 64, "PRIVATE_TASK_POPULATION_SHA256")
    _hex(predicate.get("load_bearing_check_population_sha256"), 64, "CHECK_POPULATION_SHA256")
    _hex(predicate.get("opus_reference_subject_sha256"), 64, "OPUS_REFERENCE_SUBJECT_SHA256")

    if predicate.get("private_scope_complete") is not True:
        raise OwnerAttestationError("PRIVATE_SCOPE_NOT_COMPLETE")
    if predicate.get("all_load_bearing_checks_included") is not True:
        raise OwnerAttestationError("CHECK_SCOPE_NOT_COMPLETE")
    if predicate.get("brain_weakly_dominates_current_opus55") is not True:
        raise OwnerAttestationError("NONINFERIORITY_NOT_ATTESTED")
    if predicate.get("official_owner_elo_claimed") is not False:
        raise OwnerAttestationError("DIRECT_ATTESTATION_MUST_NOT_CLAIM_OFFICIAL_ELO")
    if predicate.get("historical_1822_epoch_rewritten") is not False:
        raise OwnerAttestationError("HISTORICAL_EPOCH_REWRITE_FORBIDDEN")

    material = {
        "schema": SCHEMA,
        "status": "PASS_MINIMAL_OWNER_ATTESTATION",
        "subject_sha256": subject["digest"]["sha256"],
        "target_observed_date": observed_date,
        "current_owner_reference_elo_context_only": reference,
        "private_task_population_sha256": predicate["private_task_population_sha256"],
        "load_bearing_check_population_sha256": predicate["load_bearing_check_population_sha256"],
        "opus_reference_subject_sha256": predicate["opus_reference_subject_sha256"],
        "scope_complete_current_epoch_noninferiority": True,
        "private_task_or_check_contents_required_for_brain_verification": False,
        "numeric_elo_reconstruction_required": False,
        "official_owner_elo_claimed": False,
        "historical_1822_epoch_rewritten": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
    }
    return {**material, "verdict_sha256": _sha256(material)}
