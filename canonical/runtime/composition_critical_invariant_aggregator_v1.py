"""Fail-closed deterministic aggregator for critical composition invariants.

The verifier does not discover the invariant universe and does not prove any
invariant. It only proves the final aggregation step once a scope-complete
independent registry receipt and scope-complete invariant receipts are bound.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_COMPOSITION_CRITICAL_INVARIANT_AGGREGATOR_V1"


class CertificateError(ValueError):
    pass


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CertificateError(label + "_INVALID")
    return value.strip()


def _seq(value: Any, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CertificateError(label + "_INVALID")
    return list(value)


def _receipt(value: Any, label: str, fields: Sequence[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CertificateError(label + "_INVALID")
    path = _token(value.get("path"), label + "_PATH")
    sha = _token(value.get("git_blob_sha"), label + "_SHA")
    for field in fields:
        if value.get(field) is not True:
            raise CertificateError(label + "_" + field.upper() + "_NOT_TRUE")
    return {"path": path, "git_blob_sha": sha, **{field: True for field in fields}}


def verify_critical_invariant_certificate(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        raw_registry = _seq(cert.get("critical_invariants"), "CRITICAL_INVARIANTS")
        invariants: list[str] = []
        for i, item in enumerate(raw_registry):
            if not isinstance(item, Mapping):
                raise CertificateError(f"INVARIANT_{i}_NOT_OBJECT")
            invariant_id = _token(item.get("id"), f"INVARIANT_{i}_ID")
            if item.get("critical") is not True:
                raise CertificateError(f"INVARIANT_{i}_NOT_CRITICAL")
            invariants.append(invariant_id)
        if not invariants:
            raise CertificateError("CRITICAL_INVARIANTS_EMPTY")
        if len(invariants) != len(set(invariants)):
            raise CertificateError("CRITICAL_INVARIANT_ID_DUPLICATE")

        registry_receipt = _receipt(
            cert.get("registry_receipt"),
            "REGISTRY_RECEIPT",
            (
                "scope_complete_for_frozen_acceptance",
                "independent_or_objective",
            ),
        )

        receipts = cert.get("invariant_receipts")
        if not isinstance(receipts, Mapping):
            raise CertificateError("INVARIANT_RECEIPTS_INVALID")
        if set(receipts) != set(invariants):
            missing = sorted(set(invariants) - set(receipts))
            extra = sorted(set(receipts) - set(invariants))
            if missing:
                raise CertificateError("INVARIANT_RECEIPT_MISSING:" + missing[0])
            raise CertificateError("INVARIANT_RECEIPT_EXTRA:" + extra[0])

        bound: dict[str, dict[str, Any]] = {}
        for invariant_id in invariants:
            bound[invariant_id] = _receipt(
                receipts[invariant_id],
                "INVARIANT_RECEIPT_" + invariant_id,
                (
                    "proved",
                    "scope_complete",
                    "independent_or_objective",
                ),
            )

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "theorem": "COMPLETE_CRITICAL_INVARIANT_REGISTRY_PLUS_UNIVERSAL_PROOFS_IMPLIES_ZERO_CRITICAL_FAILURE_COUNT",
            "critical_invariant_count": len(invariants),
            "critical_failure_count": 0,
            "critical_failure_threshold": 0,
            "registry_receipt": registry_receipt,
            "bound_receipt_count": len(bound),
            "aggregation_requires_new_reality": False,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "critical_failure_count": None,
            "acceptance_credit_delta": 0,
        }
