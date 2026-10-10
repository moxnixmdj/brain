"""Currentness-aware authenticated Escape-Progress audit.

V5 preserves V4's authenticated row-proof and V3's structural proof algebra,
but closes one remaining authority hole: a canonical proof of an obsolete row
state must not close current CC_R3.

The current manifest and binding are resolved through the canonical current
residual classification. Each row's evidence source is then revalidated:
- immutable sources must still match the manifest-bound Git blob;
- mutable CURRENT_* sources are authoritative by path and required semantics
  are rechecked against their current bytes.

Any supplied independent row verifier must additionally bind the exact current
evidence source bytes it verified.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import escape_progress_shared_gap_audit_v4 as v4
from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)

SCHEMA = "PROJECT_BRAIN_ESCAPE_PROGRESS_SHARED_GAP_EXECUTABLE_AUDIT_V5"
ROOT = Path(__file__).resolve().parents[2]
CURRENT_CLASSIFICATION_PATH = (
    ROOT / "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"
)
GAP_A_RESIDUAL = "ESCAPE_GAP_A_ACQUISITION_TOTALITY"
GAP_B_RESIDUAL = "ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"


class EscapeProgressAuditV5Error(ValueError):
    pass


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _byte_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_mutable_current_path(rel: str) -> bool:
    return Path(rel).name.startswith("CURRENT_")


def _resolve_row_current_evidence(
    row: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    root = Path(repo_root)
    evidence = row.get("evidence")
    errors: list[str] = []
    warnings: list[str] = []
    if (
        not isinstance(evidence, list)
        or len(evidence) != 2
        or not isinstance(evidence[0], str)
        or not evidence[0]
        or not isinstance(evidence[1], str)
        or not evidence[1]
    ):
        return {
            "pass": False,
            "errors": ["ROW_EVIDENCE_REFERENCE_INVALID"],
            "path": None,
            "binding_mode": None,
        }

    rel = evidence[0]
    manifest_blob = evidence[1]
    path = root / rel
    if not path.is_file():
        return {
            "pass": False,
            "errors": ["ROW_EVIDENCE_SOURCE_MISSING"],
            "path": rel,
            "binding_mode": (
                "MUTABLE_CURRENT_PATH" if _is_mutable_current_path(rel)
                else "IMMUTABLE_GIT_BLOB"
            ),
        }

    data = path.read_bytes()
    actual_blob = _git_blob_sha(data)
    actual_sha256 = _byte_sha256(data)
    mutable = _is_mutable_current_path(rel)
    binding_mode = "MUTABLE_CURRENT_PATH" if mutable else "IMMUTABLE_GIT_BLOB"

    if not mutable and actual_blob != manifest_blob:
        errors.append("IMMUTABLE_EVIDENCE_BLOB_MISMATCH")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = ""
        errors.append("ROW_EVIDENCE_NOT_UTF8")

    required = row.get("required_strings")
    if not isinstance(required, list) or not all(
        isinstance(x, str) and x for x in required
    ):
        errors.append("ROW_REQUIRED_STRINGS_INVALID")
        required = []

    for token in required:
        if token not in text:
            if mutable:
                warnings.append("MUTABLE_REQUIRED_STRING_DRIFT:" + token)
            else:
                errors.append("CURRENT_REQUIRED_STRING_MISSING:" + token)

    return {
        "pass": not errors,
        "errors": errors,
        "warnings": warnings,
        "path": rel,
        "binding_mode": binding_mode,
        "manifest_observed_git_blob_sha": manifest_blob,
        "git_blob_sha": actual_blob,
        "byte_sha256": actual_sha256,
    }


def _current_evidence_verification_errors(
    verify: Mapping[str, Any],
    current: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if verify.get("current_route_semantics_verified") is not True:
        errors.append("ROW_PROOF_CURRENT_ROUTE_SEMANTICS_NOT_VERIFIED")
    subject = verify.get("current_evidence_subject")
    if not isinstance(subject, Mapping):
        errors.append("ROW_PROOF_CURRENT_EVIDENCE_SUBJECT_REQUIRED")
        return errors
    for key in ("path", "git_blob_sha", "byte_sha256"):
        if subject.get(key) != current.get(key):
            errors.append("ROW_PROOF_CURRENT_EVIDENCE_SUBJECT_MISMATCH:" + key)
    return errors


def _load_current_manifest_binding(
    *,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    root = Path(repo_root)
    current_path = root / CURRENT_CLASSIFICATION_PATH.relative_to(ROOT)
    if not current_path.is_file():
        raise EscapeProgressAuditV5Error("CURRENT_CLASSIFICATION_MISSING")
    current = json.loads(current_path.read_text(encoding="utf-8"))
    rows = current.get("classifications")
    if not isinstance(rows, list):
        raise EscapeProgressAuditV5Error("CURRENT_CLASSIFICATIONS_INVALID")

    by_id = {
        row.get("residual_id"): row
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("residual_id"), str)
    }
    a = by_id.get(GAP_A_RESIDUAL)
    b = by_id.get(GAP_B_RESIDUAL)
    if not isinstance(a, Mapping) or not isinstance(b, Mapping):
        raise EscapeProgressAuditV5Error("CURRENT_ESCAPE_RESIDUALS_MISSING")

    a_binding = a.get("existing_binding")
    b_binding = b.get("existing_binding")
    if (
        not isinstance(a_binding, str)
        or not a_binding
        or a_binding != b_binding
    ):
        raise EscapeProgressAuditV5Error("CURRENT_ESCAPE_BINDING_DIVERGENCE")

    binding_path = root / a_binding
    if not binding_path.is_file():
        raise EscapeProgressAuditV5Error("CURRENT_ESCAPE_BINDING_MISSING")
    binding = json.loads(binding_path.read_text(encoding="utf-8"))

    manifest_ref = binding.get("current_successor_manifest")
    if not isinstance(manifest_ref, Mapping):
        raise EscapeProgressAuditV5Error("CURRENT_SUCCESSOR_MANIFEST_REFERENCE_MISSING")
    manifest_rel = manifest_ref.get("path")
    if not isinstance(manifest_rel, str) or not manifest_rel:
        raise EscapeProgressAuditV5Error("CURRENT_SUCCESSOR_MANIFEST_PATH_INVALID")
    manifest_path = root / manifest_rel
    if not manifest_path.is_file():
        raise EscapeProgressAuditV5Error("CURRENT_SUCCESSOR_MANIFEST_MISSING")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    return {
        "classification_path": str(CURRENT_CLASSIFICATION_PATH.relative_to(ROOT)),
        "binding_path": a_binding,
        "binding": binding,
        "manifest_path": manifest_rel,
        "manifest": manifest,
    }


def audit(
    manifest: Mapping[str, Any],
    binding: Mapping[str, Any],
    row_proof_bindings: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    root = Path(repo_root)
    supplied = (
        row_proof_bindings if isinstance(row_proof_bindings, Mapping) else {}
    )
    rows = manifest.get("rows") if isinstance(manifest, Mapping) else None
    currentness_rows: list[dict[str, Any]] = []
    currentness_errors: list[str] = []
    currentness_warnings: list[str] = []
    current_by_oid: dict[str, Mapping[str, Any]] = {}

    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            oid = str(row.get("obligation_id") or "")
            current = _resolve_row_current_evidence(row, repo_root=root)
            current_by_oid[oid] = current
            currentness_rows.append({
                "obligation_id": oid,
                "pass": current.get("pass") is True,
                "binding_mode": current.get("binding_mode"),
                "path": current.get("path"),
                "git_blob_sha": current.get("git_blob_sha"),
                "byte_sha256": current.get("byte_sha256"),
                "errors": list(current.get("errors") or []),
                "warnings": list(current.get("warnings") or []),
            })
            for error in current.get("errors") or []:
                currentness_errors.append(oid + ":" + str(error))
            for warning in current.get("warnings") or []:
                currentness_warnings.append(oid + ":" + str(warning))
    else:
        currentness_errors.append("MANIFEST_ROWS_INVALID")

    filtered: dict[str, Mapping[str, Any]] = {}
    proof_currentness_errors: list[str] = []
    for oid, ref in supplied.items():
        current = current_by_oid.get(str(oid))
        if not isinstance(current, Mapping) or current.get("pass") is not True:
            proof_currentness_errors.append(
                str(oid) + ":ROW_CURRENT_EVIDENCE_NOT_VALID"
            )
            continue
        if not isinstance(ref, Mapping):
            proof_currentness_errors.append(
                str(oid) + ":ROW_PROOF_BINDING_NOT_OBJECT"
            )
            continue
        verify_ref = ref.get("independent_verification")
        if not isinstance(verify_ref, Mapping):
            proof_currentness_errors.append(
                str(oid) + ":ROW_PROOF_INDEPENDENT_VERIFICATION_REFERENCE_REQUIRED"
            )
            continue
        try:
            verify_bound = resolve_receipt_bytes(verify_ref, repo_root=root)
        except ReceiptResolutionError as exc:
            proof_currentness_errors.append(
                str(oid) + ":ROW_PROOF_VERIFICATION_BYTE_BINDING_INVALID:" + str(exc)
            )
            continue
        verify_doc = verify_bound["document"]
        errors = _current_evidence_verification_errors(verify_doc, current)
        if errors:
            proof_currentness_errors.extend(str(oid) + ":" + e for e in errors)
            continue
        filtered[str(oid)] = ref

    structural = v4.audit(
        manifest,
        binding,
        row_proof_bindings=filtered,
        repo_root=root,
    )
    all_currentness_errors = sorted(
        set(currentness_errors + proof_currentness_errors)
    )
    pass_gate = structural.get("pass") is True and not currentness_errors
    cc_r3 = (
        structural.get("cc_r3_proved") is True
        and not all_currentness_errors
    )
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CURRENT_AUTHENTICATED_CC_R3_PROVED"
            if cc_r3
            else (
                "PASS__CURRENTNESS_AWARE_AUDIT__CC_R3_OPEN"
                if pass_gate
                else "FAIL_CLOSED__ROW_SOURCE_CURRENTNESS_INVALID"
            )
        ),
        "pass": pass_gate,
        "cc_r3_proved": cc_r3,
        "currentness_errors": all_currentness_errors,
        "currentness_warnings": sorted(set(currentness_warnings)),
        "currentness_rows": currentness_rows,
        "authenticated_current_row_proof_count": len(filtered),
        "v4_audit": structural,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
        "rule": (
            "IMMUTABLE_ROW_SOURCES_REQUIRE_EXACT_MANIFEST_BYTES__MUTABLE_CURRENT_"
            "SOURCES_ARE_PATH_AUTHORITATIVE_WITH_SUMMARY_DRIFT_NONAUTHORITATIVE__"
            "ROW_CREDIT_REQUIRES_DISTINCT_VERIFIER_BINDING_EXACT_CURRENT_EVIDENCE_"
            "BYTES_AND_ATTESTING_CURRENT_ROUTE_SEMANTICS"
        ),
    }


def audit_repo(
    root: Path = ROOT,
    row_proof_bindings: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    resolved = _load_current_manifest_binding(repo_root=root)
    out = audit(
        resolved["manifest"],
        resolved["binding"],
        row_proof_bindings=row_proof_bindings,
        repo_root=root,
    )
    out["classification_path"] = resolved["classification_path"]
    out["binding_path"] = resolved["binding_path"]
    out["manifest_path"] = resolved["manifest_path"]
    return out


if __name__ == "__main__":
    print(json.dumps(audit_repo(), sort_keys=True))
