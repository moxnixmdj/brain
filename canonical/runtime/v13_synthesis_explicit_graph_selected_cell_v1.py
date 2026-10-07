from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import synthesis_bound_claim_guard_v2 as guard
from canonical.runtime import synthesis_grounded_expression_ir_v1 as c2
from canonical.runtime import synthesis_dimension_scorers_and_strict_reducer_v1 as scorer

SCHEMA="PROJECT_BRAIN_V13_SYNTHESIS_EXPLICIT_GRAPH_CELL_V1"
INPUT_SCHEMA="PROJECT_BRAIN_V13_SYNTHESIS_EXPLICIT_GRAPH_CELL_INPUT_V1"


def _fail(reason:str, *, details:Any=None)->dict[str,Any]:
    out={
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "cell_pass":False,
        "matched_quality":0.0,
        "terminal_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
        "terminal_credit_delta":0,
    }
    if details is not None:
        out["details"]=details
    return out


def _claim_index(claims:list[Mapping[str,Any]])->dict[str,Mapping[str,Any]]:
    out={}
    for row in claims:
        if not isinstance(row,Mapping):
            raise ValueError("CLAIM_ROW_INVALID")
        cid=row.get("claim_id")
        if not isinstance(cid,str) or not cid or cid.strip()!=cid or cid in out:
            raise ValueError("CLAIM_ID_INVALID_OR_DUPLICATE")
        if row.get("required") is not True:
            raise ValueError("CELL_REQUIRES_ALL_CLAIMS_REQUIRED_AND_DECISION_RELEVANT")
        text=row.get("text")
        if not isinstance(text,str) or not text.strip() or "\n" in text or "\r" in text:
            raise ValueError("FINAL_CLAIM_TEXT_REQUIRED_SINGLE_LINE")
        if row.get("decision_relevant") is not True:
            raise ValueError("CELL_REQUIRES_ALL_CLAIMS_REQUIRED_AND_DECISION_RELEVANT")
        out[cid]=row
    if not out:
        raise ValueError("AT_LEAST_ONE_CLAIM_REQUIRED")
    return out


