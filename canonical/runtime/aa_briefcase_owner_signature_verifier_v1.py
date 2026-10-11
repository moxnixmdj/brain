from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_OWNER_SIGNATURE_VERIFIER_V1"
SIGNATURE_SCHEME = "ED25519_CANONICAL_JSON_V1"


class OwnerSignatureError(ValueError):
    pass


def canonical_statement_bytes(statement: Mapping[str, Any]) -> bytes:
    if not isinstance(statement, Mapping):
        raise OwnerSignatureError("STATEMENT_INVALID")
    return json.dumps(
        statement,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hex(value: Any, n: int, label: str) -> str:
    if not isinstance(value, str) or len(value) != n or any(c not in "0123456789abcdef" for c in value):
        raise OwnerSignatureError(label + "_INVALID")
    return value


def verify_owner_signature(
    statement: Mapping[str, Any],
    signature_bundle: Mapping[str, Any],
    owner_key_binding: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(signature_bundle, Mapping):
        raise OwnerSignatureError("SIGNATURE_BUNDLE_INVALID")
    if signature_bundle.get("scheme") != SIGNATURE_SCHEME:
        raise OwnerSignatureError("SIGNATURE_SCHEME_MISMATCH")

    public_key_pem = signature_bundle.get("public_key_pem")
    signature_b64 = signature_bundle.get("signature_base64")
    if not isinstance(public_key_pem, str) or "BEGIN PUBLIC KEY" not in public_key_pem:
        raise OwnerSignatureError("PUBLIC_KEY_PEM_INVALID")
    if not isinstance(signature_b64, str) or not signature_b64:
        raise OwnerSignatureError("SIGNATURE_BASE64_INVALID")

    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except Exception as exc:
        raise OwnerSignatureError("SIGNATURE_BASE64_INVALID") from exc

    if not isinstance(owner_key_binding, Mapping):
        raise OwnerSignatureError("OWNER_KEY_BINDING_INVALID")
    if owner_key_binding.get("status") != "VERIFIED_OWNER_KEY_BINDING":
        raise OwnerSignatureError("OWNER_KEY_BINDING_NOT_VERIFIED")
    if owner_key_binding.get("benchmark_owner") != "Artificial Analysis":
        raise OwnerSignatureError("BENCHMARK_OWNER_MISMATCH")
    if owner_key_binding.get("authorized_for") != "AA-Briefcase v1.1":
        raise OwnerSignatureError("OWNER_KEY_NOT_AUTHORIZED_FOR_AA_BRIEFCASE")
    if owner_key_binding.get("signature_scheme") != SIGNATURE_SCHEME:
        raise OwnerSignatureError("OWNER_KEY_SCHEME_MISMATCH")
    if owner_key_binding.get("identity_verified") is not True:
        raise OwnerSignatureError("OWNER_KEY_IDENTITY_UNVERIFIED")

    expected_key_sha = _hex(
        owner_key_binding.get("public_key_pem_sha256"),
        64,
        "OWNER_PUBLIC_KEY_PEM_SHA256",
    )
    actual_key_sha = _sha256_bytes(public_key_pem.encode("utf-8"))
    if actual_key_sha != expected_key_sha:
        raise OwnerSignatureError("OWNER_PUBLIC_KEY_MISMATCH")

    binding_receipt_sha = _hex(
        owner_key_binding.get("binding_receipt_sha256"),
        64,
        "OWNER_KEY_BINDING_RECEIPT_SHA256",
    )

    message = canonical_statement_bytes(statement)
    statement_sha = _sha256_bytes(message)

    with tempfile.TemporaryDirectory(prefix="aa_owner_sig_") as tmp:
        root = Path(tmp)
        pub_path = root / "owner_public.pem"
        msg_path = root / "statement.json"
        sig_path = root / "statement.sig"
        pub_path.write_text(public_key_pem, encoding="utf-8")
        msg_path.write_bytes(message)
        sig_path.write_bytes(signature)

        try:
            proc = subprocess.run(
                [
                    "openssl",
                    "pkeyutl",
                    "-verify",
                    "-pubin",
                    "-inkey",
                    str(pub_path),
                    "-rawin",
                    "-in",
                    str(msg_path),
                    "-sigfile",
                    str(sig_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except FileNotFoundError as exc:
            raise OwnerSignatureError("OPENSSL_NOT_AVAILABLE") from exc
        except subprocess.TimeoutExpired as exc:
            raise OwnerSignatureError("OPENSSL_VERIFY_TIMEOUT") from exc

    if proc.returncode != 0:
        raise OwnerSignatureError("CRYPTographic_SIGNATURE_INVALID".upper())

    material = {
        "schema": SCHEMA,
        "status": "VERIFIED",
        "signature_scheme": SIGNATURE_SCHEME,
        "statement_sha256": statement_sha,
        "public_key_pem_sha256": actual_key_sha,
        "benchmark_owner": "Artificial Analysis",
        "authorized_for": "AA-Briefcase v1.1",
        "attestor_is_benchmark_owner_or_authorized_operator": True,
        "identity_verified": True,
        "owner_key_binding_receipt_sha256": binding_receipt_sha,
    }
    material["verification_receipt_sha256"] = _sha256_bytes(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return material
