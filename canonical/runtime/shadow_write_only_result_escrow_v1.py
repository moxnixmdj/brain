#!/usr/bin/env python3
"""Write-only LiveBench evaluation-result escrow.

The candidate already knows the response it generated. The feedback channel that
must stay hidden is the evaluator result.  This module therefore serializes only
the frozen 200-row legacy-IFEval checker truth vector into a constant-size binary
record and encrypts it to a recipient certificate with OpenSSL CMS.

The collection side needs the PUBLIC certificate only.  It exposes no score,
pass count, checker truth, result hash, plaintext length, or result-derived
filename/exit surface.  Decryption is intentionally implemented in a separate
release module and requires a private key unavailable to the collection role.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import struct
import subprocess
import tempfile
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_SHADOW_WRITE_ONLY_RESULT_ESCROW_V1"
MAGIC = b"PB-LB-ESCROW-V1\0"
CASE_COUNT = 200
MAX_CHECKERS_PER_CASE = 8
ROW_BYTES = 2
PLAINTEXT_BYTES = 512
HEADER_BYTES = len(MAGIC) + 32
VECTOR_BYTES = CASE_COUNT * ROW_BYTES
PADDING_BYTES = PLAINTEXT_BYTES - HEADER_BYTES - VECTOR_BYTES
if PADDING_BYTES < 0:
    raise RuntimeError("ESCROW_LAYOUT_INVALID")


class ResultEscrowError(RuntimeError):
    pass


def _lease_bytes(lease_digest_sha256: str) -> bytes:
    s = str(lease_digest_sha256 or "").lower()
    if len(s) != 64 or any(c not in "0123456789abcdef" for c in s):
        raise ResultEscrowError("LEASE_DIGEST_SHA256_INVALID")
    return bytes.fromhex(s)


def escrow_object_name(lease_digest_sha256: str) -> str:
    _lease_bytes(lease_digest_sha256)
    return f"livebench-result-{lease_digest_sha256.lower()}.cms"


def encode_score_vector(
    rows: Iterable[Mapping[str, Any]],
    lease_digest_sha256: str,
    *,
    padding: bytes | None = None,
) -> bytes:
    items = list(rows)
    if len(items) != CASE_COUNT:
        raise ResultEscrowError(f"CASE_COUNT_MUST_EQUAL_{CASE_COUNT}")
    body = bytearray()
    for i, row in enumerate(items):
        count = row.get("checker_count")
        mask = row.get("passed_mask")
        if not isinstance(count, int) or isinstance(count, bool) or not (1 <= count <= MAX_CHECKERS_PER_CASE):
            raise ResultEscrowError(f"INVALID_CHECKER_COUNT_AT_{i}")
        if not isinstance(mask, int) or isinstance(mask, bool) or mask < 0 or mask >= (1 << count):
            raise ResultEscrowError(f"INVALID_PASSED_MASK_AT_{i}")
        body.extend((count, mask))
    pad = os.urandom(PADDING_BYTES) if padding is None else bytes(padding)
    if len(pad) != PADDING_BYTES:
        raise ResultEscrowError("INVALID_PADDING_LENGTH")
    out = MAGIC + _lease_bytes(lease_digest_sha256) + bytes(body) + pad
    if len(out) != PLAINTEXT_BYTES:
        raise ResultEscrowError("PLAINTEXT_GEOMETRY_DRIFT")
    return out


def _run_openssl_encrypt(
    *,
    plaintext_path: Path,
    recipient_cert_path: Path,
    ciphertext_path: Path,
    openssl_bin: str,
) -> None:
    cmd = [
        openssl_bin, "cms", "-encrypt", "-binary", "-aes256",
        "-outform", "DER",
        "-in", str(plaintext_path),
        "-out", str(ciphertext_path),
        "-recip", str(recipient_cert_path),
    ]
    proc = subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={"PATH": os.environ.get("PATH", "")},
    )
    if proc.returncode != 0:
        # Never propagate OpenSSL output because future implementations must not
        # accidentally admit result-derived diagnostics into the public surface.
        raise ResultEscrowError("PUBLIC_KEY_ENCRYPTION_FAILED")


def _zero_unlink(path: Path) -> None:
    try:
        size = path.stat().st_size
        with path.open("r+b", buffering=0) as fh:
            chunk = b"\x00" * min(65536, max(1, size))
            remaining = size
            while remaining:
                n = min(len(chunk), remaining)
                fh.write(chunk[:n])
                remaining -= n
            fh.flush()
            os.fsync(fh.fileno())
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def seal_score_vector(
    *,
    rows: Iterable[Mapping[str, Any]],
    lease_digest_sha256: str,
    recipient_cert_path: str | os.PathLike[str],
    sink_dir: str | os.PathLike[str],
    openssl_bin: str = "openssl",
) -> dict[str, Any]:
    """Encrypt one fixed 200-case score vector and atomically publish it.

    The returned receipt is deliberately result-independent.  In particular it
    contains no plaintext/ciphertext hash, score, count, branch, or condition.
    """
    cert = Path(recipient_cert_path)
    if not cert.is_file():
        raise ResultEscrowError("RECIPIENT_PUBLIC_CERT_REQUIRED")
    sink = Path(sink_dir)
    sink.mkdir(parents=True, exist_ok=True)
    object_name = escrow_object_name(lease_digest_sha256)
    final_path = sink / object_name

    plaintext = encode_score_vector(rows, lease_digest_sha256)
    with tempfile.TemporaryDirectory(prefix=".pb-escrow-", dir=str(sink)) as td:
        td_path = Path(td)
        plain_path = td_path / "plain.bin"
        cipher_path = td_path / "cipher.der"
        plain_path.write_bytes(plaintext)
        try:
            _run_openssl_encrypt(
                plaintext_path=plain_path,
                recipient_cert_path=cert,
                ciphertext_path=cipher_path,
                openssl_bin=openssl_bin,
            )
        finally:
            _zero_unlink(plain_path)

        # O_EXCL makes the escrow object one-use and non-replaceable.
        data = cipher_path.read_bytes()
        try:
            fd = os.open(final_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise ResultEscrowError("ESCROW_OBJECT_ALREADY_EXISTS") from exc
        try:
            with os.fdopen(fd, "wb", closefd=True) as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
        finally:
            try:
                cipher_path.unlink()
            except FileNotFoundError:
                pass

    # Public receipt: every field is determined by frozen protocol + lease +
    # recipient certificate geometry, never by checker outcomes.
    return {
        "schema": SCHEMA,
        "status": "OPAQUE_RESULT_ESCROW_COMMITTED",
        "lease_digest_sha256": lease_digest_sha256.lower(),
        "escrow_object_name": object_name,
        "frozen_case_count": CASE_COUNT,
        "fixed_plaintext_bytes": PLAINTEXT_BYTES,
        "ciphertext_bytes": final_path.stat().st_size,
        "encryption": "OPENSSL_CMS_AES256_TO_PUBLIC_X509_RECIPIENT",
        "recipient_private_key_present_or_required": False,
        "result_body_visible": False,
        "result_score_visible": False,
        "result_summary_visible": False,
        "result_hash_visible": False,
        "result_derived_public_field_count": 0,
        "release_authority": False,
        "acceptance_credit": False,
        "promotion_authority": False,
    }


def public_receipt_fingerprint(receipt: Mapping[str, Any]) -> str:
    """Protocol fingerprint for differential noninterference tests.

    This hashes the result-independent receipt only; it is not emitted by the
    production collector.
    """
    import json
    raw = json.dumps(dict(receipt), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()
