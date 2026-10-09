"""Query-relative document-effect semantic lattice V1.

This module replaces trusted "hypothesis_set_complete" assertions with monotone
source-proof refinement.

For each source document and query target:
  effect-ID inventory starts at TOP;
  each effect relation starts at TOP;
  accepted source-aligned V7/V8 proofs may only refine TOP to finite/exact values.

A target-scope proof may discharge a document entirely when it explicitly
excludes the query target. An effect-ID inventory proves the finite set of
possible effect IDs for the query target. Every inventoried ID then requires an
exact V8 document-effect relation proof before the lattice can compile into the
finite correlated world-set engine.

Rejected or absent claims never narrow the lattice. They simply leave TOP.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v8 import verify_proof
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V1"
MAX_DOCUMENTS=32
MAX_CLAIMS_PER_DOCUMENT=256


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _source_documents(rows:Any)->list[dict[str,Any]]:
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
        if did in dids:
            raise ValueError("DOCUMENT_ID_DUPLICATE:"+did)
        if sid in sids:
            raise ValueError("SOURCE_ID_DUPLICATE:"+sid)
        dids.add(did); sids.add(sid)
        out.append({
            "document_id":did,
            "source_id":sid,
            "source_text":text,
            "claims":deepcopy(list(claims)),
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


def _unique_rows(rows:Sequence[Mapping[str,Any]],key_fn):
    out={}
    for row in rows:
        key=key_fn(row)
        out[key]=deepcopy(dict(row))
    return [out[k] for k in sorted(out,key=lambda x:str(x))]


def evaluate(problem:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(problem,Mapping) or problem.get("schema")!=SCHEMA:
            raise ValueError("PROBLEM_SCHEMA_INVALID")
        if set(problem)!={"schema","case_id","source_documents","query"}:
            raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")
        case_id=_token(problem.get("case_id"),"CASE_ID")
        documents=_source_documents(problem.get("source_documents"))
        query=_query(problem.get("query"))
        target=query["target_id"]

        lattice_docs=[]
        open_atoms=[]
        exact_effects_by_doc={}
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
            scopes=_unique_rows(
                [x for x in accepted if x.get("kind")=="CERTIFIED_EFFECT_TARGET_SCOPE"],
                lambda x: tuple(x.get("target_ids") or []),
            )
            inventories=_unique_rows(
                [x for x in accepted if x.get("kind")=="CERTIFIED_EFFECT_ID_INVENTORY"],
                lambda x: (x.get("target_id"),tuple(x.get("effect_ids") or [])),
            )
            relations=_unique_rows(
                [x for x in accepted if x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_RELATION"],
                lambda x: x.get("effect",{}).get("effect_id"),
            )

            if len(scopes)>1:
                raise ValueError("MULTIPLE_DISTINCT_TARGET_SCOPE_PROOFS:"+doc["document_id"])
            inventory_by_target={}
            for row in inventories:
                t=str(row.get("target_id") or "")
                if t in inventory_by_target and inventory_by_target[t]!=row:
                    raise ValueError("MULTIPLE_DISTINCT_INVENTORIES:"+doc["document_id"]+":"+t)
                inventory_by_target[t]=row
            relation_by_id={}
            for row in relations:
                effect=row.get("effect")
                if not isinstance(effect,Mapping):
                    raise ValueError("ACCEPTED_RELATION_EFFECT_INVALID:"+doc["document_id"])
                eid=_token(effect.get("effect_id"),"RELATION_EFFECT_ID")
                if eid in relation_by_id and relation_by_id[eid]!=row:
                    raise ValueError("MULTIPLE_DISTINCT_RELATIONS:"+doc["document_id"]+":"+eid)
                relation_by_id[eid]=row

            scope_targets=None
            if scopes:
                scope_targets=sorted(str(x) for x in scopes[0].get("target_ids") or [])
                refinement_count+=1

            for eid,row in relation_by_id.items():
                effect=row["effect"]
                if scope_targets is not None and effect["target_id"] not in scope_targets:
                    raise ValueError(
                        "RELATION_TARGET_OUTSIDE_PROVED_SCOPE:"
                        +doc["document_id"]+":"+eid
                    )
                inv=inventory_by_target.get(effect["target_id"])
                if inv is not None and eid not in set(inv.get("effect_ids") or []):
                    raise ValueError(
                        "RELATION_ID_OUTSIDE_PROVED_INVENTORY:"
                        +doc["document_id"]+":"+eid
                    )

            query_irrelevant=scope_targets is not None and target not in scope_targets
            doc_state={
                "document_id":doc["document_id"],
                "source_id":doc["source_id"],
                "target_scope":{
                    "kind":"FINITE",
                    "values":scope_targets,
                } if scope_targets is not None else {"kind":"TOP"},
                "query_effect_id_inventory":{"kind":"TOP"},
                "relation_states":{},
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

            inv=inventory_by_target.get(target)
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

            extra_query_relations=sorted(
                eid for eid,row in relation_by_id.items()
                if row["effect"]["target_id"]==target and eid not in set(ids)
            )
            if extra_query_relations:
                raise ValueError(
                    "QUERY_RELATION_OUTSIDE_PROVED_INVENTORY:"
                    +doc["document_id"]+":"+",".join(extra_query_relations)
                )

            exact=[]
            missing=[]
            for eid in ids:
                row=relation_by_id.get(eid)
                if row is None:
                    doc_state["relation_states"][eid]={"kind":"TOP"}
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
                    raise ValueError(
                        "INVENTORIED_EFFECT_RELATION_TARGET_MISMATCH:"
                        +doc["document_id"]+":"+eid
                    )
                doc_state["relation_states"][eid]={
                    "kind":"EXACT",
                    "effect":effect,
                }
                exact.append(effect)
                refinement_count+=1

            if missing:
                doc_state["query_status"]="OPEN__RELATION_TOP"
            else:
                doc_state["query_status"]="EXACT_QUERY_EFFECT_SET"
                exact_effects_by_doc[doc["document_id"]]=exact
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
            "lattice_invariant":"SOURCE_PROOF_ONLY_SHRINKS_TOP__ABSENT_OR_REJECTED_CLAIMS_NEVER_NARROW",
        }

        if open_atoms:
            return {
                **base,
                "status":"OPEN__QUERY_RELEVANT_EFFECT_SEMANTIC_TOP_REMAINS",
                "pass":False,
                "next_proof_obligations":[deepcopy(x["proof_obligation"]) for x in open_atoms],
                "query_relative_effect_semantics_finite":False,
            }

        if not any(exact_effects_by_doc.values()):
            return {
                **base,
                "status":"OPEN__NO_QUERY_EFFECT_RELATION_PROVED",
                "pass":False,
                "next_proof_obligations":[],
                "query_relative_effect_semantics_finite":True,
            }

        ws_docs=[]
        for did in sorted(exact_effects_by_doc):
            effects=exact_effects_by_doc[did]
            if not effects:
                continue
            slots=[]
            for effect in sorted(effects,key=lambda x:x["effect_id"]):
                eid=effect["effect_id"]
                slots.append({
                    "slot_id":did+"::"+eid,
                    "hypothesis_set_complete":True,
                    "hypotheses":[{
                        "hypothesis_id":did+"::"+eid+"::exact",
                        "effect":effect,
                    }],
                })
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
                "status":"OPEN__SEMANTIC_LATTICE_FINITE__EFFECT_COMPOSITION_NOT_CLOSED",
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
            "status":"PASS__SEMANTIC_LATTICE_REFINED_TO_VERIFIED_EFFECT_VALUE",
            "pass":True,
            "query_relative_effect_semantics_finite":True,
            "finite_worldset_result":finite,
            "finite_worldset_verification":checked,
            "effective_value":deepcopy(finite.get("effective_value")),
            "world_count":finite.get("world_count"),
            "next_proof_obligations":[],
            "boundary":"QUERY_RELATIVE_COMPLETENESS_ONLY__GLOBAL_ARBITRARY_LANGUAGE_COMPLETENESS_NOT_CLAIMED",
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
