"""Independent verifier for cross-document residual effect frontier V1.

This verifier does not call cross_document_residual_effect_frontier_v1.evaluate.
It independently recomputes:
- source/document identity coverage,
- V7 source-aligned scope and effect-ID inventory proofs,
- modeled target/effect-ID consistency,
- residual TOP blocking state,
- finite world-set result and its independent verifier.

The verifier grants no semantic or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v7 import verify_proof
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_RESIDUAL_EFFECT_FRONTIER_VERIFY_V1"
PROBLEM_SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_RESIDUAL_EFFECT_FRONTIER_V1"


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _source_rows(problem:Mapping[str,Any])->list[dict[str,Any]]:
    rows=problem.get("source_documents")
    if (
        not isinstance(rows,Sequence)
        or isinstance(rows,(str,bytes))
        or not rows
    ):
        raise ValueError("SOURCE_DOCUMENTS_INVALID")
    out=[]; seen=set()
    for row in rows:
        if not isinstance(row,Mapping) or set(row)!={
            "document_id","source_id","source_text","scope_claim","inventory_claims"
        }:
            raise ValueError("SOURCE_DOCUMENT_INVALID")
        did=_token(row.get("document_id"),"DOCUMENT_ID")
        if did in seen:
            raise ValueError("DOCUMENT_ID_DUPLICATE")
        seen.add(did)
        sid=_token(row.get("source_id"),"SOURCE_ID")
        text=row.get("source_text")
        if not isinstance(text,str) or not text:
            raise ValueError("SOURCE_TEXT_INVALID")
        scope=row.get("scope_claim")
        if scope is not None and not isinstance(scope,Mapping):
            raise ValueError("SCOPE_CLAIM_INVALID")
        inv=row.get("inventory_claims")
        if (
            not isinstance(inv,Sequence)
            or isinstance(inv,(str,bytes))
            or any(not isinstance(x,Mapping) for x in inv)
        ):
            raise ValueError("INVENTORY_CLAIMS_INVALID")
        out.append({
            "document_id":did,
            "source_id":sid,
            "source_text":text,
            "scope_claim":deepcopy(dict(scope)) if isinstance(scope,Mapping) else None,
            "inventory_claims":[deepcopy(dict(x)) for x in inv],
        })
    return sorted(out,key=lambda x:x["document_id"])


def _world_docs(ws:Mapping[str,Any])->dict[str,Mapping[str,Any]]:
    rows=ws.get("documents")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)):
        raise ValueError("WORLDSET_DOCUMENTS_INVALID")
    out={}
    for row in rows:
        if not isinstance(row,Mapping):
            raise ValueError("WORLDSET_DOCUMENT_INVALID")
        did=_token(row.get("document_id"),"WORLDSET_DOCUMENT_ID")
        if did in out:
            raise ValueError("WORLDSET_DOCUMENT_ID_DUPLICATE")
        out[did]=row
    return out


def _modeled(doc:Mapping[str,Any],target:str)->tuple[set[str],set[str]]:
    targets=set(); ids=set()
    for slot in doc.get("effect_slots") or []:
        for hyp in slot.get("hypotheses") or []:
            effect=hyp.get("effect")
            if not isinstance(effect,Mapping):
                continue
            tid=effect.get("target_id")
            eid=effect.get("effect_id")
            if isinstance(tid,str) and tid:
                targets.add(tid)
            if (
                tid==target
                and isinstance(eid,str)
                and eid
            ):
                ids.add(eid)
    return targets,ids


def _proofs(row:Mapping[str,Any])->tuple[Mapping[str,Any]|None,dict[str,Mapping[str,Any]],Mapping[str,Any]|None]:
    claims=[]
    scope_claim=row.get("scope_claim")
    if isinstance(scope_claim,Mapping):
        claims.append(scope_claim)
    claims.extend(row.get("inventory_claims") or [])
    if not claims:
        return None,{},None
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
        rows=[
            x for x in accepted
            if x.get("kind")=="CERTIFIED_EFFECT_TARGET_SCOPE"
            and x.get("claim_id")==scope_claim.get("claim_id")
        ]
        if len(rows)==1:
            scope=rows[0]
    inventories={}
    for claim in row.get("inventory_claims") or []:
        rows=[
            x for x in accepted
            if x.get("kind")=="CERTIFIED_EFFECT_ID_INVENTORY"
            and x.get("claim_id")==claim.get("claim_id")
        ]
        if len(rows)==1:
            inventories[str(rows[0]["target_id"])]=rows[0]
    return scope,inventories,checked


def _expected(problem:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(problem,Mapping) or problem.get("schema")!=PROBLEM_SCHEMA:
        raise ValueError("PROBLEM_SCHEMA_INVALID")
    if set(problem)!={"schema","case_id","source_documents","worldset_problem"}:
        raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")

    case_id=_token(problem.get("case_id"),"CASE_ID")
    ws=problem.get("worldset_problem")
    if not isinstance(ws,Mapping):
        raise ValueError("WORLDSET_PROBLEM_INVALID")
    query=ws.get("query")
    if not isinstance(query,Mapping):
        raise ValueError("QUERY_INVALID")
    target=_token(query.get("target_id"),"QUERY_TARGET_ID")

    sources=_source_rows(problem)
    wdocs=_world_docs(ws)
    if {x["document_id"] for x in sources}!=set(wdocs):
        raise ValueError("SOURCE_WORLDSET_DOCUMENT_ID_MISMATCH")

    blocking=[]
    residual_states={}
    consistency=[]
    obligations=[]

    for row in sources:
        did=row["document_id"]
        targets,ids=_modeled(wdocs[did],target)
        scope,inventories,_checked=_proofs(row)
        scope_targets=set(scope.get("target_ids") or []) if isinstance(scope,Mapping) else set()
        if isinstance(scope,Mapping):
            outside=sorted(targets-scope_targets)
            if outside:
                consistency.append({
                    "document_id":did,
                    "modeled_targets_outside_proved_scope":outside,
                })
        query_excluded=isinstance(scope,Mapping) and target not in scope_targets
        inventory=inventories.get(target)
        proved_ids=set(inventory.get("effect_ids") or []) if isinstance(inventory,Mapping) else set()
        inventory_matches=isinstance(inventory,Mapping) and proved_ids==ids
        if isinstance(inventory,Mapping) and not inventory_matches:
            consistency.append({
                "document_id":did,
                "query_target_id":target,
                "proved_inventory_effect_ids":sorted(proved_ids),
                "modeled_effect_ids":sorted(ids),
                "reason":"MODELED_EFFECT_ID_INVENTORY_MISMATCH",
            })

        if query_excluded:
            state="PROVED_QUERY_IRRELEVANT"
        elif inventory_matches:
            state="PROVED_QUERY_EFFECT_ID_INVENTORY_EXHAUSTIVE"
        else:
            state="TOP_EFFECT_MAY_AFFECT_QUERY"
            blocking.append(did)
            if not isinstance(scope,Mapping) and not isinstance(inventory,Mapping):
                obligations.append({
                    "kind":"PROVE_EFFECT_TARGET_SCOPE_OR_QUERY_EFFECT_ID_INVENTORY",
                    "document_id":did,
                    "query_target_id":target,
                })
            else:
                obligations.append({
                    "kind":"PROVE_QUERY_TARGET_EFFECT_ID_INVENTORY_EXHAUSTIVE",
                    "document_id":did,
                    "query_target_id":target,
                    "modeled_effect_ids":sorted(ids),
                    "proved_scope_target_ids":sorted(scope_targets),
                })
        residual_states[did]=state

    if consistency:
        return {
            "status":"FAIL_CLOSED__MODELED_EFFECTS_INCONSISTENT_WITH_SOURCE_PROOF",
            "pass":False,
            "case_id":case_id,
            "query_target_id":target,
            "blocking_residual_document_ids":sorted(blocking),
            "residual_states":residual_states,
            "scope_consistency_errors":consistency,
        }

    finite=worldset.evaluate(ws)
    finite_check=worldset_verify.verify(ws,finite)
    if finite_check.get("verified") is not True:
        raise ValueError(
            "FINITE_WORLDSET_INDEPENDENT_VERIFICATION_FAILED:"
            + ",".join(finite_check.get("errors") or [])
        )

    if blocking:
        return {
            "status":"OPEN__RESIDUAL_TOP_EFFECT_MAY_CHANGE_QUERY",
            "pass":False,
            "case_id":case_id,
            "query_target_id":target,
            "blocking_residual_document_ids":sorted(blocking),
            "residual_states":residual_states,
            "next_proof_obligations":obligations,
            "finite_pass":finite.get("pass") is True,
            "finite_effective_value":deepcopy(finite.get("effective_value")),
        }

    return {
        "status":(
            "PASS__RESIDUAL_TOP_CLOSED_FOR_QUERY_AND_FINITE_WORLDSET_PASSED"
            if finite.get("pass") is True
            else "OPEN__RESIDUAL_TOP_CLOSED_FOR_QUERY__FINITE_WORLDSET_NOT_CLOSED"
        ),
        "pass":finite.get("pass") is True,
        "case_id":case_id,
        "query_target_id":target,
        "blocking_residual_document_ids":[],
        "residual_states":residual_states,
        "effective_value":deepcopy(finite.get("effective_value")),
        "minimum_discriminator_slots":deepcopy(
            finite.get("minimum_discriminator_slots") or []
        ),
    }


def verify(problem:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    try:
        expected=_expected(problem)
        if not isinstance(result,Mapping):
            raise ValueError("RESULT_NOT_OBJECT")
        for key in (
            "status","pass","case_id","query_target_id",
            "blocking_residual_document_ids"
        ):
            if result.get(key)!=expected.get(key):
                errors.append("MISMATCH:"+key)

        if expected["status"]=="FAIL_CLOSED__MODELED_EFFECTS_INCONSISTENT_WITH_SOURCE_PROOF":
            if result.get("scope_consistency_errors")!=expected.get("scope_consistency_errors"):
                errors.append("MISMATCH:scope_consistency_errors")
        elif expected["status"]=="OPEN__RESIDUAL_TOP_EFFECT_MAY_CHANGE_QUERY":
            if result.get("next_proof_obligations")!=expected.get("next_proof_obligations"):
                errors.append("MISMATCH:next_proof_obligations")
            preview=result.get("finite_worldset_preview")
            if not isinstance(preview,Mapping):
                errors.append("FINITE_WORLDSET_PREVIEW_MISSING")
            else:
                if (preview.get("pass") is True)!=expected.get("finite_pass"):
                    errors.append("MISMATCH:finite_worldset_preview.pass")
                if preview.get("effective_value")!=expected.get("finite_effective_value"):
                    errors.append("MISMATCH:finite_worldset_preview.effective_value")
        else:
            if result.get("effective_value")!=expected.get("effective_value"):
                errors.append("MISMATCH:effective_value")
            if result.get("minimum_discriminator_slots")!=expected.get("minimum_discriminator_slots"):
                errors.append("MISMATCH:minimum_discriminator_slots")

        states={
            str(x.get("document_id")):x.get("state")
            for x in result.get("residuals") or []
            if isinstance(x,Mapping)
        }
        if states!=expected.get("residual_states"):
            errors.append("MISMATCH:residual_states")

        if result.get("semantic_truth_authority") is not False:
            errors.append("SEMANTIC_TRUTH_AUTHORITY_CLAIMED")
        if result.get("terminal_authority") is not False:
            errors.append("TERMINAL_AUTHORITY_CLAIMED")
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))

    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_RESIDUAL_FRONTIER_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "boundary":(
            "INDEPENDENT_RECOMPUTATION_OF_SOURCE_PROVED_TARGET_SCOPE_AND_EFFECT_ID_"
            "INVENTORY_RESIDUALS_PLUS_INDEPENDENT_FINITE_WORLDSET_VERIFICATION"
        ),
    }
