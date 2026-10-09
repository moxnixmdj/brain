"""Independent verifier for query-relative document-effect semantic lattice V1."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v8 import verify_proof
from canonical.runtime.certified_effect_target_scope_v1 import parse_effect_target_scope
from canonical.runtime.certified_effect_id_inventory_v1 import parse_effect_id_inventories
from canonical.runtime.certified_document_effect_relation_v1 import parse_effect_relations
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_VERIFY_V1"
PROBLEM_SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V1"
MAX_DOCUMENTS=32
MAX_CLAIMS_PER_DOCUMENT=256


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _docs(rows:Any)->list[dict[str,Any]]:
    if (
        not isinstance(rows,Sequence)
        or isinstance(rows,(str,bytes))
        or not rows
        or len(rows)>MAX_DOCUMENTS
    ):
        raise ValueError("SOURCE_DOCUMENTS_INVALID")
    out=[]; dids=set(); sids=set()
    for row in rows:
        if not isinstance(row,Mapping) or set(row)!={"document_id","source_id","source_text","claims"}:
            raise ValueError("SOURCE_DOCUMENT_FIELDS_INVALID")
        did=_token(row.get("document_id"),"DOCUMENT_ID")
        sid=_token(row.get("source_id"),"SOURCE_ID")
        text=row.get("source_text"); claims=row.get("claims")
        if not isinstance(text,str) or not text:
            raise ValueError("SOURCE_TEXT_INVALID")
        if (
            not isinstance(claims,Sequence)
            or isinstance(claims,(str,bytes))
            or len(claims)>MAX_CLAIMS_PER_DOCUMENT
        ):
            raise ValueError("CLAIMS_INVALID")
        if did in dids or sid in sids:
            raise ValueError("DOCUMENT_OR_SOURCE_ID_DUPLICATE")
        dids.add(did); sids.add(sid)
        out.append({
            "document_id":did,"source_id":sid,
            "source_text":text,"claims":deepcopy(list(claims)),
        })
    return sorted(out,key=lambda x:x["document_id"])


def _query(row:Any)->dict[str,Any]:
    if not isinstance(row,Mapping) or set(row)!={"target_id","as_of","context"}:
        raise ValueError("QUERY_INVALID")
    target=_token(row.get("target_id"),"QUERY_TARGET_ID")
    as_of=_token(row.get("as_of"),"QUERY_AS_OF")
    context=row.get("context")
    if not isinstance(context,Mapping):
        raise ValueError("QUERY_CONTEXT_INVALID")
    return {"target_id":target,"as_of":as_of,"context":deepcopy(dict(context))}


def _dedupe(rows,keyfn):
    out={}
    for row in rows:
        out[keyfn(row)]=deepcopy(dict(row))
    return [out[k] for k in sorted(out,key=lambda x:str(x))]


def _independent_missing_source_claims(doc:Mapping[str,Any])->list[dict[str,Any]]:
    """Reconstruct only omitted V7/V8 source-explicit claim slots.

    This intentionally does not import the producer-side autofill module.
    Existing claims own their semantic slot even when malformed or wrong, so this
    verifier never repairs contradictory caller evidence.
    """
    claims=list(doc["claims"])
    existing_ids={
        str(row.get("claim_id"))
        for row in claims
        if isinstance(row,Mapping) and isinstance(row.get("claim_id"),str)
    }
    scope_present=False
    inventory_targets=set()
    relation_ids=set()
    block_inventory=False
    block_relation=False
    for row in claims:
        if not isinstance(row,Mapping):
            continue
        kind=row.get("kind")
        if kind=="CERTIFIED_EFFECT_TARGET_SCOPE":
            scope_present=True
        elif kind=="CERTIFIED_EFFECT_ID_INVENTORY":
            target=row.get("target_id")
            if isinstance(target,str) and target.strip():
                inventory_targets.add(target.strip())
            else:
                block_inventory=True
        elif kind=="CERTIFIED_DOCUMENT_EFFECT_RELATION":
            effect=row.get("effect")
            eid=effect.get("effect_id") if isinstance(effect,Mapping) else None
            if isinstance(eid,str) and eid.strip():
                relation_ids.add(eid.strip())
            else:
                block_relation=True

    out=[]
    counter=0
    def fresh(kind:str)->str:
        nonlocal counter
        while True:
            counter+=1
            cid=f"VERIFY_SOURCE_AUTOFILL::{kind}::{counter}"
            if cid not in existing_ids:
                existing_ids.add(cid)
                return cid

    scope=parse_effect_target_scope(doc["source_text"],source=doc["source_id"])
    if not scope_present and scope.get("status")=="PARSED":
        out.append({
            "claim_id":fresh("scope"),
            "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
            "target_ids":list(scope["parse"]["target_ids"]),
        })

    inventories=parse_effect_id_inventories(
        doc["source_text"],source=doc["source_id"]
    )
    if not block_inventory and inventories.get("status")=="PARSED":
        for parsed in inventories.get("inventories") or []:
            target=str(parsed.get("target_id") or "")
            if target and target not in inventory_targets:
                out.append({
                    "claim_id":fresh("inventory"),
                    "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                    "target_id":target,
                    "effect_ids":list(parsed.get("effect_ids") or []),
                })

    relations=parse_effect_relations(doc["source_text"],source=doc["source_id"])
    if not block_relation and relations.get("status")=="PARSED":
        for parsed in relations.get("relations") or []:
            effect=parsed.get("effect")
            if not isinstance(effect,Mapping):
                continue
            eid=str(effect.get("effect_id") or "")
            if not eid or eid in relation_ids:
                continue
            out.append({
                "claim_id":fresh("relation"),
                "kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION",
                "effect":{
                    k:v for k,v in effect.items() if k!="source_locator"
                },
            })

    if len(claims)+len(out)>MAX_CLAIMS_PER_DOCUMENT:
        raise ValueError("COMBINED_CLAIM_COUNT_EXCEEDS_BOUND")
    return out


def _recompute(problem:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(problem,Mapping) or problem.get("schema")!=PROBLEM_SCHEMA:
        raise ValueError("PROBLEM_SCHEMA_INVALID")
    if set(problem)!={"schema","case_id","source_documents","query"}:
        raise ValueError("PROBLEM_FIELDS_INVALID")
    case_id=_token(problem.get("case_id"),"CASE_ID")
    docs=_docs(problem.get("source_documents"))
    query=_query(problem.get("query"))
    target=query["target_id"]

    states=[]; open_atoms=[]; exact_by_doc={}

    for doc in docs:
        synthesized=_independent_missing_source_claims(doc)
        proof=verify_proof(
            doc["source_text"],
            source_id=doc["source_id"],
            claims=list(doc["claims"])+synthesized,
        )
        if proof.get("status")=="FAIL_CLOSED":
            raise ValueError("SOURCE_PROOF_FAIL_CLOSED:"+doc["document_id"])
        accepted=[
            x for x in (proof.get("accepted_claims") or [])
            if isinstance(x,Mapping)
        ]
        scopes=_dedupe(
            [x for x in accepted if x.get("kind")=="CERTIFIED_EFFECT_TARGET_SCOPE"],
            lambda x:tuple(x.get("target_ids") or []),
        )
        inventories=_dedupe(
            [x for x in accepted if x.get("kind")=="CERTIFIED_EFFECT_ID_INVENTORY"],
            lambda x:(x.get("target_id"),tuple(x.get("effect_ids") or [])),
        )
        relations=_dedupe(
            [x for x in accepted if x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_RELATION"],
            lambda x:x.get("effect",{}).get("effect_id"),
        )
        if len(scopes)>1:
            raise ValueError("MULTIPLE_SCOPE_PROOFS")
        inv_by_target={}
        for row in inventories:
            t=str(row.get("target_id") or "")
            if t in inv_by_target and inv_by_target[t]!=row:
                raise ValueError("MULTIPLE_INVENTORIES")
            inv_by_target[t]=row
        rel_by_id={}
        for row in relations:
            effect=row.get("effect")
            if not isinstance(effect,Mapping):
                raise ValueError("RELATION_EFFECT_INVALID")
            eid=_token(effect.get("effect_id"),"EFFECT_ID")
            if eid in rel_by_id and rel_by_id[eid]!=row:
                raise ValueError("MULTIPLE_RELATIONS")
            rel_by_id[eid]=row

        scope=None
        if scopes:
            scope=sorted(str(x) for x in scopes[0].get("target_ids") or [])
        for eid,row in rel_by_id.items():
            effect=row["effect"]
            if scope is not None and effect["target_id"] not in scope:
                raise ValueError("RELATION_TARGET_OUTSIDE_SCOPE")
            inv=inv_by_target.get(effect["target_id"])
            if inv is not None and eid not in set(inv.get("effect_ids") or []):
                raise ValueError("RELATION_ID_OUTSIDE_INVENTORY")

        state={
            "document_id":doc["document_id"],
            "source_id":doc["source_id"],
            "target_scope":{"kind":"FINITE","values":scope} if scope is not None else {"kind":"TOP"},
            "query_effect_id_inventory":{"kind":"TOP"},
            "relation_states":{},
            "query_status":None,
            "provided_claim_count":len(doc["claims"]),
            "synthesized_claim_count":len(synthesized),
            "accepted_claim_count":len(accepted),
            "rejected_claim_count":len(proof.get("rejected_claims") or []),
        }

        if scope is not None and target not in scope:
            state["query_status"]="PROVED_QUERY_IRRELEVANT"
            states.append(state)
            continue

        inv=inv_by_target.get(target)
        if inv is None:
            state["query_status"]="OPEN__EFFECT_ID_INVENTORY_TOP"
            open_atoms.append({
                "document_id":doc["document_id"],
                "dimension":"EFFECT_ID_INVENTORY",
                "target_id":target,
                "state":"TOP",
                "proof_obligation":{
                    "kind":"PROVE_EFFECT_ID_INVENTORY_OR_QUERY_TARGET_EXCLUSION",
                    "document_id":doc["document_id"],
                    "source_id":doc["source_id"],
                    "target_id":target,
                },
            })
            states.append(state)
            continue

        ids=sorted(str(x) for x in inv.get("effect_ids") or [])
        state["query_effect_id_inventory"]={"kind":"FINITE","values":ids}
        extra=sorted(
            eid for eid,row in rel_by_id.items()
            if row["effect"]["target_id"]==target and eid not in set(ids)
        )
        if extra:
            raise ValueError("QUERY_RELATION_OUTSIDE_INVENTORY")

        exact=[]; missing=[]
        for eid in ids:
            row=rel_by_id.get(eid)
            if row is None:
                state["relation_states"][eid]={"kind":"TOP"}
                missing.append(eid)
                open_atoms.append({
                    "document_id":doc["document_id"],
                    "dimension":"DOCUMENT_EFFECT_RELATION",
                    "effect_id":eid,
                    "target_id":target,
                    "state":"TOP",
                    "proof_obligation":{
                        "kind":"PROVE_COMPLETE_DOCUMENT_EFFECT_RELATION",
                        "document_id":doc["document_id"],
                        "source_id":doc["source_id"],
                        "effect_id":eid,
                        "target_id":target,
                    },
                })
                continue
            effect=deepcopy(dict(row["effect"]))
            if effect["target_id"]!=target:
                raise ValueError("INVENTORY_RELATION_TARGET_MISMATCH")
            state["relation_states"][eid]={"kind":"EXACT","effect":effect}
            exact.append(effect)
        if missing:
            state["query_status"]="OPEN__RELATION_TOP"
        else:
            state["query_status"]="EXACT_QUERY_EFFECT_SET"
            exact_by_doc[doc["document_id"]]=exact
        states.append(state)

    if open_atoms:
        return {
            "status":"OPEN__QUERY_RELEVANT_EFFECT_SEMANTIC_TOP_REMAINS",
            "pass":False,
            "lattice_documents":states,
            "open_lattice_atoms":open_atoms,
            "next_proof_obligations":[deepcopy(x["proof_obligation"]) for x in open_atoms],
            "query_relative_effect_semantics_finite":False,
        }

    if not any(exact_by_doc.values()):
        return {
            "status":"OPEN__NO_QUERY_EFFECT_RELATION_PROVED",
            "pass":False,
            "lattice_documents":states,
            "open_lattice_atoms":[],
            "next_proof_obligations":[],
            "query_relative_effect_semantics_finite":True,
        }

    ws_docs=[]
    for did in sorted(exact_by_doc):
        slots=[]
        for effect in sorted(exact_by_doc[did],key=lambda x:x["effect_id"]):
            eid=effect["effect_id"]
            slots.append({
                "slot_id":did+"::"+eid,
                "hypothesis_set_complete":True,
                "hypotheses":[{
                    "hypothesis_id":did+"::"+eid+"::exact",
                    "effect":effect,
                }],
            })
        if slots:
            ws_docs.append({"document_id":did,"effect_slots":slots})
    wsp={
        "schema":worldset.SCHEMA,
        "case_id":case_id,
        "hypothesis_set_complete":True,
        "compatibility_constraints_complete":True,
        "incompatible_hypothesis_sets":[],
        "documents":ws_docs,
        "query":query,
    }
    finite=worldset.evaluate(wsp)
    checked=worldset_verify.verify(wsp,finite)
    if checked.get("verified") is not True:
        raise ValueError("WORLDSET_VERIFY_FAILED")

    if finite.get("pass") is not True:
        return {
            "status":"OPEN__SEMANTIC_LATTICE_FINITE__EFFECT_COMPOSITION_NOT_CLOSED",
            "pass":False,
            "lattice_documents":states,
            "open_lattice_atoms":[],
            "query_relative_effect_semantics_finite":True,
            "possible_outcomes":deepcopy(finite.get("possible_outcomes") or []),
            "minimum_discriminator_slots":deepcopy(
                finite.get("minimum_discriminator_slots") or []
            ),
            "world_count":finite.get("world_count"),
            "next_proof_obligations":[],
        }

    return {
        "status":"PASS__SEMANTIC_LATTICE_REFINED_TO_VERIFIED_EFFECT_VALUE",
        "pass":True,
        "lattice_documents":states,
        "open_lattice_atoms":[],
        "query_relative_effect_semantics_finite":True,
        "effective_value":deepcopy(finite.get("effective_value")),
        "world_count":finite.get("world_count"),
        "next_proof_obligations":[],
    }


def verify(problem:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    try:
        expected=_recompute(problem)
        if not isinstance(result,Mapping):
            raise ValueError("RESULT_NOT_OBJECT")
        keys=[
            "status","pass","lattice_documents","open_lattice_atoms",
            "next_proof_obligations","query_relative_effect_semantics_finite",
        ]
        if expected.get("pass") is True:
            keys+=["effective_value","world_count"]
        elif expected.get("query_relative_effect_semantics_finite") is True:
            keys+=["possible_outcomes","minimum_discriminator_slots","world_count"]
        for key in keys:
            if result.get(key)!=expected.get(key):
                errors.append("MISMATCH:"+key)
        if result.get("semantic_truth_authority") is not False:
            errors.append("SEMANTIC_TRUTH_AUTHORITY_CLAIMED")
        if result.get("terminal_authority") is not False:
            errors.append("TERMINAL_AUTHORITY_CLAIMED")
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_SEMANTIC_LATTICE_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "boundary":"INDEPENDENT_RECOMPUTATION_OF_V8_SOURCE_PROOF_REFINEMENT_AND_FINITE_WORLDSET_COMPILATION",
    }
