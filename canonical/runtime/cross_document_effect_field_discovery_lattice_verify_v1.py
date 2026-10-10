"""Independent verifier for bounded field-proof discovery lattice V1."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime import cross_document_effect_semantic_lattice_v8 as lattice
from canonical.runtime import cross_document_effect_semantic_lattice_verify_v8 as lattice_verify
from canonical.runtime.document_effect_field_proof_discovery_v1 import (
    SCHEMA as DISCOVERY_SCHEMA,
    discover,
)

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_FIELD_DISCOVERY_LATTICE_VERIFY_V1"
PROBLEM_SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_FIELD_DISCOVERY_LATTICE_V1"


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    cleaned=v.strip()
    if cleaned!=v:
        raise ValueError(name+"_NOT_CANONICAL")
    return cleaned


def _docs(problem:Mapping[str,Any])->dict[str,dict[str,Any]]:
    rows=problem.get("source_documents")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)):
        raise ValueError("SOURCE_DOCUMENTS_INVALID")
    out={}
    for row in rows:
        if not isinstance(row,Mapping):
            raise ValueError("SOURCE_DOCUMENT_INVALID")
        did=_token(row.get("document_id"),"DOCUMENT_ID")
        sid=_token(row.get("source_id"),"SOURCE_ID")
        text=row.get("source_text")
        claims=row.get("claims")
        if not isinstance(text,str) or not text:
            raise ValueError("SOURCE_TEXT_INVALID")
        if not isinstance(claims,Sequence) or isinstance(claims,(str,bytes)):
            raise ValueError("CLAIMS_INVALID")
        if did in out:
            raise ValueError("DOCUMENT_ID_DUPLICATE")
        out[did]={
            "document_id":did,
            "source_id":sid,
            "source_text":text,
            "claims":deepcopy(list(claims)),
        }
    return out


def _recompute(problem:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(problem,Mapping) or problem.get("schema")!=PROBLEM_SCHEMA:
        raise ValueError("PROBLEM_SCHEMA_INVALID")
    if set(problem)!={"schema","case_id","lattice_problem","discovery_requests"}:
        raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")
    case_id=_token(problem.get("case_id"),"CASE_ID")
    base=problem.get("lattice_problem")
    if not isinstance(base,Mapping):
        raise ValueError("LATTICE_PROBLEM_INVALID")
    base=deepcopy(dict(base))
    if base.get("schema")!=lattice.SCHEMA or base.get("case_id")!=case_id:
        raise ValueError("LATTICE_PROBLEM_BINDING_INVALID")

    requests=problem.get("discovery_requests")
    if not isinstance(requests,Sequence) or isinstance(requests,(str,bytes)):
        raise ValueError("DISCOVERY_REQUESTS_INVALID")

    base_result=lattice.evaluate(base)
    if base_result.get("status")=="FAIL_CLOSED":
        raise ValueError("BASE_LATTICE_FAIL_CLOSED")
    base_check=lattice_verify.verify(base,base_result)
    if base_check.get("verified") is not True:
        raise ValueError("BASE_LATTICE_VERIFY_FAILED")

    docs=_docs(base)
    open_slots={}
    for atom in base_result.get("open_lattice_atoms") or []:
        if (
            isinstance(atom,Mapping)
            and atom.get("dimension")=="DOCUMENT_EFFECT_FIELD"
        ):
            key=(
                str(atom.get("document_id") or ""),
                str(atom.get("effect_id") or ""),
                str(atom.get("field") or ""),
            )
            if all(key):
                open_slots[key]=dict(atom)

    working=deepcopy(base)
    working_docs={
        str(x.get("document_id") or ""):x
        for x in working.get("source_documents") or []
        if isinstance(x,Mapping)
    }
    discovered=[]
    unresolved=[]
    seen=set()

    for i,req in enumerate(requests):
        if not isinstance(req,Mapping) or set(req)!={
            "document_id","effect_id","field","scope_id",
            "candidate_spans","candidate_values",
            "relation_evidence_candidates",
        }:
            raise ValueError("DISCOVERY_REQUEST_FIELD_SET_INVALID:"+str(i))
        did=_token(req.get("document_id"),"DOCUMENT_ID")
        eid=_token(req.get("effect_id"),"EFFECT_ID")
        field=_token(req.get("field"),"FIELD")
        key=(did,eid,field)
        if key in seen:
            raise ValueError("DISCOVERY_REQUEST_DUPLICATE")
        seen.add(key)
        if key not in open_slots:
            raise ValueError("DISCOVERY_REQUEST_NOT_BOUND_TO_OPEN_FIELD_ATOM")
        doc=docs.get(did)
        if doc is None:
            raise ValueError("DISCOVERY_DOCUMENT_NOT_FOUND")
        found=discover({
            "schema":DISCOVERY_SCHEMA,
            "source_id":doc["source_id"],
            "source_text":doc["source_text"],
            "scope_id":req.get("scope_id"),
            "effect_id":eid,
            "field":field,
            "candidate_spans":deepcopy(req.get("candidate_spans")),
            "candidate_values":deepcopy(req.get("candidate_values")),
            "relation_evidence_candidates":deepcopy(
                req.get("relation_evidence_candidates")
            ),
        })
        if str(found.get("status") or "").startswith("FAIL_CLOSED"):
            return {
                "status":"FAIL_CLOSED__DISCOVERY_CONFLICT_OR_INVALID",
                "pass":False,
                "failed_request_key":list(key),
            }
        if found.get("pass") is not True:
            unresolved.append({
                "document_id":did,
                "effect_id":eid,
                "field":field,
                "discovery_result":found,
            })
            continue
        claim=found.get("claim")
        if not isinstance(claim,Mapping):
            raise ValueError("DISCOVERY_PASS_WITHOUT_CLAIM")
        working_docs[did]["claims"].append(deepcopy(dict(claim)))
        discovered.append({
            "document_id":did,
            "effect_id":eid,
            "field":field,
            "value":deepcopy(found.get("value")),
            "claim":deepcopy(dict(claim)),
            "field_receipt":deepcopy(found.get("field_receipt")),
            "proved_candidate_count":found.get("proved_candidate_count"),
        })

    final=lattice.evaluate(working)
    if final.get("status")=="FAIL_CLOSED":
        return {
            "status":"FAIL_CLOSED__POST_DISCOVERY_LATTICE",
            "pass":False,
            "discovered_claims":discovered,
            "unresolved_discovery_requests":unresolved,
        }
    checked=lattice_verify.verify(working,final)
    if checked.get("verified") is not True:
        raise ValueError("POST_DISCOVERY_LATTICE_VERIFY_FAILED")

    common={
        "discovered_claim_count":len(discovered),
        "discovered_claims":discovered,
        "unresolved_discovery_requests":unresolved,
    }
    if final.get("pass") is True:
        return {
            "status":"PASS__DISCOVERED_AUTHENTICATED_PROOFS_CLOSE_LATTICE",
            "pass":True,
            **common,
            "effective_value":deepcopy(final.get("effective_value")),
            "world_count":final.get("world_count"),
            "query_relative_effect_semantics_finite":True,
        }
    return {
        "status":"OPEN__DISCOVERY_EXHAUSTED_WITH_SEMANTIC_TOP_REMAINING",
        "pass":False,
        **common,
        "open_lattice_atoms":deepcopy(final.get("open_lattice_atoms") or []),
        "next_proof_obligations":deepcopy(
            final.get("next_proof_obligations") or []
        ),
        "possible_outcomes":deepcopy(final.get("possible_outcomes") or []),
        "minimum_discriminator_slots":deepcopy(
            final.get("minimum_discriminator_slots") or []
        ),
        "world_count":final.get("world_count"),
        "query_relative_effect_semantics_finite":final.get(
            "query_relative_effect_semantics_finite"
        ),
    }


def verify(problem:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    try:
        expected=_recompute(problem)
        if not isinstance(result,Mapping):
            raise ValueError("RESULT_NOT_OBJECT")
        keys=[
            "status","pass","discovered_claim_count",
            "discovered_claims","unresolved_discovery_requests",
        ]
        if expected.get("pass") is True:
            keys+=["effective_value","world_count","query_relative_effect_semantics_finite"]
        elif expected.get("status")=="OPEN__DISCOVERY_EXHAUSTED_WITH_SEMANTIC_TOP_REMAINING":
            keys+=[
                "open_lattice_atoms","next_proof_obligations",
                "possible_outcomes","minimum_discriminator_slots",
                "world_count","query_relative_effect_semantics_finite",
            ]
        elif expected.get("status")=="FAIL_CLOSED__DISCOVERY_CONFLICT_OR_INVALID":
            keys+=["failed_request_key"]
        for key in keys:
            if result.get(key)!=expected.get(key):
                errors.append("MISMATCH:"+key)
        for key in (
            "search_authority","semantic_truth_authority",
            "execution_authority","acceptance_authority","terminal_authority",
        ):
            if result.get(key) is not False:
                errors.append(key.upper()+"_CLAIMED")
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":(
            "PASS__INDEPENDENT_FIELD_DISCOVERY_LATTICE_RECOMPUTATION"
            if not errors else "FAIL_CLOSED"
        ),
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "search_authority":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "boundary":(
            "INDEPENDENT_RECOMPUTATION_OF_FINITE_DISCOVERY_REGISTRY_PROOFS_"
            "CLAIM_INJECTION_AND_EXISTING_V8_LATTICE_VERIFICATION"
        ),
    }
