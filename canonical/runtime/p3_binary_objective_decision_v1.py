"""Bounded binary objective decision derivation v1.

Bridges the verified P3 binary objective-role relevance surface into the already
verified objective_claim_operand_binding + generic_evidence_claim_relation
numeric relation evaluator.

The adapter constructs an integrity-bound extraction from the exact verified
role evidence rows, lets the existing binder choose the unique unit-compatible
numeric operands, and returns the verified boolean decision. It does not render
or style the decision and grants no policy/DB/U/terminal authority.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping

from canonical.runtime.p3_bounded_objective_role_relevance_v1 import evaluate as relevance
from canonical.runtime.bound_capabilities import objective_claim_operand_binding as binder

SCHEMA="PROJECT_BRAIN_P3_BINARY_OBJECTIVE_DECISION_V1"
EXTRACTION_SCHEMA="PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2"


def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "decision_derived":False,"required_decision_semantics_covered":False,
      "decision_expression_covered":False,"policy_adequacy_authority":False,
      "db_admission_authority":False,"u_subtraction_authority":False,
      "terminal_authority":False,"terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out


def _sha(text:str)->str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extraction(evidence:list[Mapping[str,Any]])->dict[str,Any]:
    visible="\n".join(str(row["text"]).strip() for row in evidence)
    page_sha=_sha(visible)
    visible_sha=page_sha
    rows=[]
    cursor=0
    for row in evidence:
        text=str(row["text"]).strip()
        start=cursor
        end=start+len(text)
        text_sha=_sha(text)
        uid=_sha(f"{page_sha}:{start}:{end}:{text_sha}")
        prov=row.get("provenance")
        source_id=""
        if isinstance(prov,list) and prov and isinstance(prov[0],Mapping):
            source_id=str(prov[0].get("source_id") or "")
        rows.append({
          "evidence_unit_id":uid,
          "text":text,
          "text_sha256":text_sha,
          "page_raw_sha256":page_sha,
          "visible_text_sha256":visible_sha,
          "visible_text_start":start,
          "visible_text_end":end,
          "source_url":"brain-source:"+source_id,
          "source_evidence_id":row["evidence_id"],
        })
        cursor=end+1
    return {
      "schema":EXTRACTION_SCHEMA,
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
      "output_verified":True,
      "page_raw_sha256":page_sha,
      "visible_text_sha256":visible_sha,
      "source_url":"brain://verified-role-evidence",
      "evidence_units":rows,
    }


def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    objective=payload.get("objective")
    claims=payload.get("claims")
    evidence=payload.get("evidence")
    if not isinstance(objective,str) or not objective.strip():
        return _fail("OBJECTIVE_REQUIRED")
    if not isinstance(claims,list) or not claims:
        return _fail("CLAIMS_REQUIRED")
    if not isinstance(evidence,list) or not evidence:
        return _fail("EVIDENCE_REQUIRED")

    rel=relevance({"objective":objective,"claims":claims,"evidence":evidence})
    if rel.get("pass") is not True:
        return _fail("OBJECTIVE_ROLE_RELEVANCE_UNRESOLVED",relevance=rel)
    if rel.get("optional_relevance_complete") is not True:
        return _fail("RELEVANCE_INCOMPLETE")
    bindings=rel.get("claim_role_evidence_bindings")
    if not isinstance(bindings,list) or len(bindings)!=2:
        return _fail("ROLE_EVIDENCE_BINDINGS_INVALID")
    by_eid={row.get("evidence_id"):row for row in evidence if isinstance(row,Mapping)}
    role_eids=[row.get("evidence_id") for row in bindings]
    if any(eid not in by_eid for eid in role_eids) or len(set(role_eids))!=2:
        return _fail("ROLE_EVIDENCE_ROWS_NOT_UNIQUE")

    # Keep only the two role-bound rows. This prevents unrelated numeric decoys
    # elsewhere in the evidence set from entering the objective binder.
    role_rows=[by_eid[eid] for eid in role_eids]
    ext=_extraction(role_rows)
    try:
        bound=binder.bind(objective,ext,evaluate_relation=True)
    except Exception as exc:
        return _fail("OBJECTIVE_RELATION_BINDING_FAILED",exception_type=type(exc).__name__,detail_text=str(exc)[:200])

    if bound.get("status")!="CLAIM_SPEC_AND_OPERANDS_BOUND" or bound.get("output_verified") is not True:
        return _fail("OBJECTIVE_RELATION_NOT_BOUND",binding=bound)
    relation=bound.get("relation_result")
    if not isinstance(relation,Mapping) or relation.get("status")!="NUMERIC_RELATION_VERIFIED" or relation.get("output_verified") is not True:
        return _fail("OBJECTIVE_RELATION_NOT_VERIFIED",binding=bound)
    predicate=relation.get("predicate")
    if type(predicate) is not bool:
        return _fail("OBJECTIVE_RELATION_PREDICATE_NOT_BOOLEAN")

    evidence_provenance=[]
    seen=set()
    for row in role_rows:
        for p in row.get("provenance") or []:
            if not isinstance(p,Mapping):
                return _fail("PROVENANCE_ROW_INVALID")
            sid=p.get("source_id"); loc=p.get("locator")
            if not isinstance(sid,str) or not sid.strip():
                return _fail("PROVENANCE_SOURCE_ID_REQUIRED")
            key=(sid,loc or "")
            if key in seen: continue
            seen.add(key)
            item={"source_id":sid}
            if loc is not None: item["locator"]=loc
            evidence_provenance.append(item)

    return {
      "schema":SCHEMA,"pass":True,
      "status":"PASS__BINARY_OBJECTIVE_DECISION_DERIVED",
      "objective":objective,
      "operator":relation.get("operator"),
      "decision_truth":predicate,
      "decision_derived":True,
      "required_decision_semantics_covered":True,
      "decision_expression_covered":False,
      "left_operand":relation.get("left"),
      "right_operand":relation.get("right"),
      "threshold":relation.get("threshold"),
      "decision_provenance":evidence_provenance,
      "relevance_receipt":rel,
      "objective_binding_receipt":bound,
      "extraction_sha256":_sha(str(ext)),
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,
      "boundary":"EXACT_BINARY_NUMERIC_OBJECTIVE__UNIQUE_ROLE_BOUND_VERIFIED_EVIDENCE__EXACT_UNIT_COMPATIBLE_DECIMAL_OPERANDS__DECISION_DERIVATION_ONLY__NO_PRESENTATION_OR_GENERAL_SEMANTICS",
    }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
