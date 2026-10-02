"""Brain-owned deterministic candidate adapters for contract-native terminal proof tasks.

This module MUST NOT import the proof-suite evaluator. It consumes only the public
task payload and implements the four explicit typed behavioral contracts using
Brain-owned deterministic mechanisms.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Mapping


class CandidateError(ValueError):
    pass


def _contract(task: Mapping[str, Any]) -> str:
    c=task.get("contract")
    if not isinstance(c,str) or not c:
        raise CandidateError("CONTRACT_REQUIRED")
    return c


def solve_structured_method(public: Mapping[str, Any]) -> dict[str, Any]:
    task=public.get("task")
    if not isinstance(task,Mapping):
        raise CandidateError("TASK_INVALID")
    reqs=task.get("requirements")
    if not isinstance(reqs,list):
        raise CandidateError("REQUIREMENTS_INVALID")
    graph=[]
    seen=set()
    for row in reqs:
        if not isinstance(row,Mapping):
            raise CandidateError("REQUIREMENT_ROW_INVALID")
        fid=row.get("id"); coeff=row.get("coefficient")
        if row.get("required") is not True:
            continue
        if not isinstance(fid,str) or not fid or fid in seen:
            raise CandidateError("FACTOR_INVALID")
        if not isinstance(coeff,int) or isinstance(coeff,bool):
            raise CandidateError("COEFFICIENT_INVALID")
        seen.add(fid)
        graph.append({"factor":fid,"coefficient":coeff})
    return {"graph":graph}


def solve_trajectory(public: Mapping[str, Any]) -> dict[str, Any]:
    task=public.get("task")
    if not isinstance(task,Mapping):
        raise CandidateError("TASK_INVALID")
    trajectory=task.get("trajectory")
    repairs=task.get("repair_candidates")
    if not isinstance(trajectory,list) or not isinstance(repairs,list):
        raise CandidateError("TRAJECTORY_INVALID")
    bad=[]
    for row in trajectory:
        if not isinstance(row,Mapping) or not isinstance(row.get("step"),int):
            raise CandidateError("TRAJECTORY_ROW_INVALID")
        if row.get("invariant_pass") is False:
            bad.append(int(row["step"]))
    if not bad:
        raise CandidateError("NO_CAUSAL_FAILURE_VISIBLE")
    cause=min(bad)
    matching=[
        r for r in repairs
        if isinstance(r,Mapping)
        and r.get("targets_step")==cause
        and isinstance(r.get("id"),str)
    ]
    if len(matching)!=1:
        raise CandidateError("REPAIR_NOT_IDENTIFIABLE")
    return {
        "cause_step":cause,
        "repair_id":matching[0]["id"],
        "evidence_steps":[cause],
    }


def solve_synthesis(public: Mapping[str, Any]) -> dict[str, Any]:
    task=public.get("task")
    if not isinstance(task,Mapping):
        raise CandidateError("TASK_INVALID")
    evidence=task.get("evidence")
    if not isinstance(evidence,list):
        raise CandidateError("EVIDENCE_INVALID")
    required=[]; optional=[]; uncertainty=[]
    for row in evidence:
        if not isinstance(row,Mapping):
            raise CandidateError("EVIDENCE_ROW_INVALID")
        cid=row.get("claim_id"); role=row.get("role"); support=row.get("support")
        if not isinstance(cid,str) or not cid:
            raise CandidateError("CLAIM_ID_INVALID")
        if role=="required" and support!="unsupported":
            required.append(cid)
        elif role=="optional" and support!="unsupported":
            optional.append(cid)
        if support=="conflicted" and role in {"required","optional"}:
            uncertainty.append(cid)
    selected=required+optional
    constraints=task.get("format_constraints") or {}
    max_claims=constraints.get("max_claims")
    if not isinstance(max_claims,int) or isinstance(max_claims,bool) or max_claims<0:
        raise CandidateError("FORMAT_CONSTRAINT_INVALID")
    if len(selected)>max_claims:
        optional=optional[:max(0,max_claims-len(required))]
        selected=required+optional
    selected_set=set(selected)
    return {
        "selected_claims":selected,
        "uncertainty_claims":[x for x in uncertainty if x in selected_set],
    }


def solve_professional_plan(public: Mapping[str, Any]) -> dict[str, Any]:
    task=public.get("task")
    if not isinstance(task,Mapping):
        raise CandidateError("TASK_INVALID")
    weights=task.get("rubric_weights")
    actions=task.get("edit_candidates")
    budget=task.get("edit_budget")
    if not isinstance(weights,Mapping) or not isinstance(actions,list) or not isinstance(budget,int):
        raise CandidateError("PLAN_TASK_INVALID")
    admissible=[]
    for row in actions:
        if not isinstance(row,Mapping) or not isinstance(row.get("id"),str):
            raise CandidateError("EDIT_INVALID")
        if row.get("supported") is True and row.get("hard_violation") is False:
            cost=row.get("cost"); scores=row.get("scores")
            if not isinstance(cost,int) or not isinstance(scores,Mapping):
                raise CandidateError("EDIT_FIELDS_INVALID")
            admissible.append(row)
    best=None
    for n in range(len(admissible)+1):
        for subset in combinations(admissible,n):
            cost=sum(int(x["cost"]) for x in subset)
            if cost>budget:
                continue
            score=0
            for x in subset:
                scores=x["scores"]
                for dim,w in weights.items():
                    v=scores.get(dim)
                    if not isinstance(w,int) or not isinstance(v,int):
                        raise CandidateError("RUBRIC_SCORE_INVALID")
                    score += w*v
            ids=tuple(sorted(str(x["id"]) for x in subset))
            key=(-score,cost,ids)
            if best is None or key<best[0]:
                best=(key,ids)
    if best is None:
        raise CandidateError("NO_ADMISSIBLE_PLAN")
    return {"selected_edits":list(best[1])}


def solve(public: Mapping[str, Any]) -> dict[str, Any]:
    c=_contract(public)
    if c=="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001":
        return solve_structured_method(public)
    if c=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
        return solve_trajectory(public)
    if c=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001":
        return solve_synthesis(public)
    if c=="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
        return solve_professional_plan(public)
    raise CandidateError("UNSUPPORTED_CONTRACT:"+c)
