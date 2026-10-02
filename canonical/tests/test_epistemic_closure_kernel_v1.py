from canonical.runtime.epistemic_closure_kernel_v1 import evaluate

base = {
    "worlds": [
        {"id": "w1", "decision": "ALLOW", "facts": {"license": "valid", "country": "A"}},
        {"id": "w2", "decision": "DENY",  "facts": {"license": "invalid", "country": "A"}},
        {"id": "w3", "decision": "ALLOW", "facts": {"license": "valid", "country": "B"}},
    ],
    "queryable_facts": [
        {"fact": "license", "cost": 1, "authorized": True, "available": True},
        {"fact": "country", "cost": 5, "authorized": True, "available": True},
    ],
}

r = evaluate(base)
assert r["status"] == "QUERY_MINIMUM_DISCRIMINATOR", r
assert r["minimum_discriminator_facts"] == ["license"], r

r = evaluate({**base, "observed_facts": {"license": "valid"}})
assert r["status"] == "DECIDE" and r["decision"] == "ALLOW", r

r = evaluate({
    "worlds": [
        {"id": "a", "decision": "X", "facts": {"visible": 1}},
        {"id": "b", "decision": "Y", "facts": {"visible": 1}},
    ],
    "queryable_facts": [{"fact": "visible", "cost": 1}],
})
assert r["status"] == "ABSTAIN_NONIDENTIFIABLE", r

r = evaluate({
    "worlds": [
        {"id": "a", "decision": "X", "facts": {"p": 0, "q": 0, "r": 0}},
        {"id": "b", "decision": "Y", "facts": {"p": 1, "q": 0, "r": 1}},
        {"id": "c", "decision": "Y", "facts": {"p": 0, "q": 1, "r": 1}},
    ],
    "queryable_facts": [
        {"fact": "p", "cost": 1},
        {"fact": "q", "cost": 1},
        {"fact": "r", "cost": 3},
    ],
})
assert r["status"] == "QUERY_MINIMUM_DISCRIMINATOR", r
assert r["minimum_discriminator_facts"] == ["p", "q"], r
assert r["minimum_discriminator_total_cost"] == 2, r

r = evaluate({**base, "observed_facts": {"license": "impossible"}})
assert r["status"] == "FAIL_CLOSED", r

print("test_epistemic_closure_kernel_v1: PASS")
