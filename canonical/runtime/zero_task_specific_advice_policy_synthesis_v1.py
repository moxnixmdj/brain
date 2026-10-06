from __future__ import annotations

def synthesize_finite(policies, adequate):
    if not policies:
        raise ValueError("EMPTY_POLICY_UNIVERSE")
    for p in policies:
        if adequate(p):
            return p
    raise LookupError("NO_CERTIFIED_ADEQUATE_POLICY")

def finite_theorem(policies, adequate, witness):
    assert witness in policies
    assert adequate(witness) is True
    found=synthesize_finite(policies, adequate)
    assert adequate(found) is True
    return found

def finite_counterexample_resource_bound(policies, adequate, witness, max_checks):
    checks=0
    for p in policies:
        checks+=1
        if checks>max_checks:
            return {"status":"RESOURCE_BOUND_BLOCKS_GENERIC_SEARCH","checks":checks-1}
        if adequate(p):
            return {"status":"FOUND","policy":p,"checks":checks}
    return {"status":"NO_POLICY","checks":checks}
