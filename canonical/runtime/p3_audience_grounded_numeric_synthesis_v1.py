"""Bounded audience-sensitive numeric evidence synthesis, no hidden labels.

Reuses only caller-visible, exact typed facts. It does not infer source
authorization, semantic entailment beyond Decimal comparison, natural-language
adequacy, Opus equivalence, or terminal credit. Selection and uncertainty are
derived from the underlying numeric observations, never from supplied support/
relevance labels. Audience selection is a real causal input.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_P3_AUDIENCE_GROUNDED_NUMERIC_SYNTHESIS_V1"
CONTRACT="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
PREFERENCES={
    "executive":("risk","trend"),
    "engineer":("mechanism","risk"),
    "auditor":("control","risk"),
    "operator":("operational","risk"),
}
RELATIONS={"at_least","at_most"}

class UnresolvedEvidence(ValueError):
    pass


def _hash(value:Any)->str:
    return sha256(json.dumps(value,sort_keys=True,separators=(",",":"),
                             ensure_ascii=False).encode("utf-8")).hexdigest()


def _decimal(value:Any)->Decimal:
    # No binary floating point: numeric literals must retain source precision.
    if isinstance(value,bool) or not isinstance(value,(int,str)):
        raise UnresolvedEvidence("EXACT_NUMERIC_LITERAL_REQUIRED")
    try:
        n=Decimal(str(value))
    except InvalidOperation as e:
        raise UnresolvedEvidence("NUMERIC_LITERAL_INVALID") from e
    if not n.is_finite():
        raise UnresolvedEvidence("NONFINITE_NUMERIC_LITERAL")
    return n


def _text(value:Any,field:str)->str:
    if not isinstance(value,str) or not value.strip():
        raise UnresolvedEvidence(field+"_REQUIRED")
    return value


def solve(public:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(public,Mapping) or public.get("contract")!=CONTRACT:
        raise UnresolvedEvidence("CONTRACT_REQUIRED")
    task=public.get("task")
    if not isinstance(task,Mapping):
        raise UnresolvedEvidence("TASK_REQUIRED")
    audience=_text(task.get("audience"),"AUDIENCE")
    if audience not in PREFERENCES:
        raise UnresolvedEvidence("UNSUPPORTED_AUDIENCE")
    constraints=task.get("format_constraints")
    if not isinstance(constraints,Mapping):
        raise UnresolvedEvidence("FORMAT_CONSTRAINTS_REQUIRED")
    cap=constraints.get("max_claims")
    if isinstance(cap,bool) or not isinstance(cap,int) or cap<0:
        raise UnresolvedEvidence("MAX_CLAIMS_INVALID")
    if constraints.get("ordered_required_first") is not True:
        raise UnresolvedEvidence("UNSUPPORTED_ORDER_CONSTRAINT")
    required=task.get("required_claims")
    claims=task.get("claims")
    evidence=task.get("evidence")
    if not isinstance(required,list) or not all(isinstance(x,str) and x for x in required):
        raise UnresolvedEvidence("REQUIRED_CLAIMS_INVALID")
    if len(set(required))!=len(required):
        raise UnresolvedEvidence("REQUIRED_CLAIM_DUPLICATE")
    if not isinstance(claims,list) or not isinstance(evidence,list):
        raise UnresolvedEvidence("CLAIMS_AND_EVIDENCE_REQUIRED")
    if not evidence:
        raise UnresolvedEvidence("EVIDENCE_REQUIRED")

    evidence_by_metric:dict[tuple[str,str],list[dict[str,Any]]]={}
    ids=set()
    for i,row in enumerate(evidence):
        if not isinstance(row,Mapping):
            raise UnresolvedEvidence("EVIDENCE_ROW_INVALID")
        if any(k in row for k in ("role","support","relevance","audience","required")):
            raise UnresolvedEvidence("UNVERIFIED_EVIDENCE_LABEL_FORBIDDEN")
        eid=_text(row.get("evidence_id"),"EVIDENCE_ID")
        metric=_text(row.get("metric"),"METRIC")
        unit=_text(row.get("unit"),"UNIT")
        if eid in ids:
            raise UnresolvedEvidence("DUPLICATE_EVIDENCE_ID")
        ids.add(eid)
        value=_decimal(row.get("value"))
        source=_text(row.get("source_id"),"SOURCE_ID")
        evidence_by_metric.setdefault((metric,unit),[]).append({
            "evidence_id":eid,"source_id":source,"value":value,
            "source_record_sha256":_hash(dict(row)),
        })

    unique_claims={}
    for row in claims:
        if not isinstance(row,Mapping):
            raise UnresolvedEvidence("CLAIM_INVALID")
        if any(k in row for k in ("role","support","relevance","audience")):
            raise UnresolvedEvidence("UNVERIFIED_CLAIM_LABEL_FORBIDDEN")
        cid=_text(row.get("claim_id"),"CLAIM_ID")
        metric=_text(row.get("metric"),"METRIC")
        unit=_text(row.get("unit"),"UNIT")
        kind=_text(row.get("kind"),"KIND")
        if cid in unique_claims:
            raise UnresolvedEvidence("DUPLICATE_CLAIM_ID")
        if row.get("relation") not in RELATIONS:
            raise UnresolvedEvidence("UNSUPPORTED_RELATION")
        unique_claims[cid]={
            "claim_id":cid,"metric":metric,"unit":unit,
            "kind":kind,"relation":row["relation"],
            "threshold":_decimal(row.get("threshold")),
        }
    if any(x not in unique_claims for x in required):
        raise UnresolvedEvidence("REQUIRED_CLAIM_NOT_DECLARED")

    admitted={}
    unresolved=[]
    for cid,row in unique_claims.items():
        observations=evidence_by_metric.get((row["metric"],row["unit"]),[])
        if not observations:
            unresolved.append(cid)
            continue
        votes=[
            (e["value"]>=row["threshold"] if row["relation"]=="at_least"
             else e["value"]<=row["threshold"]) for e in observations
        ]
        if not any(votes):
            unresolved.append(cid)
            continue
        admitted[cid]={
            "uncertain":not all(votes),
            "evidence":[
                {"evidence_id":e["evidence_id"],"source_id":e["source_id"],
                 "source_record_sha256":e["source_record_sha256"],
                 "comparison_holds":vote}
                for e,vote in zip(observations,votes)
            ],
        }

    if any(cid not in admitted for cid in required):
        raise UnresolvedEvidence("REQUIRED_CLAIM_NOT_PROVABLE")
    if len(required)>cap:
        raise UnresolvedEvidence("REQUIRED_CLAIMS_EXCEED_CAPACITY")

    preferences=PREFERENCES[audience]
    optional=[
        cid for cid,row in unique_claims.items()
        if cid not in required and cid in admitted and row["kind"] in preferences
    ]
    optional.sort(key=lambda cid:(
        preferences.index(unique_claims[cid]["kind"]),cid
    ))
    chosen=required+optional[:cap-len(required)]
    return {
        "schema":SCHEMA,
        "status":"BOUNDED_NUMERIC_EVIDENCE_SYNTHESIS_WITH_AUDIENCE_CONDITIONING",
        "selected_claims":chosen,
        "uncertainty_claims":[cid for cid in chosen if admitted[cid]["uncertain"]],
        "claim_provenance":{cid:admitted[cid]["evidence"] for cid in chosen},
        "unresolved_claim_ids":sorted(unresolved),
        "audience_applied":audience,
        "input_sha256":_hash(public),
        "source_authorization_verified":False,
        "semantic_claim_adequacy_verified":False,
        "target_relative_quality_verified":False,
        "u_subtraction_authorized":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "scope":"BOUNDED_DECIMAL_COMPARISON_PLUS_EXPLICIT_AUDIENCE_KIND_ORDER_ONLY",
    }
