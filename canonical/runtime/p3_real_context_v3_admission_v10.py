"""P3 real-context admission v10.

Preserves every V9 positive route and every stronger explicit selection-authority
boundary. V10 adds one narrow capacity-binding route: an independently verified
policy-influence partition whose residual semantic variation is proved
noninterfering with the committed adequate selection policy.

The new route is tried only when V9 reaches exactly
CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY and no explicit objective-weight or
exact decision-dependency authority was supplied.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.p3_real_context_v3_admission_v9 import evaluate as evaluate_v9
from canonical.runtime.p3_policy_influence_relevance_cell_v1 import (
    evaluate as evaluate_policy_influence,
)

SCHEMA = "PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V10"
_ALLOWED_PAYLOAD_FIELDS = {
    "context_id",
    "v3_input",
    "objective_weights",
    "semantic_certificates",
    "decision_dependency_contract",
    "policy_influence_contract",
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "v3_admission_authorized": False,
        "p3_contract_cell_authorized": False,
        "policy_influence_noninterference_verified": False,
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


def _boundary_ok(result: Mapping[str, Any]) -> bool:
    return (
        result.get("pass") is True
        and result.get("p3_contract_cell_authorized") is True
        and result.get("policy_influence_noninterference_verified") is True
        and result.get("source_authorization_verified") is False
        and result.get("policy_adequacy_authority") is False
        and result.get("db_admission_authority") is False
        and result.get("u_subtraction_authority") is False
        and result.get("terminal_authority") is False
        and result.get("terminal_credit_delta") == 0
    )


def evaluate(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    extra = set(payload) - _ALLOWED_PAYLOAD_FIELDS
    if extra:
        return _fail("UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS", extra=sorted(extra))

    prior_payload = {
        k: v for k, v in payload.items() if k != "policy_influence_contract"
    }
    prior = evaluate_v9(prior_payload, repo_root=repo_root)
    if prior.get("pass") is True:
        out = dict(prior)
        out["schema"] = SCHEMA
        out["v9_preserved_positive_route"] = True
        out["policy_influence_fast_path_pass"] = False
        return out

    if "objective_weights" in payload or "decision_dependency_contract" in payload:
        out = dict(prior)
        out["schema"] = SCHEMA
        out["v9_preserved_positive_route"] = False
        out["policy_influence_fast_path_pass"] = False
        return out

    contract_present = "policy_influence_contract" in payload
    if not contract_present:
        out = dict(prior)
        out["schema"] = SCHEMA
        out["v9_preserved_positive_route"] = False
        out["policy_influence_fast_path_pass"] = False
        return out

    if not isinstance(payload.get("policy_influence_contract"), Mapping):
        return _fail("POLICY_INFLUENCE_CONTRACT_INVALID")

    if prior.get("nonbinding_capacity_reason") != "CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY":
        out = dict(prior)
        out["schema"] = SCHEMA
        out["v9_preserved_positive_route"] = False
        out["policy_influence_fast_path_pass"] = False
        out["policy_influence_not_applicable_reason"] = (
            "V9_DID_NOT_REACH_CAPACITY_BINDING_RELEVANCE_FRONTIER"
        )
        return out

    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    candidate = evaluate_policy_influence(
        {
            "v3_input": payload.get("v3_input"),
            "policy_influence_contract": payload.get("policy_influence_contract"),
        },
        repo_root=root,
    )
    if candidate.get("pass") is not True:
        return _fail(
            "POLICY_INFLUENCE_CONTRACT_UNSATISFIED",
            policy_influence_result=candidate,
        )
    if not _boundary_ok(candidate):
        return _fail("POLICY_INFLUENCE_AUTHORITY_BOUNDARY_INVALID")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__P3_REAL_CONTEXT_POLICY_INFLUENCE_NONINTERFERENCE",
        "route": "POLICY_INFLUENCE_NONINTERFERENCE_RELEVANCE_CELL_V1",
        "context_id": payload.get("context_id"),
        "selected_policy_id": candidate.get("selected_policy_id"),
        "selected_claim_ids": list(candidate.get("selected_claim_ids") or []),
        "relevance_bits": dict(candidate.get("relevance_bits") or {}),
        "rendered_text": candidate.get("rendered_text"),
        "render_trace": list(candidate.get("render_trace") or []),
        "v3_admission_authorized": True,
        "p3_contract_cell_authorized": True,
        "policy_influence_noninterference_verified": True,
        "top_law_eligible": False,
        "source_authorization_verified": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "route_receipt": candidate,
        "explicit_authority_consumed": "POLICY_INFLUENCE_CONTRACT",
        "v9_preserved_positive_route": False,
        "boundary": (
            "CAPACITY_BINDING_NO_EXPLICIT_WEIGHTS_NO_EXACT_DEPENDENCY_CONTRACT;"
            "INDEPENDENTLY_VERIFIED_POLICY_WORLD_PARTITION_ONLY"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {}, repo_root=root)
