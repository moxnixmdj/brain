"""Query-relative document-effect dimension lattice V1.

This is the compositional successor to the V13 whole-relation lattice.

For each inventoried query-relevant effect ID, semantic dimensions are tracked
independently:
  target, effect_class, value, conditions, valid_from, valid_until, supersedes.

The target is fixed by the certified target-scoped effect-ID inventory. Every
other dimension starts at TOP. V8 whole-relation proofs and V9 single-dimension
proofs may only refine TOP to exact values. Exact values must agree; conflict
fails closed. Missing dimensions remain explicit TOP proof obligations.

Only fully closed effects are compiled into the finite world-set engine.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v9 import verify_proof
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify
from canonical.runtime import cross_document_effect_calculus_v1 as calculus

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_DIMENSION_LATTICE_V1"
MAX_DOCUMENTS=32
MAX_CLAIMS_PER_DOCUMENT=384
DIMENSIONS=(
    "target","effect_class","value","conditions",
    "valid_from","valid_until","supersedes",
)
RELATION_TO_DIMENSION={
    "target_id":"target",
    "effect_class":"effect_class",
    "value":"value",
    "conditions":"conditions",
    "valid_from":"valid_from",
    "valid_until":"valid_until",
    "supersedes":"supersedes",
}


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


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
        raise ValueError("SOURCE_DOCUMENTS_INVALID_OR_TOO_LARGE")
    out=[]; dids=set(); sids=set()
    for row in rows:
        if not isinstance(row,Mapping) or set(row)!={"document_id","source_id","source_text","claims"}:
            raise ValueError("SOURCE_DOCUMENT_FIELD_SET_NOT_EXACT")
        did=_token(row.get("document_id"),"DOCUMENT_ID")
        sid=_token(row.get("source_id"),"SOURCE_ID")
        text=row.get("source_text")
        claims=row.get("claims")
        if not isinstance(text,str) or not text:
            raise ValueError("SOURCE_TEXT_INVALID:"+did)
        if (
            not isinstance(claims,Sequence)
            or isinstance(claims,(str,bytes))
            or len(claims)>MAX_CLAIMS_PER_DOCUMENT
        ):
            raise ValueError("CLAIMS_INVALID_OR_TOO_LARGE:"+did)
        if did in dids: raise ValueError("DOCUMENT_ID_DUPLICATE:"+did)
        if sid in sids: raise ValueError("SOURCE_ID_DUPLICATE:"+sid)
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
    _canon(context)
    return {"target_id":target,"as_of":as_of,"context":deepcopy(dict(context))}


def _dedupe(rows:Sequence[Mapping[str,Any]],keyfn)->list[dict[str,Any]]:
    out={}
    for row in rows:
        key=keyfn(row)
        clean=deepcopy(dict(row))
        if key in out and out[key]!=clean:
            raise ValueError("DISTINCT_ACCEPTED_PROOFS_SHARE_KEY:"+str(key))
        out[key]=clean
    return [out[k] for k in sorted(out,key=lambda x:str(x))]


def _set_exact(
    state:dict[str,Any],
    dim:str,
    value:Any,
    proof_ref:Mapping[str,Any],
    *,
    doc_id:str,
    effect_id:str,
)->None:
    current=state[dim]
    if current["kind"]=="TOP":
        state[dim]={
            "kind":"EXACT",
            "value":deepcopy(value),
            "proofs":[deepcopy(dict(proof_ref))],
        }
        return
    if current.get("value")!=value:
        raise ValueError(
            "PROVED_EFFECT_DIMENSION_CONFLICT:"
            +doc_id+":"+effect_id+":"+dim
        )
    current.setdefault("proofs",[]).append(deepcopy(dict(proof_ref)))


def _proofset_locator(source_id:str,effect_id:str,state:Mapping[str,Any])->str:
    refs=[]
    for dim in DIMENSIONS:
        row=state[dim]
        for proof in row.get("proofs") or []:
            refs.append({
                "dimension":dim,
                "kind":proof.get("kind"),
                "claim_id":proof.get("claim_id"),
                "source_text_sha256":proof.get("source_text_sha256"),
                "dimension_id":proof.get("dimension_id"),
                "relation_id":proof.get("relation_id"),
            })
    digest=sha256(_canon(sorted(refs,key=_canon)).encode("utf-8")).hexdigest()
    return "proofset:"+source_id+":"+effect_id+":"+digest


def evaluate(problem:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(problem,Mapping) or problem.get("schema")!=SCHEMA:
            raise ValueError("PROBLEM_SCHEMA_INVALID")
        if set(problem)!={"schema","case_id","source_documents","query"}:
            raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")
        case_id=_token(problem.get("case_id"),"CASE_ID")
        documents=_docs(problem.get("source_documents"))
        query=_query(problem.get("query"))
        target=query["target_id"]

        lattice_docs=[]
        open_atoms=[]
        exact_by_doc={}
        proof_receipts=[]
        refinement_count=0

        for doc in documents:
            proof=verify_proof(
                doc["source_text"],
                source_id=doc["source_id"],
                claims=doc["claims"],
            )
            if proof.get("status")=="FAIL_CLOSED":
                raise ValueError(
                    "SOURCE_PROOF_FAIL_CLOSED:"+doc["document_id"]+":"
                    +",".join(proof.get("errors") or [])
                )
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
            dimensions=_dedupe(
                [x for x in accepted if x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_DIMENSION"],
                lambda x:(x.get("effect_id"),x.get("dimension")),
            )

            if len(scopes)>1:
                raise ValueError("MULTIPLE_DISTINCT_TARGET_SCOPE_PROOFS:"+doc["document_id"])

            inv_by_target={}
            for row in inventories:
                t=str(row.get("target_id") or "")
                if t in inv_by_target and inv_by_target[t]!=row:
                    raise ValueError("MULTIPLE_DISTINCT_INVENTORIES:"+doc["document_id"]+":"+t)
                inv_by_target[t]=row

            relation_by_id={}
            for row in relations:
                effect=row.get("effect")
                if not isinstance(effect,Mapping):
                    raise ValueError("ACCEPTED_RELATION_EFFECT_INVALID:"+doc["document_id"])
                eid=_token(effect.get("effect_id"),"RELATION_EFFECT_ID")
                relation_by_id[eid]=row

            dim_by_key={}
            for row in dimensions:
                eid=_token(row.get("effect_id"),"DIMENSION_EFFECT_ID")
                dim=_token(row.get("dimension"),"DIMENSION_NAME")
                if dim not in DIMENSIONS:
                    raise ValueError("ACCEPTED_DIMENSION_UNSUPPORTED:"+dim)
                dim_by_key[(eid,dim)]=row

            scope_targets=None
            if scopes:
                scope_targets=sorted(str(x) for x in scopes[0].get("target_ids") or [])
                refinement_count+=1

            query_irrelevant=scope_targets is not None and target not in scope_targets
            doc_state={
                "document_id":doc["document_id"],
                "source_id":doc["source_id"],
                "target_scope":{
                    "kind":"FINITE","values":scope_targets,
                } if scope_targets is not None else {"kind":"TOP"},
                "query_effect_id_inventory":{"kind":"TOP"},
                "effect_states":{},
                "query_status":None,
                "accepted_claim_count":len(accepted),
                "rejected_claim_count":len(proof.get("rejected_claims") or []),
            }

            if query_irrelevant:
                doc_state["query_status"]="PROVED_QUERY_IRRELEVANT"
                lattice_docs.append(doc_state)
                proof_receipts.append({
                    "document_id":doc["document_id"],
                    "source_id":doc["source_id"],
                    "proof_status":proof.get("status"),
                    "accepted_claims":deepcopy(accepted),
                    "rejected_claims":deepcopy(proof.get("rejected_claims") or []),
                })
                continue

            inv=inv_by_target.get(target)
            if inv is None:
                doc_state["query_status"]="OPEN__EFFECT_ID_INVENTORY_TOP"
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
                lattice_docs.append(doc_state)
                proof_receipts.append({
                    "document_id":doc["document_id"],
                    "source_id":doc["source_id"],
                    "proof_status":proof.get("status"),
                    "accepted_claims":deepcopy(accepted),
                    "rejected_claims":deepcopy(proof.get("rejected_claims") or []),
                })
                continue

            ids=sorted(str(x) for x in inv.get("effect_ids") or [])
            doc_state["query_effect_id_inventory"]={"kind":"FINITE","values":ids}
            refinement_count+=1
            idset=set(ids)

            for eid,row in relation_by_id.items():
                effect=row["effect"]
                if effect["target_id"]==target and eid not in idset:
                    raise ValueError(
                        "QUERY_RELATION_OUTSIDE_PROVED_INVENTORY:"
                        +doc["document_id"]+":"+eid
                    )
                if scope_targets is not None and effect["target_id"] not in scope_targets:
                    raise ValueError(
                        "RELATION_TARGET_OUTSIDE_PROVED_SCOPE:"
                        +doc["document_id"]+":"+eid
                    )
            nonquery_eids=set()
            for eid,row in relation_by_id.items():
                if row["effect"]["target_id"]!=target:
                    nonquery_eids.add(eid)
            for (eid,dim),row in dim_by_key.items():
                if dim=="target" and row.get("value")!=target:
                    nonquery_eids.add(eid)

            for (eid,dim),row in dim_by_key.items():
                if eid in idset or eid in nonquery_eids:
                    continue
                raise ValueError(
                    "QUERY_DIMENSION_OUTSIDE_PROVED_INVENTORY_WITHOUT_NONQUERY_TARGET_PROOF:"
                    +doc["document_id"]+":"+eid+":"+dim
                )

            exact=[]
            doc_open=False
            for eid in ids:
                state={dim:{"kind":"TOP"} for dim in DIMENSIONS}
                inventory_ref={
                    "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                    "claim_id":inv.get("claim_id"),
                    "source_text_sha256":inv.get("source_text_sha256"),
                }
                _set_exact(
                    state,"target",target,inventory_ref,
                    doc_id=doc["document_id"],effect_id=eid,
                )
                refinement_count+=1

                rel=relation_by_id.get(eid)
                if rel is not None:
                    effect=rel["effect"]
                    for field,dim in RELATION_TO_DIMENSION.items():
                        _set_exact(
                            state,dim,effect[field],{
                                "kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION",
                                "claim_id":rel.get("claim_id"),
                                "relation_id":rel.get("relation_id"),
                                "source_text_sha256":rel.get("source_text_sha256"),
                            },
                            doc_id=doc["document_id"],effect_id=eid,
                        )
                        refinement_count+=1

                for dim in DIMENSIONS:
                    row=dim_by_key.get((eid,dim))
                    if row is None:
                        continue
                    _set_exact(
                        state,dim,row.get("value"),{
                            "kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
                            "claim_id":row.get("claim_id"),
                            "dimension_id":row.get("dimension_id"),
                            "source_text_sha256":row.get("source_text_sha256"),
                        },
                        doc_id=doc["document_id"],effect_id=eid,
                    )
                    refinement_count+=1

                missing=[]
                for dim in DIMENSIONS:
                    if state[dim]["kind"]=="TOP":
                        missing.append(dim)
                        open_atoms.append({
                            "document_id":doc["document_id"],
                            "effect_id":eid,
                            "dimension":dim,
                            "target_id":target,
                            "state":"TOP",
                            "proof_obligation":{
                                "kind":"PROVE_DOCUMENT_EFFECT_DIMENSION",
                                "document_id":doc["document_id"],
                                "source_id":doc["source_id"],
                                "effect_id":eid,
                                "target_id":target,
                                "dimension":dim,
                            },
                        })

                effect_state={
                    "effect_id":eid,
                    "dimensions":state,
                    "status":"OPEN__DIMENSION_TOP" if missing else "EXACT",
                }
                if missing:
                    doc_open=True
                    doc_state["effect_states"][eid]=effect_state
                    continue

                raw_effect={
                    "effect_id":eid,
                    "target_id":state["target"]["value"],
                    "effect_class":state["effect_class"]["value"],
                    "value":deepcopy(state["value"]["value"]),
                    "conditions":deepcopy(state["conditions"]["value"]),
                    "valid_from":state["valid_from"]["value"],
                    "valid_until":state["valid_until"]["value"],
                    "supersedes":deepcopy(state["supersedes"]["value"]),
                    "source_locator":_proofset_locator(doc["source_id"],eid,state),
                }
                try:
                    validated=calculus._validate_effect(raw_effect)
                except Exception as exc:
                    raise ValueError(
                        "CLOSED_EFFECT_DIMENSIONS_INVALID:"
                        +doc["document_id"]+":"+eid+":"
                        +type(exc).__name__+":"+str(exc)
                    ) from exc
                effect_state["compiled_effect"]=validated
                doc_state["effect_states"][eid]=effect_state
                exact.append(validated)

            if doc_open:
                doc_state["query_status"]="OPEN__EFFECT_DIMENSION_TOP"
            else:
                doc_state["query_status"]="EXACT_QUERY_EFFECT_SET"
                exact_by_doc[doc["document_id"]]=exact

            lattice_docs.append(doc_state)
            proof_receipts.append({
                "document_id":doc["document_id"],
                "source_id":doc["source_id"],
                "proof_status":proof.get("status"),
                "accepted_claims":deepcopy(accepted),
                "rejected_claims":deepcopy(proof.get("rejected_claims") or []),
            })

        base={
            "schema":SCHEMA,
            "case_id":case_id,
            "query":query,
            "lattice_documents":lattice_docs,
            "proof_receipts":proof_receipts,
            "refinement_count":refinement_count,
            "open_lattice_atoms":open_atoms,
            "semantic_truth_authority":False,
            "terminal_authority":False,
            "lattice_invariant":"EACH_EFFECT_DIMENSION_STARTS_TOP_AND_ONLY_ACCEPTED_SOURCE_PROOFS_CAN_REFINE_IT",
        }

        if open_atoms:
            return {
                **base,
                "status":"OPEN__QUERY_RELEVANT_EFFECT_DIMENSION_TOP_REMAINS",
                "pass":False,
                "next_proof_obligations":[
                    deepcopy(x["proof_obligation"]) for x in open_atoms
                ],
                "query_relative_effect_semantics_finite":False,
            }

        if not any(exact_by_doc.values()):
            return {
                **base,
                "status":"OPEN__NO_QUERY_EFFECT_RELATION_PROVED",
                "pass":False,
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

        ws_problem={
            "schema":worldset.SCHEMA,
            "case_id":case_id,
            "hypothesis_set_complete":True,
            "compatibility_constraints_complete":True,
            "incompatible_hypothesis_sets":[],
            "documents":ws_docs,
            "query":query,
        }
        finite=worldset.evaluate(ws_problem)
        checked=worldset_verify.verify(ws_problem,finite)
        if checked.get("verified") is not True:
            raise ValueError(
                "FINITE_WORLDSET_VERIFY_FAILED:"
                +",".join(checked.get("errors") or [])
            )

        if finite.get("pass") is not True:
            return {
                **base,
                "status":"OPEN__DIMENSION_LATTICE_FINITE__EFFECT_COMPOSITION_NOT_CLOSED",
                "pass":False,
                "query_relative_effect_semantics_finite":True,
                "finite_worldset_result":finite,
                "finite_worldset_verification":checked,
                "possible_outcomes":deepcopy(finite.get("possible_outcomes") or []),
                "minimum_discriminator_slots":deepcopy(
                    finite.get("minimum_discriminator_slots") or []
                ),
                "world_count":finite.get("world_count"),
                "next_proof_obligations":[],
            }

        return {
            **base,
            "status":"PASS__DIMENSION_LATTICE_REFINED_TO_VERIFIED_EFFECT_VALUE",
            "pass":True,
            "query_relative_effect_semantics_finite":True,
            "finite_worldset_result":finite,
            "finite_worldset_verification":checked,
            "effective_value":deepcopy(finite.get("effective_value")),
            "world_count":finite.get("world_count"),
            "next_proof_obligations":[],
            "boundary":"QUERY_RELATIVE_PARTIAL_SEMANTIC_PROOFS_COMPOSE;UNPROVED_DIMENSIONS_REMAIN_TOP",
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "semantic_truth_authority":False,
            "terminal_authority":False,
        }
