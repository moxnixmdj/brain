"""P3 real-context admission v9.

Preserves every current V8 positive route and every V8 fail-closed explicit
selection-authority rule. Only when neither explicit objective weights nor an
exact decision-dependency contract is supplied may V9 try the independently
verified nonbinding-capacity common-policy cell.

That cell closes optional relevance only when all source-grounded safe claims
fit inside the explicit item budget, so no salience choice remains.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.p3_real_context_v3_admission_v8 import evaluate as evaluate_v8
from canonical.runtime.p3_nonbinding_capacity_common_policy_cell_v1 import (
    evaluate as evaluate_nonbinding,
)
from canonical.runtime.p3_v3_contract_surface_guard_v1 import validate_v3_contract_surface

SCHEMA = "PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V9"
_ALLOWED_PAYLOAD_FIELDS = {
    "context_id", "v3_input", "objective_weights", "semantic_certificates",
    "decision_dependency_contract",
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "v3_admission_authorized": False,
        "p3_contract_cell_authorized": False,
        "top_law_eligible": False,
        "source_authorization_verified": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _nonbinding_boundary_ok(r: Mapping[str, Any]) -> bool:
    return (
        r.get("pass") is True
        and r.get("p3_contract_cell_authorized") is True
        and r.get("top_law_eligible") is True
        and r.get("policy_adequacy_authority") is False
        and r.get("db_admission_authority") is False
        and r.get("u_subtraction_authority") is False
        and r.get("terminal_authority") is False
        and r.get("terminal_credit_delta") == 0
    )


def evaluate(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    prior = evaluate_v8(payload, repo_root=repo_root)
    if prior.get("pass") is True:
        out = dict(prior)
        out["schema"] = SCHEMA
        out["v8_preserved_positive_route"] = True
        return out

    # Never let a weaker implicit/common-policy route override an explicit
    # selection authority that V8 rejected or found inconsistent.
    if "objective_weights" in payload or "decision_dependency_contract" in payload:
        out = dict(prior)
        out["schema"] = SCHEMA
        out["v8_preserved_positive_route"] = False
        out["nonbinding_capacity_fast_path_pass"] = False
        return out

    if set(payload) - _ALLOWED_PAYLOAD_FIELDS:
        return _fail("UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS")

    context_id = payload.get("context_id")
    if not isinstance(context_id, str) or not context_id.strip():
        return _fail("CONTEXT_ID_REQUIRED")

    public = payload.get("v3_input")
    if not isinstance(public, Mapping):
        return _fail("V3_INPUT_REQUIRED")
    surface_failure = validate_v3_contract_surface(public)
    if surface_failure is not None:
        return _fail(surface_failure)

    candidate = evaluate_nonbinding({"v3_input": public})
    if candidate.get("pass") is True:
        if not _nonbinding_boundary_ok(candidate):
            return _fail("NONBINDING_CELL_AUTHORITY_BOUNDARY_INVALID")
        v3_result = candidate.get("v3_result") or {}
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__P3_REAL_CONTEXT_NONBINDING_CAPACITY_COMMON_POLICY",
            "route": "NONBINDING_CAPACITY_COMMON_POLICY_CELL_V1",
            "context_id": context_id,
            "selected_claim_ids": list(candidate.get("selected_claim_ids") or []),
            "selected_optional_claim_ids": list(
                candidate.get("selected_optional_claim_ids") or []
            ),
            "rendered_text": v3_result.get("rendered_text"),
            "render_trace": list(v3_result.get("render_trace") or []),
            "v3_admission_authorized": True,
            "p3_contract_cell_authorized": True,
            "top_law_eligible": True,
            "source_authorization_verified": False,
            "policy_adequacy_authority": False,
            "db_admission_authority": False,
            "u_subtraction_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "route_receipt": candidate,
            "explicit_authority_consumed": None,
            "v8_preserved_positive_route": False,
        }

    out = dict(prior)
    out["schema"] = SCHEMA
    out["v8_preserved_positive_route"] = False
    out["nonbinding_capacity_fast_path_pass"] = False
    out["nonbinding_capacity_reason"] = candidate.get("reason") or candidate.get("status")
    return out


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {}, repo_root=root)
