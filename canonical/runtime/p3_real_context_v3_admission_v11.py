"""P3 real-context admission v11.

Preserves every V10 positive route and stronger explicit authority. Adds a
source-positive selected-policy route only at the capacity-binding relevance
frontier when no objective-weight, exact dependency, or policy-world contract
was supplied.

The V11 route deletes complete semantic-world enumeration as a prerequisite:
the exact selected policy must instead be source-proved adequate across every
interpretation in the current sound semantic overapproximation and independently
bound to the selected P3 claim set.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.p3_real_context_v3_admission_v10 import evaluate as evaluate_v10
from canonical.runtime.p3_source_positive_selection_cell_v1 import evaluate as evaluate_source_positive

SCHEMA="PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V11"
_ALLOWED={
    "context_id","v3_input","objective_weights","semantic_certificates",
    "decision_dependency_contract","policy_influence_contract",
    "source_positive_selection_contract",
}


def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "v3_admission_authorized":False,"p3_contract_cell_authorized":False,
        "selected_policy_adequacy_verified":False,
        "top_law_eligible":False,
        "source_authorization_verified":False,
        "policy_adequacy_authority":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out


def _boundary_ok(r:Mapping[str,Any])->bool:
    return (
        r.get("pass") is True
        and r.get("p3_contract_cell_authorized") is True
        and r.get("selected_policy_adequacy_verified") is True
        and r.get("interpretation_set_enumeration_required") is False
        and r.get("complete_world_partition_required") is False
        and r.get("source_authorization_verified") is False
        and r.get("policy_adequacy_authority") is False
        and r.get("db_admission_authority") is False
        and r.get("u_subtraction_authority") is False
        and r.get("terminal_authority") is False
        and r.get("terminal_credit_delta")==0
    )


def evaluate(payload:Mapping[str,Any], *, repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    extra=set(payload)-_ALLOWED
    if extra:
        return _fail("UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS",extra=sorted(extra))

    prior_payload={k:v for k,v in payload.items() if k!="source_positive_selection_contract"}
    prior=evaluate_v10(prior_payload,repo_root=repo_root)
    if prior.get("pass") is True:
        out=dict(prior); out["schema"]=SCHEMA
        out["v10_preserved_positive_route"]=True
        out["source_positive_selection_fast_path_pass"]=False
        return out

    # A declared stronger selection authority cannot be silently ignored after
    # rejection in favor of the newer current-cell positive route.
    if any(k in payload for k in (
        "objective_weights","decision_dependency_contract","policy_influence_contract"
    )):
        out=dict(prior); out["schema"]=SCHEMA
        out["v10_preserved_positive_route"]=False
        out["source_positive_selection_fast_path_pass"]=False
        return out

    if "source_positive_selection_contract" not in payload:
        out=dict(prior); out["schema"]=SCHEMA
        out["v10_preserved_positive_route"]=False
        out["source_positive_selection_fast_path_pass"]=False
        return out

    contract=payload.get("source_positive_selection_contract")
    if not isinstance(contract,Mapping):
        return _fail("SOURCE_POSITIVE_SELECTION_CONTRACT_INVALID")

    if prior.get("nonbinding_capacity_reason")!="CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY":
        out=dict(prior); out["schema"]=SCHEMA
        out["v10_preserved_positive_route"]=False
        out["source_positive_selection_fast_path_pass"]=False
        out["source_positive_selection_not_applicable_reason"]="V10_DID_NOT_REACH_CAPACITY_BINDING_RELEVANCE_FRONTIER"
        return out

    root=Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    candidate=evaluate_source_positive({
        "v3_input":payload.get("v3_input"),
        "source_positive_selection_contract":contract,
    },repo_root=root)
    if candidate.get("pass") is not True:
        return _fail("SOURCE_POSITIVE_SELECTION_CONTRACT_UNSATISFIED",source_positive_result=candidate)
    if not _boundary_ok(candidate):
        return _fail("SOURCE_POSITIVE_SELECTION_AUTHORITY_BOUNDARY_INVALID")

    return {
        "schema":SCHEMA,"pass":True,
        "status":"PASS__P3_REAL_CONTEXT_SOURCE_POSITIVE_SELECTION",
        "route":"SOURCE_POSITIVE_SELECTION_CELL_V1",
        "context_id":payload.get("context_id"),
        "selected_policy_id":candidate.get("selected_policy_id"),
        "selected_claim_ids":list(candidate.get("selected_claim_ids") or []),
        "rendered_text":candidate.get("rendered_text"),
        "render_trace":list(candidate.get("render_trace") or []),
        "selected_policy_adequacy_verified":True,
        "interpretation_set_enumeration_required":False,
        "complete_world_partition_required":False,
        "unused_semantic_dimensions_need_not_be_classified":True,
        "v3_admission_authorized":True,
        "p3_contract_cell_authorized":True,
        "top_law_eligible":False,
        "source_authorization_verified":False,
        "policy_adequacy_authority":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "route_receipt":candidate,
        "explicit_authority_consumed":"SOURCE_POSITIVE_SELECTION_CONTRACT",
        "v10_preserved_positive_route":False,
        "boundary":"CURRENT_SOURCE_COMPATIBLE_SEMANTIC_OVERAPPROXIMATION_AND_EXACT_SELECTED_POLICY_ONLY",
    }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {},repo_root=root)
