"""Bounded grounded expression for a verified binary objective decision.

This cell composes:
1. the two-Sprite verified bounded binary objective decision derivation; and
2. the two-Sprite verified objective-role presentation compiler.

It emits exactly one fixed derived-decision line followed by the two verbatim,
provenance-bound operand facts in objective-role order. The decision line quotes
the exact objective and reports only the already-verified boolean result; it
does not paraphrase or introduce a new factual premise.

Supported presentation surface is intentionally narrow:
- BULLETS or PARAGRAPHS;
- INLINE_SOURCE_IDS;
- VERBATIM_GROUNDED;
- no title/sections;
- sufficient max_items/max_chars.

No caller-supplied selection/order is accepted. No policy adequacy, DB, U, or
terminal authority is minted.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.p3_binary_objective_decision_v1 import evaluate as derive_decision
from canonical.runtime.p3_bounded_objective_role_presentation_compiler_v1 import (
    evaluate as compile_presentation,
)

SCHEMA="PROJECT_BRAIN_P3_BINARY_DECISION_GROUNDED_EXPRESSION_V1"


def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "decision_expression_covered":False,
      "bound_cell_required_decision_coverage_complete":False,
      "real_context_semantic_scope_complete":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out


def _citation(prov:list[Mapping[str,Any]])->str:
    parts=[]
    seen=set()
    for row in prov:
        if not isinstance(row,Mapping):
            raise ValueError("PROVENANCE_ROW_INVALID")
        sid=row.get("source_id"); loc=row.get("locator")
        if not isinstance(sid,str) or not sid.strip():
            raise ValueError("SOURCE_ID_REQUIRED")
        if loc is not None and (not isinstance(loc,str) or not loc.strip()):
            raise ValueError("LOCATOR_INVALID")
        key=(sid,loc or "")
        if key in seen: continue
        seen.add(key)
        parts.append(sid + ("@"+loc if loc else ""))
    if not parts:
        raise ValueError("PROVENANCE_REQUIRED")
    return "[src:"+";".join(parts)+"]"


def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    objective=payload.get("objective")
    public=payload.get("v2_input")
    if not isinstance(objective,str) or not objective.strip():
        return _fail("OBJECTIVE_REQUIRED")
    if not isinstance(public,Mapping):
        return _fail("V2_INPUT_REQUIRED")
    task=public.get("task")
    if not isinstance(task,Mapping):
        return _fail("TASK_REQUIRED")
    claims=task.get("claims"); evidence=task.get("evidence")
    profile=task.get("audience_profile")
    if not isinstance(claims,list) or not isinstance(evidence,list):
        return _fail("CLAIMS_AND_EVIDENCE_REQUIRED")
    if not isinstance(profile,Mapping):
        return _fail("AUDIENCE_PROFILE_REQUIRED")
    constraints=profile.get("constraints")
    if not isinstance(constraints,Mapping):
        return _fail("AUDIENCE_CONSTRAINTS_REQUIRED")
    expected_keys={
      "output_format","citation_mode","style","required_sections","allowed_sections",
      "max_items","max_chars","heading_level","require_title",
    }
    if set(constraints)!=expected_keys:
        return _fail("AUDIENCE_CONTRACT_NOT_EXACT_BOUNDED_SHAPE",
                     missing=sorted(expected_keys-set(constraints)),
                     extra=sorted(set(constraints)-expected_keys))
    fmt=str(constraints.get("output_format") or "").upper()
    if fmt not in {"BULLETS","PARAGRAPHS"}:
        return _fail("OUTPUT_FORMAT_OUTSIDE_CELL")
    if str(constraints.get("citation_mode") or "").upper()!="INLINE_SOURCE_IDS":
        return _fail("CITATION_MODE_OUTSIDE_CELL")
    if str(constraints.get("style") or "").upper()!="VERBATIM_GROUNDED":
        return _fail("STYLE_OUTSIDE_CELL")
    if constraints.get("required_sections")!=[] or constraints.get("allowed_sections") is not None:
        return _fail("SECTIONS_OUTSIDE_CELL")
    if constraints.get("require_title") is not False:
        return _fail("TITLE_OUTSIDE_CELL")
    try:
        max_items=int(constraints.get("max_items"))
        max_chars=int(constraints.get("max_chars"))
    except Exception:
        return _fail("OUTPUT_BUDGET_INVALID")
    if max_items < 3 or max_chars <= 0:
        return _fail("OUTPUT_BUDGET_INFEASIBLE")

    decision=derive_decision({"objective":objective,"claims":claims,"evidence":evidence})
    if decision.get("pass") is not True:
        return _fail("DECISION_DERIVATION_UNRESOLVED",decision=decision)
    if (
      decision.get("required_decision_semantics_covered") is not True
      or decision.get("decision_expression_covered") is not False
      or decision.get("policy_adequacy_authority") is not False
      or decision.get("terminal_authority") is not False
      or decision.get("terminal_credit_delta") != 0
    ):
        return _fail("DECISION_AUTHORITY_BOUNDARY_INVALID")

    presentation=compile_presentation({"objective":objective,"v2_input":public})
    if presentation.get("pass") is not True:
        return _fail("OPERAND_PRESENTATION_UNRESOLVED",presentation=presentation)
    if (
      presentation.get("presentation_policy_constructed") is not True
      or presentation.get("policy_adequacy_authority") is not False
      or presentation.get("terminal_authority") is not False
      or presentation.get("terminal_credit_delta") != 0
    ):
        return _fail("PRESENTATION_AUTHORITY_BOUNDARY_INVALID")

    trace=presentation.get("render_trace")
    if not isinstance(trace,list) or len(trace)!=2:
        return _fail("OPERAND_TRACE_MUST_HAVE_EXACTLY_TWO_ITEMS")
    objective_text=" ".join(objective.strip().split())
    truth="TRUE" if decision.get("decision_truth") is True else "FALSE"
    try:
        decision_citation=_citation(list(decision.get("decision_provenance") or []))
    except ValueError as exc:
        return _fail(str(exc))
    decision_body=f'Decision: "{objective_text}" => {truth}. {decision_citation}'

    operand_bodies=[]
    objective_order=list(presentation.get("objective_role_order") or [])
    trace_ids=[str(row.get("item_id") or "").removeprefix("CLAIM_") for row in trace]
    if trace_ids != objective_order:
        return _fail("OPERAND_TRACE_ORDER_DRIFT")
    for row in trace:
        text=row.get("source_text")
        prov=row.get("provenance")
        if not isinstance(text,str) or not text.strip() or not isinstance(prov,list):
            return _fail("OPERAND_TRACE_INVALID")
        try:
            operand_bodies.append(text.strip()+" "+_citation(prov))
        except ValueError as exc:
            return _fail(str(exc))

    bodies=[decision_body]+operand_bodies
    if fmt=="BULLETS":
        rendered="\n".join("- "+x for x in bodies)
    else:
        rendered="\n\n".join(bodies)
    if len(rendered)>max_chars:
        return _fail("MAX_CHARS_INFEASIBLE__NO_TRUNCATION",
                     required_chars=len(rendered),max_chars=max_chars)

    return {
      "schema":SCHEMA,"pass":True,
      "status":"PASS__BOUND_BINARY_DECISION_GROUNDED_EXPRESSION",
      "rendered_text":rendered,
      "decision_expression":decision_body,
      "decision_truth":decision.get("decision_truth"),
      "decision_provenance":list(decision.get("decision_provenance") or []),
      "objective_role_order":objective_order,
      "operand_trace":trace,
      "decision_receipt":decision,
      "presentation_receipt":presentation,
      "audit":{
        "derived_decision_item_count":1,
        "operand_fact_item_count":2,
        "rendered_item_count":3,
        "derived_decision_is_fixed_function_of_verified_receipt":True,
        "exact_objective_quoted_in_decision":True,
        "both_decision_sources_cited":len(decision.get("decision_provenance") or [])>=2,
        "operand_facts_verbatim":True,
        "operand_order_matches_objective_roles":True,
        "content_truncated":False,
        "caller_selection_or_order_used":False,
        "unsupported_material_claim_count":0,
      },
      "decision_expression_covered":True,
      "bound_cell_required_decision_coverage_complete":True,
      "real_context_semantic_scope_complete":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,
      "boundary":"EXACT_BINARY_NUMERIC_OBJECTIVE__ONE_FIXED_DERIVED_DECISION_LINE__TWO_VERBATIM_ROLE_FACTS__BULLETS_OR_PARAGRAPHS__INLINE_SOURCE_IDS__NO_GENERAL_PRESENTATION_OR_SCOPE_COMPLETENESS",
    }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
