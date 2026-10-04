#!/usr/bin/env python3
"""Post-fixed-point release reducer for write-only LiveBench result escrow.

This module is deliberately separate from the collection path.  It requires the
recipient private key and is therefore unusable by a collection role that holds
only the public certificate.
"""
from __future__ import annotations

from fractions import Fraction
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from canonical.runtime.shadow_write_only_result_escrow_v1 import (
    CASE_COUNT,
    HEADER_BYTES,
    MAGIC,
    PLAINTEXT_BYTES,
    ResultEscrowError,
    VECTOR_BYTES,
    _lease_bytes,
)

SCHEMA = "PROJECT_BRAIN_SHADOW_RESULT_RELEASE_V1"
TARGET_PERCENT = Fraction(6573775, 100000)  # 65.73775 exactly.


def _decrypt(
    *,
    ciphertext_path: Path,
    recipient_cert_path: Path,
    private_key_path: Path,
    openssl_bin: str,
) -> bytes:
    if not private_key_path.is_file():
        raise ResultEscrowError("RELEASE_PRIVATE_KEY_REQUIRED")
    with tempfile.TemporaryDirectory(prefix=".pb-release-") as td:
        out = Path(td) / "plain.bin"
        proc = subprocess.run(
            [
                openssl_bin, "cms", "-decrypt", "-binary", "-inform", "DER",
                "-in", str(ciphertext_path),
                "-recip", str(recipient_cert_path),
                "-inkey", str(private_key_path),
                "-out", str(out),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env={"PATH": os.environ.get("PATH", "")},
        )
        if proc.returncode != 0:
            raise ResultEscrowError("ESCROW_DECRYPTION_FAILED")
        data = out.read_bytes()
    return data


def release_score_vector(
    *,
    ciphertext_path: str | os.PathLike[str],
    recipient_cert_path: str | os.PathLike[str],
    private_key_path: str | os.PathLike[str],
    expected_lease_digest_sha256: str,
    openssl_bin: str = "openssl",
) -> dict[str, Any]:
    plain = _decrypt(
        ciphertext_path=Path(ciphertext_path),
        recipient_cert_path=Path(recipient_cert_path),
        private_key_path=Path(private_key_path),
        openssl_bin=openssl_bin,
    )
    if len(plain) != PLAINTEXT_BYTES or not plain.startswith(MAGIC):
        raise ResultEscrowError("ESCROW_PLAINTEXT_GEOMETRY_INVALID")
    lease = plain[len(MAGIC):HEADER_BYTES]
    if lease != _lease_bytes(expected_lease_digest_sha256):
        raise ResultEscrowError("ESCROW_LEASE_BINDING_MISMATCH")

    vec = plain[HEADER_BYTES:HEADER_BYTES + VECTOR_BYTES]
    if len(vec) != CASE_COUNT * 2:
        raise ResultEscrowError("ESCROW_VECTOR_GEOMETRY_INVALID")

    total = Fraction(0, 1)
    full_score_cases = 0
    per_case = []
    for i in range(CASE_COUNT):
        count = vec[2 * i]
        mask = vec[2 * i + 1]
        if not (1 <= count <= 8) or mask >= (1 << count):
            raise ResultEscrowError(f"ESCROW_ROW_INVALID_AT_{i}")
        true_count = int(mask).bit_count()
        all_true = true_count == count
        if all_true:
            full_score_cases += 1
        score = Fraction(1, 2) * int(all_true) + Fraction(1, 2) * Fraction(true_count, count)
        total += score
        per_case.append({
            "index": i,
            "checker_count": count,
            "true_checker_count": true_count,
            "all_checkers_true": all_true,
            "score_numerator": score.numerator,
            "score_denominator": score.denominator,
        })

    percent = total * Fraction(100, CASE_COUNT)
    passed = percent >= TARGET_PERCENT
    return {
        "schema": SCHEMA,
        "status": "POST_FIXED_POINT_RESULT_RELEASED",
        "lease_digest_sha256": expected_lease_digest_sha256.lower(),
        "frozen_case_count": CASE_COUNT,
        "full_score_cases": full_score_cases,
        "score_percent_numerator": percent.numerator,
        "score_percent_denominator": percent.denominator,
        "score_percent": float(percent),
        "target_percent": float(TARGET_PERCENT),
        "target_met": passed,
        "per_case": per_case,
        "acceptance_credit_authorized_by_release_module": False,
        "promotion_authority": False,
    }
