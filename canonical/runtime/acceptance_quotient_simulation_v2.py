"""Semantic hardening wrapper for acceptance-quotient simulation V1.

V1 checks finite graph simulation but does not, by itself, certify that the
declared relation is a material noninferiority relation or that scope/authority
holds for each realizing macroedge. V2 makes those semantic premises explicit
content-addressed receipt obligations before delegating graph mechanics to V1.

This remains a structural verifier: independent receipt files must themselves
be verified on their exact bytes before any acceptance credit.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.acceptance_quotient_simulation_v1 import (
    verify_acceptance_quotient_certificate as verify_v1,
)

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_QUOTIENT_SIMULATION_V2"


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


def verify_acceptance_quotient_certificate_v2(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        relation_receipt = _receipt(
            cert.get("relation_soundness_receipt"),
            "RELATION_SOUNDNESS_RECEIPT",
            (
                "acceptance_preorder_sound",
                "load_bearing_dimensions_complete",
                "scope_complete",
                "independent_or_objective",
            ),
        )
        terminal_receipt = _receipt(
            cert.get("terminal_acceptance_receipt"),
            "TERMINAL_ACCEPTANCE_RECEIPT",
            (
                "terminal_noninferiority_sound",
                "scope_complete",
                "independent_or_objective",
            ),
        )

        raw_edges = cert.get("brain_macro_edges")
        if not isinstance(raw_edges, list):
            raise CertificateError("BRAIN_MACRO_EDGES_INVALID")
        transformed = copy.deepcopy(dict(cert))
        transformed_edges = transformed.get("brain_macro_edges")
        scope_receipts = []
        for index, (raw, edge) in enumerate(zip(raw_edges, transformed_edges)):
            if not isinstance(raw, Mapping) or not isinstance(edge, dict):
                raise CertificateError(f"BRAIN_EDGE_{index}_INVALID")
            scope_receipt = _receipt(
                raw.get("scope_authority_receipt"),
                f"BRAIN_EDGE_{index}_SCOPE_AUTHORITY_RECEIPT",
                (
                    "invariant_holds",
                    "scope_complete",
                    "universal_over_realizations",
                    "independent_or_objective",
                ),
            )
            scope_receipts.append(scope_receipt)
            # V1 consumes this Boolean mechanically. V2 permits it only after a
            # content-addressed semantic receipt has been supplied.
            edge["scope_authority_invariant"] = True

        v1 = verify_v1(transformed)
        if v1.get("status") != "PASS":
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "reason": "V1_GRAPH_MECHANICS_FAILED:" + str(v1.get("reason") or "UNKNOWN"),
                "acceptance_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "theorem": "SEMANTICALLY_BOUND_ACCEPTANCE_QUOTIENT_SIMULATION_V2",
            "graph_mechanics": v1,
            "relation_soundness_receipt": relation_receipt,
            "terminal_acceptance_receipt": terminal_receipt,
            "scope_authority_receipts": scope_receipts,
            "semantic_relation_receipt_required": True,
            "naked_scope_authority_boolean_accepted": False,
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
