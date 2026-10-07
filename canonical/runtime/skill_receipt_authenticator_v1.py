"""Content-addressed parsing boundary for Universal Learning V7 skill receipts.

This module can prove exact repository bytes, schema consistency, subject binding,
and that declared public-runner provenance is syntactically well formed.

It cannot prove from repository-authored JSON alone that the named workflow run,
job, artifact, digest, execution head, or verifier actually existed and produced
the declared result. Shape-valid provenance is not authenticated provenance.

Therefore V1 deliberately fails closed before returning independent_verified=True.
Reusable skill promotion must use a future boundary that verifies an independent
execution/attestation against a trust source outside the receipt author's control.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import re

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes

SCHEMA = "PROJECT_BRAIN_SKILL_RECEIPT_AUTHENTICATOR_V1"
EPISODE_SCHEMA = "PROJECT_BRAIN_SKILL_EPISODE_RECEIPT_V1"
EPISODE_VERIFY_SCHEMA = "PROJECT_BRAIN_SKILL_EPISODE_INDEPENDENT_VERIFICATION_V1"
CANDIDATE_SCHEMA = "PROJECT_BRAIN_SKILL_CANDIDATE_RECEIPT_V1"
CANDIDATE_VERIFY_SCHEMA = "PROJECT_BRAIN_SKILL_CANDIDATE_INDEPENDENT_VERIFICATION_V1"
RELATIONS = {"EXACT", "PROVEN_SUPERSET"}
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
PUBLIC_RUNNER_REPOSITORY = "moxnixmdj/verification-capsule-runner"


class SkillReceiptError(ValueError):
    pass


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SkillReceiptError(label + "_INVALID")
    return value.strip()


def _public_runner_provenance(doc: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    pr = doc.get("public_runner")
    if not isinstance(pr, Mapping):
        raise SkillReceiptError(label + "_PUBLIC_RUNNER_PROVENANCE_MISSING")
    if pr.get("repository") != PUBLIC_RUNNER_REPOSITORY:
        raise SkillReceiptError(label + "_PUBLIC_RUNNER_REPOSITORY_INVALID")
    for key in ("workflow_run_id", "workflow_job_id", "artifact_id"):
        value = pr.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise SkillReceiptError(label + "_PUBLIC_RUNNER_" + key.upper() + "_INVALID")
    head = pr.get("execution_head_sha")
    if not isinstance(head, str) or _SHA40.fullmatch(head) is None:
        raise SkillReceiptError(label + "_PUBLIC_RUNNER_EXECUTION_HEAD_INVALID")
    digest = pr.get("artifact_digest")
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise SkillReceiptError(label + "_PUBLIC_RUNNER_ARTIFACT_DIGEST_INVALID")
    if pr.get("conclusion") != "success":
        raise SkillReceiptError(label + "_PUBLIC_RUNNER_NOT_SUCCESS")
    verifier_path = pr.get("verifier_path")
    verifier_blob = pr.get("verifier_git_blob_sha")
    if not isinstance(verifier_path, str) or not verifier_path.strip():
        raise SkillReceiptError(label + "_PUBLIC_RUNNER_VERIFIER_PATH_INVALID")
    if not isinstance(verifier_blob, str) or _SHA40.fullmatch(verifier_blob) is None:
        raise SkillReceiptError(label + "_PUBLIC_RUNNER_VERIFIER_BLOB_INVALID")
    return {
        "repository": PUBLIC_RUNNER_REPOSITORY,
        "workflow_run_id": pr["workflow_run_id"],
        "workflow_job_id": pr["workflow_job_id"],
        "execution_head_sha": head,
        "artifact_id": pr["artifact_id"],
        "artifact_digest": digest,
        "verifier_path": verifier_path.strip(),
        "verifier_git_blob_sha": verifier_blob,
    }


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
    _token(vd.get("verifier_id"), "EPISODE_VERIFIER_ID")
    _public_runner_provenance(vd, label="EPISODE")

    raise SkillReceiptError(
        "EPISODE_INDEPENDENCE_UNPROVED__DECLARED_RUNNER_PROVENANCE_NOT_AUTHENTICATED"
    )


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
    _token(vd.get("verifier_id"), "CANDIDATE_VERIFIER_ID")
    _public_runner_provenance(vd, label="CANDIDATE")

    raise SkillReceiptError(
        "CANDIDATE_INDEPENDENCE_UNPROVED__DECLARED_RUNNER_PROVENANCE_NOT_AUTHENTICATED"
    )
