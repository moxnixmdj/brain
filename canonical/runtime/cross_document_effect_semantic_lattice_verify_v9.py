"""Independent verifier for compositional-natural semantic-edge effect field lattice V9."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v16 import verify_proof
from canonical.runtime.source_semantic_claim_autofill_v4 import (
    synthesize_missing_claims,
)
from canonical.runtime import cross_document_effect_calculus_v1 as calculus
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_VERIFY_V9"
PROBLEM_SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V9"
REQUIRED_FIELDS=(
    "effect_class","value","conditions",
    "valid_from","valid_until","supersedes",
)
ALL_FIELDS=("target_id",)+REQUIRED_FIELDS


def _canon(value:Any)->str:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    )


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _docs(rows:Any)->list[dict[str,Any]]:
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
        raise ValueError("SOURCE_DOCUMENTS_INVALID")
    out=[]; dids=set(); sids=set()
    for row in rows:
        if not isinstance(row,Mapping) or set(row)!={"document_id","source_id","source_text","claims"}:
            raise ValueError("SOURCE_DOCUMENT_FIELDS_INVALID")
        did=_token(row.get("document_id"),"DOCUMENT_ID")
        sid=_token(row.get("source_id"),"SOURCE_ID")
        text=row.get("source_text")
        claims=row.get("claims")
        if not isinstance(text,str) or not text:
            raise ValueError("SOURCE_TEXT_INVALID")
        if not isinstance(claims,Sequence) or isinstance(claims,(str,bytes)):
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
    _canon(context)
    return {"target_id":target,"as_of":as_of,"context":deepcopy(dict(context))}


def _dedupe(rows:Sequence[Mapping[str,Any]],keyfn):
    out={}
    for row in rows:
        key=keyfn(row)
        if key in out and out[key]!=dict(row):
            raise ValueError("DISTINCT_PROOFS_FOR_SAME_SLOT:"+str(key))
        out[key]=deepcopy(dict(row))
    return [out[k] for k in sorted(out,key=lambda x:str(x))]


def _locator(source_id,effect_id,inventory_row,field_rows):
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
    return source_id+":fieldproof:"+sha256(
        _canon(evidence).encode("utf-8")
    ).hexdigest()[:24]


def _recompute(
    problem:Mapping[str,Any],
    *,
    relation_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None,
)->dict[str,Any]:
    if not isinstance(problem,Mapping) or problem.get("schema")!=PROBLEM_SCHEMA:
        raise ValueError("PROBLEM_SCHEMA_INVALID")
    if set(problem)!={"schema","case_id","source_documents","query"}:
        raise ValueError("PROBLEM_FIELDS_INVALID")
    case_id=_token(problem.get("case_id"),"CASE_ID")
    docs=_docs(problem.get("source_documents"))
    query=_query(problem.get("query"))
    target=query["target_id"]

    open_atoms=[]
    exact_by_doc={}

    for doc in docs:
        auto=synthesize_missing_claims(
            doc["source_text"],
            source_id=doc["source_id"],
            existing_claims=doc["claims"],
        )
        if auto.get("pass") is not True:
            raise ValueError("AUTOFILL_FAIL_CLOSED:"+doc["document_id"])
        claims=list(doc["claims"])+list(auto.get("synthesized_claims") or [])
        proof=verify_proof(
            doc["source_text"],
            source_id=doc["source_id"],
            claims=claims,
            relation_verifier=relation_verifier,
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
        fields=_dedupe(
            [x for x in accepted if x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_FIELD"],
            lambda x:(x.get("effect_id"),x.get("field")),
        )

        if len(scopes)>1:
            raise ValueError("MULTIPLE_SCOPE_PROOFS")
        scope=None
        if scopes:
            scope=sorted(str(x) for x in scopes[0].get("target_ids") or [])

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

        field_by_slot={}
        for row in fields:
            eid=_token(row.get("effect_id"),"FIELD_EFFECT_ID")
            field=_token(row.get("field"),"FIELD")
            if field not in ALL_FIELDS:
                raise ValueError("FIELD_UNSUPPORTED")
            key=(eid,field)
            if key in field_by_slot and field_by_slot[key]!=row:
                raise ValueError("MULTIPLE_FIELDS")
            field_by_slot[key]=row

        for eid,row in rel_by_id.items():
            effect=row["effect"]
            if scope is not None and effect["target_id"] not in scope:
                raise ValueError("RELATION_TARGET_OUTSIDE_SCOPE")
            inv=inv_by_target.get(effect["target_id"])
            if inv is not None and eid not in set(inv.get("effect_ids") or []):
                raise ValueError("RELATION_OUTSIDE_INVENTORY")

        for (eid,field),row in field_by_slot.items():
            if field=="target_id":
                proved=str(row.get("value") or "")
                if scope is not None and proved not in scope:
                    raise ValueError("FIELD_TARGET_OUTSIDE_SCOPE")
                inv=inv_by_target.get(proved)
                if inv is not None and eid not in set(inv.get("effect_ids") or []):
                    raise ValueError("FIELD_OUTSIDE_INVENTORY")

        if scope is not None and target not in scope:
            continue

        inv=inv_by_target.get(target)
        if inv is None:
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
            continue

        ids=sorted(str(x) for x in inv.get("effect_ids") or [])
        id_set=set(ids)
        extra_rel=sorted(
            eid for eid,row in rel_by_id.items()
            if row["effect"]["target_id"]==target and eid not in id_set
        )
        if extra_rel:
            raise ValueError("QUERY_RELATION_OUTSIDE_INVENTORY")
        extra_field=sorted({
            eid for (eid,field),row in field_by_slot.items()
            if eid not in id_set and field=="target_id" and row.get("value")==target
        })
        if extra_field:
            raise ValueError("QUERY_FIELD_OUTSIDE_INVENTORY")

        exact=[]
        doc_open=False
        for eid in ids:
            full=rel_by_id.get(eid)
            per={
                field:field_by_slot[(eid,field)]
                for field in ALL_FIELDS
                if (eid,field) in field_by_slot
            }
            if "target_id" in per and per["target_id"].get("value")!=target:
                raise ValueError("INVENTORIED_TARGET_FIELD_MISMATCH")

            if full is not None:
                effect=deepcopy(dict(full["effect"]))
                if effect["target_id"]!=target:
                    raise ValueError("INVENTORIED_RELATION_TARGET_MISMATCH")
                for field,row in per.items():
                    if row.get("value")!=effect[field]:
                        raise ValueError("FULL_RELATION_FIELD_CONFLICT")
                exact.append(effect)
                continue

            field_rows={}
            missing=[]
            for field in REQUIRED_FIELDS:
                row=per.get(field)
                if row is None:
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
                    field_rows[field]=row

            if missing:
                doc_open=True
                continue

            assembled={
                "effect_id":eid,
                "target_id":target,
                "effect_class":field_rows["effect_class"]["value"],
                "value":field_rows["value"]["value"],
                "conditions":field_rows["conditions"]["value"],
                "valid_from":field_rows["valid_from"]["value"],
                "valid_until":field_rows["valid_until"]["value"],
                "supersedes":field_rows["supersedes"]["value"],
                "source_locator":_locator(
                    doc["source_id"],eid,inv,field_rows
                ),
            }
            exact.append(calculus._validate_effect(assembled))

        if not doc_open:
            exact_by_doc[doc["document_id"]]=exact

    if open_atoms:
        return {
            "status":"OPEN__QUERY_RELEVANT_EFFECT_FIELD_TOP_REMAINS",
            "pass":False,
            "open_lattice_atoms":open_atoms,
            "next_proof_obligations":[
                deepcopy(x["proof_obligation"]) for x in open_atoms
            ],
            "query_relative_effect_semantics_finite":False,
            "exact_effects_by_document":exact_by_doc,
        }

    if not any(exact_by_doc.values()):
        return {
            "status":"OPEN__NO_QUERY_EFFECT_RELATION_PROVED",
            "pass":False,
            "open_lattice_atoms":[],
            "next_proof_obligations":[],
            "query_relative_effect_semantics_finite":True,
            "exact_effects_by_document":exact_by_doc,
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
            "status":"OPEN__FIELD_LATTICE_FINITE__EFFECT_COMPOSITION_NOT_CLOSED",
            "pass":False,
            "open_lattice_atoms":[],
            "next_proof_obligations":[],
            "query_relative_effect_semantics_finite":True,
            "possible_outcomes":deepcopy(finite.get("possible_outcomes") or []),
            "minimum_discriminator_slots":deepcopy(
                finite.get("minimum_discriminator_slots") or []
            ),
            "world_count":finite.get("world_count"),
            "exact_effects_by_document":exact_by_doc,
        }

    return {
        "status":"PASS__FIELD_LATTICE_REFINED_TO_VERIFIED_EFFECT_VALUE",
        "pass":True,
        "open_lattice_atoms":[],
        "next_proof_obligations":[],
        "query_relative_effect_semantics_finite":True,
        "effective_value":deepcopy(finite.get("effective_value")),
        "world_count":finite.get("world_count"),
        "exact_effects_by_document":exact_by_doc,
    }


def _extract_result_effects(result:Mapping[str,Any])->dict[str,list[dict[str,Any]]]:
    out={}
    for doc in result.get("lattice_documents") or []:
        if not isinstance(doc,Mapping):
            continue
        did=str(doc.get("document_id") or "")
        effects=[]
        states=doc.get("effect_states")
        if not isinstance(states,Mapping):
            continue
        for eid in sorted(states):
            state=states[eid]
            if (
                isinstance(state,Mapping)
                and state.get("kind") in {"EXACT_RELATION","EXACT_FIELDS"}
                and isinstance(state.get("effect"),Mapping)
            ):
                effects.append(deepcopy(dict(state["effect"])))
        if effects:
            out[did]=effects
    return out


def verify(
    problem:Mapping[str,Any],
    result:Mapping[str,Any],
    *,
    relation_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None,
)->dict[str,Any]:
    errors=[]
    try:
        expected=_recompute(problem,relation_verifier=relation_verifier)
        if not isinstance(result,Mapping):
            raise ValueError("RESULT_NOT_OBJECT")

        for key in (
            "status","pass","open_lattice_atoms",
            "next_proof_obligations",
            "query_relative_effect_semantics_finite",
        ):
            if result.get(key)!=expected.get(key):
                errors.append("MISMATCH:"+key)

        actual_effects=_extract_result_effects(result)
        if actual_effects!=expected.get("exact_effects_by_document"):
            errors.append("MISMATCH:EXACT_EFFECTS_BY_DOCUMENT")

        if expected.get("pass") is True:
            for key in ("effective_value","world_count"):
                if result.get(key)!=expected.get(key):
                    errors.append("MISMATCH:"+key)
        elif expected.get("query_relative_effect_semantics_finite") is True:
            for key in (
                "possible_outcomes",
                "minimum_discriminator_slots",
                "world_count",
            ):
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
        "status":(
            "PASS__INDEPENDENT_FIELD_LATTICE_RECOMPUTATION"
            if not errors else "FAIL_CLOSED"
        ),
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "boundary":(
            "INDEPENDENT_V11_SOURCE_PROOF_DIRECT_BOUNDED_NATURAL_AND_SEMANTIC_"
            "EDGE_FIELD_ASSEMBLY_CROSS_FIELD_VALIDATION_AND_FINITE_WORLDSET_"
            "RECOMPUTATION"
        ),
    }
