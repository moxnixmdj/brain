"""Generic executable-refinement receipt verification for Project Brain.

This module generalizes the current R4 executable-semantic-verifier pattern to
abstract-specification -> concrete-executable refinement claims.

A slot is accepted only when:
1. the refinement certificate bytes are content-addressed;
2. a content-addressed semantic/refinement verifier is declared;
3. that verifier is rerun over the exact certificate and requested subject;
4. an independent receipt binds the same subject, certificate, verifier, and
   exact successful rerun result;
5. any required liveness-preservation claim is present in the rerun result.

This verifier grants zero acceptance, capability, ownership, or terminal credit.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_EXECUTABLE_REFINEMENT_VERIFICATION_V1"
PROTOCOL = "EXECUTABLE_REFINEMENT_VERIFIER_V1"
ALLOWED_PROOF_MODES = frozenset({
    "KERNEL_CHECKED",
    "DECISION_PROCEDURE",
    "MODEL_CHECKED",
    "FORMAL_REDUCTION",
    "INDEPENDENT_REPLAY",
})


def _blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


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
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def validate_executable_refinement(
    root: Path,
    slot: Mapping[str, Any],
    subject_id: str,
) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []

    if slot.get("status") != "REFINEMENT_VERIFIED":
        return _fail("SLOT_NOT_REFINEMENT_VERIFIED")
    if not isinstance(subject_id, str) or not subject_id.strip():
        return _fail("REQUESTED_SUBJECT_INVALID")
    subject_id = subject_id.strip()
    if slot.get("subject_id") != subject_id:
        return _fail("SLOT_SUBJECT_MISMATCH")

    certificate = slot.get("refinement_certificate")
    verifier = slot.get("semantic_verifier")
    receipt_ref = slot.get("independent_verification")
    if not isinstance(certificate, Mapping):
        return _fail("REFINEMENT_CERTIFICATE_REF_MISSING")
    if not isinstance(verifier, Mapping):
        return _fail("SEMANTIC_VERIFIER_REF_MISSING")
    if not isinstance(receipt_ref, Mapping):
        return _fail("INDEPENDENT_VERIFICATION_REF_MISSING")

    refs = {
        "refinement_certificate": certificate,
        "semantic_verifier": verifier,
        "independent_verification": receipt_ref,
    }
    resolved: dict[str, Path] = {}
    for label, ref in refs.items():
        p = _safe_path(root, ref.get("path"))
        sha = ref.get("git_blob_sha")
        if p is None or not isinstance(sha, str) or not sha:
            errors.append(label.upper() + "_REF_INVALID")
            continue
        if not p.is_file():
            errors.append(label.upper() + "_FILE_MISSING")
            continue
        if _blob_sha(p) != sha:
            errors.append(label.upper() + "_BLOB_SHA_MISMATCH")
            continue
        resolved[label] = p

    if errors:
        return _fail(*errors)

    try:
        spec = importlib.util.spec_from_file_location(
            "project_brain_executable_refinement_semantic_verifier_runtime",
            resolved["semantic_verifier"],
        )
        if spec is None or spec.loader is None:
            return _fail("SEMANTIC_VERIFIER_LOAD_SPEC_FAILED")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        verify_fn = getattr(module, "verify_refinement", None)
        if not callable(verify_fn):
            return _fail("SEMANTIC_VERIFIER_ENTRYPOINT_MISSING")
        rerun = verify_fn(
            root=root,
            certificate_path=resolved["refinement_certificate"],
            subject_id=subject_id,
        )
    except Exception as exc:
        return _fail("SEMANTIC_VERIFIER_EXCEPTION:" + type(exc).__name__)

    if not isinstance(rerun, Mapping):
        return _fail("SEMANTIC_VERIFIER_RESULT_NOT_OBJECT")
    if rerun.get("pass") is not True:
        return _fail("SEMANTIC_VERIFIER_REJECTED_REFINEMENT")
    if rerun.get("subject_id") != subject_id:
        return _fail("SEMANTIC_VERIFIER_SUBJECT_MISMATCH")
    if rerun.get("certificate_subject_id") not in {None, subject_id}:
        return _fail("SEMANTIC_VERIFIER_CERTIFICATE_SUBJECT_MISMATCH")
    if slot.get("liveness_required") is True and rerun.get("liveness_preserved") is not True:
        return _fail("LIVENESS_REFINEMENT_REQUIRED_BUT_UNPROVED")

    result_sha256 = hashlib.sha256(
        json.dumps(
            rerun,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()

    try:
        receipt = json.loads(
            resolved["independent_verification"].read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return _fail("INDEPENDENT_VERIFICATION_RECEIPT_INVALID_JSON")
    if not isinstance(receipt, Mapping):
        return _fail("INDEPENDENT_VERIFICATION_RECEIPT_NOT_OBJECT")

    checks = (
        (receipt.get("schema") == SCHEMA, "RECEIPT_SCHEMA_INVALID"),
        (receipt.get("verifier_protocol") == PROTOCOL, "RECEIPT_PROTOCOL_INVALID"),
        (receipt.get("pass") is True, "RECEIPT_PASS_NOT_TRUE"),
        (
            isinstance(receipt.get("status"), str)
            and receipt.get("status", "").startswith("PASS"),
            "RECEIPT_STATUS_NOT_PASS",
        ),
        (receipt.get("independent") is True, "RECEIPT_NOT_INDEPENDENT"),
        (
            receipt.get("refinement_claim_verified") is True,
            "RECEIPT_REFINEMENT_CLAIM_NOT_VERIFIED",
        ),
        (receipt.get("subject_id") == subject_id, "RECEIPT_SUBJECT_MISMATCH"),
        (
            receipt.get("proof_mode") in ALLOWED_PROOF_MODES,
            "RECEIPT_PROOF_MODE_INVALID",
        ),
        (
            receipt.get("verifier_result_sha256") == result_sha256,
            "RECEIPT_RERUN_RESULT_MISMATCH",
        ),
        (
            receipt.get("acceptance_credit_delta", 0) == 0,
            "RECEIPT_NONZERO_ACCEPTANCE_CREDIT",
        ),
        (
            receipt.get("capability_credit_delta", 0) == 0,
            "RECEIPT_NONZERO_CAPABILITY_CREDIT",
        ),
        (
            receipt.get("ownership_credit_delta", 0) == 0,
            "RECEIPT_NONZERO_OWNERSHIP_CREDIT",
        ),
        (
            receipt.get("terminal_credit_delta", 0) == 0,
            "RECEIPT_NONZERO_TERMINAL_CREDIT",
        ),
        (receipt.get("errors") == [], "RECEIPT_ERRORS_NONEMPTY"),
    )
    for ok, error in checks:
        if not ok:
            errors.append(error)

    receipt_certificate = receipt.get("certificate") or {}
    if (
        receipt_certificate.get("path") != certificate.get("path")
        or receipt_certificate.get("git_blob_sha") != certificate.get("git_blob_sha")
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
        "status": "PASS__EXECUTABLE_REFINEMENT_VERIFIED",
        "subject_id": subject_id,
        "verifier_result_sha256": result_sha256,
        "proof_mode": receipt.get("proof_mode"),
        "liveness_required": slot.get("liveness_required") is True,
        "liveness_preserved": rerun.get("liveness_preserved") is True,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        "errors": [],
    }
