from __future__ import annotations
from functools import lru_cache
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_SEMANTIC_INFORMATION_FRONTIER_V1"

def solve(problem:Mapping[str,Any])->dict[str,Any]:
    """Exact minimax information policy for a finite COMPLETE semantic hypothesis set.

    It distinguishes interpretations only when they imply different terminal signatures.
    The objective is minimum worst-case observation cost. If all surviving worlds are
    terminal-equivalent, it stops immediately even if their internal interpretations differ.
    """
    if not isinstance(problem,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"PROBLEM_REQUIRED"}
    if problem.get("hypothesis_set_complete") is not True:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"HYPOTHESIS_SET_COMPLETENESS_UNPROVED"}

    worlds=problem.get("worlds")
    observations=problem.get("observations")
    if not isinstance(worlds,Sequence) or isinstance(worlds,(str,bytes)) or not worlds:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"WORLDS_REQUIRED"}
    if not isinstance(observations,Sequence) or isinstance(observations,(str,bytes)):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"OBSERVATIONS_REQUIRED"}

    sig={}
    ids=[]
    for i,w in enumerate(worlds):
        if not isinstance(w,Mapping):
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":f"WORLD_INVALID:{i}"}
        wid=w.get("world_id")
        if not isinstance(wid,str) or not wid or wid in sig:
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":f"WORLD_ID_INVALID:{i}"}
        if w.get("terminal_signature_complete") is not True:
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":f"TERMINAL_SIGNATURE_COMPLETENESS_UNPROVED:{wid}"}
        signature=w.get("terminal_signature")
        if not isinstance(signature,Mapping):
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":f"TERMINAL_SIGNATURE_INVALID:{wid}"}
        ids.append(wid); sig[wid]=tuple(sorted((str(k),repr(v)) for k,v in signature.items()))

    obs={}
    for i,o in enumerate(observations):
        if not isinstance(o,Mapping):
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":f"OBSERVATION_INVALID:{i}"}
        oid=o.get("observation_id")
        outcomes=o.get("outcomes")
        cost=o.get("cost_units")
        if not isinstance(oid,str) or not oid or oid in obs:
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":f"OBSERVATION_ID_INVALID:{i}"}
        if o.get("outcome_map_complete") is not True or not isinstance(outcomes,Mapping) or set(outcomes)!=set(ids):
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":f"OBSERVATION_OUTCOME_MAP_INCOMPLETE:{oid}"}
        if not isinstance(cost,(int,float)) or isinstance(cost,bool) or cost<0:
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":f"OBSERVATION_COST_INVALID:{oid}"}
        obs[oid]={"cost":float(cost),"outcomes":{w:repr(outcomes[w]) for w in ids}}

    def resolved(state:frozenset[str])->bool:
        return len({sig[w] for w in state})<=1

    def partition(state:frozenset[str], oid:str):
        buckets={}
        for w in state:
            buckets.setdefault(obs[oid]["outcomes"][w],set()).add(w)
        return tuple(frozenset(v) for _,v in sorted(buckets.items()))

    @lru_cache(maxsize=None)
    def dp(state:frozenset[str]):
        if resolved(state):
            return (0.0,None,())
        best=None
        for oid in sorted(obs):
            parts=partition(state,oid)
            if len(parts)<=1 or any(p==state for p in parts):
                continue
            child=[]
            impossible=False
            worst=0.0
            for p in parts:
                c=dp(p)
                if c[0]==float("inf"):
                    impossible=True; break
                child.append((tuple(sorted(p)),c[0]))
                worst=max(worst,c[0])
            if impossible:
                continue
            total=obs[oid]["cost"]+worst
            cand=(total,oid,tuple(child))
            if best is None or (cand[0],cand[1]) < (best[0],best[1]):
                best=cand
        return best if best is not None else (float("inf"),None,())

    initial=frozenset(ids)
    total,first,children=dp(initial)
    if total==float("inf"):
        unresolved=sorted({
            (a,b) for i,a in enumerate(ids) for b in ids[i+1:]
            if sig[a]!=sig[b]
            and all(obs[o]["outcomes"][a]==obs[o]["outcomes"][b] for o in obs)
        })
        return {
            "schema":SCHEMA,"pass":False,
            "status":"FAIL_CLOSED__TERMINALLY_DISTINCT_WORLDS_NOT_SEPARABLE_BY_DECLARED_OBSERVATIONS",
            "unresolved_pairs":unresolved,
            "terminal_authority":False
        }

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__EXACT_MINIMAX_SEMANTIC_INFORMATION_POLICY",
        "world_count":len(ids),
        "terminal_equivalence_class_count":len(set(sig.values())),
        "minimum_worst_case_cost_units":total,
        "first_observation_id":first,
        "first_observation_partitions":[{"world_ids":list(p),"remaining_optimal_cost":c} for p,c in children],
        "stops_when_terminally_equivalent":True,
        "does_not_require_full_world_identification":True,
        "theorem_boundary":"EXACT_ONLY_FOR_THE_DECLARED_COMPLETE_HYPOTHESIS_SET_COMPLETE_TERMINAL_SIGNATURES_AND_COMPLETE_OBSERVATION_OUTCOME_MAPS",
        "terminal_authority":False,
        "capability_credit_delta":0,
    }
