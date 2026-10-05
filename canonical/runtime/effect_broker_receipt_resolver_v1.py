"""Fail-closed byte resolver for Project Brain effect-broker receipts.

This module deliberately does *not* claim that a verified JSON receipt is true.
It establishes the narrower prerequisite that the receipt exists at the declared
canonical repository path and that its exact bytes match the declared Git blob
object ID. Semantic/objective verification remains schema-specific and must be
performed before an effect carrier treats any precommit verdict as authority.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

MAX_RECEIPT_BYTES = 8_000_000


class ReceiptResolutionError(ValueError):
    pass


def _repo_relative_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\x00" in value or "\\\\" in value:
        raise ReceiptResolutionError("RECEIPT_PATH_INVALID")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ReceiptResolutionError("RECEIPT_PATH_NOT_CANONICAL_RELATIVE")
    return path


def _expected_blob_id(data: bytes, declared: str) -> str:
    if not isinstance(declared, str):
        raise ReceiptResolutionError("RECEIPT_BLOB_ID_INVALID")
    payload = f"blob {len(data)}\\0".encode("ascii") + data
    if len(declared) == 40:
        return hashlib.sha1(payload).hexdigest()
    if len(declared) == 64:
        return hashlib.sha256(payload).hexdigest()
    raise ReceiptResolutionError("RECEIPT_BLOB_ID_LENGTH_UNSUPPORTED")


def resolve_receipt_bytes(reference: Mapping[str, Any], *, repo_root: str | Path) -> dict[str, Any]:
    """Resolve one receipt reference against exact repository bytes.

    Required reference keys are only ``path`` and ``git_blob_sha``. Extra keys
    are ignored by this resolver because semantic claims belong to a separate,
    schema-specific verifier rather than to the byte-existence layer.
    """
    if not isinstance(reference, Mapping):
        raise ReceiptResolutionError("RECEIPT_REFERENCE_INVALID")
    rel = _repo_relative_path(reference.get("path"))
    declared = reference.get("git_blob_sha")

    root = Path(repo_root).resolve(strict=True)
    lexical = root.joinpath(*rel.parts)

    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ReceiptResolutionError("RECEIPT_PATH_SYMLINK_REJECTED")

    try:
        resolved = lexical.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ReceiptResolutionError("RECEIPT_PATH_NOT_FOUND") from exc
    if resolved != root and root not in resolved.parents:
        raise ReceiptResolutionError("RECEIPT_PATH_ESCAPES_REPOSITORY")
    if not resolved.is_file():
        raise ReceiptResolutionError("RECEIPT_PATH_NOT_FILE")

    data = resolved.read_bytes()
    if len(data) > MAX_RECEIPT_BYTES:
        raise ReceiptResolutionError("RECEIPT_TOO_LARGE")
    actual_blob = _expected_blob_id(data, declared)
    if actual_blob != declared:
        raise ReceiptResolutionError("RECEIPT_GIT_BLOB_MISMATCH")

    try:
        document = json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise ReceiptResolutionError("RECEIPT_JSON_INVALID") from exc
    if not isinstance(document, dict):
        raise ReceiptResolutionError("RECEIPT_JSON_NOT_OBJECT")

    return {
        "path": rel.as_posix(),
        "git_blob_sha": declared,
        "byte_sha256": hashlib.sha256(data).hexdigest(),
        "byte_length": len(data),
        "schema": document.get("schema"),
        "document": document,
    }


def verify_receipt_pair_bytes(grant: Mapping[str, Any], *, repo_root: str | Path) -> dict[str, Any]:
    """Resolve both current broker receipt references, failing closed on either."""
    if not isinstance(grant, Mapping):
        raise ReceiptResolutionError("GRANT_INVALID")
    authority = resolve_receipt_bytes(grant.get("authority_receipt"), repo_root=repo_root)
    composition = resolve_receipt_bytes(grant.get("composition_receipt"), repo_root=repo_root)
    return {
        "status": "RECEIPT_BYTES_VERIFIED",
        "authority": {k: authority[k] for k in ("path", "git_blob_sha", "byte_sha256", "byte_length", "schema")},
        "composition": {k: composition[k] for k in ("path", "git_blob_sha", "byte_sha256", "byte_length", "schema")},
        "semantic_verification_still_required": True,
        "effect_carrier_enforcement_still_required": True,
        "acceptance_credit_delta": 0,
    }
