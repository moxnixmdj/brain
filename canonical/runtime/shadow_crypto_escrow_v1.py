"""Write-only cryptographic escrow writer for pre-fixed-point shadow results.

This module contains encryption only. It deliberately has no decryption path.
A scoring job may pass result bytes here after candidate execution; the result
is padded to a fixed plaintext size and encrypted to a pre-bound X.509
recipient with OpenSSL CMS. Only an opaque ciphertext and non-sensitive receipt
leave the scoring job.

The writer itself grants no case-reveal, collection, fresh-reality,
acceptance, or promotion authority.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import secrets
import subprocess
import tempfile
from typing import Any

SCHEMA="PROJECT_BRAIN_SHADOW_CRYPTO_ESCROW_WRITER_V1"
HEX=set("0123456789abcdef")
DEFAULT_PADDED_PLAINTEXT_BYTES=16*1024*1024
LENGTH_PREFIX_BYTES=8


class EscrowWriteFailure(RuntimeError):
    pass


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value,str) and len(value)==64 and set(value.lower()) <= HEX


def output_filename(lease_digest_sha256: str) -> str:
    if not _valid_sha256(lease_digest_sha256):
        raise EscrowWriteFailure("INVALID_LEASE_DIGEST_SHA256")
    return lease_digest_sha256.lower()+".cms.der"


def _fixed_envelope(result: bytes, padded_plaintext_bytes: int) -> bytes:
    if isinstance(padded_plaintext_bytes,bool) or not isinstance(padded_plaintext_bytes,int):
        raise EscrowWriteFailure("PADDED_SIZE_NOT_INT")
    if padded_plaintext_bytes < LENGTH_PREFIX_BYTES:
        raise EscrowWriteFailure("PADDED_SIZE_TOO_SMALL")
    if len(result) > padded_plaintext_bytes-LENGTH_PREFIX_BYTES:
        raise EscrowWriteFailure("RESULT_EXCEEDS_FIXED_ESCROW_PAYLOAD")
    prefix=len(result).to_bytes(LENGTH_PREFIX_BYTES,"big")
    padding=secrets.token_bytes(padded_plaintext_bytes-LENGTH_PREFIX_BYTES-len(result))
    return prefix+result+padding


def write_encrypted_result(
    *,
    result_bytes: bytes,
    recipient_certificate_pem: bytes,
    expected_certificate_sha256: str,
    lease_digest_sha256: str,
    output_dir: str | os.PathLike[str],
    padded_plaintext_bytes: int=DEFAULT_PADDED_PLAINTEXT_BYTES,
) -> dict[str,Any]:
    if not isinstance(result_bytes,bytes):
        raise EscrowWriteFailure("RESULT_MUST_BE_BYTES")
    if not isinstance(recipient_certificate_pem,bytes) or not recipient_certificate_pem:
        raise EscrowWriteFailure("RECIPIENT_CERTIFICATE_REQUIRED")
    if not _valid_sha256(expected_certificate_sha256):
        raise EscrowWriteFailure("EXPECTED_CERTIFICATE_SHA256_INVALID")
    cert_sha=_sha256_bytes(recipient_certificate_pem)
    if cert_sha != expected_certificate_sha256.lower():
        raise EscrowWriteFailure("RECIPIENT_CERTIFICATE_SHA256_MISMATCH")

    out_dir=pathlib.Path(output_dir)
    out_dir.mkdir(parents=True,exist_ok=True)
    out_path=out_dir/output_filename(lease_digest_sha256)
    if out_path.exists():
        raise EscrowWriteFailure("ESCROW_RESULT_ALREADY_EXISTS")

    envelope=_fixed_envelope(result_bytes,padded_plaintext_bytes)
    with tempfile.TemporaryDirectory(prefix="brain-shadow-escrow-") as td:
        cert_path=pathlib.Path(td)/"recipient.crt"
        cert_path.write_bytes(recipient_certificate_pem)
        proc=subprocess.run(
            [
                "openssl","cms","-encrypt","-binary","-aes-256-cbc",
                "-outform","DER","-in","-","-recip",str(cert_path),
            ],
            input=envelope,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if proc.returncode != 0:
        raise EscrowWriteFailure(
            "OPENSSL_CMS_ENCRYPT_FAILED:"+proc.stderr.decode("utf-8","replace")[:500]
        )
    ciphertext=proc.stdout
    if not ciphertext:
        raise EscrowWriteFailure("EMPTY_ESCROW_CIPHERTEXT")

    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    fd=os.open(out_path,flags,0o600)
    try:
        with os.fdopen(fd,"wb",closefd=True) as f:
            f.write(ciphertext)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        try:
            out_path.unlink(missing_ok=True)
        finally:
            raise

    return {
        "schema":SCHEMA,
        "lease_digest_sha256":lease_digest_sha256.lower(),
        "output_filename":out_path.name,
        "ciphertext_sha256":_sha256_bytes(ciphertext),
        "ciphertext_bytes":len(ciphertext),
        "recipient_certificate_sha256":cert_sha,
        "fixed_plaintext_bytes":padded_plaintext_bytes,
        "plaintext_length_disclosed":False,
        "plaintext_sha256_disclosed":False,
        "score_or_result_signal_disclosed":False,
        "exclusive_create":True,
        "decryption_path_present_in_writer":False,
        "result_visibility_before_fixed_point":False,
        "terminal_cases_consumed_by_writer":0,
        "global_fresh_reality_authority":False,
        "shadow_collection_authority":False,
        "acceptance_credit_authorized":False,
        "promotion_authority":False,
    }
