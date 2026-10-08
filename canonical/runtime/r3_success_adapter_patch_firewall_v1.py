"""Fail-closed source-write firewall for R3 success-adapter patch candidates.

This module is deliberately not an author, verifier, promoter, or acceptance judge.
It can atomically replace exactly one already-owned success-adapter source file when
the candidate is bound to the current base bytes and all verification-authority
files remain byte-identical.
"""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_PATCH_FIREWALL_V1"

ALLOWED_TARGETS = frozenset({
    "canonical/runtime/r3_bound_success_adapter_v1.py",
    "canonical/runtime/r3_raw_success_adapter_v1.py",
})

IMMUTABLE_VERIFICATION_PATHS = (
    "canonical/runtime/r3_independent_learning_verifier_v1.py",
    "canonical/runtime/r3_bound_success_checkpoint_verifier_v1.py",
    "canonical/runtime/r3_raw_success_checkpoint_verifier_v1.py",
)

MAX_SOURCE_BYTES = 256 * 1024


class AdapterPatchFirewallError(ValueError):
    pass


def _digest_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "source_patch_execution_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _resolve_owned_file(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise AdapterPatchFirewallError("PATH_INVALID:" + relative)
    target = (root / rel).resolve(strict=True)
    target.relative_to(root)
    if not target.is_file() or target.is_symlink():
        raise AdapterPatchFirewallError("TARGET_NOT_REGULAR_OWNED_FILE:" + relative)
    return target


def _verification_snapshot(root: Path) -> dict[str, str]:
    return {
        relative: _digest_bytes(_resolve_owned_file(root, relative).read_bytes())
        for relative in IMMUTABLE_VERIFICATION_PATHS
    }


def validate_candidate(
    candidate: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        if not isinstance(candidate, Mapping):
            return _fail("CANDIDATE_NOT_OBJECT")
        if candidate.get("schema") != "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_PATCH_CANDIDATE_V1":
            return _fail("CANDIDATE_SCHEMA_INVALID")
        if candidate.get("candidate_only") is not True:
            return _fail("CANDIDATE_ONLY_REQUIRED")
        for key in (
            "verification_authority",
            "promotion_authority",
            "acceptance_authority",
            "terminal_authority",
        ):
            if candidate.get(key) is not False:
                return _fail("CANDIDATE_AUTHORITY_FIREWALL_REQUIRED:" + key)

        relative = str(candidate.get("path") or "").strip()
        if relative not in ALLOWED_TARGETS:
            return _fail("TARGET_PATH_OUTSIDE_SUCCESS_ADAPTER_ALLOWLIST")

        content = candidate.get("content")
        if not isinstance(content, str) or not content.strip():
            return _fail("CANDIDATE_SOURCE_REQUIRED")
        raw = content.encode("utf-8")
        if len(raw) > MAX_SOURCE_BYTES:
            return _fail("CANDIDATE_SOURCE_TOO_LARGE")
        expected_content_sha = str(candidate.get("content_sha256") or "").strip()
        actual_content_sha = _digest_bytes(raw)
        if expected_content_sha != actual_content_sha:
            return _fail(
                "CANDIDATE_CONTENT_DIGEST_MISMATCH",
                expected_content_sha256=expected_content_sha or None,
                actual_content_sha256=actual_content_sha,
            )

        root = Path(repo_root).resolve(strict=True)
        target = _resolve_owned_file(root, relative)
        current = target.read_bytes()
        current_sha = _digest_bytes(current)
        expected_base_sha = str(candidate.get("base_sha256") or "").strip()
        if expected_base_sha != current_sha:
            return _fail(
                "CANDIDATE_BASE_DRIFT",
                expected_base_sha256=expected_base_sha or None,
                actual_base_sha256=current_sha,
            )

        try:
            compile(content, relative, "exec", dont_inherit=True)
        except Exception as exc:
            return _fail(
                "CANDIDATE_SOURCE_SYNTAX_INVALID",
                syntax_error=type(exc).__name__ + ":" + str(exc),
            )

        verification_before = _verification_snapshot(root)
        return {
            "schema": SCHEMA,
            "status": "PASS__CANDIDATE_PATCH_ADMISSIBLE",
            "pass": True,
            "path": relative,
            "base_sha256": current_sha,
            "content_sha256": actual_content_sha,
            "content_bytes": len(raw),
            "verification_authority_snapshot": verification_before,
            "source_patch_execution_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def apply_candidate(
    candidate: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    validation = validate_candidate(candidate, repo_root=repo_root)
    if validation.get("pass") is not True:
        return validation

    root = Path(repo_root).resolve(strict=True)
    relative = str(validation["path"])
    target = _resolve_owned_file(root, relative)
    old_bytes = target.read_bytes()
    old_mode = target.stat().st_mode & 0o777
    content = str(candidate["content"])
    new_bytes = content.encode("utf-8")
    verification_before = dict(validation["verification_authority_snapshot"])
    tmp = target.with_name(target.name + ".candidate.tmp")

    try:
        tmp.write_bytes(new_bytes)
        os.chmod(tmp, old_mode)
        if _digest_bytes(tmp.read_bytes()) != validation["content_sha256"]:
            raise AdapterPatchFirewallError("TEMPORARY_WRITE_DIGEST_MISMATCH")
        os.replace(tmp, target)

        after_target_sha = _digest_bytes(target.read_bytes())
        if after_target_sha != validation["content_sha256"]:
            raise AdapterPatchFirewallError("INSTALLED_TARGET_DIGEST_MISMATCH")

        verification_after = _verification_snapshot(root)
        if verification_after != verification_before:
            target.write_bytes(old_bytes)
            os.chmod(target, old_mode)
            return _fail(
                "VERIFICATION_AUTHORITY_CHANGED_DURING_PATCH",
                path=relative,
                target_rolled_back=True,
                verification_authority_before=verification_before,
                verification_authority_after=verification_after,
            )

        return {
            "schema": SCHEMA,
            "status": "PASS__CANDIDATE_ADAPTER_PATCH_APPLIED__AWAITING_INDEPENDENT_VERIFICATION",
            "pass": True,
            "path": relative,
            "base_sha256": validation["base_sha256"],
            "content_sha256": validation["content_sha256"],
            "verification_authority_before": verification_before,
            "verification_authority_after": verification_after,
            "verification_authority_unchanged": True,
            "candidate_installed_only": True,
            "independent_verification_required": True,
            "original_success_replay_required": True,
            "source_patch_execution_authority": True,
            "verification_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        if tmp.exists():
            tmp.unlink()
        if target.read_bytes() != old_bytes:
            target.write_bytes(old_bytes)
            os.chmod(target, old_mode)
        return _fail(
            "PATCH_APPLICATION_EXCEPTION:" + type(exc).__name__ + ":" + str(exc),
            path=relative,
            target_rolled_back=True,
        )
