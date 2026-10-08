"""P3 explicit-weight salience common-policy cell v1.

Owns the deterministic P3 subcell where optional salience and ordering are fully
specified by explicit integer objective weights. It recomputes inclusion/order
rather than trusting caller include/order choices.

Boundary: bounded fact grammar, conflict-free evidence, explicit empty extra
uncertainty, fully explicit render constraints. No source authority, hidden
uncertainty discovery, general semantic relevance, U-empty, or terminal credit.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime import bounded_claim_support as support
from canonical.runtime import synthesis_certified_visible_support_policy_v3 as v3

SCHEMA="PROJECT_BRAIN_P3_EXPLICIT_WEIGHTED_SALIENCE_CELL_V1"
_REQUIRED_CONSTRAINTS={
    "output_format","citation_mode","style","required_sections","allowed_sections",
    "max_items","max_chars","heading_level","require_title",
}

def _fail(reason:str,**detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "v3_admission_authorized":False,"top_law_eligible":False,
        "policy_adequacy_authority":False,"db_admission_authority":False,
        "u_subtraction_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out

def _weight(value:Any)->int:
    if isinstance(value,bool) or not isinstance(value,int):
        raise ValueError("INTEGER_OBJECTIVE_WEIGHT_REQUIRED")
    return value

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    public=payload.get("v3_input")
    weights=payload.get("objective_weights")
    if not isinstance(public,Mapping):
        return _fail("V3_INPUT_REQUIRED")
    if not isinstance(weights,Mapping):
        return _fail("OBJECTIVE_WEIGHTS_REQUIRED")
    task=public.get("task")
    if not isinstance(task,Mapping):
        return _fail("TASK_REQUIRED")
    claims=task.get("claims")
    evidence=task.get("evidence")
    profile=task.get("audience_profile")
    if not isinstance(claims,list) or not claims:
        return _fail("CLAIMS_REQUIRED")
    if not isinstance(evidence,list) or not evidence:
        return _fail("EVIDENCE_REQUIRED")
    if not isinstance(profile,Mapping):
        return _fail("AUDIENCE_PROFILE_REQUIRED")
    if task.get("required_uncertainty_units") != []:
        return _fail("NONEMPTY_OR_UNBOUND_UNCERTAINTY_OUTSIDE_WEIGHTED_CELL")
    if "claim_order" in task:
        return _fail("CALLER_CLAIM_ORDER_FORBIDDEN")

    constraints=profile.get("constraints")
    if not isinstance(constraints,Mapping):
        return _fail("AUDIENCE_CONSTRAINTS_REQUIRED")
    missing=sorted(_REQUIRED_CONSTRAINTS-set(constraints))
    if missing:
        return _fail("AUDIENCE_FORMAT_CONTRACT_NOT_EXPLICITLY_COMPLETE",missing=missing)
    if set(profile)-{"profile_id","constraints","title"}:
        return _fail("UNMODELED_AUDIENCE_PROFILE_FIELDS")
    max_items=constraints.get("max_items")
    if isinstance(max_items,bool) or not isinstance(max_items,int) or max_items<0:
        return _fail("MAX_ITEMS_INVALID")

    ids=[]; required=[]; optional=[]; by_id={}
    for row in claims:
        if not isinstance(row,Mapping):
            return _fail("CLAIM_ROW_INVALID")
        cid=row.get("claim_id")
        if not isinstance(cid,str) or not cid or cid in by_id:
            return _fail("CLAIM_ID_INVALID_OR_DUPLICATE")
        req=row.get("required")
        if req not in (True,False):
            return _fail("CLAIM_REQUIRED_FLAG_MUST_BE_BOOLEAN")
        if "include" in row:
            return _fail("CALLER_INCLUDE_FORBIDDEN")
        ids.append(cid); by_id[cid]=row
        (required if req else optional).append(cid)
    if set(weights)!=set(ids):
        return _fail("OBJECTIVE_WEIGHTS_MUST_EXACTLY_COVER_ALL_CLAIMS")
    try:
        w={cid:_weight(weights[cid]) for cid in ids}
    except ValueError as exc:
        return _fail(str(exc))
    if len(required)>max_items:
        return _fail("REQUIRED_CLAIMS_EXCEED_ITEM_CAPACITY")

    support_count={cid:0 for cid in ids}
    conflict_count=0
    for cid in ids:
        claim_text=by_id[cid].get("text")
        if not isinstance(claim_text,str):
            return _fail("CLAIM_TEXT_REQUIRED")
        for ev in evidence:
            if not isinstance(ev,Mapping):
                return _fail("EVIDENCE_ROW_INVALID")
            if ev.get("verified") is not True:
                return _fail("UNVERIFIED_EVIDENCE_UNIT")
            etext=ev.get("text"); eid=ev.get("evidence_id")
            if not isinstance(etext,str) or not isinstance(eid,str):
                return _fail("EVIDENCE_FIELDS_REQUIRED")
            rel=support.classify_support(claim_text,etext,evidence_id=eid)
            if rel.get("status")!="RESOLVED":
                return _fail("OUTSIDE_BOUNDED_FACT_GRAMMAR")
            if rel.get("relation")=="SUPPORTS":
                support_count[cid]+=1
            elif rel.get("relation")=="CONFLICTS":
                conflict_count+=1
    if conflict_count:
        return _fail("CONFLICT_REQUIRES_UNCERTAINTY_SEMANTICS",conflict_count=conflict_count)
    if any(support_count[cid]==0 for cid in required):
        return _fail("REQUIRED_CLAIM_LACKS_SUPPORT")

    remaining=max_items-len(required)
    admissible=[cid for cid in optional if support_count[cid]>0 and w[cid]>0]
    admissible.sort(key=lambda cid:(-w[cid],cid))
    selected_optional=admissible[:remaining]
    selected_set=set(required)|set(selected_optional)
    if not selected_set:
        return _fail("OBJECTIVE_SELECTS_NO_CLAIMS")
    selected_order=sorted(selected_set,key=lambda cid:(-w[cid],cid))

    compiled=deepcopy(dict(public))
    ctask=compiled["task"]
    cclaims=[]
    for row in claims:
        r=dict(row); cid=r["claim_id"]
        r["include"]=True if r["required"] is True else cid in selected_set
        cclaims.append(r)
    ctask["claims"]=cclaims
    ctask["claim_order"]=list(selected_order)

    result=v3.solve(compiled)
    if result.get("status")!="PASS":
        return _fail("V3_RUNTIME_FAIL_CLOSED",v3_result=result)
    audit=result.get("audit") or {}
    for key in (
        "all_selected_claims_supported","all_claim_evidence_relations_resolved",
        "all_selected_detected_conflicts_rendered","all_required_uncertainty_preserved",
        "all_rendered_items_provenance_bound","audience_profile_applied",
        "exact_complete_item_order_applied",
    ):
        if audit.get(key) is not True:
            return _fail("V3_AUDIT_INCOMPLETE",field=key)
    if audit.get("dropped_material_item_count")!=0 or audit.get("new_material_claim_count")!=0:
        return _fail("V3_MATERIAL_CONTENT_DRIFT")
    sa=result.get("selection_audit") or {}
    expected_selected=[cid for cid in ids if cid in selected_set]
    if sa.get("selected_claim_ids")!=expected_selected:
        return _fail("V3_SELECTION_DRIFT")
    if sa.get("claim_order")!=selected_order:
        return _fail("V3_ORDER_DRIFT")

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__P3_EXPLICIT_WEIGHTED_SALIENCE_COMMON_POLICY_CELL",
        "v3_admission_authorized":True,
        "top_law_eligible":True,
        "selected_claim_ids":expected_selected,
        "claim_order":selected_order,
        "selected_optional_claim_ids":selected_optional,
        "objective_value":sum(w[cid] for cid in selected_set),
        "objective_rule":"MANDATORY_REQUIRED_PLUS_MAX_POSITIVE_INTEGER_WEIGHT_OPTIONALS_UNDER_MAX_ITEMS__ORDER_BY_DESC_WEIGHT_THEN_ID",
        "policy_adequacy_authority":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "v3_result":result,
        "boundary":"EXPLICIT_INTEGER_OBJECTIVE_WEIGHTS_AND_BOUNDED_CONFLICT_FREE_FACT_GRAMMAR_ONLY__NO_GENERAL_SEMANTIC_SALIENCE",
    }

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
