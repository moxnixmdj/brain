"""Exact finite adaptive experiment planner for Universal Learning V5.

Given a closed finite decision-relevant hypothesis space and independently
verified probe safety/outcome models, compute a minimum worst-case-cost adaptive
probe tree. No probabilities are used. This avoids greedy one-step traps.
"""
from __future__ import annotations
from fractions import Fraction
from functools import lru_cache
from typing import Any, Mapping, Sequence

from canonical.runtime import open_world_hypothesis_guard_v4 as guard
from canonical.runtime import verified_probe_model_v5 as model

SCHEMA="PROJECT_BRAIN_ADAPTIVE_EXPERIMENT_PLANNER_V5"
class AdaptiveExperimentPlannerError(ValueError): pass

def plan(*,environment_id:str,goal_id:str,hypotheses:Sequence[Mapping[str,Any]],hypothesis_coverage_receipt:Mapping[str,Any],probes:Sequence[Mapping[str,Any]])->dict[str,Any]:
    closure=guard.close_space(environment_id=environment_id,goal_id=goal_id,hypotheses=hypotheses,coverage_receipt=hypothesis_coverage_receipt)
    if closure.get("closed") is not True:
        raise AdaptiveExperimentPlannerError("CLOSED_HYPOTHESIS_SPACE_REQUIRED")

    ids=[]; best={};seen=set()
    for h in hypotheses:
        hid=str(h.get("id") or "").strip()
        if not hid or hid in seen: raise AdaptiveExperimentPlannerError("HYPOTHESIS_ID_INVALID_OR_DUPLICATE")
        seen.add(hid)
        if h.get("plausible") is not True: continue
        act=str(h.get("best_action") or "").strip()
        if not act: raise AdaptiveExperimentPlannerError("LIVE_HYPOTHESIS_ACTION_REQUIRED")
        ids.append(hid);best[hid]=act
    if not ids: raise AdaptiveExperimentPlannerError("LIVE_HYPOTHESES_REQUIRED")

    admitted=[];pseen=set()
    for raw in probes:
        p=model.admit(environment_id=environment_id,goal_id=goal_id,hypotheses=hypotheses,probe=raw)
        if p["id"] in pseen: raise AdaptiveExperimentPlannerError("PROBE_ID_DUPLICATE")
        pseen.add(p["id"]);admitted.append(p)

    by_id={p["id"]:p for p in admitted}

    def solved(state:frozenset[str])->str|None:
        acts={best[x] for x in state}
        return next(iter(acts)) if len(acts)==1 else None

    @lru_cache(maxsize=None)
    def dp(state:frozenset[str], remaining:tuple[str,...]):
        terminal=solved(state)
        if terminal is not None:
            return (Fraction(0),Fraction(0),Fraction(0),0,{"type":"DECIDE","action":terminal,"hypotheses":sorted(state)})
        best_candidate=None
        for pid in remaining:
            p=by_id[pid]
            groups={}
            for hid in state:
                outcome=p["outcome_by_hypothesis"][hid]
                groups.setdefault(outcome,set()).add(hid)
            if len(groups)<=1: continue
            next_remaining=tuple(x for x in remaining if x!=pid)
            children={}; child_vectors=[]; feasible=True
            for outcome,group in sorted(groups.items()):
                child=dp(frozenset(group),next_remaining)
                if child is None:
                    feasible=False;break
                wt,wc,wr,ws,ct=child
                children[outcome]=ct
                child_vectors.append((wt,wc,wr,ws))
            if not feasible: continue
            worst=max(child_vectors) if child_vectors else (Fraction(0),Fraction(0),Fraction(0),0)
            vector=(p["wall_clock"]+worst[0],p["resource_cost"]+worst[1],p["residual_risk"]+worst[2],1+worst[3])
            tree={
                "type":"PROBE","probe_id":pid,
                "probe_wall_clock":str(p["wall_clock"]),
                "probe_resource_cost":str(p["resource_cost"]),
                "probe_residual_risk":str(p["residual_risk"]),
                "safety_receipt":p["safety_receipt"],"outcome_model_receipt":p["outcome_model_receipt"],
                "branches":children,
            }
            candidate=(vector,pid,tree)
            if best_candidate is None or (candidate[0],candidate[1])<(best_candidate[0],best_candidate[1]):
                best_candidate=candidate
        if best_candidate is None: return None
        v=best_candidate[0]
        return (v[0],v[1],v[2],v[3],best_candidate[2])

    result=dp(frozenset(ids),tuple(sorted(by_id)))
    if result is None:
        return {
            "schema":SCHEMA,"status":"NO_VERIFIED_ADAPTIVE_RESOLUTION_PLAN",
            "hypothesis_space_closed":True,"recommended_probe":None,
            "worst_case_wall_clock":None,"worst_case_resource_cost":None,"worst_case_residual_risk":None,"worst_case_steps":None,"plan":None,
            "acceptance_credit_delta":0,"ownership_credit_delta":0,
        }
    wall_clock,resource_cost,residual_risk,steps,tree=result
    first=tree.get("probe_id") if tree.get("type")=="PROBE" else None
    return {
        "schema":SCHEMA,"status":"VERIFIED_MINIMUM_WORST_CASE_ADAPTIVE_PLAN",
        "hypothesis_space_closed":True,
        "optimization":"EXACT_FINITE_LEXICOGRAPHIC_MINIMUM__HARD_SAFETY_THEN_WORST_CASE_WALL_CLOCK_THEN_RESOURCE_COST_THEN_RESIDUAL_RISK_THEN_STEPS",
        "probability_model_required":False,
        "recommended_probe":first,
        "worst_case_wall_clock":str(wall_clock),
        "worst_case_resource_cost":str(resource_cost),
        "worst_case_residual_risk":str(residual_risk),
        "worst_case_steps":steps,"plan":tree,
        "acceptance_credit_delta":0,"ownership_credit_delta":0,
    }
