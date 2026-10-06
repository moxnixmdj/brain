from __future__ import annotations
from itertools import combinations
from typing import Any, Mapping, Sequence
from canonical.runtime.k6_minimum_adequate_policy_cover_v1 import (
    minimum_policy_cover, minimum_fixed_length_bits
)

class PolicyIndexCompilerError(ValueError):
    pass

def _admissible(worlds, discriminators, deadline):
    out=[]; seen=set()
    for d in discriminators:
        did=str(d.get("id") or "")
        if not did or did in seen:
            raise PolicyIndexCompilerError("DISCRIMINATOR_ID_INVALID_OR_DUPLICATE")
        seen.add(did)
        obs=d.get("observations")
        if not isinstance(obs,Mapping) or any(w not in obs for w in worlds):
            raise PolicyIndexCompilerError("DISCRIMINATOR_OBSERVATIONS_INCOMPLETE:"+did)
        cost=float(d.get("cost",0))
        arrival=float(d.get("arrival",0))
        if cost<0: raise PolicyIndexCompilerError("NEGATIVE_COST:"+did)
        if d.get("authorized") is True and d.get("owned_operator") is True and arrival<=deadline:
            out.append({"id":did,"observations":dict(obs),"cost":cost,"arrival":arrival})
    return sorted(out,key=lambda x:x["id"])

def _cells(worlds, selected):
    groups={}
    for w in worlds:
        sig=tuple((d["id"],repr(d["observations"][w])) for d in selected)
        groups.setdefault(sig,[]).append(w)
    return [tuple(v) for _,v in sorted(groups.items(),key=lambda kv:repr(kv[0]))]

def _common_policy(cell, adequate):
    it=iter(cell)
    first=next(it)
    common=set(adequate[first])
    for w in it:
        common.intersection_update(adequate[w])
    return common

def compile_policy_index(
    *,
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    discriminators: Sequence[Mapping[str,Any]],
    commitment_deadline: float,
    separator_reacquirable_after_restart_before_deadline: bool,
) -> dict[str,Any]:
    ws=tuple(str(w) for w in worlds)
    ps=tuple(str(p) for p in policies)
    if not ws or len(set(ws))!=len(ws): raise PolicyIndexCompilerError("WORLD_DOMAIN_INVALID")
    if not ps or len(set(ps))!=len(ps): raise PolicyIndexCompilerError("POLICY_DOMAIN_INVALID")
    pset=set(ps)
    aset={}
    for w in ws:
        if w not in adequate: raise PolicyIndexCompilerError("ADEQUATE_SET_MISSING:"+w)
        s=set(str(p) for p in adequate[w])
        if not s: raise PolicyIndexCompilerError("NO_ADEQUATE_POLICY:"+w)
        if not s<=pset: raise PolicyIndexCompilerError("UNKNOWN_POLICY_IN_ADEQUATE_SET:"+w)
        aset[w]=s

    cover=minimum_policy_cover(ws,ps,{w:tuple(aset[w]) for w in ws})
    tau=len(cover)
    label_bits=minimum_fixed_length_bits(tau)
    persistent_bits=0 if separator_reacquirable_after_restart_before_deadline else label_bits
    ds=_admissible(ws,discriminators,float(commitment_deadline))

    candidates=[]
    for r in range(len(ds)+1):
        for combo in combinations(ds,r):
            cells=_cells(ws,combo)
            commons=[_common_policy(c,aset) for c in cells]
            if all(commons):
                cost=sum(d["cost"] for d in combo)
                candidates.append((cost,len(combo),tuple(d["id"] for d in combo),combo,cells,commons))
    if not candidates:
        cells=_cells(ws,ds)
        bad=[list(c) for c in cells if not _common_policy(c,aset)]
        return {
          "status":"NONIDENTIFIABLE_WITH_ADMISSIBLE_PRECOMMITMENT_INFORMATION",
          "policy_cover":list(cover),
          "tau":tau,
          "minimum_policy_index_bits":label_bits,
          "persistent_policy_index_bits_lower_bound":persistent_bits,
          "witness_cells":bad,
          "terminal_credit_delta":0,
        }

    candidates.sort(key=lambda x:(x[0],x[1],x[2]))
    cost,_,ids,combo,cells,commons=candidates[0]
    decisions=[]
    for cell,common in zip(cells,commons):
        preferred=[p for p in cover if p in common]
        policy=preferred[0] if preferred else sorted(common)[0]
        decisions.append({"worlds":list(cell),"policy":policy,"common_adequate_policies":sorted(common)})
    return {
      "status":"SUFFICIENT_POLICY_INDEX_PARTITION_FOUND",
      "policy_cover":list(cover),
      "tau":tau,
      "minimum_policy_index_bits":label_bits,
      "selected_discriminators":list(ids),
      "total_discriminator_cost":cost,
      "cells":[list(c) for c in cells],
      "decisions":decisions,
      "separator_reacquirable_after_restart_before_deadline":bool(separator_reacquirable_after_restart_before_deadline),
      "persistent_policy_index_bits_lower_bound":persistent_bits,
      "terminal_credit_delta":0,
    }
