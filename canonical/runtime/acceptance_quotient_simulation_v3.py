"""Causal-strategy hardening wrapper for acceptance-quotient simulation V2.

V2 binds graph simulation to semantic noninferiority/scope receipts, but the
underlying graph mechanics are still pointwise existential: for each target
edge, some matching Brain macroedge may be selected. That is insufficient for
an owned agent unless all such matches are induced by one causal Brain policy
whose choices depend only on information available at the decision prefix.

V3 makes that uniform-strategy premise explicit and fail-closed. It remains a
structural verifier: the referenced policy-binding receipt bytes must still be
independently verified before any acceptance credit.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.acceptance_quotient_simulation_v2 import (
    verify_acceptance_quotient_certificate_v2 as verify_v2,
)

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_QUOTIENT_SIMULATION_V3"


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


def verify_acceptance_quotient_certificate_v3(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        strategy_receipt = _receipt(
            cert.get("causal_strategy_receipt"),
            "CAUSAL_STRATEGY_RECEIPT",
            (
                "single_owned_policy",
                "complete_on_claimed_domain",
                "history_adapted",
                "no_future_or_target_oracle",
                "existential_matches_induced_by_policy",
                "independent_or_objective",
            ),
        )

        raw_edges = cert.get("brain_macro_edges")
        if not isinstance(raw_edges, list):
            raise CertificateError("BRAIN_MACRO_EDGES_INVALID")

        transformed = copy.deepcopy(dict(cert))
        policy_binding_receipts = []
        for index, raw in enumerate(raw_edges):
            if not isinstance(raw, Mapping):
                raise CertificateError(f"BRAIN_EDGE_{index}_INVALID")
            receipt = _receipt(
                raw.get("causal_policy_binding_receipt"),
                f"BRAIN_EDGE_{index}_CAUSAL_POLICY_BINDING_RECEIPT",
                (
                    "induced_by_bound_policy",
                    "choice_uses_current_or_past_information_only",
                    "no_target_edge_or_future_branch_oracle",
                    "scope_complete",
                    "independent_or_objective",
                ),
            )
            policy_binding_receipts.append(receipt)

        v2 = verify_v2(transformed)
        if v2.get("status") != "PASS":
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "reason": "V2_SEMANTIC_OR_GRAPH_CHECK_FAILED:" + str(v2.get("reason") or "UNKNOWN"),
                "acceptance_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "theorem": "SEMANTICALLY_BOUND_UNIFORM_CAUSAL_ACCEPTANCE_QUOTIENT_SIMULATION_V3",
            "v2": v2,
            "causal_strategy_receipt": strategy_receipt,
            "causal_policy_binding_receipts": policy_binding_receipts,
            "pointwise_existential_graph_match_not_load_bearing": True,
            "single_owned_causal_policy_required": True,
            "future_or_target_edge_oracle_forbidden": True,
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
