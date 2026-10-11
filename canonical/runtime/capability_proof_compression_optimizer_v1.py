#!/usr/bin/env python3
"""Exact bounded optimizer for capability-first proof compression.

This scheduler does not create proof credit. It chooses the cheapest admissible
set of evidence actions that covers explicitly required propositions. If full
coverage is impossible with the supplied options, it returns the best partial
cover and the exact uncovered proposition set.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_CAPABILITY_PROOF_COMPRESSION_OPTIMIZER_V1"
MAX_REQUIRED=24
MAX_OPTIONS=64

class ProofCompressionError(ValueError): pass

def _require(cond: bool, msg: str) -> None:
    if not cond: raise ProofCompressionError(msg)

def _nonneg_int(value: Any, name: str) -> int:
    try: x=int(value)
    except Exception as exc: raise ProofCompressionError(name+"_INVALID") from exc
    if x < 0: raise ProofCompressionError(name+"_NEGATIVE")
    return x

def _validate(required: Sequence[Mapping[str,Any]], options: Sequence[Mapping[str,Any]]):
    _require(isinstance(required,Sequence) and len(required)>0,"REQUIRED_PROPOSITIONS_REQUIRED")
    _require(len(required)<=MAX_REQUIRED,"TOO_MANY_REQUIRED_PROPOSITIONS_FOR_EXACT_OPTIMIZER")
    _require(isinstance(options,Sequence),"EVIDENCE_OPTIONS_REQUIRED")
    _require(len(options)<=MAX_OPTIONS,"TOO_MANY_EVIDENCE_OPTIONS")
    req_ids=[]; weights={}
    for row in required:
        rid=str(row.get("id") or "")
        _require(rid and rid not in weights,"REQUIRED_ID_EMPTY_OR_DUPLICATE")
        w=_nonneg_int(row.get("weight",1),"REQUIRED_WEIGHT")
        _require(w>0,"REQUIRED_WEIGHT_ZERO")
        req_ids.append(rid); weights[rid]=w
    seen=set()
    normalized=[]
    for raw in options:
        oid=str(raw.get("id") or "")
        _require(oid and oid not in seen,"OPTION_ID_EMPTY_OR_DUPLICATE"); seen.add(oid)
        covers=[str(x) for x in (raw.get("covers") or [])]
        _require(all(x in weights for x in covers),"OPTION_COVERS_UNKNOWN_PROPOSITION")
        normalized.append({
            "id":oid,
            "covers":sorted(set(covers)),
            "admissible":bool(raw.get("admissible",True)),
            "wall_clock_cost":_nonneg_int(raw.get("wall_clock_cost",0),"WALL_CLOCK_COST"),
            "reusable_coverage_bonus":_nonneg_int(raw.get("reusable_coverage_bonus",0),"REUSABLE_COVERAGE_BONUS"),
            "external_dependency_risk":_nonneg_int(raw.get("external_dependency_risk",0),"EXTERNAL_DEPENDENCY_RISK"),
            "compute_cost":_nonneg_int(raw.get("compute_cost",0),"COMPUTE_COST"),
            "waits_for_external_event":bool(raw.get("waits_for_external_event",False)),
            "incremental_spend_usd":float(raw.get("incremental_spend_usd",0)),
            "external_runtime_cognition":int(raw.get("external_runtime_cognition",0)),
        })
    return req_ids,weights,normalized

def _admissible(o: Mapping[str,Any]) -> tuple[bool,str]:
    if not o["admissible"]: return False,"OPTION_MARKED_INADMISSIBLE"
    if o["waits_for_external_event"]: return False,"EXTERNAL_WAIT_NOT_EXECUTABLE_NOW"
    if o["incremental_spend_usd"] != 0: return False,"HARD_ZERO_INCREMENTAL_SPEND"
    if o["external_runtime_cognition"] != 0: return False,"EXTERNAL_RUNTIME_COGNITION_FORBIDDEN"
    if not o["covers"]: return False,"OPTION_COVERS_NOTHING_REQUIRED"
    return True,"ADMITTED"

def _cost_tuple(state: Mapping[str,Any]):
    return (
        state["wall_clock_cost"],
        -state["reusable_coverage_bonus"],
        state["external_dependency_risk"],
        state["compute_cost"],
        tuple(state["selected_ids"]),
    )

def optimize(required: Sequence[Mapping[str,Any]], options: Sequence[Mapping[str,Any]]) -> dict[str,Any]:
    req_ids,weights,normalized=_validate(required,options)
    index={rid:i for i,rid in enumerate(req_ids)}
    full=(1<<len(req_ids))-1
    rejected=[]; admitted=[]
    for o in normalized:
        ok,reason=_admissible(o)
        if ok: admitted.append(o)
        else: rejected.append({"id":o["id"],"reason":reason})

    dp={0:{"mask":0,"wall_clock_cost":0,"reusable_coverage_bonus":0,"external_dependency_risk":0,"compute_cost":0,"selected_ids":[]}}
    for o in admitted:
        omask=0
        for rid in o["covers"]: omask |= 1<<index[rid]
        snapshot=list(dp.items())
        for mask,state in snapshot:
            nmask=mask|omask
            cand={
                "mask":nmask,
                "wall_clock_cost":state["wall_clock_cost"]+o["wall_clock_cost"],
                "reusable_coverage_bonus":state["reusable_coverage_bonus"]+o["reusable_coverage_bonus"],
                "external_dependency_risk":state["external_dependency_risk"]+o["external_dependency_risk"],
                "compute_cost":state["compute_cost"]+o["compute_cost"],
                "selected_ids":state["selected_ids"]+[o["id"]],
            }
            cur=dp.get(nmask)
            if cur is None or _cost_tuple(cand) < _cost_tuple(cur): dp[nmask]=cand

    def covered_weight(mask: int) -> int:
        return sum(weights[rid] for rid,i in index.items() if mask & (1<<i))
    if full in dp:
        best=dp[full]; complete=True
    else:
        best=min(dp.values(),key=lambda s:(-covered_weight(s["mask"]),)+_cost_tuple(s)); complete=False
    covered=[rid for rid in req_ids if best["mask"] & (1<<index[rid])]
    uncovered=[rid for rid in req_ids if rid not in covered]
    selected={o["id"]:o for o in admitted}
    return {
        "schema":SCHEMA,
        "complete_cover":complete,
        "selected_evidence_ids":best["selected_ids"],
        "selected_evidence":[selected[x] for x in best["selected_ids"]],
        "covered_required_propositions":covered,
        "uncovered_required_propositions":uncovered,
        "covered_required_weight":covered_weight(best["mask"]),
        "total_required_weight":sum(weights.values()),
        "objective":{
            "wall_clock_cost":best["wall_clock_cost"],
            "reusable_coverage_bonus":best["reusable_coverage_bonus"],
            "external_dependency_risk":best["external_dependency_risk"],
            "compute_cost":best["compute_cost"],
            "order":"MIN_WALL_CLOCK__MAX_REUSABLE_COVERAGE__MIN_EXTERNAL_DEPENDENCY_RISK__MIN_COMPUTE_COST__DETERMINISTIC_ID_TIEBREAK",
        },
        "rejected":rejected,
        "credit_authority":False,
        "rule":"OPTIMIZATION_ONLY__SELECTED_EVIDENCE_MUST_STILL_PASS_ITS_OWN_PROOF_AND_OWNERSHIP_GATES",
    }
