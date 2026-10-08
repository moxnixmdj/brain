"""P3 mechanically closed common-policy cell v1.

This is a positive admission path only for a deliberately degenerate formal cell
where the three V2 real-context semantic predicates disappear by construction:

* every claim is mandatory, so no salience/selection decision exists;
* claim order is exactly source input order, so no semantic reordering exists;
* every claim/evidence relation is resolved in the bounded fact grammar;
* no conflict is present and no extra uncertainty unit is supplied, so the
  admitted bounded cell contains no disagreement/uncertainty to discover;
* every supported audience/format constraint is explicitly present, making the
  renderer contract fully specified rather than inferred from an audience label.

This proves membership only for this narrow cell. It does not prove source
authority, general natural-language semantics, general audience adaptation,
global U-empty, or terminality.
"""
from __future__ import annotations

from typing import Any, Mapping
from canonical.runtime import synthesis_certified_visible_support_policy_v3 as v3

SCHEMA="PROJECT_BRAIN_P3_MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1"
_REQUIRED_CONSTRAINTS={
    "output_format","citation_mode","style","required_sections","allowed_sections",
    "max_items","max_chars","heading_level","require_title",
}

def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "mechanically_closed_cell":False,"v3_admission_authorized":False,
        "policy_adequacy_authority":False,"db_admission_authority":False,
        "u_subtraction_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    public=payload.get("v3_input")
    if not isinstance(public,Mapping):
        return _fail("V3_INPUT_REQUIRED")
    task=public.get("task")
    if not isinstance(task,Mapping):
        return _fail("TASK_REQUIRED")

    claims=task.get("claims")
    evidence=task.get("evidence")
    profile=task.get("audience_profile")
    uncertainty=task.get("required_uncertainty_units")
    if not isinstance(claims,list) or not claims:
        return _fail("CLAIMS_REQUIRED")
    if not isinstance(evidence,list) or not evidence:
        return _fail("EVIDENCE_REQUIRED")
    if not isinstance(profile,Mapping):
        return _fail("AUDIENCE_PROFILE_REQUIRED")
    if uncertainty != []:
        return _fail("NONEMPTY_OR_UNBOUND_UNCERTAINTY_OUTSIDE_ZERO_RESIDUAL_CELL")
    if "claim_order" in task:
        return _fail("EXPLICIT_SEMANTIC_REORDERING_OUTSIDE_ZERO_RESIDUAL_CELL")

    for row in claims:
        if not isinstance(row,Mapping):
            return _fail("CLAIM_ROW_INVALID")
        if row.get("required") is not True:
            return _fail("OPTIONAL_CLAIM_REQUIRES_RELEVANCE_JUDGMENT")
        if "include" in row and row.get("include") is not True:
            return _fail("CLAIM_SELECTION_OUTSIDE_ZERO_RESIDUAL_CELL")

    constraints=profile.get("constraints")
    if not isinstance(constraints,Mapping):
        return _fail("AUDIENCE_CONSTRAINTS_REQUIRED")
    missing=sorted(_REQUIRED_CONSTRAINTS-set(constraints))
    if missing:
        return _fail("AUDIENCE_FORMAT_CONTRACT_NOT_EXPLICITLY_COMPLETE",missing=missing)
    extra_semantic=set(profile)-{"profile_id","constraints","title"}
    if extra_semantic:
        return _fail("UNMODELED_AUDIENCE_PROFILE_FIELDS",fields=sorted(extra_semantic))

    result=v3.solve(public)
    if result.get("status")!="PASS":
        return _fail("V3_RUNTIME_FAIL_CLOSED",v3_result=result)

    audit=result.get("audit") or {}
    needed={
      "all_selected_claims_supported":True,
      "all_claim_evidence_relations_resolved":True,
      "all_selected_detected_conflicts_rendered":True,
      "all_required_uncertainty_preserved":True,
      "all_rendered_items_provenance_bound":True,
      "audience_profile_applied":True,
      "exact_complete_item_order_applied":True,
    }
    failed=[k for k,v in needed.items() if audit.get(k) is not v]
    if audit.get("dropped_material_item_count")!=0: failed.append("dropped_material_item_count")
    if audit.get("new_material_claim_count")!=0: failed.append("new_material_claim_count")
    if failed:
        return _fail("V3_MECHANICAL_AUDIT_INCOMPLETE",failed=sorted(set(failed)))

    rel=result.get("relation_audit")
    if not isinstance(rel,list):
        return _fail("RELATION_AUDIT_REQUIRED")
    if any(not isinstance(x,Mapping) or x.get("relation") not in {"SUPPORTS","UNRELATED","CONFLICTS"} for x in rel):
        return _fail("RELATION_AUDIT_INVALID")
    conflicts=[x for x in rel if x.get("relation")=="CONFLICTS"]
    if conflicts:
        return _fail("CONFLICT_REQUIRES_UNCERTAINTY_SEMANTICS",conflict_count=len(conflicts))

    selection=result.get("selection_audit") or {}
    claim_ids=[str(x.get("claim_id")) for x in claims]
    if selection.get("required_claim_ids")!=claim_ids:
        return _fail("REQUIRED_SET_NOT_EXACT_INPUT_SET")
    if selection.get("selected_claim_ids")!=claim_ids:
        return _fail("SELECTION_NOT_IDENTITY")
    if selection.get("excluded_optional_claim_ids")!=[]:
        return _fail("OPTIONAL_EXCLUSION_PRESENT")
    if selection.get("claim_order")!=claim_ids:
        return _fail("ORDER_NOT_EXACT_INPUT_ORDER")
    if selection.get("claim_order_mode")!="EXPLICIT_INPUT_CLAIM_ORDER":
        return _fail("ORDER_MODE_NOT_STRUCTURAL_INPUT_ORDER")

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__MECHANICALLY_CLOSED_P3_COMMON_POLICY_CELL",
        "mechanically_closed_cell":True,
        "v3_admission_authorized":True,
        "top_law_eligible":True,
        "semantic_predicates_eliminated_by_structure":{
            "REQUIRED_UNCERTAINTY_SET_COMPLETE":"TRUE_FOR_THIS_BOUNDED_CELL__NO_CONFLICTS_AND_EXPLICIT_EMPTY_SET",
            "SELECTION_AND_ORDER_DECISION_RELEVANCE_COMPLETE":"TRUE_FOR_THIS_BOUNDED_CELL__ALL_CLAIMS_REQUIRED_AND_INPUT_ORDER_ONLY",
            "AUDIENCE_FORMAT_PROFILE_COMPLETE":"NOT_INFERRED__COMMON_POLICY_HAS_NO_REMAINING_CONTENT_SELECTION_OR_ORDER_DEGREE_OF_FREEDOM_AND_RENDER_CONSTRAINTS_ARE_FULLY_EXPLICIT",
        },
        "policy_adequacy_authority":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "v3_result":result,
        "boundary":"NARROW_FORMAL_COMMON_POLICY_CELL_ONLY__NO_GENERAL_REAL_CONTEXT_SEMANTIC_COMPLETENESS",
    }

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
