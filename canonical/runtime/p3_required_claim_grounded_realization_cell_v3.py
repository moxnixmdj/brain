"""P3 required-claim grounded realization cell v3.

A narrow positive synthesis cell for tasks where every claim is structurally required,
selection/order are therefore fixed, support truth is recomputed by the V5
support portfolio, uncertainty is explicitly empty, and output constraints are explicit.

Supported claims are rendered verbatim with provenance from supporting evidence only.
Unsupported, conflicting, or semantically unresolved required claims fail closed.
No source authorization, optional relevance, general uncertainty discovery, U-empty,
or terminal credit is minted.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.selected_support_truth_certificate_v5 import evaluate as support_truth
from canonical.runtime import synthesis_grounded_expression_ir_v1 as realizer

SCHEMA="PROJECT_BRAIN_P3_REQUIRED_CLAIM_GROUNDED_REALIZATION_CELL_V3"
_REQUIRED_CONSTRAINTS={
    "output_format","citation_mode","style","required_sections","allowed_sections",
    "max_items","max_chars","heading_level","require_title",
}

def _fail(reason:str,**detail:Any)->dict[str,Any]:
    out={
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "p3_contract_cell_authorized":False,"source_authorization_verified":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out

def _support_provenance(evidence:list[Mapping[str,Any]], ids:set[str])->list[dict[str,str]]:
    out=[];seen=set()
    for row in evidence:
        if row.get("evidence_id") not in ids:
            continue
        prov=row.get("provenance")
        if not isinstance(prov,list):
            raise ValueError("SUPPORT_PROVENANCE_REQUIRED")
        for p in prov:
            if not isinstance(p,Mapping):
                raise ValueError("SUPPORT_PROVENANCE_ROW_INVALID")
            sid=p.get("source_id");loc=p.get("locator")
            if not isinstance(sid,str) or not sid.strip():
                raise ValueError("SUPPORT_SOURCE_ID_REQUIRED")
            if loc is not None and (not isinstance(loc,str) or not loc.strip()):
                raise ValueError("SUPPORT_LOCATOR_INVALID")
            key=(sid,loc or "")
            if key in seen: continue
            seen.add(key)
            item={"source_id":sid}
            if loc is not None:item["locator"]=loc
            out.append(item)
    if not out:
        raise ValueError("NO_SUPPORT_PROVENANCE")
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
    claims=task.get("claims");evidence=task.get("evidence");profile=task.get("audience_profile")
    if not isinstance(claims,list) or not claims:
        return _fail("CLAIMS_REQUIRED")
    if not isinstance(evidence,list) or not evidence:
        return _fail("EVIDENCE_REQUIRED")
    if not isinstance(profile,Mapping):
        return _fail("AUDIENCE_PROFILE_REQUIRED")
    if task.get("required_uncertainty_units")!=[]:
        return _fail("NONEMPTY_OR_UNBOUND_UNCERTAINTY_OUTSIDE_CELL")
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
    if str(constraints.get("output_format") or "").upper()=="SECTIONED_MARKDOWN":
        return _fail("SECTIONED_MARKDOWN_OUTSIDE_V1_WITHOUT_EXPLICIT_ITEM_SECTIONS")

    normalized_evidence=[]
    seen_eids=set()
    for row in evidence:
        if not isinstance(row,Mapping):
            return _fail("EVIDENCE_ROW_INVALID")
        eid=row.get("evidence_id")
        if not isinstance(eid,str) or not eid.strip() or eid in seen_eids:
            return _fail("EVIDENCE_ID_INVALID_OR_DUPLICATE")
        seen_eids.add(eid)
        if row.get("verified") is not True:
            return _fail("UNVERIFIED_EVIDENCE_UNIT")
        if not isinstance(row.get("text"),str) or not row["text"].strip():
            return _fail("EVIDENCE_TEXT_REQUIRED")
        if not isinstance(row.get("provenance"),list) or not row["provenance"]:
            return _fail("EVIDENCE_PROVENANCE_REQUIRED")
        normalized_evidence.append(dict(row))

    items=[];support_receipts=[];seen_claims=set()
    for row in claims:
        if not isinstance(row,Mapping):
            return _fail("CLAIM_ROW_INVALID")
        cid=row.get("claim_id");text=row.get("text")
        if not isinstance(cid,str) or not cid.strip() or cid in seen_claims:
            return _fail("CLAIM_ID_INVALID_OR_DUPLICATE")
        seen_claims.add(cid)
        if not isinstance(text,str) or not text.strip():
            return _fail("CLAIM_TEXT_REQUIRED")
        if row.get("required") is not True:
            return _fail("OPTIONAL_CLAIM_OUTSIDE_REQUIRED_ONLY_CELL")
        if "include" in row:
            return _fail("CALLER_INCLUDE_FORBIDDEN")

        receipt=support_truth({
          "predicate_id":"P3_REQUIRED_SUPPORT:"+cid,
          "claim":{"claim_id":cid,"text":text,"required":True},
          "evidence":normalized_evidence,
        })
        support_receipts.append({"claim_id":cid,"receipt":receipt})
        if receipt.get("pass") is not True:
            return _fail("REQUIRED_CLAIM_SUPPORT_UNKNOWN",claim_id=cid,support_receipt=receipt)
        if receipt.get("predicate_truth")!="TRUE":
            return _fail("REQUIRED_CLAIM_NOT_CERTIFIABLY_SUPPORTED",claim_id=cid,support_receipt=receipt)
        support_ids=set(receipt.get("support_evidence_ids") or [])
        try:
            provenance=_support_provenance(normalized_evidence,support_ids)
        except ValueError as exc:
            return _fail(str(exc),claim_id=cid)
        items.append({"id":cid,"kind":"CLAIM","text":text,"provenance":provenance})

    realizer_constraints=dict(constraints)
    realizer_constraints["item_order"]="INPUT"
    c2={
      "schema":realizer.INPUT_SCHEMA,
      "task":{
        "items":items,
        "constraints":realizer_constraints,
      },
    }
    title=task.get("title")
    if title is None:
        title=profile.get("title")
    if title is not None:
        c2["task"]["title"]=title

    rendered=realizer.solve(c2)
    if rendered.get("status")!="PASS":
        return _fail("GROUNDED_REALIZER_FAIL_CLOSED",realizer_result=rendered)
    audit=rendered.get("audit") or {}
    if (
        audit.get("input_item_count")!=len(claims)
        or audit.get("rendered_item_count")!=len(claims)
        or audit.get("dropped_item_count")!=0
        or audit.get("rewritten_material_item_count")!=0
        or audit.get("new_material_claim_count")!=0
        or audit.get("all_items_provenance_bound") is not True
    ):
        return _fail("GROUNDED_REALIZER_AUDIT_INCOMPLETE",audit=audit)

    return {
      "schema":SCHEMA,"pass":True,
      "status":"PASS__P3_REQUIRED_CLAIM_GROUNDED_REALIZATION_CELL",
      "p3_contract_cell_authorized":True,
      "claim_count":len(claims),
      "support_receipts":support_receipts,
      "rendered_text":rendered["rendered_text"],
      "render_trace":rendered["trace"],
      "realizer_audit":audit,
      "source_authorization_verified":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,
      "boundary":"ALL_CLAIMS_REQUIRED__SUPPORT_TRUTH_V5_TRUE_FOR_EACH__EMPTY_REQUIRED_UNCERTAINTY__EXPLICIT_BOUNDED_RENDER_CONSTRAINTS__NO_OPTIONAL_RELEVANCE_OR_GENERAL_UNCERTAINTY",
    }

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
