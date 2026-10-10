"""Minimal content-addressed authority kernel for exact goal->decision bindings.

Extracted from the already-live General Adequate Decision Controller so callers
that need only authenticated goal/decision identity do not import the controller's
entire policy-cover and solver dependency cone.

This module creates no semantic interpretation, policy adequacy, execution,
quality, acceptance, promotion, or terminal authority.  It only authenticates an
already-produced binding and its independent verification against exact bytes.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

GOAL_BINDING_SCHEMA = "PROJECT_BRAIN_GOAL_TO_DECISION_CONTEXT_BINDING_V1"
GOAL_BINDING_VERIFY_SCHEMA = (
    "PROJECT_BRAIN_GOAL_TO_DECISION_CONTEXT_BINDING_INDEPENDENT_VERIFICATION_V1"
)


class GoalBindingAuthorityError(ValueError):
    pass


def canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return "sha256:" + sha256(canon(value).encode("utf-8")).hexdigest()


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def bound_json(
    ref: Mapping[str, Any],
    *,
    repo_root: Path,
    prefixes: tuple[str, ...],
) -> tuple[dict[str, Any], str, str]:
    if not isinstance(ref, Mapping):
        raise GoalBindingAuthorityError("BOUND_REF_REQUIRED")
    rel = str(ref.get("path") or "").strip()
    expected = str(ref.get("git_blob_sha") or "").strip()
    p = Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        raise GoalBindingAuthorityError("BOUND_PATH_INVALID")
    if not any(rel.startswith(prefix) for prefix in prefixes):
        raise GoalBindingAuthorityError("BOUND_PATH_OUTSIDE_ALLOWED_SCOPE")
    base = repo_root.resolve(strict=True)
    full = base / p
    if any(
        part.is_symlink()
        for part in [full, *full.parents]
        if part != base and base in part.parents
    ):
        raise GoalBindingAuthorityError("BOUND_SYMLINK_FORBIDDEN:" + rel)
    resolved = full.resolve(strict=False)
    if not any(
        resolved.is_relative_to((base / prefix).resolve(strict=False))
        for prefix in prefixes
    ):
        raise GoalBindingAuthorityError("BOUND_RESOLVED_PATH_OUTSIDE_ALLOWED_SCOPE")
    if not full.is_file():
        raise GoalBindingAuthorityError("BOUND_FILE_MISSING:" + rel)
    actual = git_blob_sha(full)
    if expected != actual:
        raise GoalBindingAuthorityError("BOUND_BLOB_DRIFT:" + rel)
    doc = json.loads(full.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise GoalBindingAuthorityError("BOUND_JSON_NOT_OBJECT:" + rel)
    return doc, rel, actual


def authenticate_goal_binding(
    binding: Mapping[str, Any] | None,
    *,
    goal: str,
    decision_payload: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        return {"pass": False, "status": "OPEN__GOAL_TO_DECISION_BINDING_REQUIRED"}
    try:
        receipt, receipt_path, receipt_blob = bound_json(
            binding.get("receipt"),
            repo_root=repo_root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification, verification_path, verification_blob = bound_json(
            binding.get("verification"),
            repo_root=repo_root,
            prefixes=("canonical/verification/",),
        )
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        decision_sha = digest(decision_payload)
        if receipt.get("schema") != GOAL_BINDING_SCHEMA:
            raise GoalBindingAuthorityError("GOAL_BINDING_SCHEMA_INVALID")
        if receipt.get("goal_sha256") != goal_sha:
            raise GoalBindingAuthorityError("GOAL_BINDING_GOAL_MISMATCH")
        if receipt.get("decision_payload_sha256") != decision_sha:
            raise GoalBindingAuthorityError("GOAL_BINDING_DECISION_MISMATCH")
        for field in (
            "binding_proved",
            "load_bearing_constraints_preserved",
            "decision_context_semantically_sufficient",
        ):
            if receipt.get(field) is not True:
                raise GoalBindingAuthorityError(
                    "GOAL_BINDING_PREMISE_UNPROVED:" + field
                )
        if verification.get("schema") != GOAL_BINDING_VERIFY_SCHEMA:
            raise GoalBindingAuthorityError("GOAL_BINDING_VERIFY_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise GoalBindingAuthorityError("GOAL_BINDING_VERIFY_SUBJECT_MISMATCH")
        if verification.get("goal_sha256") != goal_sha:
            raise GoalBindingAuthorityError("GOAL_BINDING_VERIFY_GOAL_MISMATCH")
        if verification.get("decision_payload_sha256") != decision_sha:
            raise GoalBindingAuthorityError("GOAL_BINDING_VERIFY_DECISION_MISMATCH")
        for field in ("pass", "independent_verified", "semantic_preservation_verified"):
            if verification.get(field) is not True:
                raise GoalBindingAuthorityError(
                    "GOAL_BINDING_VERIFY_PREMISE_UNPROVED:" + field
                )
        return {
            "pass": True,
            "status": "PASS__GOAL_TO_DECISION_CONTEXT_AUTHENTICATED",
            "goal_sha256": goal_sha,
            "decision_payload_sha256": decision_sha,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verification_path,
            "verification_git_blob_sha": verification_blob,
        }
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__GOAL_TO_DECISION_BINDING_INVALID",
            "reason": type(exc).__name__ + ":" + str(exc),
        }
