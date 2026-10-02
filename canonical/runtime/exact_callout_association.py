"""Exact fail-closed association solver for finite callout/feature candidate graphs.

Upstream vision/parser stages enumerate *all* source-consistent candidate targets and
explicit hard relations. This solver never invents weights or proximity preferences.
It returns an assignment only when the hard evidence admits exactly one solution.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

SCHEMA="BRAIN_EXACT_CALLOUT_ASSOCIATION_V1"

def solve(
    callouts: Sequence[Mapping[str,Any]],
    *,
    distinct_targets: bool=False,
    same_target: Sequence[Sequence[str]]=(),
    different_target: Sequence[Sequence[str]]=(),
    max_solutions: int=2,
) -> dict[str,Any]:
    if max_solutions < 2:
        raise ValueError("max_solutions must be >=2")
    domains={}
    errors=[]
    order=[]
    for i,row in enumerate(callouts):
        if not isinstance(row,Mapping):
            errors.append(f"CALLOUT_NOT_OBJECT:{i}"); continue
        cid=str(row.get("id","")).strip()
        raw=row.get("candidate_targets")
        if not cid or cid in domains:
            errors.append(f"BAD_OR_DUPLICATE_CALLOUT_ID:{i}:{cid}"); continue
        if not isinstance(raw,Sequence) or isinstance(raw,(str,bytes)):
            errors.append(f"CANDIDATES_NOT_SEQUENCE:{cid}"); continue
        vals=sorted({str(x).strip() for x in raw if str(x).strip()})
        if not vals:
            errors.append(f"EMPTY_CANDIDATE_SET:{cid}"); continue
        domains[cid]=vals; order.append(cid)
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),"terminal_authority":False}

    ids=set(order)
    same=[tuple(str(x) for x in g) for g in same_target]
    diff=[tuple(str(x) for x in g) for g in different_target]
    for kind,groups in (("SAME",same),("DIFFERENT",diff)):
        for g in groups:
            if len(g)<2 or any(x not in ids for x in g):
                errors.append(f"INVALID_{kind}_GROUP:"+",".join(g))
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),"terminal_authority":False}

    # Most constrained first, deterministic tie-break by id.
    search_order=sorted(order,key=lambda x:(len(domains[x]),x))
    solutions=[]

    def consistent(partial):
        vals=list(partial.values())
        if distinct_targets and len(vals)!=len(set(vals)):
            return False
        for g in same:
            assigned=[partial[x] for x in g if x in partial]
            if assigned and len(set(assigned))>1:
                return False
        for g in diff:
            assigned=[partial[x] for x in g if x in partial]
            if len(assigned)!=len(set(assigned)):
                return False
        return True

    def dfs(k,partial):
        if len(solutions)>=max_solutions:
            return
        if k==len(search_order):
            solutions.append(dict(partial)); return
        cid=search_order[k]
        for target in domains[cid]:
            partial[cid]=target
            if consistent(partial):
                dfs(k+1,partial)
            partial.pop(cid,None)
            if len(solutions)>=max_solutions:
                return

    dfs(0,{})
    if not solutions:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "error":"NO_CONSISTENT_ASSOCIATION",
            "domains":domains,"terminal_authority":False
        }
    if len(solutions)>1:
        witness=[]
        a,b=solutions[0],solutions[1]
        for cid in sorted(ids):
            if a.get(cid)!=b.get(cid):
                witness.append({"callout_id":cid,"alternative_targets":[a.get(cid),b.get(cid)]})
        return {
            "schema":SCHEMA,"status":"AMBIGUOUS",
            "ambiguity_witness":witness,
            "first_two_solutions":solutions[:2],
            "next":"ACQUIRE_DISCRIMINATING_SOURCE_EVIDENCE",
            "terminal_authority":False
        }
    return {
        "schema":SCHEMA,"status":"UNIQUE",
        "assignment":solutions[0],
        "proof":{"solution_count_with_cap":1,"candidate_domains":domains},
        "terminal_authority":False
    }
