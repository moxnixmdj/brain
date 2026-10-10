"""Executable semantic verification for canonical coverage-root certificates.

A PROVED_CURRENT root slot is authoritative only when:
1. certificate bytes are content-addressed;
2. a content-addressed canonical semantic verifier is declared;
3. the verifier is rerun over the exact certificate and active claim;
4. the stored independent verification receipt binds the same root, claim,
   certificate, verifier, and successful verifier result.

This module is subordinate to R4 and grants zero terminal credit.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_COVERAGE_ROOT_SEMANTIC_VERIFICATION_V1"
PROTOCOL = "COVERAGE_ROOT_SEMANTIC_VERIFIER_V1"
ALLOWED_PROOF_MODES = frozenset({
    "KERNEL_CHECKED",
    "DECISION_PROCEDURE",
    "MODEL_CHECKED",
    "FORMAL_REDUCTION",
    "INDEPENDENT_REPLAY",
})


def _blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _safe_path(root: Path, rel: Any) -> Path | None:
    if not isinstance(rel, str) or not rel or rel.startswith("/"):
        return None
    p = Path(rel)
    if ".." in p.parts:
        return None
    out = (root / p).resolve()
    try:
        out.relative_to(root.resolve())
    except ValueError:
        return None
    return out


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "pass": False,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "terminal_credit_delta": 0,
    }


def validate_semantic_root_slot(
    root: Path,
    slot: Mapping[str, Any],
    active_claim: Mapping[str, Any],
) -> dict[str, Any]:
    root = root.resolve()
    root_id = slot.get("root_id")
    cert = slot.get("certificate")
    verifier = slot.get("semantic_verifier")
    receipt_ref = slot.get("independent_verification")
    errors: list[str] = []

    if slot.get("status") != "PROVED_CURRENT":
        return _fail("SLOT_NOT_PROVED_CURRENT")
    if not isinstance(root_id, str) or not root_id:
        return _fail("ROOT_ID_INVALID")
    if not isinstance(active_claim, Mapping) or not isinstance(active_claim.get("claim_id"), str):
        return _fail("ACTIVE_CLAIM_INVALID")
    if not isinstance(cert, Mapping):
        return _fail("CERTIFICATE_REF_MISSING")
    if not isinstance(verifier, Mapping):
        return _fail("SEMANTIC_VERIFIER_REF_MISSING")
    if not isinstance(receipt_ref, Mapping):
        return _fail("INDEPENDENT_VERIFICATION_REF_MISSING")

    refs = {
        "certificate": cert,
        "semantic_verifier": verifier,
        "independent_verification": receipt_ref,
    }
    resolved: dict[str, Path] = {}
    for label, ref in refs.items():
        p = _safe_path(root, ref.get("path"))
        sha = ref.get("git_blob_sha")
        if p is None or not isinstance(sha, str) or not sha:
            errors.append(f"{label.upper()}_REF_INVALID")
            continue
        if not p.is_file():
            errors.append(f"{label.upper()}_FILE_MISSING")
            continue
        if _blob_sha(p) != sha:
            errors.append(f"{label.upper()}_BLOB_SHA_MISMATCH")
            continue
        resolved[label] = p

    if errors:
        return _fail(*errors)

    try:
        spec = importlib.util.spec_from_file_location(
            "coverage_root_semantic_verifier_runtime",
            resolved["semantic_verifier"],
        )
        if spec is None or spec.loader is None:
            return _fail("SEMANTIC_VERIFIER_LOAD_SPEC_FAILED")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        verify_fn = getattr(module, "verify_certificate", None)
        if not callable(verify_fn):
            return _fail("SEMANTIC_VERIFIER_ENTRYPOINT_MISSING")
        rerun = verify_fn(
            root=root,
            certificate_path=resolved["certificate"],
            active_claim=dict(active_claim),
            root_id=root_id,
        )
    except Exception as exc:
        return _fail("SEMANTIC_VERIFIER_EXCEPTION:" + type(exc).__name__)

    if not isinstance(rerun, Mapping):
        return _fail("SEMANTIC_VERIFIER_RESULT_NOT_OBJECT")
    if rerun.get("pass") is not True:
        return _fail("SEMANTIC_VERIFIER_REJECTED_CERTIFICATE")
    if rerun.get("root_id") != root_id:
        return _fail("SEMANTIC_VERIFIER_ROOT_MISMATCH")
    if rerun.get("claim_id") != active_claim.get("claim_id"):
        return _fail("SEMANTIC_VERIFIER_CLAIM_MISMATCH")
    result_sha256 = hashlib.sha256(
        json.dumps(rerun, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()

    try:
        receipt = json.loads(resolved["independent_verification"].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _fail("INDEPENDENT_VERIFICATION_RECEIPT_INVALID_JSON")
    if not isinstance(receipt, Mapping):
        return _fail("INDEPENDENT_VERIFICATION_RECEIPT_NOT_OBJECT")

    checks = (
        (receipt.get("schema") == SCHEMA, "RECEIPT_SCHEMA_INVALID"),
        (receipt.get("verifier_protocol") == PROTOCOL, "RECEIPT_PROTOCOL_INVALID"),
        (receipt.get("pass") is True, "RECEIPT_PASS_NOT_TRUE"),
        (isinstance(receipt.get("status"), str) and receipt.get("status", "").startswith("PASS"), "RECEIPT_STATUS_NOT_PASS"),
        (receipt.get("independent") is True, "RECEIPT_NOT_INDEPENDENT"),
        (receipt.get("semantic_claim_verified") is True, "RECEIPT_SEMANTIC_CLAIM_NOT_VERIFIED"),
        (receipt.get("root_id") == root_id, "RECEIPT_ROOT_MISMATCH"),
        (receipt.get("claim_id") == active_claim.get("claim_id"), "RECEIPT_CLAIM_MISMATCH"),
        (receipt.get("proof_mode") in ALLOWED_PROOF_MODES, "RECEIPT_PROOF_MODE_INVALID"),
        (receipt.get("verifier_result_sha256") == result_sha256, "RECEIPT_RERUN_RESULT_MISMATCH"),
        (receipt.get("terminal_credit_delta", 0) == 0, "RECEIPT_NONZERO_TERMINAL_CREDIT"),
        (receipt.get("errors") == [], "RECEIPT_ERRORS_NONEMPTY"),
    )
    for ok, error in checks:
        if not ok:
            errors.append(error)

    receipt_cert = receipt.get("certificate") or {}
    if (
        receipt_cert.get("path") != cert.get("path")
        or receipt_cert.get("git_blob_sha") != cert.get("git_blob_sha")
    ):
        errors.append("RECEIPT_CERTIFICATE_BINDING_MISMATCH")
    receipt_verifier = receipt.get("semantic_verifier") or {}
    if (
        receipt_verifier.get("path") != verifier.get("path")
        or receipt_verifier.get("git_blob_sha") != verifier.get("git_blob_sha")
    ):
        errors.append("RECEIPT_VERIFIER_BINDING_MISMATCH")

    if errors:
        return _fail(*errors)

    return {
        "pass": True,
        "status": "PASS__EXECUTABLE_SEMANTIC_ROOT_CERTIFICATE_VERIFICATION",
        "root_id": root_id,
        "claim_id": active_claim.get("claim_id"),
        "verifier_result_sha256": result_sha256,
        "proof_mode": receipt.get("proof_mode"),
        "terminal_credit_delta": 0,
        "errors": [],
    }
