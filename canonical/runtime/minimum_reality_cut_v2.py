#!/usr/bin/env python3
"""Exact weighted minimum-reality-cut solver over atomic proof requirements.

V2 fixes two V1 modeling limits:
1. Conjunctive family proofs are represented as separate atomic requirements.
2. Exact search is branch-and-bound over candidate observations, so requirement
   count is not capped by a 24-bit dynamic-programming mask.

Input:
{
  "requirements": ["R1", ...],
  "already_resolved": ["R1", ...],
  "observations": [
    {"id":"O1","covers":["R2"],"cost":1},
    ...
  ]
}
"""
from __future__ import annotations

import argparse
import json
import math
from decimal import Decimal
from pathlib import Path
from typing import Any

MAX_OBSERVATIONS = 80


def _validate(data: dict[str, Any]):
    reqs=data.get("requirements")
    resolved=data.get("already_resolved",[])
    obs=data.get("observations")
    if not isinstance(reqs,list) or not reqs or not all(isinstance(x,str) and x for x in reqs):
        raise ValueError("requirements must be a nonempty string list")
    if len(reqs)!=len(set(reqs)):
        raise ValueError("duplicate requirement")
    if not isinstance(resolved,list) or not all(isinstance(x,str) for x in resolved):
        raise ValueError("already_resolved must be a string list")
    universe=set(reqs)
    if not set(resolved)<=universe:
        raise ValueError("already_resolved contains unknown requirement")
    if not isinstance(obs,list) or len(obs)>MAX_OBSERVATIONS:
        raise ValueError("observations must be a list within limit")
    clean=[]
    ids=set()
    for row in obs:
        if not isinstance(row,dict):
            raise ValueError("observation must be object")
        oid=row.get("id"); covers=row.get("covers"); cost=row.get("cost")
        if not isinstance(oid,str) or not oid or oid in ids:
            raise ValueError("invalid or duplicate observation id")
        ids.add(oid)
        if not isinstance(covers,list) or not all(isinstance(x,str) for x in covers):
            raise ValueError(f"{oid}: covers must be string list")
        cover=set(covers)
        if not cover<=universe:
            raise ValueError(f"{oid}: covers unknown requirement")
        if not isinstance(cost,(int,float)) or isinstance(cost,bool) or not math.isfinite(float(cost)) or float(cost)<0:
            raise ValueError(f"{oid}: invalid cost")
        clean.append({"id":oid,"covers":cover,"cost":Decimal(str(cost))})
    return reqs,set(resolved),clean


def solve(data: dict[str, Any]) -> dict[str, Any]:
    reqs,resolved,obs=_validate(data)
    remaining=set(reqs)-resolved
    if not remaining:
        return {"schema":"PROJECT_BRAIN_MINIMUM_REALITY_CUT_V2","status":"EXACT_MINIMUM","exact_minimum":True,
                "selected_observations":[],"total_cost":0.0,"observation_count":0,"unresolved_requirements":[]}

    obs=[o for o in obs if o["covers"] & remaining]
    cover_union=set().union(*(o["covers"] for o in obs)) if obs else set()
    missing=sorted(remaining-cover_union)
    if missing:
        return {"schema":"PROJECT_BRAIN_MINIMUM_REALITY_CUT_V2","status":"UNRESOLVABLE_WITH_DECLARED_OBSERVATIONS",
                "exact_minimum":False,"missing_requirements":missing}

    # Delete strictly dominated observations.
    kept=[]
    for i,a in enumerate(obs):
        dominated=False
        for j,b in enumerate(obs):
            if i==j:
                continue
            if a["covers"]<=b["covers"] and b["cost"]<=a["cost"]:
                if a["covers"]<b["covers"] or b["cost"]<a["cost"] or b["id"]<a["id"]:
                    dominated=True
                    break
        if not dominated:
            kept.append(a)
    obs=sorted(kept,key=lambda x:x["id"])

    by_req={r:[] for r in remaining}
    for i,o in enumerate(obs):
        for r in o["covers"] & remaining:
            by_req[r].append(i)
    if any(not v for v in by_req.values()):
        missing=sorted(r for r,v in by_req.items() if not v)
        return {"schema":"PROJECT_BRAIN_MINIMUM_REALITY_CUT_V2","status":"UNRESOLVABLE_AFTER_DOMINANCE",
                "exact_minimum":False,"missing_requirements":missing}

    best: tuple[Decimal,int,tuple[str,...]]|None=None
    best_sel: tuple[int,...]=()
    memo: dict[frozenset[str],Decimal]={}

    def recurse(uncovered:set[str], chosen:tuple[int,...], cost:Decimal):
        nonlocal best,best_sel
        if not uncovered:
            ids=tuple(sorted(obs[i]["id"] for i in chosen))
            cand=(cost,len(ids),ids)
            if best is None or cand<best:
                best=cand; best_sel=chosen
            return
        if best is not None and cost>best[0]:
            return
        key=frozenset(uncovered)
        prev=memo.get(key)
        if prev is not None and cost>prev:
            return
        if prev is None or cost<prev:
            memo[key]=cost

        # Pick the hardest uncovered requirement first.
        r=min(uncovered,key=lambda x:(len(by_req[x]),x))
        for i in by_req[r]:
            if i in chosen:
                continue
            o=obs[i]
            new_uncovered=uncovered-o["covers"]
            new_cost=cost+o["cost"]
            if best is not None and new_cost>best[0]:
                continue
            recurse(new_uncovered,tuple(sorted(chosen+(i,))),new_cost)

    recurse(set(remaining),(),Decimal("0"))
    if best is None:
        raise RuntimeError("exact search found no cover despite validated union")
    return {
      "schema":"PROJECT_BRAIN_MINIMUM_REALITY_CUT_V2",
      "status":"EXACT_MINIMUM",
      "exact_minimum":True,
      "selected_observations":list(best[2]),
      "observation_count":best[1],
      "total_cost":float(best[0]),
      "unresolved_requirements":sorted(remaining),
      "candidate_observations_after_dominance":len(obs),
      "rule":"MIN_COST__THEN_MIN_OBSERVATION_COUNT__THEN_LEXICOGRAPHIC_ID"
    }


def self_test():
    r=solve({
      "requirements":["A","B","C","D"],
      "already_resolved":[],
      "observations":[
        {"id":"ab","covers":["A","B"],"cost":1},
        {"id":"bc","covers":["B","C"],"cost":1},
        {"id":"cd","covers":["C","D"],"cost":1},
        {"id":"a","covers":["A"],"cost":1},
        {"id":"d","covers":["D"],"cost":1}
      ]
    })
    assert r["exact_minimum"] is True
    assert r["total_cost"]==2.0
    assert r["selected_observations"]==["ab","cd"],r


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("input",type=Path,nargs="?")
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        self_test(); print(json.dumps({"status":"SELF_TEST_PASS"})); return 0
    if args.input is None:
        ap.error("input required")
    out=solve(json.loads(args.input.read_text(encoding="utf-8")))
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("exact_minimum") is True else 1

if __name__=="__main__":
    raise SystemExit(main())
