#!/usr/bin/env python3
"""Fixed-size public-key result escrow for zero-case-safe shadow evaluation.

Security boundary:
- the execution process receives only a recipient public certificate;
- plaintext result bytes are accepted on stdin/in memory and never returned;
- output ciphertext has a fixed plaintext envelope size chosen pre-execution;
- the only returned receipt contains lease-bound opaque ciphertext metadata;
- raw OpenSSL stderr is never propagated.

This module intentionally contains no decrypt operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from typing import Any

SCHEMA = "PROJECT_BRAIN_SHADOW_WRITE_ONLY_ESCROW_RECEIPT_V1"
MAGIC = b"PBESCROWV1\x00\x00\x00\x00\x00\x00"
HEADER_BYTES = len(MAGIC) + 8 + 32
HEX = set("0123456789abcdef")


class EscrowError(RuntimeError):
    pass


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _valid_sha256(value: str) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value.lower()) <= HEX


def preflight(*, declared_max_result_bytes: int, fixed_envelope_bytes: int) -> dict[str, Any]:
    if declared_max_result_bytes < 0:
        raise EscrowError("INVALID_DECLARED_MAX_RESULT_BYTES")
    if fixed_envelope_bytes <= HEADER_BYTES:
        raise EscrowError("FIXED_ENVELOPE_TOO_SMALL")
    capacity = fixed_envelope_bytes - HEADER_BYTES
    if declared_max_result_bytes > capacity:
        raise EscrowError("DECLARED_RESULT_BOUND_EXCEEDS_ESCROW_CAPACITY")
    return {
        "schema": "PROJECT_BRAIN_SHADOW_WRITE_ONLY_ESCROW_PREFLIGHT_V1",
        "pass": True,
        "declared_max_result_bytes": declared_max_result_bytes,
        "fixed_envelope_bytes": fixed_envelope_bytes,
        "payload_capacity_bytes": capacity,
        "result_content_read": False,
    }


def _build_fixed_envelope(result: bytes, *, fixed_envelope_bytes: int) -> bytearray:
    capacity = fixed_envelope_bytes - HEADER_BYTES
    if len(result) > capacity:
        # Valid production runs must make this branch unreachable by binding an
        # upstream deterministic max-result-size proof in preflight.
        raise EscrowError("RESULT_EXCEEDS_PRECOMMITTED_ESCROW_CAPACITY")
    envelope = bytearray()
    envelope += MAGIC
    envelope += len(result).to_bytes(8, "big")
    envelope += hashlib.sha256(result).digest()
    envelope += result
    envelope += secrets.token_bytes(fixed_envelope_bytes - len(envelope))
    if len(envelope) != fixed_envelope_bytes:
        raise EscrowError("INTERNAL_ENVELOPE_SIZE_ERROR")
    return envelope


def seal_result(
    result: bytes,
    *,
    recipient_certificate_pem: bytes,
    lease_digest_sha256: str,
    output_dir: str | os.PathLike[str],
    fixed_envelope_bytes: int,
    declared_max_result_bytes: int,
    openssl_binary: str = "openssl",
) -> dict[str, Any]:
    lease = lease_digest_sha256.lower()
    if not _valid_sha256(lease):
        raise EscrowError("INVALID_LEASE_DIGEST_SHA256")

    preflight(
        declared_max_result_bytes=declared_max_result_bytes,
        fixed_envelope_bytes=fixed_envelope_bytes,
    )
    if len(result) > declared_max_result_bytes:
        raise EscrowError("RESULT_EXCEEDS_DECLARED_MAX_RESULT_BYTES")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_name = f"{lease}.cms"
    artifact_path = out_dir / artifact_name

    envelope = _build_fixed_envelope(
        result,
        fixed_envelope_bytes=fixed_envelope_bytes,
    )

    cert_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix="pb-escrow-public-", suffix=".pem", delete=False
        ) as cert_file:
            cert_file.write(recipient_certificate_pem)
            cert_path = Path(cert_file.name)

        proc = subprocess.run(
            [
                openssl_binary,
                "cms",
                "-encrypt",
                "-binary",
                "-aes-256-cbc",
                "-outform",
                "DER",
                str(cert_path),
            ],
            input=bytes(envelope),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0:
            # Never expose OpenSSL stderr: it may contain paths/environment
            # details and is unnecessary for the result-visibility contract.
            raise EscrowError("ESCROW_ENCRYPTION_FAILED")

        ciphertext = proc.stdout
        tmp_path = artifact_path.with_suffix(".cms.tmp")
        tmp_path.write_bytes(ciphertext)
        os.replace(tmp_path, artifact_path)

        receipt = {
            "schema": SCHEMA,
            "status": "SEALED__OPAQUE_RECEIPT_ONLY",
            "lease_digest_sha256": lease,
            "artifact_name": artifact_name,
            "ciphertext_sha256": _sha256_hex(ciphertext),
            "ciphertext_size_bytes": len(ciphertext),
            "fixed_envelope_bytes": fixed_envelope_bytes,
            "declared_max_result_bytes": declared_max_result_bytes,
            "result_body_visible": False,
            "result_score_visible": False,
            "result_summary_visible": False,
            "result_length_visible": False,
            "candidate_mutation_authorized": False,
            "policy_mutation_authorized": False,
            "release_authorized": False,
        }
        return receipt
    finally:
        for i in range(len(envelope)):
            envelope[i] = 0
        if cert_path is not None:
            try:
                cert_path.unlink()
            except FileNotFoundError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipient-cert", required=True)
    parser.add_argument("--lease-digest-sha256", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--fixed-envelope-bytes", type=int, required=True)
    parser.add_argument("--declared-max-result-bytes", type=int, required=True)
    args = parser.parse_args(argv)

    try:
        result = sys.stdin.buffer.read()
        receipt = seal_result(
            result,
            recipient_certificate_pem=Path(args.recipient_cert).read_bytes(),
            lease_digest_sha256=args.lease_digest_sha256,
            output_dir=args.output_dir,
            fixed_envelope_bytes=args.fixed_envelope_bytes,
            declared_max_result_bytes=args.declared_max_result_bytes,
        )
    except EscrowError:
        # Generic constant failure surface. No result-derived values or raw
        # exception details are emitted.
        print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED"}))
        return 2

    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
