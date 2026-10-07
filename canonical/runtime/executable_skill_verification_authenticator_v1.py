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
            "receipt_id": "SKVR:" + rr["git_blob_sha"],
        }
        verified = verify_candidate(
            candidate=candidate,
            verification_receipt=legacy,
        )
        return {
            "schema": SCHEMA,
            "status": "PASS__AUTHENTICATED_VERIFIED_EXECUTABLE_SKILL",
            "pass": True,
            "verified_skill": verified,
            "receipt": {"path": rr["path"], "git_blob_sha": rr["git_blob_sha"]},
            "verification": {"path": vr["path"], "git_blob_sha": vr["git_blob_sha"]},
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
