from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime import synthesis_certified_visible_support_policy_v2 as base
from canonical.runtime import synthesis_grounded_expression_ir_v1 as realizer

SCHEMA="PROJECT_BRAIN_SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V3"
INPUT_SCHEMA="PROJECT_BRAIN_SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_INPUT_V3"


def _fail(reason:str, *, details:Any=None)->dict[str,Any]:
    out={"schema":SCHEMA,"status":"FAIL_CLOSED","reason":reason,
         "terminal_authority":False,"promotion_authority":False,"terminal_credit_delta":0}
    if details is not None:
        out["details"]=details
    return out


def _token(value:Any)->str:
    if not isinstance(value,str) or not value.strip() or value!=value.strip():
        raise ValueError("NORMALIZED_NONEMPTY_STRING_REQUIRED")
    return value


def _provenance(value:Any)->list[dict[str,str]]:
    if not isinstance(value,list) or not value:
        raise ValueError("PROVENANCE_REQUIRED")
    out=[]; seen=set()
    for row in value:
        if not isinstance(row,Mapping):
            raise ValueError("PROVENANCE_ROW_INVALID")
        source_id=_token(row.get("source_id"))
        locator=row.get("locator")
        if locator is not None:
            locator=_token(locator)
        key=(source_id,locator or "")
        if key in seen:
            continue
        seen.add(key)
        item={"source_id":source_id}
        if locator is not None:
            item["locator"]=locator
        out.append(item)
    if not out:
        raise ValueError("PROVENANCE_REQUIRED")
    return out


