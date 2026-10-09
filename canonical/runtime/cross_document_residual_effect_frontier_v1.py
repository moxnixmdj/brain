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
            "document_id","source_id","source_text","scope_claim"
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
        out.append({
            "document_id":did,
            "source_id":sid,
            "source_text":text,
            "scope_claim":deepcopy(dict(claim)) if isinstance(claim,Mapping) else None,
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


def _scope_for_document(row:Mapping[str,Any])->dict[str,Any]:
    claim=row.get("scope_claim")
    if not isinstance(claim,Mapping):
        return {
            "proved":False,
            "status":"UNPROVED",
            "reason":"NO_SOURCE_ALIGNED_SCOPE_CLAIM",
            "target_ids":[],
            "proof":None,
        }
    checked=verify_proof(
        row["source_text"],
        source_id=row["source_id"],
        claims=[claim],
    )
    accepted=[
        x for x in checked.get("accepted_claims") or []
        if isinstance(x,Mapping)
        and x.get("kind")=="CERTIFIED_EFFECT_TARGET_SCOPE"
        and x.get("claim_id")==claim.get("claim_id")
    ]
    if len(accepted)!=1:
        return {
            "proved":False,
            "status":checked.get("status"),
            "reason":"CERTIFIED_EFFECT_TARGET_SCOPE_NOT_ACCEPTED",
            "target_ids":[],
            "proof":checked,
        }
    return {
        "proved":True,
        "status":checked.get("status"),
        "reason":None,
        "target_ids":list(accepted[0].get("target_ids") or []),
        "proof":checked,
        "accepted_claim":deepcopy(dict(accepted[0])),
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
            scope=_scope_for_document(row)
            modeled_targets=_concrete_targets_for_doc(ws,row["document_id"])

            if scope["proved"]:
                allowed=set(scope["target_ids"])
                outside=sorted(modeled_targets-allowed)
                if outside:
                    scope_consistency_errors.append({
                        "document_id":row["document_id"],
                        "modeled_targets_outside_proved_scope":outside,
                    })
                query_excluded=target not in allowed
            else:
                query_excluded=False

            if query_excluded:
                state="PROVED_QUERY_IRRELEVANT"
                next_obligation=None
            else:
                state="TOP_EFFECT_MAY_AFFECT_QUERY"
                if not scope["proved"]:
                    next_obligation={
                        "kind":"PROVE_EFFECT_TARGET_SCOPE_OR_QUERY_EXCLUSION",
                        "document_id":row["document_id"],
                        "query_target_id":target,
                    }
                else:
                    next_obligation={
                        "kind":"PROVE_QUERY_TARGET_EFFECT_INVENTORY_EXHAUSTIVE",
                        "document_id":row["document_id"],
                        "query_target_id":target,
                        "proved_scope_target_ids":list(scope["target_ids"]),
                    }
                blocking.append(row["document_id"])

            residuals.append({
                "residual_id":"RESIDUAL_TOP::"+row["document_id"],
                "document_id":row["document_id"],
                "state":state,
                "query_target_id":target,
                "proved_scope_target_ids":list(scope["target_ids"]),
                "scope_proved":scope["proved"],
                "scope_proof_status":scope["status"],
                "scope_proof_reason":scope["reason"],
                "scope_accepted_claim":deepcopy(scope.get("accepted_claim")),
                "next_proof_obligation":next_obligation,
            })

        if scope_consistency_errors:
            return {
                "schema":SCHEMA,
                "status":"FAIL_CLOSED__MODELED_EFFECT_OUTSIDE_PROVED_SOURCE_SCOPE",
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
                "EFFECT_TARGET_SCOPE_EXCLUSION__QUERY_TARGET_EFFECT_INVENTORY_"
                "EXHAUSTIVENESS_REMAINS_UNPROVED_WHEN_TARGET_IS_INCLUDED"
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
