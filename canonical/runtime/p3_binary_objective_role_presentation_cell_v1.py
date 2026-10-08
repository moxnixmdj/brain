"""P3 binary-objective role presentation common-policy cell v1.

Narrow cell:
- an explicit binary numeric-comparison objective;
- exactly two optional claims, already certifiably RELEVANT by the verified
  binary objective-role relevance gate;
- no required claims and no required uncertainty units;
- explicit audience/format constraints accepted by the grounded realizer.

The common organization policy is: preserve both decision-relevant role claims
verbatim, LEFT role then RIGHT role, with their exact provenance. The grounded
realizer must prove zero drops, zero material rewrites, zero new claims, complete
provenance, and exact order. This does not establish source authorization,
general semantic salience, arbitrary audience preference, policy adequacy,
DB admission, U subtraction, or terminal closure.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.p3_bounded_objective_role_relevance_v1 import evaluate as relevance
from canonical.runtime import synthesis_grounded_expression_ir_v1 as realizer

SCHEMA="PROJECT_BRAIN_P3_BINARY_OBJECTIVE_ROLE_PRESENTATION_CELL_V1"


def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "p3_contract_cell_authorized":False,
        "organization_policy_complete":False,
        "source_authorization_verified":False,
        "policy_adequacy_authority":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
    if detail:
        out["detail"]=detail
    return out


def _canon(value:Any)->str:
    return " ".join(str(value or "").strip().split())


def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    claims=payload.get("claims")
    evidence=payload.get("evidence")
    if not isinstance(claims,Sequence) or isinstance(claims,(str,bytes)) or not claims:
        return _fail("CLAIMS_REQUIRED")
    if not isinstance(evidence,Sequence) or isinstance(evidence,(str,bytes)) or not evidence:
        return _fail("EVIDENCE_REQUIRED")
    if payload.get("required_uncertainty_units") != []:
        return _fail("NONEMPTY_OR_UNBOUND_UNCERTAINTY_OUTSIDE_CELL")

    required=[]
    for row in claims:
        if not isinstance(row,Mapping):
            return _fail("CLAIM_ROW_INVALID")
        if row.get("required") is True:
            required.append(row.get("claim_id"))
    if required:
        return _fail(
            "REQUIRED_CLAIMS_OUTSIDE_BINARY_OPTIONAL_PRESENTATION_CELL",
            required_claim_ids=required,
        )

    rel=relevance({
        "objective":payload.get("objective"),
        "claims":claims,
        "evidence":evidence,
    })
    if rel.get("pass") is not True:
        return _fail("RELEVANCE_CERTIFICATE_FAILED", relevance_result=rel)
    if (
        rel.get("optional_relevance_complete") is not True
        or rel.get("negative_relevance_authority") is not False
        or set((rel.get("truthful_precommitment_relevance_bits") or {}).values()) != {"RELEVANT"}
    ):
        return _fail("RELEVANCE_CERTIFICATE_BOUNDARY_INVALID")

    left=rel.get("left_claim_id")
    right=rel.get("right_claim_id")
    if not isinstance(left,str) or not isinstance(right,str) or left==right:
        return _fail("OBJECTIVE_ROLE_ORDER_INVALID")

    claim_by_id={}
    for row in claims:
        cid=row.get("claim_id")
        if not isinstance(cid,str) or cid in claim_by_id:
            return _fail("CLAIM_ID_INVALID_OR_DUPLICATE")
        text=_canon(row.get("text"))
        if not text:
            return _fail("CLAIM_TEXT_REQUIRED")
        claim_by_id[cid]={"claim_id":cid,"text":text}

    evidence_by_id={}
    for row in evidence:
        if not isinstance(row,Mapping):
            return _fail("EVIDENCE_ROW_INVALID")
        eid=row.get("evidence_id")
        if not isinstance(eid,str) or not eid or eid in evidence_by_id:
            return _fail("EVIDENCE_ID_INVALID_OR_DUPLICATE")
        evidence_by_id[eid]=row

    bindings=rel.get("claim_role_evidence_bindings")
    if not isinstance(bindings,list) or len(bindings)!=2:
        return _fail("RELEVANCE_EVIDENCE_BINDING_INVALID")
    evidence_for_claim={}
    for row in bindings:
        if not isinstance(row,Mapping):
            return _fail("RELEVANCE_EVIDENCE_BINDING_INVALID")
        cid=row.get("claim_id"); eid=row.get("evidence_id")
        if cid not in {left,right} or eid not in evidence_by_id or cid in evidence_for_claim:
            return _fail("RELEVANCE_EVIDENCE_BINDING_INVALID")
        ev=evidence_by_id[eid]
        if ev.get("verified") is not True:
            return _fail("RELEVANCE_EVIDENCE_BINDING_INVALID")
        provenance=ev.get("provenance")
        if not isinstance(provenance,list) or not provenance:
            return _fail("EVIDENCE_PROVENANCE_REQUIRED")
        evidence_for_claim[cid]=ev
    if set(evidence_for_claim)!={left,right}:
        return _fail("RELEVANCE_EVIDENCE_BINDING_INVALID")

    constraints=payload.get("audience_constraints")
    if not isinstance(constraints,Mapping):
        return _fail("AUDIENCE_CONSTRAINTS_REQUIRED")
    compiled_constraints=dict(constraints)
    compiled_constraints["item_order"]=[left,right]

    items=[]
    for cid in (left,right):
        ev=evidence_for_claim[cid]
        items.append({
            "id":cid,
            "kind":"CLAIM",
            "text":claim_by_id[cid]["text"],
            "provenance":[dict(x) for x in ev["provenance"]],
        })

    task={"items":items,"constraints":compiled_constraints}
    if payload.get("title") is not None:
        task["title"]=payload.get("title")
    rendered=realizer.solve({"schema":realizer.INPUT_SCHEMA,"task":task})
    if rendered.get("status")!="PASS":
        return _fail("GROUNDED_REALIZER_FAIL_CLOSED", realizer_result=rendered)

    audit=rendered.get("audit") or {}
    trace=rendered.get("trace") or []
    if (
        audit.get("input_item_count") != 2
        or audit.get("rendered_item_count") != 2
        or audit.get("dropped_item_count") != 0
        or audit.get("rewritten_material_item_count") != 0
        or audit.get("new_material_claim_count") != 0
        or audit.get("all_items_provenance_bound") is not True
        or [x.get("item_id") for x in trace] != [left,right]
    ):
        return _fail("GROUNDED_REALIZER_AUDIT_INCOMPLETE", audit=audit)

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__P3_BINARY_OBJECTIVE_ROLE_PRESENTATION_COMMON_POLICY_CELL",
        "p3_contract_cell_authorized":True,
        "selected_claim_ids":[left,right],
        "claim_order":[left,right],
        "organization_policy":"PRESERVE_BOTH_RELEVANT_OBJECTIVE_ROLES__LEFT_THEN_RIGHT__VERBATIM_WITH_PROVENANCE",
        "organization_policy_complete":True,
        "organization_claim_scope":"EXACT_TWO_POSITIVELY_RELEVANT_BINARY_OBJECTIVE_ROLE_CLAIMS_WITH_NO_OTHER_CLAIMS_OR_UNCERTAINTY",
        "relevance_receipt":rel,
        "rendered_text":rendered.get("rendered_text"),
        "render_trace":trace,
        "realizer_audit":audit,
        "source_authorization_verified":False,
        "general_audience_semantics_verified":False,
        "policy_adequacy_authority":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "boundary":"EXACT_BINARY_OBJECTIVE_ROLE_RELEVANCE_PASS__NO_REQUIRED_CLAIMS__EMPTY_UNCERTAINTY__EXPLICIT_REALIZER_CONSTRAINTS__NO_GENERAL_PRESENTATION_OR_AUDIENCE_SEMANTICS",
    }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
