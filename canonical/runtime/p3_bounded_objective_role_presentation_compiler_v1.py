"""P3 bounded objective-role presentation compiler v1.

Composes the independently verified binary objective-role relevance certificate
with the existing explicit-selection/order synthesis top-law runtime.

For the exact declared cell:
- exactly two optional claims, no required claims;
- both claims bind bijectively to the explicit binary objective's LEFT/RIGHT roles;
- both are exact verified-evidence statements with provenance;
- audience/format constraints are explicit in the existing typed realizer language;

the compiler sets include=True for the two verified-relevant claims and derives
claim_order from objective_role_order. It never accepts caller-supplied include
or claim_order fields.

This proves construction of the existing explicit-selection/order top-law policy
for the declared mechanical cell. It does not self-certify that no additional
implicit presentation semantics exist in the real context, and grants no DB,
U-empty, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime.p3_bounded_objective_role_relevance_v1 import evaluate as relevance
from canonical.runtime.synthesis_certified_visible_support_policy_v2 import (
    INPUT_SCHEMA as V2_INPUT_SCHEMA,
    solve as solve_v2,
)

SCHEMA="PROJECT_BRAIN_P3_BOUNDED_OBJECTIVE_ROLE_PRESENTATION_COMPILER_V1"


def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "presentation_policy_constructed":False,
      "declared_cell_top_law_conditions_mechanically_satisfied":False,
      "real_context_semantic_scope_complete":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out


def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    objective=payload.get("objective")
    public=payload.get("v2_input")
    if not isinstance(objective,str) or not objective.strip():
        return _fail("OBJECTIVE_REQUIRED")
    if not isinstance(public,Mapping) or public.get("schema")!=V2_INPUT_SCHEMA:
        return _fail("V2_INPUT_REQUIRED")
    task=public.get("task")
    if not isinstance(task,Mapping):
        return _fail("TASK_REQUIRED")
    claims=task.get("claims"); evidence=task.get("evidence")
    if not isinstance(claims,list) or len(claims)!=2:
        return _fail("EXACTLY_TWO_CLAIMS_REQUIRED")
    if not isinstance(evidence,list) or not evidence:
        return _fail("EVIDENCE_REQUIRED")
    if "claim_order" in task:
        return _fail("CALLER_CLAIM_ORDER_FORBIDDEN")
    for row in claims:
        if not isinstance(row,Mapping):
            return _fail("CLAIM_ROW_INVALID")
        if row.get("required") is not False:
            return _fail("EXACT_CELL_REQUIRES_TWO_OPTIONAL_CLAIMS")
        if "include" in row:
            return _fail("CALLER_INCLUDE_FORBIDDEN")

    rel=relevance({"objective":objective,"claims":claims,"evidence":evidence})
    if rel.get("pass") is not True:
        return _fail("OBJECTIVE_ROLE_RELEVANCE_UNRESOLVED", relevance=rel)
    if (
      rel.get("optional_relevance_complete") is not True
      or rel.get("organization_policy_complete") is not False
      or rel.get("policy_adequacy_authority") is not False
      or rel.get("u_subtraction_authority") is not False
      or rel.get("terminal_authority") is not False
      or rel.get("terminal_credit_delta") != 0
    ):
        return _fail("RELEVANCE_AUTHORITY_BOUNDARY_INVALID")

    order=list(rel.get("objective_role_order") or [])
    include=list(rel.get("include_optional_claim_ids") or [])
    ids=[row.get("claim_id") for row in claims]
    if len(order)!=2 or len(set(order))!=2 or set(order)!=set(ids):
        return _fail("OBJECTIVE_ROLE_ORDER_INVALID")
    if set(include)!=set(ids):
        return _fail("RELEVANCE_DID_NOT_INCLUDE_EXACT_CLAIM_SET")

    compiled=deepcopy(dict(public))
    ctask=compiled["task"]
    for row in ctask["claims"]:
        row["include"]=True
    ctask["claim_order"]=order

    out=solve_v2(compiled)
    if out.get("status")!="PASS":
        return _fail("EXPLICIT_SELECTION_ORDER_TOP_LAW_RUNTIME_FAILED", top_law_result=out)
    audit=out.get("audit") or {}
    selection=out.get("selection_audit") or {}
    if (
      selection.get("selected_claim_ids") != ids
      or selection.get("excluded_optional_claim_ids") != []
      or selection.get("claim_order") != order
      or selection.get("optional_selection_inferred") is not False
      or selection.get("semantic_reordering_inferred") is not False
      or audit.get("all_selected_claims_supported") is not True
      or audit.get("all_claim_evidence_relations_resolved") is not True
      or audit.get("all_selected_detected_conflicts_rendered") is not True
      or audit.get("exact_selected_order_applied") is not True
      or audit.get("dropped_selected_material_item_count") != 0
      or audit.get("new_material_claim_count") != 0
      or out.get("terminal_authority") is not False
      or out.get("terminal_credit_delta") != 0
    ):
        return _fail("TOP_LAW_AUDIT_INCOMPLETE", top_law_result=out)

    return {
      "schema":SCHEMA,"pass":True,
      "status":"PASS__BOUND_OBJECTIVE_ROLE_PRESENTATION_POLICY_CONSTRUCTED",
      "presentation_policy_constructed":True,
      "declared_cell_top_law_conditions_mechanically_satisfied":True,
      "objective_role_order":order,
      "selected_claim_ids":ids,
      "rendered_text":out.get("rendered_text"),
      "render_trace":list(out.get("render_trace") or []),
      "relevance_receipt":rel,
      "top_law_receipt":out,
      "real_context_semantic_scope_complete":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,
      "boundary":(
        "EXACT_TWO_OPTIONAL_BINARY_OBJECTIVE_ROLE_CLAIMS__BOTH_VERIFIED_RELEVANT__"
        "OBJECTIVE_ROLE_ORDER_COMPILED_TO_EXISTING_EXPLICIT_SELECTION_ORDER_TOP_LAW__"
        "REAL_CONTEXT_NO_ADDITIONAL_IMPLICIT_PRESENTATION_SEMANTICS_NOT_SELF_CERTIFIED"
      ),
    }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
