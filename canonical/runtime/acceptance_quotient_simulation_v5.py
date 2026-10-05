"""Policy-identity hardening for acceptance-quotient simulation V4.

V3 requires a single causal policy semantically, but neither V3 nor V4
mechanically ties the global strategy receipt, per-edge policy bindings, and
policy-distribution receipt to the same policy identity. V5 closes that
referential-integrity gap with a content commitment.

This remains a structural verifier. Referenced receipt bytes require separate
independent verification before any acceptance credit.
"""
from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from canonical.runtime.acceptance_quotient_simulation_v4 import (
    STOCHASTIC_CLASS,
    DISTRIBUTION_FREE_CLASSES,
    verify_acceptance_quotient_certificate_v4 as verify_v4,
)

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_QUOTIENT_SIMULATION_V5"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CertificateError(ValueError):
    pass


def _commitment(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise CertificateError(label + "_INVALID")
    return value


def _receipt_mapping(cert: Mapping[str, Any], key: str, label: str) -> Mapping[str, Any]:
    value = cert.get(key)
    if not isinstance(value, Mapping):
        raise CertificateError(label + "_INVALID")
    return value


def _receipt_commitment(
    receipt: Mapping[str, Any],
    expected: str,
    label: str,
) -> str:
    got = _commitment(receipt.get("policy_commitment_sha256"), label + "_POLICY_COMMITMENT")
    if got != expected:
        raise CertificateError(label + "_POLICY_COMMITMENT_MISMATCH")
    return got


def _bind_distribution_free_receipt(
    cert: Mapping[str, Any],
    expected: str,
) -> dict[str, Any]:
    receipt = _receipt_mapping(
        cert,
        "distribution_free_dominance_receipt",
        "DISTRIBUTION_FREE_DOMINANCE_RECEIPT",
    )
    if receipt.get("universal_over_all_admissible_brain_policies") is True:
        return {
            "mode": "UNIVERSAL_OVER_ALL_ADMISSIBLE_BRAIN_POLICIES",
            "policy_commitment_required": False,
        }
    got = _receipt_commitment(
        receipt,
        expected,
        "DISTRIBUTION_FREE_DOMINANCE_RECEIPT",
    )
    return {
        "mode": "BOUND_POLICY",
        "policy_commitment_required": True,
        "policy_commitment_sha256": got,
    }


def verify_acceptance_quotient_certificate_v5(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        strategy = _receipt_mapping(
            cert,
            "causal_strategy_receipt",
            "CAUSAL_STRATEGY_RECEIPT",
        )
        policy_commitment = _commitment(
            strategy.get("policy_commitment_sha256"),
            "CAUSAL_STRATEGY_RECEIPT_POLICY_COMMITMENT",
        )

        raw_edges = cert.get("brain_macro_edges")
        if not isinstance(raw_edges, list):
            raise CertificateError("BRAIN_MACRO_EDGES_INVALID")
        edge_bindings = []
        for index, edge in enumerate(raw_edges):
            if not isinstance(edge, Mapping):
                raise CertificateError(f"BRAIN_EDGE_{index}_INVALID")
            receipt = edge.get("causal_policy_binding_receipt")
            if not isinstance(receipt, Mapping):
                raise CertificateError(
                    f"BRAIN_EDGE_{index}_CAUSAL_POLICY_BINDING_RECEIPT_INVALID"
                )
            got = _receipt_commitment(
                receipt,
                policy_commitment,
                f"BRAIN_EDGE_{index}_CAUSAL_POLICY_BINDING_RECEIPT",
            )
            edge_bindings.append(got)

        semantics = cert.get("acceptance_semantics_class")
        acceptance_binding: dict[str, Any]
        if semantics == STOCHASTIC_CLASS:
            distribution = _receipt_mapping(
                cert,
                "policy_distribution_bridge_receipt",
                "POLICY_DISTRIBUTION_BRIDGE_RECEIPT",
            )
            got = _receipt_commitment(
                distribution,
                policy_commitment,
                "POLICY_DISTRIBUTION_BRIDGE_RECEIPT",
            )
            acceptance_binding = {
                "mode": "BOUND_POLICY_DISTRIBUTION",
                "policy_commitment_sha256": got,
            }
        elif semantics in DISTRIBUTION_FREE_CLASSES:
            acceptance_binding = _bind_distribution_free_receipt(
                cert,
                policy_commitment,
            )
        else:
            # Let V4 preserve the exact unsupported-class failure, but never
            # allow an unrecognized class to bypass policy identity checks.
            acceptance_binding = {"mode": "UNSUPPORTED_PENDING_V4"}

        v4 = verify_v4(cert)
        if v4.get("status") != "PASS":
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "reason": "V4_ACCEPTANCE_CAUSAL_SEMANTIC_CHECK_FAILED:"
                + str(v4.get("reason") or "UNKNOWN"),
                "acceptance_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "theorem": "POLICY_IDENTITY_BOUND_ACCEPTANCE_QUOTIENT_SIMULATION_V5",
            "v4": v4,
            "policy_commitment_sha256": policy_commitment,
            "edge_policy_binding_count": len(edge_bindings),
            "all_edge_bindings_same_policy": True,
            "acceptance_policy_binding": acceptance_binding,
            "separate_existential_policy_receipts_sufficient": False,
            "shared_policy_commitment_required": True,
            "independent_receipt_byte_verification_still_required": True,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }
