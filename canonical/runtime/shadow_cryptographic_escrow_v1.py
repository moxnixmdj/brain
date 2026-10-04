#!/usr/bin/env python3
"""Fixed-size public-key result escrow for shadow evaluation.

The writer receives only an X.509 recipient certificate. It never accepts a
private key, writes no plaintext file, derives the output name only from the
lease digest, and pads every valid payload to a fixed envelope size before
OpenSSL CMS encryption.

This module grants no case-reveal, execution, result-release, promotion, or
acceptance authority.
"""
from __future__ import annotations
import hashlib
import os
import pathlib
import secrets
import subprocess
import tempfile
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_SHADOW_CRYPTOGRAPHIC_ESCROW_V1"
DEFAULT_PADDED_PLAINTEXT_BYTES=16*1024*1024
MAGIC=b"PBESCROW1"
HEX=set("0123456789abcdef")

class EscrowError(RuntimeError):
    pass

def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _valid_sha256(value: Any) -> bool:
    return isinstance(value,str) and len(value)==64 and set(value.lower()) <= HEX

def output_name(lease_digest_sha256: str) -> str:
    if not _valid_sha256(lease_digest_sha256):
        raise EscrowError("INVALID_LEASE_DIGEST_SHA256")
    return "shadow-result-"+lease_digest_sha256.lower()+".cms"

def recipient_fingerprint_sha256(cert_path: str|os.PathLike[str]) -> str:
    data=pathlib.Path(cert_path).read_bytes()
    return _sha256_hex(data)

def _fixed_plaintext(payload: bytes, capacity: int) -> bytes:
    if not isinstance(payload,(bytes,bytearray)):
        raise EscrowError("PAYLOAD_MUST_BE_BYTES")
    payload=bytes(payload)
    header=MAGIC+len(payload).to_bytes(8,"big")
    if capacity < len(header) or len(payload) > capacity-len(header):
        raise EscrowError("PAYLOAD_EXCEEDS_FIXED_ESCROW_CAPACITY")
    return header+payload+secrets.token_bytes(capacity-len(header)-len(payload))

def write_encrypted_result(
    *,
    payload: bytes,
    lease_digest_sha256: str,
    recipient_cert_path: str|os.PathLike[str],
    expected_recipient_cert_sha256: str,
    escrow_dir: str|os.PathLike[str],
    padded_plaintext_bytes: int=DEFAULT_PADDED_PLAINTEXT_BYTES,
) -> Mapping[str,Any]:
    """Encrypt one result with public material only and return opaque metadata."""
    if not _valid_sha256(expected_recipient_cert_sha256):
        raise EscrowError("INVALID_EXPECTED_RECIPIENT_CERT_SHA256")
    cert=pathlib.Path(recipient_cert_path)
    if not cert.is_file():
        raise EscrowError("RECIPIENT_CERT_MISSING")
    observed=recipient_fingerprint_sha256(cert)
    if observed != expected_recipient_cert_sha256.lower():
        raise EscrowError("RECIPIENT_CERT_SHA256_MISMATCH")
    if padded_plaintext_bytes != DEFAULT_PADDED_PLAINTEXT_BYTES:
        raise EscrowError("NONCANONICAL_PADDED_SIZE")

    out_dir=pathlib.Path(escrow_dir)
    out_dir.mkdir(parents=True,exist_ok=True)
    out=out_dir/output_name(lease_digest_sha256)
    if out.exists():
        raise EscrowError("ESCROW_OBJECT_ALREADY_EXISTS")

    fixed=_fixed_plaintext(payload,padded_plaintext_bytes)
    fd,tmp_name=tempfile.mkstemp(prefix=".escrow-",suffix=".cms",dir=str(out_dir))
    os.close(fd)
    tmp=pathlib.Path(tmp_name)
    try:
        proc=subprocess.run(
            [
                "openssl","cms","-encrypt","-binary","-outform","DER",
                "-aes-256-cbc","-recip",str(cert),"-out",str(tmp)
            ],
            input=fixed,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if proc.returncode != 0:
            raise EscrowError("CMS_ENCRYPTION_FAILED")
        if not tmp.is_file() or tmp.stat().st_size <= padded_plaintext_bytes:
            raise EscrowError("ESCROW_CIPHERTEXT_INVALID")
        os.chmod(tmp,0o600)
        os.replace(tmp,out)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass

    cipher=out.read_bytes()
    return {
        "schema":SCHEMA,
        "status":"ESCROW_WRITE_OK",
        "lease_digest_sha256":lease_digest_sha256.lower(),
        "recipient_cert_sha256":observed,
        "object_name":out.name,
        "ciphertext_sha256":_sha256_hex(cipher),
        "ciphertext_bytes":len(cipher),
        "padded_plaintext_bytes":padded_plaintext_bytes,
        "plaintext_bytes_disclosed":False,
        "private_key_required_by_writer":False,
        "result_body_disclosed":False,
        "result_score_disclosed":False,
        "result_summary_disclosed":False,
        "case_reveal_authority":False,
        "result_release_authority":False,
        "fresh_reality_authority":False,
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_credit_authorized":False,
    }

def recover_fixed_plaintext(blob: bytes) -> bytes:
    """Reducer-side parser used only after separately authorized decryption."""
    if not blob.startswith(MAGIC) or len(blob)<len(MAGIC)+8:
        raise EscrowError("INVALID_ESCROW_PLAINTEXT")
    n=int.from_bytes(blob[len(MAGIC):len(MAGIC)+8],"big")
    start=len(MAGIC)+8
    end=start+n
    if end>len(blob):
        raise EscrowError("INVALID_ESCROW_LENGTH")
    return blob[start:end]