def solve(public:Any)->dict[str,Any]:
    try:
        if not isinstance(public,Mapping) or public.get("schema")!=INPUT_SCHEMA:
            return _fail("INPUT_SCHEMA_INVALID")
        task=public.get("task")
        if not isinstance(task,Mapping):
            return _fail("TASK_INVALID")
        if "required_uncertainty_units" not in task:
            return _fail("REQUIRED_UNCERTAINTY_BINDING_MISSING")
        raw_uncertainty=task.get("required_uncertainty_units")
        if not isinstance(raw_uncertainty,list):
            return _fail("REQUIRED_UNCERTAINTY_UNITS_INVALID")

        uncertainty=[]
        seen=set()
        for row in raw_uncertainty:
            if not isinstance(row,Mapping):
                return _fail("UNCERTAINTY_ROW_INVALID")
            uid=_token(row.get("uncertainty_id"))
            if uid in seen:
                return _fail("DUPLICATE_UNCERTAINTY_ID")
            seen.add(uid)
            text=_token(row.get("text"))
            prov=_provenance(row.get("provenance"))
            section=row.get("section")
            if section is not None:
                section=_token(section)
            uncertainty.append({
                "id":"UNCERTAINTY_"+uid,
                "kind":"UNCERTAINTY",
                "text":text,
                "provenance":prov,
                "section":section,
            })

        # Delegate claim/evidence selection, support, conflict, explicit order and
        # audience-constraint checking to V2. V3 adds no inferred uncertainty.
        v2_public=deepcopy(dict(public))
        v2_public["schema"]=base.INPUT_SCHEMA
        v2_task=v2_public["task"]
        v2_task.pop("required_uncertainty_units",None)
        v2=base.solve(v2_public)
        if v2.get("status")!="PASS":
            return _fail("V2_BASE_POLICY_FAIL_CLOSED",details=v2)

        base_items=[]
        for row in v2.get("render_trace") or []:
            item={
                "id":_token(row.get("item_id")),
                "kind":_token(row.get("kind")),
                "text":_token(row.get("source_text")),
                "provenance":_provenance(row.get("provenance")),
            }
            if row.get("section") is not None:
                item["section"]=_token(row.get("section"))
            else:
                item["section"]=None
            base_items.append(item)

        all_items=base_items+uncertainty
        profile=task.get("audience_profile")
        if not isinstance(profile,Mapping):
            return _fail("AUDIENCE_PROFILE_REQUIRED")
        constraints=profile.get("constraints")
        if not isinstance(constraints,Mapping):
            return _fail("AUDIENCE_CONSTRAINTS_REQUIRED")
        c=dict(constraints)
        # V3 owns the complete item order: the exact V2-selected content first,
        # followed by required uncertainty units in their explicit input order.
        c["item_order"]=[x["id"] for x in all_items]

        rendered=realizer.solve({
            "schema":realizer.INPUT_SCHEMA,
            "task":{
                "items":all_items,
                "constraints":c,
                "title":profile.get("title"),
            },
        })
        if rendered.get("status")!="PASS":
            return _fail("UNCERTAINTY_PRESERVATION_REALIZATION_FAILED",details=rendered)

        trace=rendered.get("trace") or []
        trace_ids=[x.get("item_id") for x in trace]
        expected=[x["id"] for x in all_items]
        if trace_ids!=expected:
            return _fail("V3_ITEM_ORDER_DRIFT")

        rendered_uncertainty=[
            x for x in trace if str(x.get("item_id") or "").startswith("UNCERTAINTY_")
        ]
        if len(rendered_uncertainty)!=len(uncertainty):
            return _fail("REQUIRED_UNCERTAINTY_DROPPED")

        out={
            "schema":SCHEMA,
            "status":"PASS",
            "scope":(
                "V2_EXPLICIT_SELECTION_ORDER_VISIBLE_SUPPORT_CLASS_PLUS_"
                "EXPLICIT_COMPLETE_REQUIRED_UNCERTAINTY_LIST_WITH_PROVENANCE"
            ),
            "rendered_text":rendered["rendered_text"],
            "render_trace":trace,
            "base_v2_audit":v2.get("audit"),
            "selection_audit":v2.get("selection_audit"),
            "relation_audit":v2.get("relation_audit"),
            "uncertainty_audit":{
                "binding_explicit":True,
                "required_uncertainty_count":len(uncertainty),
                "preserved_uncertainty_count":len(rendered_uncertainty),
                "all_required_uncertainty_preserved":len(rendered_uncertainty)==len(uncertainty),
                "uncertainty_order":"EXPLICIT_INPUT_ORDER_AFTER_SELECTED_CONTENT",
                "uncertainty_inferred":False,
            },
            "audit":{
                "all_selected_claims_supported":bool((v2.get("audit") or {}).get("all_selected_claims_supported")),
                "all_claim_evidence_relations_resolved":bool((v2.get("audit") or {}).get("all_claim_evidence_relations_resolved")),
                "all_selected_detected_conflicts_rendered":bool((v2.get("audit") or {}).get("all_selected_detected_conflicts_rendered")),
                "all_required_uncertainty_preserved":len(rendered_uncertainty)==len(uncertainty),
                "all_rendered_items_provenance_bound":bool((rendered.get("audit") or {}).get("all_items_provenance_bound")),
                "dropped_material_item_count":int((rendered.get("audit") or {}).get("dropped_item_count",0)),
                "new_material_claim_count":int((rendered.get("audit") or {}).get("new_material_claim_count",0)),
                "audience_profile_applied":True,
                "exact_complete_item_order_applied":trace_ids==expected,
            },
            "semantic_boundary":{
                "required_uncertainty_discovery":"UPSTREAM_EXPLICIT_BINDING_REQUIRED",
                "general_paraphrase_entailment":"UNPROVED",
                "arbitrary_optional_salience":"UNPROVED",
                "arbitrary_semantic_reordering":"UNPROVED",
                "arbitrary_audience_meaning":"UNPROVED",
                "outside_bounded_fact_grammar":"FAIL_CLOSED",
            },
            "terminal_authority":False,
            "promotion_authority":False,
            "terminal_credit_delta":0,
        }
        return out
    except ValueError as exc:
        return _fail(str(exc))


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return solve(args or {})
