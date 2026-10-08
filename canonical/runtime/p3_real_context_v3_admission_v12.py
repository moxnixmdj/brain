"""P3 real-context admission v12.

Preserves V11 and all earlier positive routes/explicit authority precedence.
Only when V11 reaches the unweighted capacity-binding relevance frontier may
V12 invoke the verified bound relevance CEGAR loop.

The nested loop cannot override the top-level context or v3 input.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.p3_real_context_v3_admission_v11 import evaluate as evaluate_v11
from canonical.runtime.p3_bound_relevance_cegar_loop_v1 import evaluate as evaluate_loop

SCHEMA="PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V12"
_ALLOWED={
    "context_id","v3_input","objective_weights","semantic_certificates",
    "decision_dependency_contract","policy_influence_contract",
    "source_positive_selection_contract","bound_relevance_cegar_loop",
}
_STRONGER={
    "objective_weights","decision_dependency_contract",
    "policy_influence_contract","source_positive_selection_contract",
}
_LOOP_FIELDS={
    "cegar_problem","truth_payloads_by_discriminator_id",
    "source_positive_selection_contracts","max_refinement_steps",
}


def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "v3_admission_authorized":False,
        "p3_contract_cell_authorized":False,
        "relevance_control_loop_authorized":False,
        "source_authorization_verified":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
    if detail:
        out["detail"]=detail
    return out


def evaluate(payload:Mapping[str,Any], *, repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    extra=set(payload)-_ALLOWED
    if extra:
        return _fail("UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS",extra=sorted(extra))

    prior_payload={k:v for k,v in payload.items() if k!="bound_relevance_cegar_loop"}
    prior=evaluate_v11(prior_payload,repo_root=repo_root)
    if prior.get("pass") is True:
        out=dict(prior); out["schema"]=SCHEMA
        out["v11_preserved_positive_route"]=True
        out["bound_relevance_cegar_loop_fast_path_pass"]=False
        return out

    if any(k in payload for k in _STRONGER):
        out=dict(prior); out["schema"]=SCHEMA
        out["v11_preserved_positive_route"]=False
        out["bound_relevance_cegar_loop_fast_path_pass"]=False
        return out

    loop_cfg=payload.get("bound_relevance_cegar_loop")
    if loop_cfg is None:
        out=dict(prior); out["schema"]=SCHEMA
        out["v11_preserved_positive_route"]=False
        out["bound_relevance_cegar_loop_fast_path_pass"]=False
        return out
    if not isinstance(loop_cfg,Mapping):
        return _fail("BOUND_RELEVANCE_CEGAR_LOOP_INVALID")
    extra_loop=set(loop_cfg)-_LOOP_FIELDS
    if extra_loop:
        return _fail("BOUND_RELEVANCE_CEGAR_LOOP_FIELDS_INVALID",extra=sorted(extra_loop))

    if prior.get("nonbinding_capacity_reason")!="CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY":
        out=dict(prior); out["schema"]=SCHEMA
        out["v11_preserved_positive_route"]=False
        out["bound_relevance_cegar_loop_fast_path_pass"]=False
        out["bound_relevance_cegar_loop_not_applicable_reason"]="V11_DID_NOT_REACH_CAPACITY_BINDING_RELEVANCE_FRONTIER"
        return out

    candidate=evaluate_loop(
        {
            "context_id":payload.get("context_id"),
            "v3_input":payload.get("v3_input"),
            **dict(loop_cfg),
        },
        repo_root=repo_root,
    )
    if candidate.get("pass") is not True:
        return _fail(
            "BOUND_RELEVANCE_CEGAR_LOOP_UNSATISFIED",
            loop_status=candidate.get("status"),
            loop_reason=candidate.get("reason"),
            loop_result=candidate,
        )
    if (
        candidate.get("p3_contract_cell_authorized") is not True
        or candidate.get("relevance_control_loop_authorized") is not True
        or candidate.get("source_authorization_verified") is not False
        or candidate.get("db_admission_authority") is not False
        or candidate.get("u_subtraction_authority") is not False
        or candidate.get("terminal_authority") is not False
        or candidate.get("terminal_credit_delta")!=0
    ):
        return _fail("BOUND_RELEVANCE_CEGAR_LOOP_AUTHORITY_BOUNDARY_INVALID")

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__P3_REAL_CONTEXT_BOUND_RELEVANCE_CEGAR_LOOP",
        "route":"BOUND_RELEVANCE_CEGAR_LOOP_V1",
        "context_id":payload.get("context_id"),
        "selected_policy_id":candidate.get("selected_policy_id"),
        "selected_claim_ids":list(candidate.get("selected_claim_ids") or []),
        "rendered_text":candidate.get("rendered_text"),
        "render_trace":list(candidate.get("render_trace") or []),
        "refinement_steps":candidate.get("refinement_steps"),
        "loop_trace":candidate.get("trace"),
        "v3_admission_authorized":True,
        "p3_contract_cell_authorized":True,
        "relevance_control_loop_authorized":True,
        "source_authorization_verified":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "route_receipt":candidate,
        "v11_preserved_positive_route":False,
        "boundary":"ONLY_AFTER_V11_CAPACITY_BINDING_RELEVANCE_FRONTIER__STRONGER_EXPLICIT_AUTHORITY_NEVER_FALLS_THROUGH",
    }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {},repo_root=root)
