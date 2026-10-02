"""Exact professional-plan selection when the quality rubric is explicit.

This does not score subjective quality. It selects among already-scored candidate plans
under a frozen explicit rubric, hard constraints, evidence-grounding gate, and cost.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Mapping,Sequence

@dataclass(frozen=True)
class Plan:
    plan_id:str
    dimension_scores:Mapping[str,float]
    hard_violations:frozenset[str]=frozenset()
    evidence_supported:bool=True
    cost:float=0.0

def select_plan(weights:Mapping[str,float],plans:Sequence[Plan])->dict:
    if not weights or any(
        not isinstance(k,str) or not k or not isinstance(v,(int,float)) or isinstance(v,bool)
        or not math.isfinite(float(v)) or float(v)<0
        for k,v in weights.items()
    ) or sum(float(v) for v in weights.values())<=0:
        return {"status":"FAIL_CLOSED","reason":"RUBRIC_INVALID"}
    ids=[p.plan_id for p in plans]
    if any(not isinstance(x,str) or not x for x in ids) or len(ids)!=len(set(ids)):
        return {"status":"FAIL_CLOSED","reason":"PLAN_IDENTITIES_INVALID_OR_DUPLICATE"}
    eligible=[]
    for p in plans:
        if p.hard_violations or not p.evidence_supported:
            continue
        if not isinstance(p.cost,(int,float)) or isinstance(p.cost,bool) or not math.isfinite(float(p.cost)) or p.cost<0:
            continue
        if any(d not in p.dimension_scores for d in weights):
            continue
        vals={d:p.dimension_scores[d] for d in weights}
        if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(float(v)) or not 0<=float(v)<=1 for v in vals.values()):
            continue
        utility=sum(float(weights[d])*float(vals[d]) for d in weights)/sum(float(v) for v in weights.values())
        eligible.append((utility,-float(p.cost),p.plan_id))
    if not eligible:
        return {"status":"ESCALATE","reason":"NO_EVIDENCE_SUPPORTED_HARD_CONSTRAINT_COMPLIANT_FULL_RUBRIC_PLAN"}
    eligible.sort(key=lambda x:(-x[0],-x[1],x[2]))
    best=eligible[0]
    ties=[x for x in eligible if x[0]==best[0] and x[1]==best[1]]
    if len(ties)>1:
        return {"status":"ESCALATE","reason":"EXACT_RUBRIC_AND_COST_TIE","candidate_ids":sorted(x[2] for x in ties)}
    return {
        "status":"SELECT",
        "plan_id":best[2],
        "weighted_score":best[0],
        "cost":-best[1],
        "reason":"MAX_EXPLICIT_WEIGHTED_RUBRIC_SCORE__THEN_MIN_COST",
        "terminal_authority":False,
    }
