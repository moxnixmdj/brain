from functools import lru_cache

class AdaptiveK6Error(ValueError): pass

def compile_adaptive(*,worlds,adequate,discriminators,commitment_deadline):
    worlds=tuple(map(str,worlds))
    if not worlds or len(set(worlds))!=len(worlds): raise AdaptiveK6Error("WORLD_DOMAIN_INVALID")
    A={}
    for w in worlds:
        if w not in adequate: raise AdaptiveK6Error("ADEQUATE_SET_MISSING:"+w)
        A[w]=set(map(str,adequate[w]))
        if not A[w]: raise AdaptiveK6Error("NO_ADEQUATE_POLICY:"+w)

    D={}
    for raw in discriminators:
        i=str(raw.get("id") or "")
        if not i or i in D: raise AdaptiveK6Error("DISCRIMINATOR_ID_INVALID")
        obs=raw.get("observations")
        if not isinstance(obs,dict) or any(w not in obs for w in worlds):
            raise AdaptiveK6Error("OBSERVATIONS_INCOMPLETE:"+i)
        cost=float(raw.get("cost",0))
        if cost<0: raise AdaptiveK6Error("NEGATIVE_COST:"+i)
        if raw.get("authorized") is True and raw.get("owned_operator") is True and float(raw.get("arrival",0))<=float(commitment_deadline):
            D[i]=(cost,{w:repr(obs[w]) for w in worlds})

    def common(cell):
        s=set(A[cell[0]])
        for w in cell[1:]: s&=A[w]
        return s

    @lru_cache(None)
    def solve(cell,remaining):
        C=common(cell)
        if C:
            return (0.0,{"type":"policy","worlds":list(cell),"policy":sorted(C)[0]})
        best=None
        for i in remaining:
            cost,obs=D[i]
            groups={}
            for w in cell: groups.setdefault(obs[w],[]).append(w)
            if len(groups)<2: continue
            rem=tuple(x for x in remaining if x!=i)
            children={}; vals=[]; bad=False
            for sig,g in sorted(groups.items()):
                z=solve(tuple(sorted(g)),rem)
                if z is None: bad=True; break
                vals.append(z[0]); children[sig]=z[1]
            if bad: continue
            total=cost+max(vals)
            cand=(total,i,{"type":"probe","id":i,"cost":cost,"worlds":list(cell),"children":children})
            if best is None or (cand[0],cand[1])<(best[0],best[1]): best=cand
        return None if best is None else (best[0],best[2])

    out=solve(tuple(sorted(worlds)),tuple(sorted(D)))
    if out is None:
        return {"status":"NONIDENTIFIABLE_WITH_ADMISSIBLE_ADAPTIVE_INFORMATION","terminal_credit_delta":0}
    return {"status":"SUFFICIENT_ADAPTIVE_REFINEMENT_FOUND","worst_case_cost":out[0],"tree":out[1],"terminal_credit_delta":0}
