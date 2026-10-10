"""Query-relative document-effect semantic lattice V9.

V7 preserves V5 and routes semantic-edge field proofs through the Brain-owned relation registry via
source_aligned_semantic_proof_v12. Edge-derived fields refine TOP only when the
scoped entailment DAG is independently recomputed by either an explicit caller
verifier or the Brain-owned supported-proof registry. Unsupported evidence
without a verifier remains rejected/TOP.

For every effect ID in a source-proved query-target inventory:
- target_id is anchored by that inventory;
- effect_class, value, conditions, valid_from, valid_until, and supersedes are
  independent lattice coordinates initialized to TOP;
- a V8 complete relation may close every coordinate at once;
- otherwise V9 field proofs close coordinates individually;
- absent/rejected claims never narrow TOP;
- cross-field validity is checked only after all required coordinates are exact.

Only then is a typed effect admitted to the already-verified finite world-set
composer.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v16 import verify_proof
from canonical.runtime.source_semantic_claim_autofill_v5 import (
    synthesize_missing_claims,
)
from canonical.runtime import cross_document_effect_calculus_v1 as calculus
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V9"
MAX_DOCUMENTS=32
MAX_CLAIMS_PER_DOCUMENT=256
REQUIRED_FIELDS=(
    "effect_class",
    "value",
    "conditions",
    "valid_from",
    "valid_until",
    "supersedes",
)
ALL_FIELDS=("target_id",)+REQUIRED_FIELDS


def _canon(value:Any)->str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
        allow_nan=False,
    )


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
    _canon(context)
    return {
        "target_id":target,
        "as_of":as_of,
        "context":deepcopy(dict(context)),
    }


def _unique_rows(rows:Sequence[Mapping[str,Any]],key_fn):
    out={}
    for row in rows:
        key=key_fn(row)
        if key in out and out[key]!=dict(row):
            raise ValueError("DISTINCT_PROOFS_FOR_SAME_SEMANTIC_SLOT:"+str(key))
        out[key]=deepcopy(dict(row))
    return [out[k] for k in sorted(out,key=lambda x:str(x))]


def _field_locator(
    source_id:str,
    effect_id:str,
    inventory_row:Mapping[str,Any],
    field_rows:Mapping[str,Mapping[str,Any]],
)->str:
    evidence={
        "source_id":source_id,
        "effect_id":effect_id,
        "inventory_claim_id":inventory_row.get("claim_id"),
        "fields":[
            {
                "field":field,
                "field_id":field_rows[field].get("field_id"),
                "source_span_bytes":field_rows[field].get("source_span_bytes"),
                "source_text_sha256":field_rows[field].get("source_text_sha256"),
            }
            for field in sorted(field_rows)
            if field in REQUIRED_FIELDS
        ],
    }
    digest=sha256(_canon(evidence).encode("utf-8")).hexdigest()[:24]
    return source_id+":fieldproof:"+digest


def evaluate(
    problem:Mapping[str,Any],
    *,
    relation_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None,
)->dict[str,Any]:
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
        proof_receipts=[]
        open_atoms=[]
        exact_effects_by_doc={}
        refinement_count=0

        for doc in documents:
            autofill=synthesize_missing_claims(
                doc["source_text"],
                source_id=doc["source_id"],
                existing_claims=doc["claims"],
            )
            if autofill.get("pass") is not True:
                raise ValueError(
                    "SOURCE_EXPLICIT_AUTOFILL_FAIL_CLOSED:"
                    +doc["document_id"]+":"
                    +str(autofill.get("reason") or "UNKNOWN")
                )
            proof_claims=list(doc["claims"])+list(
                autofill.get("synthesized_claims") or []
            )
            proof=verify_proof(
                doc["source_text"],
                source_id=doc["source_id"],
                claims=proof_claims,
                relation_verifier=relation_verifier,
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
                lambda x:tuple(x.get("target_ids") or []),
            )
            inventories=_unique_rows(
                [x for x in accepted if x.get("kind")=="CERTIFIED_EFFECT_ID_INVENTORY"],
                lambda x:(x.get("target_id"),tuple(x.get("effect_ids") or [])),
            )
            relations=_unique_rows(
                [x for x in accepted if x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_RELATION"],
                lambda x:x.get("effect",{}).get("effect_id"),
            )
            fields=_unique_rows(
                [x for x in accepted if x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_FIELD"],
                lambda x:(x.get("effect_id"),x.get("field")),
            )

            if len(scopes)>1:
                raise ValueError(
                    "MULTIPLE_DISTINCT_TARGET_SCOPE_PROOFS:"+doc["document_id"]
                )

            inventory_by_target={}
            for row in inventories:
                t=str(row.get("target_id") or "")
                if t in inventory_by_target and inventory_by_target[t]!=row:
                    raise ValueError(
                        "MULTIPLE_DISTINCT_INVENTORIES:"
                        +doc["document_id"]+":"+t
                    )
                inventory_by_target[t]=row

            relation_by_id={}
            for row in relations:
                effect=row.get("effect")
                if not isinstance(effect,Mapping):
                    raise ValueError(
                        "ACCEPTED_RELATION_EFFECT_INVALID:"+doc["document_id"]
                    )
                eid=_token(effect.get("effect_id"),"RELATION_EFFECT_ID")
                if eid in relation_by_id and relation_by_id[eid]!=row:
                    raise ValueError(
                        "MULTIPLE_DISTINCT_RELATIONS:"
                        +doc["document_id"]+":"+eid
                    )
                relation_by_id[eid]=row

            field_by_slot={}
            for row in fields:
                eid=_token(row.get("effect_id"),"FIELD_EFFECT_ID")
                field=_token(row.get("field"),"FIELD_NAME")
                if field not in ALL_FIELDS:
                    raise ValueError("ACCEPTED_FIELD_UNSUPPORTED:"+field)
                key=(eid,field)
                if key in field_by_slot and field_by_slot[key]!=row:
                    raise ValueError(
                        "MULTIPLE_DISTINCT_FIELD_PROOFS:"
                        +doc["document_id"]+":"+eid+":"+field
                    )
                field_by_slot[key]=row

            scope_targets=None
            if scopes:
                scope_targets=sorted(
                    str(x) for x in scopes[0].get("target_ids") or []
                )
                refinement_count+=1

            for eid,row in relation_by_id.items():
                effect=row["effect"]
                if (
                    scope_targets is not None
                    and effect["target_id"] not in scope_targets
                ):
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

            for (eid,field),row in field_by_slot.items():
                if field=="target_id":
                    proved_target=str(row.get("value") or "")
                    if (
                        scope_targets is not None
                        and proved_target not in scope_targets
                    ):
                        raise ValueError(
                            "FIELD_TARGET_OUTSIDE_PROVED_SCOPE:"
                            +doc["document_id"]+":"+eid
                        )
                    inv=inventory_by_target.get(proved_target)
                    if (
                        inv is not None
                        and eid not in set(inv.get("effect_ids") or [])
                    ):
                        raise ValueError(
                            "FIELD_ID_OUTSIDE_PROVED_INVENTORY:"
                            +doc["document_id"]+":"+eid
                        )

            query_irrelevant=(
                scope_targets is not None and target not in scope_targets
            )
            doc_state={
                "document_id":doc["document_id"],
                "source_id":doc["source_id"],
                "target_scope":{
                    "kind":"FINITE",
                    "values":scope_targets,
                } if scope_targets is not None else {"kind":"TOP"},
                "query_effect_id_inventory":{"kind":"TOP"},
                "effect_states":{},
                "query_status":None,
                "provided_claim_count":len(doc["claims"]),
                "synthesized_claim_count":len(
                    autofill.get("synthesized_claims") or []
                ),
                "accepted_claim_count":len(accepted),
                "rejected_claim_count":len(
                    proof.get("rejected_claims") or []
                ),
            }

            if query_irrelevant:
                doc_state["query_status"]="PROVED_QUERY_IRRELEVANT"
                lattice_docs.append(doc_state)
                proof_receipts.append({
                    "document_id":doc["document_id"],
                    "source_id":doc["source_id"],
                    "proof_status":proof.get("status"),
                    "accepted_claims":deepcopy(accepted),
                    "rejected_claims":deepcopy(
                        proof.get("rejected_claims") or []
                    ),
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
                    "rejected_claims":deepcopy(
                        proof.get("rejected_claims") or []
                    ),
                })
                continue

            ids=sorted(str(x) for x in inv.get("effect_ids") or [])
            id_set=set(ids)
            doc_state["query_effect_id_inventory"]={
                "kind":"FINITE",
                "values":ids,
            }
            refinement_count+=1

            extra_query_relations=sorted(
                eid for eid,row in relation_by_id.items()
                if row["effect"]["target_id"]==target and eid not in id_set
            )
            if extra_query_relations:
                raise ValueError(
                    "QUERY_RELATION_OUTSIDE_PROVED_INVENTORY:"
                    +doc["document_id"]+":"
                    +",".join(extra_query_relations)
                )

            extra_query_fields=sorted({
                eid for (eid,field),row in field_by_slot.items()
                if (
                    eid not in id_set
                    and field=="target_id"
                    and row.get("value")==target
                )
            })
            if extra_query_fields:
                raise ValueError(
                    "QUERY_FIELD_RELATION_OUTSIDE_PROVED_INVENTORY:"
                    +doc["document_id"]+":"
                    +",".join(extra_query_fields)
                )

            exact=[]
            document_open=False

            for eid in ids:
                full=relation_by_id.get(eid)
                per_fields={
                    field:field_by_slot[(eid,field)]
                    for field in ALL_FIELDS
                    if (eid,field) in field_by_slot
                }

                target_field=per_fields.get("target_id")
                if (
                    target_field is not None
                    and target_field.get("value")!=target
                ):
                    raise ValueError(
                        "INVENTORIED_EFFECT_TARGET_FIELD_MISMATCH:"
                        +doc["document_id"]+":"+eid
                    )

                if full is not None:
                    full_effect=deepcopy(dict(full["effect"]))
                    if full_effect["target_id"]!=target:
                        raise ValueError(
                            "INVENTORIED_EFFECT_RELATION_TARGET_MISMATCH:"
                            +doc["document_id"]+":"+eid
                        )
                    for field,row in per_fields.items():
                        if row.get("value")!=full_effect[field]:
                            raise ValueError(
                                "FULL_RELATION_FIELD_PROOF_CONFLICT:"
                                +doc["document_id"]+":"+eid+":"+field
                            )
                    component_states={
                        field:{
                            "kind":"EXACT_FROM_RELATION",
                            "value":deepcopy(full_effect[field]),
                        }
                        for field in ALL_FIELDS
                    }
                    doc_state["effect_states"][eid]={
                        "kind":"EXACT_RELATION",
                        "components":component_states,
                        "effect":full_effect,
                    }
                    exact.append(full_effect)
                    refinement_count+=len(REQUIRED_FIELDS)
                    continue

                component_states={
                    "target_id":{
                        "kind":"EXACT_FROM_INVENTORY",
                        "value":target,
                    }
                }
                if target_field is not None:
                    component_states["target_id"]["field_proof"]=deepcopy(
                        dict(target_field)
                    )
                    refinement_count+=1

                missing=[]
                exact_field_rows={}
                for field in REQUIRED_FIELDS:
                    row=per_fields.get(field)
                    if row is None:
                        component_states[field]={"kind":"TOP"}
                        missing.append(field)
                        open_atoms.append({
                            "document_id":doc["document_id"],
                            "dimension":"DOCUMENT_EFFECT_FIELD",
                            "effect_id":eid,
                            "field":field,
                            "target_id":target,
                            "state":"TOP",
                            "proof_obligation":{
                                "kind":"PROVE_DOCUMENT_EFFECT_FIELD",
                                "document_id":doc["document_id"],
                                "source_id":doc["source_id"],
                                "effect_id":eid,
                                "field":field,
                                "target_id":target,
                            },
                        })
                    else:
                        component_states[field]={
                            "kind":"EXACT",
                            "value":deepcopy(row.get("value")),
                            "field_id":row.get("field_id"),
                            "source_span_bytes":deepcopy(
                                row.get("source_span_bytes")
                            ),
                            "source_text_sha256":row.get(
                                "source_text_sha256"
                            ),
                        }
                        exact_field_rows[field]=row
                        refinement_count+=1

                if missing:
                    document_open=True
                    doc_state["effect_states"][eid]={
                        "kind":"PARTIAL_FIELDS",
                        "components":component_states,
                        "missing_fields":missing,
                    }
                    continue

                assembled={
                    "effect_id":eid,
                    "target_id":target,
                    "effect_class":component_states["effect_class"]["value"],
                    "value":component_states["value"]["value"],
                    "conditions":component_states["conditions"]["value"],
                    "valid_from":component_states["valid_from"]["value"],
                    "valid_until":component_states["valid_until"]["value"],
                    "supersedes":component_states["supersedes"]["value"],
                    "source_locator":_field_locator(
                        doc["source_id"],
                        eid,
                        inv,
                        exact_field_rows,
                    ),
                }
                try:
                    validated=calculus._validate_effect(assembled)
                except Exception as exc:
                    raise ValueError(
                        "ASSEMBLED_EFFECT_INVALID:"
                        +doc["document_id"]+":"+eid+":"
                        +type(exc).__name__+":"+str(exc)
                    ) from exc

                doc_state["effect_states"][eid]={
                    "kind":"EXACT_FIELDS",
                    "components":component_states,
                    "effect":validated,
                }
                exact.append(validated)

            if document_open:
                doc_state["query_status"]="OPEN__EFFECT_FIELD_TOP"
            else:
                doc_state["query_status"]="EXACT_QUERY_EFFECT_SET"
                exact_effects_by_doc[doc["document_id"]]=exact

            lattice_docs.append(doc_state)
            proof_receipts.append({
                "document_id":doc["document_id"],
                "source_id":doc["source_id"],
                "proof_status":proof.get("status"),
                "accepted_claims":deepcopy(accepted),
                "rejected_claims":deepcopy(
                    proof.get("rejected_claims") or []
                ),
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
            "lattice_invariant":(
                "SOURCE_PROOF_ONLY_SHRINKS_INDEPENDENT_FIELD_TOP_COORDINATES__"
                "ABSENT_OR_REJECTED_CLAIMS_NEVER_NARROW"
            ),
        }

        if open_atoms:
            return {
                **base,
                "status":"OPEN__QUERY_RELEVANT_EFFECT_FIELD_TOP_REMAINS",
                "pass":False,
                "next_proof_obligations":[
                    deepcopy(x["proof_obligation"]) for x in open_atoms
                ],
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
            slots=[]
            for effect in sorted(
                exact_effects_by_doc[did],
                key=lambda x:x["effect_id"],
            ):
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
                ws_docs.append({
                    "document_id":did,
                    "effect_slots":slots,
                })

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
                "status":"OPEN__FIELD_LATTICE_FINITE__EFFECT_COMPOSITION_NOT_CLOSED",
                "pass":False,
                "query_relative_effect_semantics_finite":True,
                "finite_worldset_result":finite,
                "finite_worldset_verification":checked,
                "possible_outcomes":deepcopy(
                    finite.get("possible_outcomes") or []
                ),
                "minimum_discriminator_slots":deepcopy(
                    finite.get("minimum_discriminator_slots") or []
                ),
                "world_count":finite.get("world_count"),
                "next_proof_obligations":[],
            }

        return {
            **base,
            "status":"PASS__FIELD_LATTICE_REFINED_TO_VERIFIED_EFFECT_VALUE",
            "pass":True,
            "query_relative_effect_semantics_finite":True,
            "finite_worldset_result":finite,
            "finite_worldset_verification":checked,
            "effective_value":deepcopy(finite.get("effective_value")),
            "world_count":finite.get("world_count"),
            "next_proof_obligations":[],
            "boundary":(
                "QUERY_RELATIVE_EFFECT_FIELDS_FROM_DIRECT_BOUNDED_NATURAL_OR_"
                "AUTHENTICATED_SEMANTIC_EDGE_PROOFS_ONLY__GLOBAL_ARBITRARY_"
                "LANGUAGE_SEMANTIC_COMPLETENESS_NOT_CLAIMED"
            ),
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
