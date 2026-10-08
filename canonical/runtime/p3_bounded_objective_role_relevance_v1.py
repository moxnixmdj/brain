"""Bounded P3 optional-relevance role binding v1.

Closes one narrow information gap: when an explicit binary-comparison objective
names exactly two operand roles, and the complete optional-claim set consists of
exact verified-evidence statements that surface-anchor those two operand phrases,
the two optional claims are decision-role relevant.

This is a relevance certificate only. It does not decide general semantic
salience, presentation adequacy, claim ordering quality, source authority,
policy adequacy, DB admission, U subtraction, or terminal closure.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.bound_capabilities import objective_claim_operand_binding as binder

SCHEMA="PROJECT_BRAIN_P3_BOUNDED_OBJECTIVE_ROLE_RELEVANCE_V1"


def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "optional_relevance_complete":False,
        "general_semantic_relevance":False,
        "organization_policy_complete":False,
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

    objective=_canon(payload.get("objective"))
    if not objective:
        return _fail("OBJECTIVE_REQUIRED")

    claims=payload.get("claims")
    evidence=payload.get("evidence")
    if not isinstance(claims,Sequence) or isinstance(claims,(str,bytes)) or not claims:
        return _fail("CLAIMS_REQUIRED")
    if not isinstance(evidence,Sequence) or isinstance(evidence,(str,bytes)) or not evidence:
        return _fail("EVIDENCE_REQUIRED")

    parsed,parse_reason=binder._parse_objective(objective)
    if parse_reason or not parsed or parsed.get("mode")!="NUMERIC_RELATION":
        return _fail("OBJECTIVE_ROLE_BINDING_UNRESOLVED", parser_reason=parse_reason)

    left_phrase=_canon(parsed.get("left_entity"))
    right_phrase=_canon(parsed.get("right_entity"))
    if not left_phrase or not right_phrase or left_phrase.casefold()==right_phrase.casefold():
        return _fail("OBJECTIVE_ROLE_BINDING_UNRESOLVED")

    by_text:dict[str,list[dict[str,Any]]]={}
    seen_eids:set[str]=set()
    evidence_bindings=[]
    for row in evidence:
        if not isinstance(row,Mapping):
            return _fail("EVIDENCE_ROW_INVALID")
        eid=row.get("evidence_id")
        text=_canon(row.get("text"))
        if not isinstance(eid,str) or not eid.strip() or eid in seen_eids:
            return _fail("EVIDENCE_ID_INVALID_OR_DUPLICATE")
        if not text:
            return _fail("EVIDENCE_TEXT_REQUIRED")
        if row.get("verified") is not True:
            return _fail("UNVERIFIED_EVIDENCE_UNIT")
        provenance=row.get("provenance")
        if not isinstance(provenance,list) or not provenance or not all(isinstance(x,Mapping) for x in provenance):
            return _fail("EVIDENCE_PROVENANCE_REQUIRED")
        seen_eids.add(eid)
        item={"evidence_id":eid,"text":text,"provenance":[dict(x) for x in provenance]}
        by_text.setdefault(text.casefold(),[]).append(item)
        evidence_bindings.append(item)

    left_role_evidence=[
        row for row in evidence_bindings
        if left_phrase.casefold() in row["text"].casefold()
    ]
    right_role_evidence=[
        row for row in evidence_bindings
        if right_phrase.casefold() in row["text"].casefold()
    ]
    if len(left_role_evidence)!=1 or len(right_role_evidence)!=1:
        return _fail(
            "OBJECTIVE_ROLE_BINDING_UNRESOLVED",
            left_role_evidence_count=len(left_role_evidence),
            right_role_evidence_count=len(right_role_evidence),
        )
    if left_role_evidence[0]["evidence_id"]==right_role_evidence[0]["evidence_id"]:
        return _fail("OBJECTIVE_ROLE_BINDING_UNRESOLVED")

    optional=[]
    required=[]
    seen_cids:set[str]=set()
    for row in claims:
        if not isinstance(row,Mapping):
            return _fail("CLAIM_ROW_INVALID")
        cid=row.get("claim_id")
        text=_canon(row.get("text"))
        req=row.get("required")
        if not isinstance(cid,str) or not cid.strip() or cid in seen_cids:
            return _fail("CLAIM_ID_INVALID_OR_DUPLICATE")
        if not text:
            return _fail("CLAIM_TEXT_REQUIRED")
        if type(req) is not bool:
            return _fail("CLAIM_REQUIRED_FLAG_MUST_BE_BOOLEAN")
        seen_cids.add(cid)
        item={"claim_id":cid,"text":text,"required":req}
        (required if req else optional).append(item)

    if len(optional)!=2:
        return _fail(
            "OPTIONAL_CLAIM_SET_NOT_EXACTLY_BINARY_OBJECTIVE_ROLES",
            optional_claim_count=len(optional),
        )

    role_to_claim:dict[str,dict[str,Any]]={}
    claim_bindings=[]
    for claim in optional:
        matches=by_text.get(claim["text"].casefold(),[])
        if len(matches)!=1:
            return _fail(
                "OPTIONAL_CLAIM_NOT_EXACT_VERIFIED_EVIDENCE",
                claim_id=claim["claim_id"],
                exact_evidence_match_count=len(matches),
            )
        surface=claim["text"].casefold()
        is_left=left_phrase.casefold() in surface
        is_right=right_phrase.casefold() in surface
        if is_left == is_right:
            return _fail(
                "OPTIONAL_CLAIM_NOT_UNIQUE_OBJECTIVE_ROLE",
                claim_id=claim["claim_id"],
            )
        role="LEFT" if is_left else "RIGHT"
        if role in role_to_claim:
            return _fail("OBJECTIVE_ROLE_NOT_BIJECTIVE", duplicate_role=role)
        role_to_claim[role]=claim
        claim_bindings.append({
            "claim_id":claim["claim_id"],
            "role":role,
            "evidence_id":matches[0]["evidence_id"],
        })

    if set(role_to_claim)!={"LEFT","RIGHT"}:
        return _fail("OBJECTIVE_ROLE_NOT_BIJECTIVE")

    left=role_to_claim["LEFT"]["claim_id"]
    right=role_to_claim["RIGHT"]["claim_id"]
    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__BOUNDED_OPTIONAL_RELEVANCE_ROLE_BINDING",
        "objective":objective,
        "objective_operator":parsed.get("operator"),
        "left_objective_phrase":left_phrase,
        "right_objective_phrase":right_phrase,
        "left_claim_id":left,
        "right_claim_id":right,
        "relevant_optional_claim_ids":[left,right],
        "required_claim_ids":[row["claim_id"] for row in required],
        "objective_role_order":[left,right],
        "claim_role_evidence_bindings":sorted(claim_bindings,key=lambda x:x["role"]),
        "optional_relevance_complete":True,
        "relevance_claim_scope":"EXACT_BINARY_OBJECTIVE_OPERAND_PHRASE_TO_EXACT_VERIFIED_EVIDENCE_CLAIM",
        "general_semantic_relevance":False,
        "organization_policy_complete":False,
        "source_authorization_verified":False,
        "policy_adequacy_authority":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "boundary":"EXPLICIT_BINARY_NUMERIC_COMPARISON_GRAMMAR__EXACT_OPTIONAL_CLAIM_TO_VERIFIED_EVIDENCE_TEXT__EXACT_OPERAND_PHRASE_ROLE_ANCHORS_ONLY",
    }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
