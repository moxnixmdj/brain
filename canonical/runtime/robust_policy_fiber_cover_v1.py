from __future__ import annotations

def fiber_cover(worlds, policies, adequate, fibers):
    W=set(worlds); P=set(policies)
    used=set()
    for name, members in fibers.items():
        F=set(members)
        if not F <= W:
            return {"pass":False,"reason":"FIBER_OUTSIDE_WORLD_SET","terminal_credit_delta":0}
        robust=[p for p in P if all((w,p) in adequate for w in F)]
        if not robust:
            return {"pass":False,"reason":"NO_COMMON_ADEQUATE_POLICY:"+name,"terminal_credit_delta":0}
        used.add(sorted(robust)[0])
    return {"pass":True,"selected_policy_count":len(used),"terminal_credit_delta":0}

def common_policy(worlds, policies, adequate):
    W=set(worlds)
    return sorted(p for p in policies if all((w,p) in adequate for w in W))

def verifier_bypass(*, pass_implies_adequate, portfolio_guaranteed_pass, owned, resource_safe):
    ok=all([pass_implies_adequate,portfolio_guaranteed_pass,owned,resource_safe])
    return {"pass":ok,"semantic_discriminator_required":False if ok else None,"terminal_credit_delta":0}
