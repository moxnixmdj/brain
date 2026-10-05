"""Fail-closed kernel for target-free top-support monotone dominance.

This kernel proves only the finite order-theoretic premise:
every certified Brain support class dominates every admissible outcome class.
It does NOT prove that a live Brain runtime is actually confined to that support.
That requires a separate scope-complete independent receipt.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_HIDDEN_EVALUATOR_TOP_SUPPORT_DOMINANCE_V1"


class CertificateError(ValueError):
    pass


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CertificateError(label + "_INVALID")
    return value.strip()


def _sequence(value: Any, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CertificateError(label + "_INVALID")
    return list(value)


def verify_top_support_certificate(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        raw_outcomes = _sequence(cert.get("outcomes"), "OUTCOMES")
        outcomes = [_token(x, "OUTCOME") for x in raw_outcomes]
        if not outcomes:
            raise CertificateError("OUTCOMES_EMPTY")
        if len(outcomes) != len(set(outcomes)):
            raise CertificateError("OUTCOMES_DUPLICATE")
        outcome_set = set(outcomes)

        raw_edges = _sequence(cert.get("dominance_edges"), "DOMINANCE_EDGES")
        reach: dict[str, set[str]] = {x: {x} for x in outcomes}
        for i, edge in enumerate(raw_edges):
            pair = _sequence(edge, f"EDGE_{i}")
            if len(pair) != 2:
                raise CertificateError(f"EDGE_{i}_ARITY")
            better = _token(pair[0], f"EDGE_{i}_BETTER")
            worse = _token(pair[1], f"EDGE_{i}_WORSE")
            if better not in outcome_set or worse not in outcome_set:
                raise CertificateError(f"EDGE_{i}_UNKNOWN_OUTCOME")
            reach[better].add(worse)

        # Transitive closure over the declared finite relation.
        changed = True
        while changed:
            changed = False
            for a in outcomes:
                closure = set(reach[a])
                for b in tuple(reach[a]):
                    closure.update(reach[b])
                if closure != reach[a]:
                    reach[a] = closure
                    changed = True

        # GE must be a partial order, not merely a preorder.
        for a in outcomes:
            for b in outcomes:
                if a != b and b in reach[a] and a in reach[b]:
                    raise CertificateError("DOMINANCE_NOT_ANTISYMMETRIC:" + a + ":" + b)

        support = [_token(x, "BRAIN_TOP_SUPPORT") for x in _sequence(cert.get("brain_top_support"), "BRAIN_TOP_SUPPORT")]
        if not support:
            raise CertificateError("BRAIN_TOP_SUPPORT_EMPTY")
        if len(support) != len(set(support)):
            raise CertificateError("BRAIN_TOP_SUPPORT_DUPLICATE")
        if any(x not in outcome_set for x in support):
            raise CertificateError("BRAIN_TOP_SUPPORT_UNKNOWN_OUTCOME")

        missing: list[tuple[str, str]] = []
        for brain_outcome in support:
            for target_outcome in outcomes:
                if target_outcome not in reach[brain_outcome]:
                    missing.append((brain_outcome, target_outcome))
        if missing:
            b, t = missing[0]
            raise CertificateError("TOP_SUPPORT_DOES_NOT_DOMINATE_ALL:" + b + ":" + t)

        receipt = cert.get("brain_support_receipt")
        if not isinstance(receipt, Mapping):
            raise CertificateError("BRAIN_SUPPORT_RECEIPT_INVALID")
        receipt_path = _token(receipt.get("path"), "BRAIN_SUPPORT_RECEIPT_PATH")
        receipt_sha = _token(receipt.get("git_blob_sha"), "BRAIN_SUPPORT_RECEIPT_SHA")
        if receipt.get("scope_complete") is not True:
            raise CertificateError("BRAIN_SUPPORT_RECEIPT_NOT_SCOPE_COMPLETE")
        if receipt.get("independent_or_objective") is not True:
            raise CertificateError("BRAIN_SUPPORT_RECEIPT_NOT_INDEPENDENT")

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "outcome_count": len(outcomes),
            "top_support_count": len(support),
            "target_distribution_required": False,
            "target_case_level_outputs_required_for_this_monotone_conjunct": False,
            "brain_support_receipt": {
                "path": receipt_path,
                "git_blob_sha": receipt_sha,
                "scope_complete": True,
                "independent_or_objective": True,
            },
            "theorem": "UNIVERSAL_TOP_SUPPORT_IMPLIES_TARGET_FREE_MONOTONE_DOMINANCE",
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "target_distribution_required": None,
            "acceptance_credit_delta": 0,
        }
