"""Content-addressed authentication for Universal Learning V7 skill receipts.

The underlying executable_skill_program_v7 API consumes receipt mappings. This
module is the hardened repository boundary: it resolves exact receipt bytes by Git
blob ID and requires a separate independent-verification receipt bound to the
subject blob.

Direct in-memory booleans are therefore insufficient for skill promotion.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes

SCHEMA = "PROJECT_BRAIN_SKILL_RECEIPT_AUTHENTICATOR_V1"
EPISODE_SCHEMA = "PROJECT_BRAIN_SKILL_EPISODE_RECEIPT_V1"
EPISODE_VERIFY_SCHEMA = "PROJECT_BRAIN_SKILL_EPISODE_INDEPENDENT_VERIFICATION_V1"
CANDIDATE_SCHEMA = "PROJECT_BRAIN_SKILL_CANDIDATE_RECEIPT_V1"
CANDIDATE_VERIFY_SCHEMA = "PROJECT_BRAIN_SKILL_CANDIDATE_INDEPENDENT_VERIFICATION_V1"
RELATIONS = {"EXACT", "PROVEN_SUPERSET"}


class SkillReceiptError(ValueError):
    pass


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SkillReceiptError(label + "_INVALID")
    return value.strip()


def authenticate_episode_receipt(
    references: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(references, Mapping):
        raise SkillReceiptError("REFERENCES_INVALID")
    subject = resolve_receipt_bytes(references.get("receipt"), repo_root=repo_root)
    verify = resolve_receipt_bytes(references.get("verification"), repo_root=repo_root)
    sd = subject["document"]
    vd = verify["document"]

    if sd.get("schema") != EPISODE_SCHEMA:
        raise SkillReceiptError("EPISODE_SCHEMA_INVALID")
    episode_id = _token(sd.get("episode_id"), "EPISODE_ID")
    scope_id = _token(sd.get("scope_id"), "SCOPE_ID")
    program_sha256 = _token(sd.get("program_sha256"), "PROGRAM_SHA256")
    if sd.get("behavior_verified") is not True or sd.get("conclusion") != "success":
        raise SkillReceiptError("EPISODE_SUBJECT_NOT_SUCCESS")

    if vd.get("schema") != EPISODE_VERIFY_SCHEMA:
        raise SkillReceiptError("EPISODE_VERIFY_SCHEMA_INVALID")
    if vd.get("subject_git_blob_sha") != subject["git_blob_sha"]:
        raise SkillReceiptError("EPISODE_VERIFY_SUBJECT_BLOB_MISMATCH")
    if vd.get("episode_id") != episode_id or vd.get("scope_id") != scope_id:
        raise SkillReceiptError("EPISODE_VERIFY_IDENTITY_MISMATCH")
    if vd.get("program_sha256") != program_sha256:
        raise SkillReceiptError("EPISODE_VERIFY_PROGRAM_MISMATCH")
    if vd.get("pass") is not True:
        raise SkillReceiptError("EPISODE_VERIFY_NOT_PASS")
    verifier_id = _token(vd.get("verifier_id"), "EPISODE_VERIFIER_ID")

    return {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "behavior_verified": True,
        "episode_id": episode_id,
        "scope_id": scope_id,
        "program_sha256": program_sha256,
        "receipt_id": subject["git_blob_sha"] + ":" + verify["git_blob_sha"],
        "subject_path": subject["path"],
        "subject_git_blob_sha": subject["git_blob_sha"],
        "verification_path": verify["path"],
        "verification_git_blob_sha": verify["git_blob_sha"],
        "verifier_id": verifier_id,
    }


def authenticate_candidate_receipt(
    references: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(references, Mapping):
        raise SkillReceiptError("REFERENCES_INVALID")
    subject = resolve_receipt_bytes(references.get("receipt"), repo_root=repo_root)
    verify = resolve_receipt_bytes(references.get("verification"), repo_root=repo_root)
    sd = subject["document"]
    vd = verify["document"]

    if sd.get("schema") != CANDIDATE_SCHEMA:
        raise SkillReceiptError("CANDIDATE_SCHEMA_INVALID")
    candidate_sha256 = _token(sd.get("candidate_sha256"), "CANDIDATE_SHA256")
    source_episode_ids = sd.get("source_episode_ids")
    if not isinstance(source_episode_ids, list) or not source_episode_ids:
        raise SkillReceiptError("SOURCE_EPISODE_IDS_INVALID")
    if any(not isinstance(x, str) or not x.strip() for x in source_episode_ids):
        raise SkillReceiptError("SOURCE_EPISODE_ID_INVALID")
    if len(source_episode_ids) != len(set(source_episode_ids)):
        raise SkillReceiptError("SOURCE_EPISODE_ID_DUPLICATE")
    if sd.get("behavior_preserving_on_claimed_scope") is not True:
        raise SkillReceiptError("CANDIDATE_BEHAVIOR_PRESERVATION_NOT_PROVED")
    relation = _token(sd.get("scope_relation"), "SCOPE_RELATION")
    if relation not in RELATIONS:
        raise SkillReceiptError("SCOPE_RELATION_NOT_ADMISSIBLE")
    if sd.get("conclusion") != "success":
        raise SkillReceiptError("CANDIDATE_SUBJECT_NOT_SUCCESS")

    if vd.get("schema") != CANDIDATE_VERIFY_SCHEMA:
        raise SkillReceiptError("CANDIDATE_VERIFY_SCHEMA_INVALID")
    if vd.get("subject_git_blob_sha") != subject["git_blob_sha"]:
        raise SkillReceiptError("CANDIDATE_VERIFY_SUBJECT_BLOB_MISMATCH")
    if vd.get("candidate_sha256") != candidate_sha256:
        raise SkillReceiptError("CANDIDATE_VERIFY_DIGEST_MISMATCH")
    if sorted(vd.get("source_episode_ids") or []) != sorted(source_episode_ids):
        raise SkillReceiptError("CANDIDATE_VERIFY_SOURCE_EPISODES_MISMATCH")
    if vd.get("scope_relation") != relation:
        raise SkillReceiptError("CANDIDATE_VERIFY_SCOPE_RELATION_MISMATCH")
    if vd.get("pass") is not True:
        raise SkillReceiptError("CANDIDATE_VERIFY_NOT_PASS")
    verifier_id = _token(vd.get("verifier_id"), "CANDIDATE_VERIFIER_ID")

    return {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "candidate_sha256": candidate_sha256,
        "source_episode_ids": sorted(source_episode_ids),
        "behavior_preserving_on_claimed_scope": True,
        "scope_relation": relation,
        "receipt_id": subject["git_blob_sha"] + ":" + verify["git_blob_sha"],
        "subject_path": subject["path"],
        "subject_git_blob_sha": subject["git_blob_sha"],
        "verification_path": verify["path"],
        "verification_git_blob_sha": verify["git_blob_sha"],
        "verifier_id": verifier_id,
    }
