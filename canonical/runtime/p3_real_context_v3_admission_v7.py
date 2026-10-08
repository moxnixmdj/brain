"""P3 real-context admission v7.

Preserves every V6 positive route unchanged. If V6 fails closed, retries one
already independently verified bounded subregion where optional evidence
selection is driven by explicit audience kind priorities over typed Decimal
evidence, not caller-supplied relevance/support labels or explicit numeric
objective weights.

This is a front-door integration only. It does not prove source authorization,
general semantic salience, target-relative quality, U-empty, or terminality.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.p3_real_context_v3_admission_v6 import evaluate as evaluate_v6
from canonical.runtime.p3_audience_grounded_numeric_synthesis_v1 import (
    UnresolvedEvidence,
    solve as solve_grounded_numeric,
)

SCHEMA = "PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V7"


def _boundary() -> dict[str, Any]:
    return {
        "p3_contract_cell_authorized": False,
        "source_authorization_verified": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "PAYLOAD_MAPPING_REQUIRED",
            **_boundary(),
        }

    try:
        prior = evaluate_v6(payload)
    except Exception as exc:
        prior = {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "V6_PREDECESSOR_EXCEPTION",
            "detail": {"exception_type": type(exc).__name__, "detail_text": str(exc)[:160]},
            **_boundary(),
        }
    if prior.get("pass") is True:
        out = dict(prior)
        out["schema"] = SCHEMA
        out["v6_preserved_positive_route"] = True
        out["grounded_numeric_fast_path_pass"] = False
        return out

    candidate = payload.get("grounded_numeric_input")
    if isinstance(candidate, Mapping):
        try:
            result = solve_grounded_numeric(candidate)
        except UnresolvedEvidence as exc:
            result = {
                "status": "UNRESOLVED",
                "reason": str(exc),
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }

        if result.get("status") == "BOUNDED_NUMERIC_EVIDENCE_SYNTHESIS_WITH_AUDIENCE_CONDITIONING":
            if (
                result.get("source_authorization_verified") is not False
                or result.get("semantic_claim_adequacy_verified") is not False
                or result.get("target_relative_quality_verified") is not False
                or result.get("u_subtraction_authorized") is not False
                or result.get("terminal_authority") is not False
                or result.get("terminal_credit_delta") != 0
            ):
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "status": "FAIL_CLOSED",
                    "reason": "GROUNDED_NUMERIC_AUTHORITY_BOUNDARY_INVALID",
                    **_boundary(),
                }
            selected = result.get("selected_claims")
            if not isinstance(selected, list) or not selected or any(
                not isinstance(x, str) or not x for x in selected
            ):
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "status": "FAIL_CLOSED",
                    "reason": "GROUNDED_NUMERIC_SELECTED_CLAIMS_INVALID",
                    **_boundary(),
                }
            return {
                "schema": SCHEMA,
                "pass": True,
                "status": "PASS__P3_REAL_CONTEXT_GROUNDED_AUDIENCE_NUMERIC_FAST_PATH",
                "route": "GROUNDED_AUDIENCE_NUMERIC_SYNTHESIS_V1",
                "context_id": payload.get("context_id"),
                "selected_claim_ids": list(selected),
                "uncertainty_claim_ids": list(result.get("uncertainty_claims") or []),
                "audience_applied": result.get("audience_applied"),
                "claim_provenance": dict(result.get("claim_provenance") or {}),
                "p3_contract_cell_authorized": True,
                "source_authorization_verified": False,
                "policy_adequacy_authority": False,
                "db_admission_authority": False,
                "u_subtraction_authority": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
                "route_receipt": result,
                "v6_preserved_positive_route": False,
                "grounded_numeric_fast_path_pass": True,
                "boundary": (
                    "TYPED_DECIMAL_EVIDENCE_PLUS_EXPLICIT_AUDIENCE_KIND_PRIORITY_ONLY;"
                    "NO_CALLER_RELEVANCE_OR_SUPPORT_LABELS;NO_EXPLICIT_OBJECTIVE_WEIGHTS;"
                    "NO_GENERAL_SEMANTIC_SALIENCE_OR_SOURCE_AUTHORITY"
                ),
            }

    out = dict(prior)
    out["schema"] = SCHEMA
    out["v6_preserved_positive_route"] = False
    out["grounded_numeric_fast_path_pass"] = False
    return out


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {})
