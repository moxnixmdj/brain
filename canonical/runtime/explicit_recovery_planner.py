"""Exact bounded recovery-plan selection from explicit repair effects.

Given failed invariants and candidate repair actions whose restore sets, prerequisites,
costs, risks, and authorization are explicit, find the minimum-cost admissible action
subset that restores every failed invariant. Unknown repair effects remain out of scope.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
import math
from typing import FrozenSet,Sequence

@dataclass(frozen=True)
class RepairAction:
    action_id:str
    restores:FrozenSet[str]
    prerequisites:FrozenSet[str]=frozenset()
    cost:float=0.0
    risk:float=0.0
    authorized:bool=True
    verified_effects:bool=True

def plan_recovery(
    failed_invariants:set[str],
    satisfied_prerequisites:set[str],
    actions:Sequence[RepairAction],
)->dict:
    if not failed_invariants:
        return {"status":"PASS","selected_actions":[],"reason":"NO_FAILED_INVARIANTS"}
    ids=[a.action_id for a in actions]
    if any(not isinstance(x,str) or not x for x in ids) or len(ids)!=len(set(ids)):
        return {"status":"FAIL_CLOSED","reason":"ACTION_IDENTITIES_INVALID_OR_DUPLICATE"}
    eligible=[]
    for a in actions:
        if not a.authorized or not a.verified_effects:
            continue
        if not a.prerequisites.issubset(satisfied_prerequisites):
            continue
        if not isinstance(a.cost,(int,float)) or isinstance(a.cost,bool) or not math.isfinite(float(a.cost)) or a.cost<0:
            continue
        if not isinstance(a.risk,(int,float)) or isinstance(a.risk,bool) or not math.isfinite(float(a.risk)) or a.risk<0:
            continue
        if not (a.restores & failed_invariants):
            continue
        eligible.append(a)
    if not eligible:
        return {"status":"ESCALATE","reason":"NO_VERIFIED_AUTHORIZED_REPAIR_EFFECT"}
    if len(eligible)>24:
        return {"status":"ESCALATE","reason":"BOUNDED_EXACT_SEARCH_LIMIT_EXCEEDED"}
    best=None
    for k in range(1,len(eligible)+1):
        for subset in combinations(eligible,k):
            covered=set().union(*(a.restores for a in subset))
            if not failed_invariants.issubset(covered):
                continue
            cost=sum(float(a.cost) for a in subset)
            risk=sum(float(a.risk) for a in subset)
            names=tuple(sorted(a.action_id for a in subset))
            key=(cost,risk,k,names)
            if best is None or key<best[0]:
                best=(key,names)
    if best is None:
        union=set().union(*(a.restores for a in eligible)) if eligible else set()
        return {
            "status":"ESCALATE",
            "reason":"FAILED_INVARIANTS_NOT_FULLY_COVERED",
            "uncovered":sorted(failed_invariants-union),
        }
    return {
        "status":"SELECT",
        "selected_actions":list(best[1]),
        "total_cost":best[0][0],
        "total_risk":best[0][1],
        "reason":"MIN_COST__THEN_MIN_RISK__THEN_MIN_ACTION_COUNT",
        "terminal_authority":False,
    }
