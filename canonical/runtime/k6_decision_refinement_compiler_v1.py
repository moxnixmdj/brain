from __future__ import annotations
from itertools import combinations
from typing import Any, Hashable, Mapping, Sequence

class RefinementCompilerError(ValueError):
    pass

def _worlds(worlds: Sequence[Hashable]) -> tuple[Hashable,...]:
    w=tuple(worlds)
    if not w or len(set(w))!=len(w):
        raise RefinementCompilerError("WORLDS_MUST_BE_NONEMPTY_UNIQUE")
    return w

def _acceptable(worlds, acceptable: Mapping[Hashable, Sequence[Hashable]]) -> dict[Hashable,set[Hashable]]:
    out={}
    for w in worlds:
        if w not in acceptable:
            raise RefinementCompilerError("ACCEPTABLE_ACTIONS_MISSING:"+repr(w))
        s=set(acceptable[w])
        if not s:
            raise RefinementCompilerError("WORLD_HAS_NO_TARGET_ACCEPTABLE_ACTION:"+repr(w))
        out[w]=s
    return out

def _admissible_discriminators(worlds, discriminators: Sequence[Mapping[str,Any]], deadline: float):
    out=[]
    seen=set()
    for d in discriminators:
        did=str(d.get("id") or "")
        if not did or did in seen:
            raise RefinementCompilerError("DISCRIMINATOR_ID_INVALID_OR_DUPLICATE")
        seen.add(did)
        obs=d.get("observations")
        if not isinstance(obs,Mapping) or any(w not in obs for w in worlds):
            raise RefinementCompilerError("DISCRIMINATOR_OBSERVATIONS_INCOMPLETE:"+did)
        cost=float(d.get("cost",0.0))
        arrival=float(d.get("arrival",0.0))
        if cost < 0:
            raise RefinementCompilerError("NEGATIVE_COST:"+did)
        if d.get("authorized") is True and d.get("owned_operator") is True and arrival <= deadline:
            out.append({"id":did,"observations":dict(obs),"cost":cost,"arrival":arrival})
    return sorted(out,key=lambda x:x["id"])

def _cells(worlds, selected):
    groups={}
    for w in worlds:
        sig=tuple((d["id"],repr(d["observations"][w])) for d in selected)
        groups.setdefault(sig,[]).append(w)
    return [tuple(v) for _,v in sorted(groups.items(),key=lambda kv:repr(kv[0]))]

def _common(cell, acceptable):
    it=iter(cell)
    first=next(it)
    s=set(acceptable[first])
    for w in it:
        s.intersection_update(acceptable[w])
    return s

def compile_refinement(
    *,
    worlds: Sequence[Hashable],
    acceptable_actions: Mapping[Hashable, Sequence[Hashable]],
    discriminators: Sequence[Mapping[str,Any]],
    commitment_deadline: float,
) -> dict[str,Any]:
    w=_worlds(worlds)
    a=_acceptable(w,acceptable_actions)
    ds=_admissible_discriminators(w,discriminators,float(commitment_deadline))
    candidates=[]
    for r in range(len(ds)+1):
        for combo in combinations(ds,r):
            cells=_cells(w,combo)
            commons=[_common(c,a) for c in cells]
            if all(commons):
                total=sum(d["cost"] for d in combo)
                candidates.append((total,len(combo),tuple(d["id"] for d in combo),combo,cells,commons))
    if not candidates:
        # Strongest fail-closed witness available under all admissible discriminators.
        cells=_cells(w,ds)
        bad=[c for c in cells if not _common(c,a)]
        return {
            "status":"NONIDENTIFIABLE_WITH_ADMISSIBLE_PRECOMMITMENT_INFORMATION",
            "selected_discriminators":[d["id"] for d in ds],
            "witness_cells":[list(c) for c in bad],
            "terminal_credit_delta":0,
        }
    candidates.sort(key=lambda x:(x[0],x[1],x[2]))
    total,_,ids,combo,cells,commons=candidates[0]
    policy=[]
    for cell,common in zip(cells,commons):
        action=sorted(common,key=repr)[0]
        policy.append({"worlds":list(cell),"action":action,"common_acceptable_actions":sorted(common,key=repr)})
    return {
        "status":"SUFFICIENT_DECISION_PARTITION_FOUND",
        "selected_discriminators":list(ids),
        "total_cost":total,
        "cells":[list(c) for c in cells],
        "policy":policy,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    import json
    demo=compile_refinement(
      worlds=["w0","w1"],
      acceptable_actions={"w0":["a0"],"w1":["a1"]},
      discriminators=[{"id":"bit","observations":{"w0":0,"w1":1},"cost":1,"arrival":0,"authorized":True,"owned_operator":True}],
      commitment_deadline=0,
    )
    print(json.dumps(demo,sort_keys=True))
