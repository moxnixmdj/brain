#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import os
import pathlib
import struct
import tempfile
from dataclasses import dataclass
from typing import Any, BinaryIO, Mapping

SCHEMA = "PROJECT_BRAIN_TYPED_PARENT_FINALIZER_V1"
FRAME_SCHEMA = "PROJECT_BRAIN_TYPED_ARTIFACT_FRAME_V1"
MAX_HEADER = 65536

class FinalizerError(ValueError):
    pass

@dataclass(frozen=True)
class Declaration:
    artifact_id: str
    destination: str
    max_bytes: int
    media_type: str

def _read_exact(r: BinaryIO, n: int) -> bytes:
    chunks = []
    left = n
    while left:
        b = r.read(left)
        if not b:
            raise FinalizerError("TRUNCATED_FRAME")
        chunks.append(b)
        left -= len(b)
    return b"".join(chunks)

def _valid_final_authorization(auth: Mapping[str, Any], effect_request_sha256: str) -> bool:
    return (
        isinstance(auth, Mapping)
        and auth.get("allowed") is True
        and auth.get("status") == "ALLOW_FINAL_AUTHORIZATION"
        and auth.get("canonical_request_sha256") == effect_request_sha256
        and isinstance(auth.get("authorization_sha256"), str)
        and len(auth["authorization_sha256"]) == 64
    )

def finalize_one(
    r: BinaryIO,
    declarations: Mapping[str, Declaration],
    final_authorization: Mapping[str, Any],
) -> dict[str, Any]:
    (header_len,) = struct.unpack(">I", _read_exact(r, 4))
    if not (2 <= header_len <= MAX_HEADER):
        raise FinalizerError("HEADER_LENGTH_INVALID")
    header = json.loads(_read_exact(r, header_len).decode("utf-8"))
    if not isinstance(header, dict) or header.get("schema") != FRAME_SCHEMA:
        raise FinalizerError("HEADER_SCHEMA_INVALID")
    required = {
        "schema",
        "artifact_id",
        "size",
        "sha256",
        "media_type",
        "effect_request_sha256",
    }
    if set(header) != required:
        raise FinalizerError("HEADER_FIELD_SET_INVALID")

    artifact_id = header["artifact_id"]
    if artifact_id not in declarations:
        raise FinalizerError("ARTIFACT_NOT_PREDECLARED")
    decl = declarations[artifact_id]
    size = header["size"]
    if not isinstance(size, int) or size < 0 or size > decl.max_bytes:
        raise FinalizerError("SIZE_INVALID")
    if header["media_type"] != decl.media_type:
        raise FinalizerError("MEDIA_TYPE_MISMATCH")
    if not isinstance(header["sha256"], str) or len(header["sha256"]) != 64:
        raise FinalizerError("SHA256_INVALID")
    effect_sha = header["effect_request_sha256"]
    if not isinstance(effect_sha, str) or len(effect_sha) != 64:
        raise FinalizerError("EFFECT_REQUEST_SHA256_INVALID")
    if not _valid_final_authorization(final_authorization, effect_sha):
        raise FinalizerError("FINAL_AUTHORIZATION_INVALID")

    dest = pathlib.Path(decl.destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".brain-finalize-", dir=str(dest.parent))
    h = hashlib.sha256()
    remaining = size
    try:
        with os.fdopen(fd, "wb", closefd=True) as w:
            while remaining:
                chunk = r.read(min(65536, remaining))
                if not chunk:
                    raise FinalizerError("TRUNCATED_PAYLOAD")
                if len(chunk) > remaining:
                    chunk = chunk[:remaining]
                w.write(chunk)
                h.update(chunk)
                remaining -= len(chunk)
            w.flush()
            os.fsync(w.fileno())

        actual = h.hexdigest()
        if actual != header["sha256"]:
            raise FinalizerError("PAYLOAD_SHA256_MISMATCH")
        tail = r.read(1)
        if tail not in (b"", None):
            raise FinalizerError("TRAILING_BYTES_FORBIDDEN")

        os.replace(tmp, dest)
        dfd = os.open(str(dest.parent), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise

    return {
        "schema": SCHEMA,
        "status": "COMMITTED_TYPED_ARTIFACT",
        "artifact_id": artifact_id,
        "destination": str(dest),
        "size": size,
        "sha256": actual,
        "media_type": decl.media_type,
        "effect_request_sha256": effect_sha,
        "authorization_sha256": final_authorization["authorization_sha256"],
        "acceptance_credit_delta": 0,
    }
