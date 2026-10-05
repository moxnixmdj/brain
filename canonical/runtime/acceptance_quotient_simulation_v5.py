"""Acceptance-semantics binding gate over quotient simulation V4.

V4 correctly distinguishes stochastic matched noninferiority from several
classes that can, with a sufficient receipt, be proved without a target
distribution. But V4 trusts the certificate's self-declared
`acceptance_semantics_class`. Without an independently bound classification,
a stochastic obligation could be mislabeled as distribution-free and bypass
the policy-distribution bridge.

V5 closes that classification-boundary hole. It requires an independently
verifiable receipt binding the exact acceptance obligation and behavioral
contract to the declared semantics class before V4 is allowed to discharge the
class-specific proof rule.

This module still verifies receipt shape only. Exact receipt bytes remain a
separate independent promotion gate.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.acceptance_quotient_simulation_v4 import (
    STOCHASTIC_CLASS,
    DISTRIBUTION_FREE_CLASSES,
    verify_acceptance_quotient_certificate_v4 as verify_v4,
)

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_QUOTIENT_SIMULATION_V5"
SUPPORTED_CLASSES = {STOCHASTIC_CLASS, *DISTRIBUTION_FREE_CLASSES}


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


def _verify_semantics_binding(cert: Mapping[str, Any]) -> dict[str, Any]:
    declared = _token(
        cert.get("acceptance_semantics_class"),
        "ACCEPTANCE_SEMANTICS_CLASS",
    )
    if declared not in SUPPORTED_CLASSES:
        raise CertificateError(
            "ACCEPTANCE_SEMANTICS_CLASS_UNSUPPORTED:" + declared
        )

    raw = cert.get("acceptance_semantics_binding_receipt")
    receipt = _receipt(
        raw,
        "ACCEPTANCE_SEMANTICS_BINDING_RECEIPT",
        (
            "acceptance_obligation_bound",
            "behavioral_contract_bound",
            "class_assignment_sound",
            "classification_complete_on_claimed_scope",
            "distribution_dependence_decided",
            "scope_complete",
            "independent_or_objective",
        ),
    )
    assert isinstance(raw, Mapping)

    obligation_id = _token(
        raw.get("acceptance_obligation_id"),
        "ACCEPTANCE_SEMANTICS_BINDING_RECEIPT_ACCEPTANCE_OBLIGATION_ID",
    )
    contract_id = _token(
        raw.get("behavioral_contract_id"),
        "ACCEPTANCE_SEMANTICS_BINDING_RECEIPT_BEHAVIORAL_CONTRACT_ID",
    )
    bound_class = _token(
        raw.get("bound_acceptance_semantics_class"),
        "ACCEPTANCE_SEMANTICS_BINDING_RECEIPT_BOUND_CLASS",
    )

    if bound_class != declared:
        raise CertificateError(
            "ACCEPTANCE_SEMANTICS_BINDING_CLASS_MISMATCH:"
            + bound_class
            + "!="
            + declared
        )

    if declared == STOCHASTIC_CLASS:
        if raw.get("requires_distributional_comparison") is not True:
            raise CertificateError(
                "ACCEPTANCE_SEMANTICS_BINDING_STOCHASTIC_DISTRIBUTION_REQUIREMENT_NOT_TRUE"
            )
    else:
        if raw.get("distribution_free_class_proved") is not True:
            raise CertificateError(
                "ACCEPTANCE_SEMANTICS_BINDING_DISTRIBUTION_FREE_CLASS_NOT_PROVED"
            )

    return {
        **receipt,
        "acceptance_obligation_id": obligation_id,
        "behavioral_contract_id": contract_id,
        "bound_acceptance_semantics_class": bound_class,
        "requires_distributional_comparison": declared == STOCHASTIC_CLASS,
        "distribution_free_class_proved": declared in DISTRIBUTION_FREE_CLASSES,
    }


def verify_acceptance_quotient_certificate_v5(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        semantics_binding = _verify_semantics_binding(cert)
        v4 = verify_v4(cert)
        if v4.get("status") != "PASS":
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "reason": "V4_ACCEPTANCE_CLASS_OR_CAUSAL_GRAPH_CHECK_FAILED:"
                + str(v4.get("reason") or "UNKNOWN"),
                "acceptance_credit_delta": 0,
            }

        if (
            v4.get("acceptance_semantics_class")
            != semantics_binding["bound_acceptance_semantics_class"]
        ):
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "reason": "V4_V5_ACCEPTANCE_CLASS_BINDING_DIVERGENCE",
                "acceptance_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "theorem": "INDEPENDENTLY_BOUND_ACCEPTANCE_SEMANTICS_CAUSAL_QUOTIENT_SIMULATION_V5",
            "v4": v4,
            "acceptance_semantics_binding_receipt": semantics_binding,
            "self_declared_semantics_class_not_load_bearing": True,
            "stochastic_to_distribution_free_relabel_bypass_closed": True,
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
