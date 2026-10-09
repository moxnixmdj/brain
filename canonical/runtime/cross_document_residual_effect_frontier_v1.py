"""Residual-TOP semantic frontier for cross-document effects V1.

This module prevents false completeness when finite effect hypotheses were
generated from arbitrary document language.

Every source document implicitly carries a residual TOP_EFFECT representing any
still-unmodeled semantic effect. A residual can be proved irrelevant to the
current query only through a Brain-recomputed source-aligned target-scope proof
that excludes the query target.

If a residual can still touch the query target, the frontier MUST remain open,
even when the finite world-set engine happens to return one common value.

This is intentionally incomplete but sound relative to the V7 source-scope
primitive. It does not accept caller-supplied "complete" flags for arbitrary
raw prose.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v7 import verify_proof
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_RESIDUAL_EFFECT_FRONTIER_V1"


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _source_docs(problem:Mapping[str,Any])->list[dict[str,Any]]:
    docs=problem.get("source_documents")
    if (
        not isinstance(docs,Sequence)
        or isinstance(docs,(str,bytes))
        or not docs
    ):
        raise ValueError("SOURCE_DOCUMENTS_INVALID")
    out=[]
    seen=set()
    for i,row in enumerate(docs):
        if not isinstance(row,Mapping) or set(row)!={
            "document_id","source_id","source_text","scope_claim","inventory_claims"
        }:
            raise ValueError("SOURCE_DOCUMENT_INVALID:"+str(i))
        did=_token(row.get("document_id"),"DOCUMENT_ID")
        sid=_token(row.get("source_id"),"SOURCE_ID")
        text=row.get("source_text")
        if not isinstance(text,str) or not text:
            raise ValueError("SOURCE_TEXT_INVALID:"+did)
        if did in seen:
            raise ValueError("DOCUMENT_ID_DUPLICATE:"+did)
        seen.add(did)
        claim=row.get("scope_claim")
        if claim is not None and not isinstance(claim,Mapping):
            raise ValueError("SCOPE_CLAIM_INVALID:"+did)
        inventories=row.get("inventory_claims")
        if (
            not isinstance(inventories,Sequence)
            or isinstance(inventories,(str,bytes))
            or any(not isinstance(x,Mapping) for x in inventories)
        ):
            raise ValueError("INVENTORY_CLAIMS_INVALID:"+did)
        out.append({
            "document_id":did,
            "source_id":sid,
            "source_text":text,
            "scope_claim":deepcopy(dict(claim)) if isinstance(claim,Mapping) else None,
            "inventory_claims":[deepcopy(dict(x)) for x in inventories],
        })
    out.sort(key=lambda x:x["document_id"])
    return out


def _worldset_document_ids(problem:Mapping[str,Any])->set[str]:
    docs=problem.get("documents")
    if not isinstance(docs,Sequence) or isinstance(docs,(str,bytes)):
        raise ValueError("WORLDSET_DOCUMENTS_INVALID")
    ids=set()
    for row in docs:
        if not isinstance(row,Mapping):
            raise ValueError("WORLDSET_DOCUMENT_INVALID")
        did=_token(row.get("document_id"),"WORLDSET_DOCUMENT_ID")
        if did in ids:
            raise ValueError("WORLDSET_DOCUMENT_ID_DUPLICATE:"+did)
        ids.add(did)
    return ids


def _concrete_targets_for_doc(problem:Mapping[str,Any],document_id:str)->set[str]:
    out=set()
    for doc in problem.get("documents") or []:
        if doc.get("document_id")!=document_id:
            continue
        for slot in doc.get("effect_slots") or []:
            for hyp in slot.get("hypotheses") or []:
                effect=hyp.get("effect")
                if isinstance(effect,Mapping):
                    tid=effect.get("target_id")
                    if isinstance(tid,str) and tid:
                        out.add(tid)
    return out


def _concrete_effect_ids_for_doc_target(
    problem:Mapping[str,Any],
    document_id:str,
    target_id:str,
)->set[str]:
    out=set()
    for doc in problem.get("documents") or []:
        if doc.get("document_id")!=document_id:
            continue
        for slot in doc.get("effect_slots") or []:
            for hyp in slot.get("hypotheses") or []:
                effect=hyp.get("effect")
                if (
                    isinstance(effect,Mapping)
                    and effect.get("target_id")==target_id
                    and isinstance(effect.get("effect_id"),str)
                    and effect.get("effect_id")
                ):
                    out.add(effect["effect_id"])
    return out


def _proofs_for_document(row:Mapping[str,Any])->dict[str,Any]:
    claims=[]
    scope_claim=row.get("scope_claim")
    if isinstance(scope_claim,Mapping):
        claims.append(scope_claim)
    claims.extend(row.get("inventory_claims") or [])

    if not claims:
        return {
            "status":"UNPROVED",
            "proof":None,
            "scope":None,
            "inventories":{},
        }

    checked=verify_proof(
        row["source_text"],
        source_id=row["source_id"],
        claims=claims,
    )
    accepted=[
        x for x in checked.get("accepted_claims") or []
        if isinstance(x,Mapping)
    ]

    scope=None
    if isinstance(scope_claim,Mapping):
        matches=[
            x for x in accepted
            if x.get("kind")=="CERTIFIED_EFFECT_TARGET_SCOPE"
            and x.get("claim_id")==scope_claim.get("claim_id")
        ]
        if len(matches)==1:
            scope=deepcopy(dict(matches[0]))

    inventories={}
    for claim in row.get("inventory_claims") or []:
        matches=[
            x for x in accepted
            if x.get("kind")=="CERTIFIED_EFFECT_ID_INVENTORY"
            and x.get("claim_id")==claim.get("claim_id")
        ]
        if len(matches)==1:
            inventories[str(matches[0]["target_id"])]=deepcopy(dict(matches[0]))

    return {
        "status":checked.get("status"),
        "proof":checked,
        "scope":scope,
        "inventories":inventories,
    }


def evaluate(problem:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(problem,Mapping) or problem.get("schema")!=SCHEMA:
            raise ValueError("PROBLEM_SCHEMA_INVALID")
        if set(problem)!={"schema","case_id","source_documents","worldset_problem"}:
            raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")
        case_id=_token(problem.get("case_id"),"CASE_ID")
        ws=problem.get("worldset_problem")
        if not isinstance(ws,Mapping):
            raise ValueError("WORLDSET_PROBLEM_INVALID")

        source_docs=_source_docs(problem)
        source_ids={x["document_id"] for x in source_docs}
        world_ids=_worldset_document_ids(ws)
        if source_ids!=world_ids:
            raise ValueError(
                "SOURCE_WORLDSET_DOCUMENT_ID_MISMATCH:"
                + ",".join(sorted(source_ids ^ world_ids))
            )

        query=ws.get("query")
        if not isinstance(query,Mapping):
            raise ValueError("WORLDSET_QUERY_INVALID")
        target=_token(query.get("target_id"),"QUERY_TARGET_ID")

        residuals=[]
        blocking=[]
        scope_consistency_errors=[]
        for row in source_docs:
            proofs=_proofs_for_document(row)
            scope=proofs.get("scope")
            inventories=proofs.get("inventories") or {}
            modeled_targets=_concrete_targets_for_doc(ws,row["document_id"])
            modeled_query_effect_ids=_concrete_effect_ids_for_doc_target(
                ws,row["document_id"],target
            )

            scope_target_ids=list(scope.get("target_ids") or []) if isinstance(scope,Mapping) else []
            if isinstance(scope,Mapping):
                allowed=set(scope_target_ids)
                outside=sorted(modeled_targets-allowed)
                if outside:
                    scope_consistency_errors.append({
                        "document_id":row["document_id"],
                        "modeled_targets_outside_proved_scope":outside,
                    })
                query_excluded=target not in allowed
            else:
                query_excluded=False

            inventory=inventories.get(target)
            inventory_ids=set(inventory.get("effect_ids") or []) if isinstance(inventory,Mapping) else set()
            inventory_matches=(
                isinstance(inventory,Mapping)
                and inventory_ids==modeled_query_effect_ids
            )
            if isinstance(inventory,Mapping) and not inventory_matches:
                scope_consistency_errors.append({
                    "document_id":row["document_id"],
                    "query_target_id":target,
                    "proved_inventory_effect_ids":sorted(inventory_ids),
                    "modeled_effect_ids":sorted(modeled_query_effect_ids),
                    "reason":"MODELED_EFFECT_ID_INVENTORY_MISMATCH",
                })

            if query_excluded:
                state="PROVED_QUERY_IRRELEVANT"
                next_obligation=None
            elif inventory_matches:
                state="PROVED_QUERY_EFFECT_ID_INVENTORY_EXHAUSTIVE"
                next_obligation=None
            else:
                state="TOP_EFFECT_MAY_AFFECT_QUERY"
                if not isinstance(scope,Mapping) and not isinstance(inventory,Mapping):
                    next_obligation={
                        "kind":"PROVE_EFFECT_TARGET_SCOPE_OR_QUERY_EFFECT_ID_INVENTORY",
                        "document_id":row["document_id"],
                        "query_target_id":target,
                    }
                else:
                    next_obligation={
                        "kind":"PROVE_QUERY_TARGET_EFFECT_ID_INVENTORY_EXHAUSTIVE",
                        "document_id":row["document_id"],
                        "query_target_id":target,
                        "modeled_effect_ids":sorted(modeled_query_effect_ids),
                        "proved_scope_target_ids":scope_target_ids,
                    }
                blocking.append(row["document_id"])

            residuals.append({
                "residual_id":"RESIDUAL_TOP::"+row["document_id"],
                "document_id":row["document_id"],
                "state":state,
                "query_target_id":target,
                "proved_scope_target_ids":scope_target_ids,
                "scope_proved":isinstance(scope,Mapping),
                "scope_accepted_claim":deepcopy(scope),
                "proved_query_effect_id_inventory":deepcopy(inventory),
                "modeled_query_effect_ids":sorted(modeled_query_effect_ids),
                "source_proof_status":proofs.get("status"),
                "next_proof_obligation":next_obligation,
            })

        if scope_consistency_errors:
            return {
                "schema":SCHEMA,
                "status":"FAIL_CLOSED__MODELED_EFFECTS_INCONSISTENT_WITH_SOURCE_PROOF",
                "pass":False,
                "case_id":case_id,
                "query_target_id":target,
                "scope_consistency_errors":scope_consistency_errors,
                "residuals":residuals,
                "semantic_truth_authority":False,
                "terminal_authority":False,
            }

        finite=worldset.evaluate(ws)

        if blocking:
            return {
                "schema":SCHEMA,
                "status":"OPEN__RESIDUAL_TOP_EFFECT_MAY_CHANGE_QUERY",
                "pass":False,
                "case_id":case_id,
                "query_target_id":target,
                "blocking_residual_document_ids":sorted(blocking),
                "residuals":residuals,
                "finite_worldset_preview":finite,
                "next_proof_obligations":[
                    r["next_proof_obligation"]
                    for r in residuals
                    if r["next_proof_obligation"] is not None
                ],
                "semantic_truth_authority":False,
                "terminal_authority":False,
                "soundness_rule":(
                    "FINITE_EFFECT_HYPOTHESES_CANNOT_CLOSE_WHILE_ANY_UNMODELED_"
                    "RESIDUAL_EFFECT_MAY_STILL_TOUCH_THE_QUERY_TARGET"
                ),
            }

        return {
            "schema":SCHEMA,
            "status":(
                "PASS__RESIDUAL_TOP_CLOSED_FOR_QUERY_AND_FINITE_WORLDSET_PASSED"
                if finite.get("pass") is True
                else "OPEN__RESIDUAL_TOP_CLOSED_FOR_QUERY__FINITE_WORLDSET_NOT_CLOSED"
            ),
            "pass":finite.get("pass") is True,
            "case_id":case_id,
            "query_target_id":target,
            "blocking_residual_document_ids":[],
            "residuals":residuals,
            "finite_worldset_result":finite,
            "effective_value":deepcopy(finite.get("effective_value")),
            "minimum_discriminator_slots":deepcopy(
                finite.get("minimum_discriminator_slots") or []
            ),
            "semantic_truth_authority":False,
            "terminal_authority":False,
            "boundary":(
                "RESIDUAL_TOP_IS_CLOSED_ONLY_BY_BRAIN_RECOMPUTED_EXPLICIT_"
                "QUERY_TARGET_EXCLUSION_OR_EXACT_EFFECT_ID_INVENTORY_MATCH;"
                "EFFECT_VALUE_CLASS_CONDITION_INTERPRETATIONS_REMAIN_WITH_THE_WORLDSET_ENGINE"
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
