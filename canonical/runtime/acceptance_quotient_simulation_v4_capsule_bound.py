"""Capsule-state hardening wrapper for acceptance quotient simulation V3.

V3 establishes semantic receipts and a single causal owned strategy, but its
Brain states are abstract identifiers. V4 binds every claimed Brain quotient
state to a structurally verified full-capsule cutpoint under one common
scope-complete cross-role channel receipt.

The external receipt truth is still load-bearing and must be independently
verified on exact bytes. This wrapper grants no acceptance credit by itself.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.acceptance_cutpoint_capsule_quotient_v1 import (
    verify_cutpoint,
)
from canonical.runtime.acceptance_quotient_simulation_v3 import (
    verify_acceptance_quotient_certificate_v3 as verify_v3,
)

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_QUOTIENT_SIMULATION_V4_CAPSULE_BOUND"


class CertificateError(ValueError):
    pass


def _seq(value: Any, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CertificateError(label + "_INVALID")
    return list(value)


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CertificateError(label + "_INVALID")
    return value.strip()


def verify_acceptance_quotient_certificate_v4(
    cert: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        brain_states = [
            _token(x, "BRAIN_STATE") for x in _seq(cert.get("brain_states"), "BRAIN_STATES")
        ]
        if not brain_states:
            raise CertificateError("BRAIN_STATES_EMPTY")
        if len(brain_states) != len(set(brain_states)):
            raise CertificateError("BRAIN_STATES_DUPLICATE")

        cutpoints = cert.get("brain_cutpoints")
        if not isinstance(cutpoints, Mapping):
            raise CertificateError("BRAIN_CUTPOINTS_INVALID")
        if set(cutpoints.keys()) != set(brain_states):
            missing = sorted(set(brain_states) - set(cutpoints.keys()))
            extra = sorted(set(cutpoints.keys()) - set(brain_states))
            raise CertificateError(
                "BRAIN_CUTPOINT_COVERAGE_MISMATCH:"
                + "missing="
                + ",".join(missing)
                + ":extra="
                + ",".join(extra)
            )

        receipt_binding = None
        cutpoint_digests: dict[str, str] = {}
        for state in brain_states:
            cutpoint = cutpoints[state]
            verdict = verify_cutpoint(cutpoint)
            if verdict.get("status") != "PASS":
                raise CertificateError(
                    "BRAIN_CUTPOINT_INVALID:"
                    + state
                    + ":"
                    + str(verdict.get("reason", "UNKNOWN"))
                )
            quotient = cutpoint["quotient"]
            binding = quotient["channel_receipt_binding"]
            if receipt_binding is None:
                receipt_binding = binding
            elif binding != receipt_binding:
                raise CertificateError("CHANNEL_RECEIPT_BINDING_DRIFT:" + state)
            cutpoint_digests[state] = verdict["quotient_sha256"]

        v3 = verify_v3(cert)
        if v3.get("status") != "PASS":
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "reason": "V3_SEMANTIC_CAUSAL_CHECK_FAILED:"
                + str(v3.get("reason", "UNKNOWN")),
                "acceptance_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "theorem": (
                "CAPSULE_BOUND_CAUSAL_ACCEPTANCE_QUOTIENT_SIMULATION_V4"
            ),
            "v3": v3,
            "brain_cutpoint_count": len(brain_states),
            "brain_cutpoint_digests": cutpoint_digests,
            "shared_channel_receipt_binding": receipt_binding,
            "full_capsule_retained_at_every_brain_quotient_state": True,
            "cross_role_state_evidence_receipt_uniform_across_states": True,
            "external_no_bypass_receipt_truth_still_load_bearing": True,
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
