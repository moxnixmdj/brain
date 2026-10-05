"""Fail-closed byte resolver for Project Brain effect-broker receipts.

V2 verifies the declared Git blob object ID against the exact bytes at the
canonical repository-relative path. It proves byte identity/existence only;
schema-specific semantic/objective verification and carrier enforcement remain
separate mandatory gates.
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
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ReceiptResolutionError("RECEIPT_PATH_INVALID")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ReceiptResolutionError("RECEIPT_PATH_NOT_CANONICAL_RELATIVE")
    return path


def git_blob_id(data: bytes, *, object_format: str) -> str:
    payload = f"blob {len(data)}\0".encode("ascii") + data
    if object_format == "sha1":
        return hashlib.sha1(payload).hexdigest()
    if object_format == "sha256":
        return hashlib.sha256(payload).hexdigest()
    raise ReceiptResolutionError("GIT_OBJECT_FORMAT_UNSUPPORTED")


def _expected_blob_id(data: bytes, declared: Any) -> str:
    if not isinstance(declared, str):
        raise ReceiptResolutionError("RECEIPT_BLOB_ID_INVALID")
    if len(declared) == 40:
        return git_blob_id(data, object_format="sha1")
    if len(declared) == 64:
        return git_blob_id(data, object_format="sha256")
    raise ReceiptResolutionError("RECEIPT_BLOB_ID_LENGTH_UNSUPPORTED")


def resolve_receipt_bytes(reference: Mapping[str, Any], *, repo_root: str | Path) -> dict[str, Any]:
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
    if not isinstance(grant, Mapping):
        raise ReceiptResolutionError("GRANT_INVALID")
    authority = resolve_receipt_bytes(grant.get("authority_receipt"), repo_root=repo_root)
    composition = resolve_receipt_bytes(grant.get("composition_receipt"), repo_root=repo_root)
    keys = ("path", "git_blob_sha", "byte_sha256", "byte_length", "schema")
    return {
        "status": "RECEIPT_BYTES_VERIFIED",
        "authority": {key: authority[key] for key in keys},
        "composition": {key: composition[key] for key in keys},
        "semantic_verification_still_required": True,
        "effect_carrier_enforcement_still_required": True,
        "acceptance_credit_delta": 0,
    }
