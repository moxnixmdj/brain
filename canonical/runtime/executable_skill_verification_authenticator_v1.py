"""Authenticate independent behavior-preservation verification for skill candidates.

A reusable executable skill may be produced only from:
- an internally deterministic candidate digest;
- a content-addressed candidate-verification receipt;
- a separate content-addressed independent-verification receipt binding the exact
  candidate digest, source episode ids, and claimed scope relation.

The output is passed through executable_skill_program_v7.verify_candidate using a
sanitized legacy receipt. Callers cannot gain reuse authority from a raw mapping.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)
from canonical.runtime.executable_skill_program_v7 import (
    RELATIONS,
    SUPERSET_SCOPE_PREDICATES,
    ExecutableSkillProgramError,
    verify_candidate,
)

SCHEMA = "PROJECT_BRAIN_EXECUTABLE_SKILL_VERIFICATION_AUTHENTICATOR_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_EXECUTABLE_SKILL_BEHAVIOR_VERIFICATION_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_EXECUTABLE_SKILL_INDEPENDENT_VERIFICATION_V1"


class SkillVerificationError(ValueError):
    pass


def authenticate_and_verify(
    candidate: Mapping[str, Any],
    binding: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        if not isinstance(candidate, Mapping):
            raise SkillVerificationError("SKILL_CANDIDATE_INVALID")
        if candidate.get("candidate_only") is not True:
            raise SkillVerificationError("SKILL_CANDIDATE_ONLY_REQUIRED")
        candidate_sha = candidate.get("candidate_sha256")
        source_ids = sorted(
            str(x) for x in candidate.get("source_episode_ids", [])
            if isinstance(x, str) and x
        )
        if not isinstance(candidate_sha, str) or not candidate_sha.startswith("sha256:"):
            raise SkillVerificationError("SKILL_CANDIDATE_SHA_INVALID")
        if not source_ids:
            raise SkillVerificationError("SKILL_SOURCE_EPISODES_REQUIRED")
        if not isinstance(binding, Mapping):
            raise SkillVerificationError("SKILL_VERIFICATION_BINDING_INVALID")

        rr = resolve_receipt_bytes(binding.get("receipt"), repo_root=repo_root)
        vr = resolve_receipt_bytes(binding.get("verification"), repo_root=repo_root)
        rd, vd = rr["document"], vr["document"]
        if rd.get("schema") != RECEIPT_SCHEMA:
            raise SkillVerificationError("SKILL_RECEIPT_SCHEMA_INVALID")
        if vd.get("schema") != VERIFY_SCHEMA:
            raise SkillVerificationError("SKILL_VERIFY_SCHEMA_INVALID")
        if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
            raise SkillVerificationError("SKILL_VERIFY_SUBJECT_MISMATCH")

        relation = rd.get("scope_relation")
        if relation not in RELATIONS:
            raise SkillVerificationError("SKILL_SCOPE_RELATION_INVALID")
        scope_predicate = str(rd.get("scope_predicate") or "").strip()
        if relation == "PROVEN_SUPERSET":
            if scope_predicate and scope_predicate not in SUPERSET_SCOPE_PREDICATES:
                raise SkillVerificationError("SKILL_SCOPE_PREDICATE_INVALID")
            verifier_scope_predicate = str(vd.get("scope_predicate") or "").strip()
            if verifier_scope_predicate != scope_predicate:
                raise SkillVerificationError("SKILL_SCOPE_PREDICATE_BINDING_MISMATCH")
        else:
            if scope_predicate or str(vd.get("scope_predicate") or "").strip():
                raise SkillVerificationError("EXACT_SCOPE_MAY_NOT_DECLARE_SUPERSET_PREDICATE")
        expected = {
            "candidate_sha256": candidate_sha,
            "source_episode_ids": source_ids,
            "scope_relation": relation,
        }
        for key, value in expected.items():
            if rd.get(key) != value:
                raise SkillVerificationError("SKILL_RECEIPT_BINDING_MISMATCH:" + key)
            if vd.get(key) != value:
                raise SkillVerificationError("SKILL_VERIFY_BINDING_MISMATCH:" + key)

        required_receipt = {
            "pass": True,
            "conclusion": "success",
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
        }
        for key, value in required_receipt.items():
            if rd.get(key) != value:
                raise SkillVerificationError("SKILL_RECEIPT_CLAIM_INVALID:" + key)

        required_verify = {
            "pass": True,
            "independent_verified": True,
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
            "candidate_reexecuted_or_equivalently_checked": True,
            "source_episode_lineage_reverified": True,
        }
        for key, value in required_verify.items():
            if vd.get(key) != value:
                raise SkillVerificationError("SKILL_VERIFY_CLAIM_INVALID:" + key)
        verifier_id = vd.get("independent_verifier_id")
        if not isinstance(verifier_id, str) or not verifier_id.strip():
            raise SkillVerificationError("SKILL_INDEPENDENT_VERIFIER_ID_MISSING")

        legacy = {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "candidate_sha256": candidate_sha,
            "source_episode_ids": source_ids,
            "behavior_preserving_on_claimed_scope": True,
            "scope_relation": relation,
            "scope_predicate": scope_predicate or None,
            "receipt_id": "SKVR:" + rr["git_blob_sha"],
        }
        verified = verify_candidate(
            candidate=candidate,
            verification_receipt=legacy,
        )
        receipt_ref = {"path": rr["path"], "git_blob_sha": rr["git_blob_sha"]}
        verification_ref = {"path": vr["path"], "git_blob_sha": vr["git_blob_sha"]}
        verified = {
            **verified,
            "verification_binding": {
                "receipt": receipt_ref,
                "verification": verification_ref,
            },
            "independent_verifier_id": verifier_id.strip(),
        }
        return {
            "schema": SCHEMA,
            "status": "PASS__AUTHENTICATED_VERIFIED_EXECUTABLE_SKILL",
            "pass": True,
            "verified_skill": verified,
            "receipt": receipt_ref,
            "verification": verification_ref,
            "independent_verifier_id": verifier_id.strip(),
            "terminal_authority": False,
        }
    except (Exception, ReceiptResolutionError, ExecutableSkillProgramError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "terminal_authority": False,
        }


def _candidate_from_verified_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise SkillVerificationError("VERIFIED_SKILL_RECORD_INVALID")
    candidate = dict(record)
    for key in (
        "scope_relation",
        "scope_predicate",
        "verification_receipt",
        "verification_binding",
        "independent_verifier_id",
        "verified_skill",
        "reuse_authorized",
        "candidate_only",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
        "promotion_authority",
        "execution_authority",
    ):
        candidate.pop(key, None)
    candidate["status"] = "EXECUTABLE_SKILL_CANDIDATE_ONLY"
    candidate["verified_skill"] = False
    candidate["reuse_authorized"] = False
    candidate["candidate_only"] = True
    return candidate


def reauthenticate_record(
    record: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Re-authenticate a durable verified skill against its exact receipt pair."""
    try:
        if not isinstance(record, Mapping):
            raise SkillVerificationError("VERIFIED_SKILL_RECORD_INVALID")
        if record.get("verified_skill") is not True or record.get("reuse_authorized") is not True:
            raise SkillVerificationError("VERIFIED_SKILL_RECORD_NOT_REUSABLE")
        binding = record.get("verification_binding")
        if not isinstance(binding, Mapping):
            raise SkillVerificationError("VERIFIED_SKILL_RECORD_BINDING_MISSING")
        candidate = _candidate_from_verified_record(record)
        verdict = authenticate_and_verify(
            candidate,
            binding,
            repo_root=repo_root,
        )
        if verdict.get("pass") is not True:
            raise SkillVerificationError(
                "VERIFIED_SKILL_RECORD_REAUTHENTICATION_FAILED:"
                + str(verdict.get("reason") or "UNKNOWN")
            )
        authenticated = verdict.get("verified_skill")
        if not isinstance(authenticated, Mapping):
            raise SkillVerificationError("VERIFIED_SKILL_RECORD_AUTHENTICATED_VALUE_MISSING")

        authority_fields = (
            "candidate_sha256",
            "source_episode_ids",
            "source_episode_receipts",
            "source_scopes",
            "steps",
            "preconditions",
            "postconditions",
            "invalidators",
            "scope_relation",
            "scope_predicate",
            "verification_receipt",
            "verified_skill",
            "reuse_authorized",
            "candidate_only",
        )
        for key in authority_fields:
            if record.get(key) != authenticated.get(key):
                raise SkillVerificationError(
                    "VERIFIED_SKILL_RECORD_AUTHORITY_FIELD_MISMATCH:" + key
                )
        return {
            "schema": SCHEMA,
            "status": "PASS__VERIFIED_SKILL_RECORD_REAUTHENTICATED",
            "pass": True,
            "verified_skill": dict(authenticated),
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "terminal_authority": False,
        }