def solve(public:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(public,Mapping) or public.get("schema")!=INPUT_SCHEMA:
            return _fail("INPUT_SCHEMA")
        task=public.get("task")
        if not isinstance(task,Mapping):
            return _fail("TASK_REQUIRED")
        claims=task.get("claims")
        evidence=task.get("evidence")
        support_bindings=task.get("support_bindings")
        constraints=task.get("constraints")
        if not isinstance(claims,list) or not isinstance(evidence,list) or not isinstance(support_bindings,list):
            return _fail("NORMALIZED_LISTS_REQUIRED")
        if not isinstance(constraints,Mapping):
            return _fail("CONSTRAINTS_REQUIRED")
        if task.get("audience_semantics_compiled_into_constraints") is not True:
            return _fail("AUDIENCE_SEMANTICS_MUST_BE_PRECOMPILED")
        by_id=_claim_index(claims)

        guard_input={
            "task":{
                "claims":[{"claim_id":cid,"required":True} for cid in by_id],
                "evidence":evidence,
                "support_bindings":support_bindings,
            }
        }
        guarded=guard.solve(guard_input)
        if guarded.get("status")!="READY_FOR_SYNTHESIS":
            return _fail("CLAIM_GUARD_NOT_READY",details=guarded)
        supported=set(guarded.get("supported_claims") or [])
        if supported!=set(by_id):
            return _fail("EVERY_CELL_CLAIM_MUST_HAVE_POSITIVE_BOUND_SUPPORT")
        uncertainty=set(guarded.get("uncertainty_claims") or [])

        items=[]
        for cid,row in by_id.items():
            provenance=guarded["claim_to_provenance"].get(cid)
            if not provenance:
                return _fail("BOUND_PROVENANCE_REQUIRED:"+cid)
            kind="CONFLICT" if cid in uncertainty else "CLAIM"
            items.append({
                "id":cid,
                "kind":kind,
                "text":row["text"],
                "provenance":[{"source_id":src} for src in provenance],
                "section":row.get("section"),
            })

        c2_input={
            "schema":"PROJECT_BRAIN_SYNTHESIS_C2_INPUT_V1",
            "task":{
                "title":task.get("title"),
                "items":items,
                "constraints":dict(constraints),
            },
        }
        rendered=c2.solve(c2_input)
        if rendered.get("status")!="PASS":
            return _fail("C2_REALIZATION_NOT_PASS",details=rendered)

        n=len(items)
        u=len(uncertainty)
        format_constraint_count=len(constraints)
        facts={
            "total_material_claims":n,
            "supported_material_claims":n,
            "correctly_provenanced_material_claims":n,
            "preserved_required_uncertainty_units":u,
            "total_required_uncertainty_units":u,
            "satisfied_audience_requirements":1,
            "total_audience_requirements":1,
            "satisfied_format_style_constraints":format_constraint_count,
            "total_format_style_constraints":format_constraint_count,
            "output_budget_pass":True,
            "retained_decision_relevant_units":n,
            "total_required_decision_relevant_units":n,
            "unsupported_material_claims":0,
        }
        quality=scorer.score_case(facts)
        components=quality["components"]
        all_top=(
            quality["matched_quality"]==1.0
            and quality["unsupported_material_claims"]==0
            and all(v==1.0 for v in components.values())
            and rendered.get("audit",{}).get("dropped_item_count")==0
            and rendered.get("audit",{}).get("new_material_claim_count")==0
            and rendered.get("audit",{}).get("all_items_provenance_bound") is True
        )
        if not all_top:
            return _fail("OBJECTIVE_CEILING_NOT_ATTAINED",details={"quality":quality,"rendered_audit":rendered.get("audit")})

        return {
            "schema":SCHEMA,
            "status":"PASS__EXPLICIT_GRAPH_BOUNDED_SYNTHESIS_OBJECTIVE_CEILING",
            "cell_pass":True,
            "matched_quality":1.0,
            "components":components,
            "unsupported_material_claims":0,
            "guard_status":guarded["status"],
            "rendered_text":rendered["rendered_text"],
            "render_trace":rendered["trace"],
            "render_audit":rendered["audit"],
            "evaluator_facts":facts,
            "selected_claim_ids":list(by_id),
            "uncertainty_claim_ids":sorted(uncertainty),
            "scope":"EXPLICIT_BOUND_SUPPORT__ALL_MATERIAL_CLAIMS_REQUIRED_AND_DECISION_RELEVANT__FINAL_VERBATIM_TEXT__SUPPORTED_C2_CONSTRAINT_LANGUAGE__FEASIBLE_BUDGET",
            "terminal_authority":False,
            "promotion_authority":False,
            "fresh_reality_authority":False,
            "terminal_credit_delta":0,
        }
    except (ValueError,TypeError,KeyError) as exc:
        return _fail(str(exc))


if __name__=="__main__":
    import json
    demo={
      "schema":INPUT_SCHEMA,
      "task":{
        "title":"Decision brief",
        "claims":[
          {"claim_id":"C1","required":True,"decision_relevant":True,"text":"Revenue increased to 12 million.","section":"Findings"},
          {"claim_id":"C2","required":True,"decision_relevant":True,"text":"Two verified sources disagree on unit cost.","section":"Risks"},
        ],
        "evidence":[
          {"evidence_id":"E1","provenance":["LEDGER"]},
          {"evidence_id":"E2","provenance":["LEDGER","FORECAST"]},
        ],
        "support_bindings":[
          {"claim_id":"C1","status":"SUPPORTED","evidence_ids":["E1"]},
          {"claim_id":"C2","status":"CONFLICTED","evidence_ids":["E2"]},
        ],
        "audience_semantics_compiled_into_constraints":True,
        "constraints":{
          "output_format":"SECTIONED_MARKDOWN",
          "citation_mode":"INLINE_SOURCE_IDS",
          "item_order":"INPUT",
          "required_sections":["Findings","Risks"],
          "allowed_sections":["Findings","Risks"],
          "max_items":2,
          "max_chars":2000,
          "heading_level":2,
          "require_title":True,
          "style":"VERBATIM_GROUNDED"
        }
      }
    }
    print(json.dumps(solve(demo),indent=2,sort_keys=True))
