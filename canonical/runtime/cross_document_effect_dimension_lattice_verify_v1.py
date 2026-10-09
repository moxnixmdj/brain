"""Independent verifier for cross-document effect dimension lattice V1."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v9 import verify_proof
from canonical.runtime import cross_document_effect_calculus_v1 as calculus
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_DIMENSION_LATTICE_VERIFY_V1"
PROBLEM_SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_DIMENSION_LATTICE_V1"
DIMS=("target","effect_class","value","conditions","valid_from","valid_until","supersedes")
RMAP={
    "target_id":"target","effect_class":"effect_class","value":"value",
    "conditions":"conditions","valid_from":"valid_from",
    "valid_until":"valid_until","supersedes":"supersedes",
}


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _tok(v:Any)->str:
    if not isinstance(v,str) or not v.strip(): raise ValueError("TOKEN_INVALID")
    return v.strip()


def _set(state:dict[str,Any],dim:str,value:Any,*,did:str,eid:str)->None:
    prior=state.get(dim)
    if prior is None:
        state[dim]=deepcopy(value); return
    if prior!=value:
        raise ValueError("PROVED_EFFECT_DIMENSION_CONFLICT:"+did+":"+eid+":"+dim)


def _locator(source_id:str,eid:str,state:Mapping[str,Any])->str:
    digest=sha256(_canon({"source_id":source_id,"effect_id":eid,"state":state}).encode("utf-8")).hexdigest()
    return "verify-proofset:"+source_id+":"+eid+":"+digest


def _recompute(problem:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(problem,Mapping) or problem.get("schema")!=PROBLEM_SCHEMA:
        raise ValueError("PROBLEM_SCHEMA_INVALID")
    if set(problem)!={"schema","case_id","source_documents","query"}:
        raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")
    case_id=_tok(problem.get("case_id"))
    query=problem.get("query")
    if not isinstance(query,Mapping) or set(query)!={"target_id","as_of","context"}:
        raise ValueError("QUERY_INVALID")
    target=_tok(query.get("target_id"))
    as_of=_tok(query.get("as_of"))
    context=query.get("context")
    if not isinstance(context,Mapping): raise ValueError("QUERY_CONTEXT_INVALID")
    clean_query={"target_id":target,"as_of":as_of,"context":deepcopy(dict(context))}

    docs=problem.get("source_documents")
    if not isinstance(docs,Sequence) or isinstance(docs,(str,bytes)) or not docs:
        raise ValueError("SOURCE_DOCUMENTS_INVALID")

    did_seen=set(); sid_seen=set(); open_atoms=[]; exact_by_doc={}; states=[]
    for raw_doc in docs:
        if not isinstance(raw_doc,Mapping) or set(raw_doc)!={"document_id","source_id","source_text","claims"}:
            raise ValueError("SOURCE_DOCUMENT_FIELDS_INVALID")
        did=_tok(raw_doc.get("document_id")); sid=_tok(raw_doc.get("source_id"))
        if did in did_seen or sid in sid_seen: raise ValueError("DOCUMENT_OR_SOURCE_DUPLICATE")
        did_seen.add(did); sid_seen.add(sid)
        text=raw_doc.get("source_text"); claims=raw_doc.get("claims")
        if not isinstance(text,str) or not text: raise ValueError("SOURCE_TEXT_INVALID")
        if not isinstance(claims,Sequence) or isinstance(claims,(str,bytes)):
            raise ValueError("CLAIMS_INVALID")

        proof=verify_proof(text,source_id=sid,claims=claims)
        if proof.get("status")=="FAIL_CLOSED": raise ValueError("SOURCE_PROOF_FAIL_CLOSED")
        accepted=[x for x in proof.get("accepted_claims") or [] if isinstance(x,Mapping)]

        scope_rows=[x for x in accepted if x.get("kind")=="CERTIFIED_EFFECT_TARGET_SCOPE"]
        scope_sets={tuple(x.get("target_ids") or []) for x in scope_rows}
        if len(scope_sets)>1: raise ValueError("MULTIPLE_DISTINCT_TARGET_SCOPE_PROOFS")
        scope=sorted(next(iter(scope_sets))) if scope_sets else None

        inv_rows=[x for x in accepted if x.get("kind")=="CERTIFIED_EFFECT_ID_INVENTORY" and x.get("target_id")==target]
        inv_sets={tuple(x.get("effect_ids") or []) for x in inv_rows}
        if len(inv_sets)>1: raise ValueError("MULTIPLE_DISTINCT_QUERY_INVENTORIES")
        inventory=sorted(next(iter(inv_sets))) if inv_sets else None

        rels={}
        for row in accepted:
            if row.get("kind")!="CERTIFIED_DOCUMENT_EFFECT_RELATION": continue
            eff=row.get("effect")
            if not isinstance(eff,Mapping): raise ValueError("RELATION_INVALID")
            eid=_tok(eff.get("effect_id"))
            if eid in rels and rels[eid]!=dict(eff): raise ValueError("RELATION_CONFLICT")
            rels[eid]=dict(eff)

        dims={}
        for row in accepted:
            if row.get("kind")!="CERTIFIED_DOCUMENT_EFFECT_DIMENSION": continue
            eid=_tok(row.get("effect_id")); dim=_tok(row.get("dimension"))
            key=(eid,dim); val=deepcopy(row.get("value"))
            if key in dims and dims[key]!=val: raise ValueError("DIMENSION_CONFLICT")
            dims[key]=val

        if scope is not None and target not in scope:
            states.append({"document_id":did,"query_status":"PROVED_QUERY_IRRELEVANT"})
            continue

        if inventory is None:
            obligation={
                "kind":"PROVE_EFFECT_ID_INVENTORY_OR_QUERY_TARGET_EXCLUSION",
                "document_id":did,"source_id":sid,"target_id":target,
            }
            open_atoms.append({
                "document_id":did,"dimension":"EFFECT_ID_INVENTORY",
                "target_id":target,"state":"TOP","proof_obligation":obligation,
            })
            states.append({"document_id":did,"query_status":"OPEN__EFFECT_ID_INVENTORY_TOP"})
            continue

        idset=set(inventory)
        nonquery=set()
        for eid,eff in rels.items():
            if eff.get("target_id")!=target: nonquery.add(eid)
        for (eid,dim),val in dims.items():
            if dim=="target" and val!=target: nonquery.add(eid)
        for (eid,dim) in dims:
            if eid not in idset and eid not in nonquery:
                raise ValueError("QUERY_DIMENSION_OUTSIDE_INVENTORY_WITHOUT_NONQUERY_TARGET_PROOF")
        for eid,eff in rels.items():
            if eff.get("target_id")==target and eid not in idset:
                raise ValueError("QUERY_RELATION_OUTSIDE_INVENTORY")
            if scope is not None and eff.get("target_id") not in scope:
                raise ValueError("RELATION_TARGET_OUTSIDE_SCOPE")

        exact=[]; doc_open=False
        for eid in inventory:
            state={"target":target}
            rel=rels.get(eid)
            if rel is not None:
                for field,dim in RMAP.items(): _set(state,dim,rel[field],did=did,eid=eid)
            for dim in DIMS:
                if (eid,dim) in dims: _set(state,dim,dims[(eid,dim)],did=did,eid=eid)

            missing=[dim for dim in DIMS if dim not in state]
            if missing:
                doc_open=True
                for dim in missing:
                    obligation={
                        "kind":"PROVE_DOCUMENT_EFFECT_DIMENSION",
                        "document_id":did,"source_id":sid,
                        "effect_id":eid,"target_id":target,"dimension":dim,
                    }
                    open_atoms.append({
                        "document_id":did,"effect_id":eid,"dimension":dim,
                        "target_id":target,"state":"TOP",
                        "proof_obligation":obligation,
                    })
                continue

            raw={
                "effect_id":eid,"target_id":state["target"],
                "effect_class":state["effect_class"],"value":state["value"],
                "conditions":state["conditions"],"valid_from":state["valid_from"],
                "valid_until":state["valid_until"],"supersedes":state["supersedes"],
                "source_locator":_locator(sid,eid,state),
            }
            exact.append(calculus._validate_effect(raw))
        states.append({
            "document_id":did,
            "query_status":"OPEN__EFFECT_DIMENSION_TOP" if doc_open else "EXACT_QUERY_EFFECT_SET",
        })
        if not doc_open: exact_by_doc[did]=exact

    if open_atoms:
        return {
            "status":"OPEN__QUERY_RELEVANT_EFFECT_DIMENSION_TOP_REMAINS",
            "pass":False,
            "open_lattice_atoms":open_atoms,
            "next_proof_obligations":[deepcopy(x["proof_obligation"]) for x in open_atoms],
            "query_relative_effect_semantics_finite":False,
        }
    if not any(exact_by_doc.values()):
        return {
            "status":"OPEN__NO_QUERY_EFFECT_RELATION_PROVED","pass":False,
            "open_lattice_atoms":[],"next_proof_obligations":[],
            "query_relative_effect_semantics_finite":True,
        }

    ws_docs=[]
    for did in sorted(exact_by_doc):
        slots=[]
        for eff in sorted(exact_by_doc[did],key=lambda x:x["effect_id"]):
            eid=eff["effect_id"]
            slots.append({
                "slot_id":did+"::"+eid,"hypothesis_set_complete":True,
                "hypotheses":[{"hypothesis_id":did+"::"+eid+"::exact","effect":eff}],
            })
        if slots: ws_docs.append({"document_id":did,"effect_slots":slots})
    wsp={
        "schema":worldset.SCHEMA,"case_id":case_id,
        "hypothesis_set_complete":True,
        "compatibility_constraints_complete":True,
        "incompatible_hypothesis_sets":[],
        "documents":ws_docs,"query":clean_query,
    }
    finite=worldset.evaluate(wsp)
    checked=worldset_verify.verify(wsp,finite)
    if checked.get("verified") is not True: raise ValueError("WORLDSET_VERIFY_FAILED")
    if finite.get("pass") is not True:
        return {
            "status":"OPEN__DIMENSION_LATTICE_FINITE__EFFECT_COMPOSITION_NOT_CLOSED",
            "pass":False,"open_lattice_atoms":[],
            "next_proof_obligations":[],
            "query_relative_effect_semantics_finite":True,
            "possible_outcomes":deepcopy(finite.get("possible_outcomes") or []),
            "minimum_discriminator_slots":deepcopy(finite.get("minimum_discriminator_slots") or []),
            "world_count":finite.get("world_count"),
        }
    return {
        "status":"PASS__DIMENSION_LATTICE_REFINED_TO_VERIFIED_EFFECT_VALUE",
        "pass":True,"open_lattice_atoms":[],"next_proof_obligations":[],
        "query_relative_effect_semantics_finite":True,
        "effective_value":deepcopy(finite.get("effective_value")),
        "world_count":finite.get("world_count"),
    }


def verify(problem:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    try:
        expected=_recompute(problem)
        if not isinstance(result,Mapping): raise ValueError("RESULT_NOT_OBJECT")
        keys=["status","pass","open_lattice_atoms","next_proof_obligations","query_relative_effect_semantics_finite"]
        if expected.get("pass") is True:
            keys+=["effective_value","world_count"]
        elif expected.get("query_relative_effect_semantics_finite") is True:
            if "possible_outcomes" in expected:
                keys+=["possible_outcomes","minimum_discriminator_slots","world_count"]
        for key in keys:
            if result.get(key)!=expected.get(key): errors.append("MISMATCH:"+key)
        if result.get("semantic_truth_authority") is not False: errors.append("SEMANTIC_TRUTH_AUTHORITY_CLAIMED")
        if result.get("terminal_authority") is not False: errors.append("TERMINAL_AUTHORITY_CLAIMED")
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_EFFECT_DIMENSION_LATTICE_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "boundary":"INDEPENDENT_V9_PROOF_RECOMPUTATION_DIMENSION_INTERSECTION_CROSS_FIELD_VALIDATION_AND_FINITE_WORLDSET",
    }
