"""Bounded authenticated proof discovery over an open effect-field lattice V1.

This wrapper does not broaden semantic authority. It:
1. independently evaluates the existing V8 field lattice;
2. permits discovery only for exact DOCUMENT_EFFECT_FIELD atoms already at TOP;
3. searches a supplied finite proposal universe using
   document_effect_field_proof_discovery_v1;
4. injects only independently authenticated discovered edge claims;
5. reruns the unchanged V8 lattice and independent V8 verifier.

Search failure leaves TOP. Conflicting authenticated discoveries fail closed.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime import cross_document_effect_semantic_lattice_v8 as lattice
from canonical.runtime import cross_document_effect_semantic_lattice_verify_v8 as lattice_verify
from canonical.runtime.document_effect_field_proof_discovery_v1 import (
    SCHEMA as DISCOVERY_SCHEMA,
    discover,
)

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_FIELD_DISCOVERY_LATTICE_V1"
MAX_DISCOVERY_REQUESTS=64


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    cleaned=v.strip()
    if cleaned!=v:
        raise ValueError(name+"_NOT_CANONICAL")
    return cleaned


def _docs(problem:Mapping[str,Any])->dict[str,dict[str,Any]]:
    docs=problem.get("source_documents")
    if not isinstance(docs,Sequence) or isinstance(docs,(str,bytes)):
        raise ValueError("LATTICE_SOURCE_DOCUMENTS_INVALID")
    out={}
    for row in docs:
        if not isinstance(row,Mapping):
            raise ValueError("LATTICE_SOURCE_DOCUMENT_INVALID")
        did=_token(row.get("document_id"),"DOCUMENT_ID")
        sid=_token(row.get("source_id"),"SOURCE_ID")
        text=row.get("source_text")
        claims=row.get("claims")
        if not isinstance(text,str) or not text:
            raise ValueError("SOURCE_TEXT_INVALID:"+did)
        if not isinstance(claims,Sequence) or isinstance(claims,(str,bytes)):
            raise ValueError("CLAIMS_INVALID:"+did)
        if did in out:
            raise ValueError("DOCUMENT_ID_DUPLICATE:"+did)
        out[did]={
            "document_id":did,
            "source_id":sid,
            "source_text":text,
            "claims":deepcopy(list(claims)),
        }
    return out


def evaluate(problem:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(problem,Mapping) or problem.get("schema")!=SCHEMA:
            raise ValueError("PROBLEM_SCHEMA_INVALID")
        if set(problem)!={"schema","case_id","lattice_problem","discovery_requests"}:
            raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")
        case_id=_token(problem.get("case_id"),"CASE_ID")
        base_problem=problem.get("lattice_problem")
        if not isinstance(base_problem,Mapping):
            raise ValueError("LATTICE_PROBLEM_INVALID")
        base_problem=deepcopy(dict(base_problem))
        if base_problem.get("schema")!=lattice.SCHEMA:
            raise ValueError("LATTICE_PROBLEM_SCHEMA_INVALID")
        if base_problem.get("case_id")!=case_id:
            raise ValueError("CASE_ID_MISMATCH")

        requests=problem.get("discovery_requests")
        if (
            not isinstance(requests,Sequence)
            or isinstance(requests,(str,bytes))
            or len(requests)>MAX_DISCOVERY_REQUESTS
        ):
            raise ValueError("DISCOVERY_REQUESTS_INVALID_OR_TOO_LARGE")

        base_result=lattice.evaluate(base_problem)
        if base_result.get("status")=="FAIL_CLOSED":
            raise ValueError(
                "BASE_LATTICE_FAIL_CLOSED:"+str(base_result.get("reason") or "")
            )
        base_checked=lattice_verify.verify(base_problem,base_result)
        if base_checked.get("verified") is not True:
            raise ValueError(
                "BASE_LATTICE_VERIFY_FAILED:"
                +",".join(base_checked.get("errors") or [])
            )

        docs=_docs(base_problem)
        open_slots={}
        for atom in base_result.get("open_lattice_atoms") or []:
            if not isinstance(atom,Mapping):
                continue
            if atom.get("dimension")!="DOCUMENT_EFFECT_FIELD":
                continue
            key=(
                str(atom.get("document_id") or ""),
                str(atom.get("effect_id") or ""),
                str(atom.get("field") or ""),
            )
            if all(key):
                open_slots[key]=deepcopy(dict(atom))

        seen=set()
        discovered=[]
        unresolved=[]
        working=deepcopy(base_problem)
        working_docs={
            str(row["document_id"]):row
            for row in working.get("source_documents") or []
            if isinstance(row,Mapping)
        }

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
                raise ValueError("DISCOVERY_REQUEST_DUPLICATE:"+":".join(key))
            seen.add(key)
            if key not in open_slots:
                raise ValueError(
                    "DISCOVERY_REQUEST_NOT_BOUND_TO_OPEN_FIELD_ATOM:"
                    +":".join(key)
                )
            doc=docs.get(did)
            if doc is None:
                raise ValueError("DISCOVERY_DOCUMENT_NOT_FOUND:"+did)

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
            status=str(found.get("status") or "")
            if status.startswith("FAIL_CLOSED"):
                return {
                    "schema":SCHEMA,
                    "status":"FAIL_CLOSED__DISCOVERY_CONFLICT_OR_INVALID",
                    "pass":False,
                    "case_id":case_id,
                    "failed_request_key":list(key),
                    "discovery_result":found,
                    "search_authority":False,
                    "semantic_truth_authority":False,
                    "execution_authority":False,
                    "acceptance_authority":False,
                    "terminal_authority":False,
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
                raise ValueError("DISCOVERY_PASS_WITHOUT_CLAIM:"+":".join(key))
            row=working_docs.get(did)
            if row is None:
                raise ValueError("WORKING_DOCUMENT_NOT_FOUND:"+did)
            claims=row.get("claims")
            if not isinstance(claims,list):
                raise ValueError("WORKING_CLAIMS_NOT_LIST:"+did)
            claims.append(deepcopy(dict(claim)))
            discovered.append({
                "document_id":did,
                "effect_id":eid,
                "field":field,
                "value":deepcopy(found.get("value")),
                "claim":deepcopy(dict(claim)),
                "field_receipt":deepcopy(found.get("field_receipt")),
                "proved_candidate_count":found.get("proved_candidate_count"),
            })

        final_result=lattice.evaluate(working)
        if final_result.get("status")=="FAIL_CLOSED":
            return {
                "schema":SCHEMA,
                "status":"FAIL_CLOSED__POST_DISCOVERY_LATTICE",
                "pass":False,
                "case_id":case_id,
                "discovered_claims":discovered,
                "unresolved_discovery_requests":unresolved,
                "lattice_result":final_result,
                "search_authority":False,
                "semantic_truth_authority":False,
                "execution_authority":False,
                "acceptance_authority":False,
                "terminal_authority":False,
            }
        final_checked=lattice_verify.verify(working,final_result)
        if final_checked.get("verified") is not True:
            raise ValueError(
                "POST_DISCOVERY_LATTICE_VERIFY_FAILED:"
                +",".join(final_checked.get("errors") or [])
            )

        common={
            "schema":SCHEMA,
            "case_id":case_id,
            "base_lattice_status":base_result.get("status"),
            "base_open_field_atom_count":len(open_slots),
            "discovery_request_count":len(requests),
            "discovered_claim_count":len(discovered),
            "discovered_claims":discovered,
            "unresolved_discovery_requests":unresolved,
            "post_discovery_lattice_result":final_result,
            "post_discovery_lattice_verification":final_checked,
            "search_authority":False,
            "semantic_truth_authority":False,
            "execution_authority":False,
            "acceptance_authority":False,
            "terminal_authority":False,
        }

        if final_result.get("pass") is True:
            return {
                **common,
                "status":"PASS__DISCOVERED_AUTHENTICATED_PROOFS_CLOSE_LATTICE",
                "pass":True,
                "effective_value":deepcopy(final_result.get("effective_value")),
                "world_count":final_result.get("world_count"),
                "query_relative_effect_semantics_finite":True,
            }

        return {
            **common,
            "status":"OPEN__DISCOVERY_EXHAUSTED_WITH_SEMANTIC_TOP_REMAINING",
            "pass":False,
            "open_lattice_atoms":deepcopy(
                final_result.get("open_lattice_atoms") or []
            ),
            "next_proof_obligations":deepcopy(
                final_result.get("next_proof_obligations") or []
            ),
            "possible_outcomes":deepcopy(
                final_result.get("possible_outcomes") or []
            ),
            "minimum_discriminator_slots":deepcopy(
                final_result.get("minimum_discriminator_slots") or []
            ),
            "world_count":final_result.get("world_count"),
            "query_relative_effect_semantics_finite":final_result.get(
                "query_relative_effect_semantics_finite"
            ),
            "boundary":(
                "DISCOVERY_IS_COMPLETE_ONLY_RELATIVE_TO_SUPPLIED_FINITE_CANDIDATE_"
                "UNIVERSES__UNRESOLVED_OR_UNREQUESTED_TOP_REMAINS_OPEN"
            ),
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "search_authority":False,
            "semantic_truth_authority":False,
            "execution_authority":False,
            "acceptance_authority":False,
            "terminal_authority":False,
        }
