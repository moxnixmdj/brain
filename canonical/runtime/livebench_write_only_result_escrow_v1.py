"""Cryptographic write-only result escrow for LiveBench shadow execution.

The production module can encrypt and create one fixed-size escrow object.
It intentionally contains no private-key loader and no decrypt/reveal function.
A separate post-fixed-point authority must hold the private key.

Visible pre-fixed-point surfaces are result-independent:
- output path: derived only from the lease digest;
- artifact size: constant;
- completion schema/status: constant;
- receipt: contains ciphertext metadata, never plaintext score/body/summary/length/hash.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import struct
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_LIVEBENCH_WRITE_ONLY_RESULT_ESCROW_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_LIVEBENCH_WRITE_ONLY_RESULT_ESCROW_RECEIPT_V1"
OPAQUE_COMPLETION_SCHEMA="PROJECT_BRAIN_LIVEBENCH_OPAQUE_COMPLETION_V1"
MAGIC=b"PBR_ESCROW_V1\0\0\0"
RSA_BITS=2048
RSA_BYTES=RSA_BITS//8
NONCE_BYTES=12
AES_KEY_BYTES=32
GCM_TAG_BYTES=16
FIXED_PLAINTEXT_BYTES=262144
INTERNAL_HEADER_BYTES=1+8+32
MAX_STORED_RESULT_BYTES=FIXED_PLAINTEXT_BYTES-INTERNAL_HEADER_BYTES
EXPECTED_ENVELOPE_BYTES=len(MAGIC)+RSA_BYTES+NONCE_BYTES+FIXED_PLAINTEXT_BYTES+GCM_TAG_BYTES
HEX=set("0123456789abcdef")

class EscrowConfigurationError(ValueError):
    pass

def _require_lease_digest(value: str) -> str:
    v=str(value or "").lower()
    if len(v)!=64 or set(v) > HEX:
        raise EscrowConfigurationError("INVALID_LEASE_DIGEST_SHA256")
    return v

def escrow_object_relpath(lease_digest_sha256: str) -> str:
    lease=_require_lease_digest(lease_digest_sha256)
    return f"livebench-shadow-escrow/{lease}.bin"

def _fixed_plaintext(result: bytes) -> bytes:
    raw=bytes(result)
    digest=hashlib.sha256(raw).digest()
    if len(raw) <= MAX_STORED_RESULT_BYTES:
        mode=0
        stored=raw
    else:
        # Overflow itself remains encrypted. Pre-fixed-point observers see the
        # same envelope size/status as any ordinary result.
        mode=1
        stored=b""
    header=struct.pack(">BQ",mode,len(raw))+digest
    payload=header+stored
    if len(payload)>FIXED_PLAINTEXT_BYTES:
        raise AssertionError("FIXED_ESCROW_LAYOUT_OVERFLOW")
    return payload+b"\0"*(FIXED_PLAINTEXT_BYTES-len(payload))

def _aad(lease_digest_sha256: str) -> bytes:
    return b"PROJECT_BRAIN_LIVEBENCH_ESCROW_V1\0"+_require_lease_digest(lease_digest_sha256).encode("ascii")

def seal_result_bytes(
    result: bytes,
    *,
    lease_digest_sha256: str,
    public_key_pem: bytes,
) -> bytes:
    """Return a fixed-size encrypted envelope using public-key-only capability."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    lease=_require_lease_digest(lease_digest_sha256)
    public_key=serialization.load_pem_public_key(bytes(public_key_pem))
    if not isinstance(public_key,rsa.RSAPublicKey) or public_key.key_size!=RSA_BITS:
        raise EscrowConfigurationError("RSA_2048_PUBLIC_KEY_REQUIRED")

    aes_key=secrets.token_bytes(AES_KEY_BYTES)
    nonce=secrets.token_bytes(NONCE_BYTES)
    ciphertext=AESGCM(aes_key).encrypt(nonce,_fixed_plaintext(result),_aad(lease))
    wrapped_key=public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    if len(wrapped_key)!=RSA_BYTES:
        raise EscrowConfigurationError("UNEXPECTED_RSA_CIPHERTEXT_SIZE")
    envelope=MAGIC+wrapped_key+nonce+ciphertext
    if len(envelope)!=EXPECTED_ENVELOPE_BYTES:
        raise AssertionError("NON_CONSTANT_ESCROW_ENVELOPE_SIZE")
    return envelope

def write_result_opaque(
    result: bytes,
    *,
    lease_digest_sha256: str,
    public_key_pem: bytes,
    output_root: str | os.PathLike[str],
) -> dict[str,Any]:
    """Create exactly one encrypted escrow object and return plaintext-free metadata."""
    lease=_require_lease_digest(lease_digest_sha256)
    relpath=escrow_object_relpath(lease)
    path=Path(output_root)/relpath
    path.parent.mkdir(parents=True,exist_ok=True)
    envelope=seal_result_bytes(
        result,
        lease_digest_sha256=lease,
        public_key_pem=public_key_pem,
    )
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        view=memoryview(envelope)
        while view:
            n=os.write(fd,view)
            if n<=0:
                raise OSError("ESCROW_WRITE_FAILED")
            view=view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return {
        "schema":RECEIPT_SCHEMA,
        "status":"OPAQUE_ESCROW_COMMITTED",
        "lease_digest_sha256":lease,
        "escrow_object_path":relpath,
        "envelope_sha256":hashlib.sha256(envelope).hexdigest(),
        "envelope_byte_length":EXPECTED_ENVELOPE_BYTES,
        "fixed_size_envelope":True,
        "plaintext_result_fields_visible":False,
        "plaintext_result_length_visible":False,
        "plaintext_result_hash_visible":False,
        "decrypt_capability_present":False,
        "private_key_present_in_execution_context":False,
        "result_release_authority":False,
        "candidate_mutation_authorized":False,
        "policy_mutation_authorized":False,
        "terminal_cases_consumed_by_escrow":0,
    }

def opaque_completion(receipt: Mapping[str,Any]) -> dict[str,Any]:
    """Return the only completion surface intended for pre-fixed-point logs."""
    committed=receipt.get("schema")==RECEIPT_SCHEMA and receipt.get("status")=="OPAQUE_ESCROW_COMMITTED"
    return {
        "schema":OPAQUE_COMPLETION_SCHEMA,
        "status":"OPAQUE_COMPLETION" if committed else "OPAQUE_ESCROW_INFRASTRUCTURE_FAILURE",
        "result_visible":False,
        "score_visible":False,
        "summary_visible":False,
        "result_release_authority":False,
        "candidate_mutation_authorized":False,
        "policy_mutation_authorized":False,
    }
