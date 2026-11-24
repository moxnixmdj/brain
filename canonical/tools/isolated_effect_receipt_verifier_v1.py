"""Experimental byte-level receipt verifier; NOT an execution or admission authority.

The expected receipt digest, base and policy must be obtained independently from a
trusted collector/reviewer. Passing a digest supplied by an untrusted worker proves
nothing. This module does not launch a carrier, collect effects, authenticate a
collector, approve a patch, or modify any front-door execution path.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_ISOLATED_EFFECT_RECEIPT_EXPERIMENT_V1"
MAX_EFFECT_BYTES = 8_000_000
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


class ReceiptRefused(ValueError):
    pass


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def receipt_digest(receipt: Mapping[str, Any]) -> str:
    return digest_bytes(json.dumps(receipt, sort_keys=True, separators=(",", ":"),
                                   ensure_ascii=True, allow_nan=False).encode("ascii"))


def _path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ReceiptRefused("EFFECT_PATH_INVALID")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(p in (".", "..") for p in value.split("/")):
        raise ReceiptRefused("EFFECT_PATH_INVALID")
    return value


def verify_patch(receipt: Mapping[str, Any], effect_bytes: Mapping[str, bytes], *,
                 expected_receipt_sha256: str, expected_base_commit: str,
                 expected_policy_sha256: str, expected_patch_path: str,
                 expected_effect_paths: tuple[str, ...]) -> bytes:
    """Return exact verified patch bytes or raise ReceiptRefused.

    Integrity only: trusted caller must bind all expectations to independent
    provenance. No authenticity, isolation, applicability, task success, or
    publication is inferred. The independently supplied path set must include
    exactly one designated patch effect.
    """
    try:
        if not isinstance(receipt, Mapping) or set(receipt) != {"schema", "base_commit", "policy_sha256", "effects"}:
            raise ReceiptRefused("RECEIPT_SHAPE_INVALID")
        if receipt["schema"] != SCHEMA:
            raise ReceiptRefused("RECEIPT_SCHEMA_INVALID")
        if not isinstance(expected_receipt_sha256, str) or not _DIGEST.fullmatch(expected_receipt_sha256):
            raise ReceiptRefused("TRUSTED_RECEIPT_DIGEST_INVALID")
        if receipt_digest(receipt) != expected_receipt_sha256:
            raise ReceiptRefused("RECEIPT_DIGEST_MISMATCH")
        if not isinstance(expected_base_commit, str) or not _COMMIT.fullmatch(expected_base_commit):
            raise ReceiptRefused("TRUSTED_BASE_INVALID")
        if receipt["base_commit"] != expected_base_commit:
            raise ReceiptRefused("BASE_COMMIT_MISMATCH")
        if not isinstance(expected_policy_sha256, str) or not _DIGEST.fullmatch(expected_policy_sha256):
            raise ReceiptRefused("TRUSTED_POLICY_INVALID")
        if receipt["policy_sha256"] != expected_policy_sha256:
            raise ReceiptRefused("POLICY_MISMATCH")
        path = _path(expected_patch_path)
        if not isinstance(expected_effect_paths, tuple) or not expected_effect_paths:
            raise ReceiptRefused("TRUSTED_EFFECT_SET_INVALID")
        paths = [_path(p) for p in expected_effect_paths]
        if len(set(paths)) != len(paths) or path not in paths:
            raise ReceiptRefused("TRUSTED_EFFECT_SET_INVALID")
        effects = receipt["effects"]
        if not isinstance(effects, Mapping) or set(effects) != set(paths):
            raise ReceiptRefused("EFFECT_SET_MISMATCH")
        if not isinstance(effect_bytes, Mapping) or set(effect_bytes) != set(paths):
            raise ReceiptRefused("EFFECT_SET_MISMATCH")
        total = 0
        for name in paths:
            metadata, data = effects[name], effect_bytes[name]
            if not isinstance(metadata, Mapping) or set(metadata) != {"sha256", "size"}:
                raise ReceiptRefused("EFFECT_METADATA_INVALID")
            if not isinstance(data, bytes):
                raise ReceiptRefused("EFFECT_BYTES_INVALID")
            total += len(data)
            if total > MAX_EFFECT_BYTES or (name == path and not data):
                raise ReceiptRefused("EFFECT_BYTES_INVALID")
            if type(metadata["size"]) is not int or metadata["size"] != len(data):
                raise ReceiptRefused("EFFECT_SIZE_MISMATCH")
            if not isinstance(metadata["sha256"], str) or not _DIGEST.fullmatch(metadata["sha256"]):
                raise ReceiptRefused("EFFECT_DIGEST_INVALID")
            if digest_bytes(data) != metadata["sha256"]:
                raise ReceiptRefused("EFFECT_DIGEST_MISMATCH")
        return effect_bytes[path]
    except ReceiptRefused:
        raise
    except (TypeError, ValueError, KeyError, UnicodeError, OverflowError) as exc:
        raise ReceiptRefused("RECEIPT_INVALID") from exc
