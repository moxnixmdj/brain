"""Acceptance-class gate over causal-strategy quotient simulation V3.

V3 prevents per-target-edge oracle selection by requiring one owned causal
policy. V4 additionally binds the acceptance semantics class so stochastic
matched noninferiority cannot be inferred from structural/causal trace
simulation unless a policy-level distribution, stochastic-dominance, or
expected-utility bridge is independently certified.

This module verifies receipt shape only. Exact receipt bytes remain a separate
independent promotion gate.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.acceptance_quotient_simulation_v3 import (
    verify_acceptance_quotient_certificate_v3 as verify_v3,
)

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_QUOTIENT_SIMULATION_V4"
STOCHASTIC_CLASS = "STOCHASTIC_MATCHED_NONINFERIORITY"
DISTRIBUTION_FREE_CLASSES = {
    "OBJECTIVE_CEILING",
    "UNIVERSAL_TOP_SUPPORT",
    "UNIVERSAL_ZERO_VIOLATION",
    "NONPROBABILISTIC_COMPLETE_ORDER",
}


class CertificateError(ValueError):
    pass


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CertificateError(label + "_INVALID")
    return value.strip()


def _receipt(value: Any, label: str, required_true: Sequence[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CertificateError(label + "_INVALID")
    path = _token(value.get("path"), label + "_PATH")
    sha = _token(value.get("git_blob_sha"), label + "_SHA")
    for field in required_true:
        if value.get(field) is not True:
            raise CertificateError(label + "_" + field.upper() + "_NOT_TRUE")
    return {"path": path, "git_blob_sha": sha, **{f: True for f in required_true}}


def _verify_acceptance_class(cert: Mapping[str, Any]) -> dict[str, Any]:
    semantics = _token(
        cert.get("acceptance_semantics_class"),
        "ACCEPTANCE_SEMANTICS_CLASS",
    )

    if semantics == STOCHASTIC_CLASS:
        receipt = _receipt(
            cert.get("policy_distribution_bridge_receipt"),
            "POLICY_DISTRIBUTION_BRIDGE_RECEIPT",
            (
                "policy_choice_coherent",
                "scope_complete",
                "distribution_or_expected_utility_order_proved",
                "independent_or_objective",
            ),
        )
        return {
            "acceptance_semantics_class": semantics,
            "target_distribution_or_equivalent_information_required": True,
            "distribution_requirement_satisfied_by": receipt,
        }

    if semantics == "OBJECTIVE_CEILING":
        receipt = _receipt(
            cert.get("distribution_free_dominance_receipt"),
            "DISTRIBUTION_FREE_DOMINANCE_RECEIPT",
            (
                "objective_ceiling_proved",
                "scope_complete",
                "target_distribution_irrelevant",
                "independent_or_objective",
            ),
        )
    elif semantics == "UNIVERSAL_TOP_SUPPORT":
        receipt = _receipt(
            cert.get("distribution_free_dominance_receipt"),
            "DISTRIBUTION_FREE_DOMINANCE_RECEIPT",
            (
                "class_wide_top_support_dominance_proved",
                "scope_complete",
                "target_distribution_irrelevant",
                "independent_or_objective",
            ),
        )
    elif semantics == "UNIVERSAL_ZERO_VIOLATION":
        receipt = _receipt(
            cert.get("distribution_free_dominance_receipt"),
            "DISTRIBUTION_FREE_DOMINANCE_RECEIPT",
            (
                "universal_zero_violation_proved",
                "absolute_bound_proved",
                "scope_complete",
                "independent_or_objective",
            ),
        )
    elif semantics == "NONPROBABILISTIC_COMPLETE_ORDER":
        receipt = _receipt(
            cert.get("distribution_free_dominance_receipt"),
            "DISTRIBUTION_FREE_DOMINANCE_RECEIPT",
            (
                "complete_order_preservation_proved",
                "scope_complete",
                "independent_or_objective",
            ),
        )
    else:
        raise CertificateError(
            "ACCEPTANCE_SEMANTICS_CLASS_UNSUPPORTED:" + semantics
        )

    return {
        "acceptance_semantics_class": semantics,
        "target_distribution_or_equivalent_information_required": False,
        "distribution_requirement_satisfied_by": receipt,
    }


def verify_acceptance_quotient_certificate_v4(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        acceptance = _verify_acceptance_class(cert)
        v3 = verify_v3(cert)
        if v3.get("status") != "PASS":
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "reason": "V3_CAUSAL_SEMANTIC_GRAPH_CHECK_FAILED:"
                + str(v3.get("reason") or "UNKNOWN"),
                "acceptance_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "theorem": "ACCEPTANCE_CLASS_AND_CAUSAL_POLICY_BOUND_QUOTIENT_SIMULATION_V4",
            "v3": v3,
            **acceptance,
            "support_or_edge_matching_alone_sufficient_for_stochastic_noninferiority": False,
            "single_owned_causal_policy_alone_sufficient_for_stochastic_noninferiority": False,
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
