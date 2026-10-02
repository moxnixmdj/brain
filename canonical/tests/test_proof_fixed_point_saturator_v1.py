from canonical.runtime.proof_fixed_point_saturator_v1 import evaluate

ir = {
    "status": "PASS",
    "predicates": [
        {"id": "A", "state": "PROVED"},
        {"id": "B", "state": "OPEN"},
        {"id": "C", "state": "BLOCKED"},
        {"id": "D", "state": "OPEN"},
    ],
    "families": [
        {"family": "F1", "required_predicates": ["A", "B", "C"]},
        {"family": "F2", "required_predicates": ["D"]},
    ],
}

rules = [
    {
        "id": "r1",
        "requires": ["A"],
        "proves": ["B"],
        "receipt": "receipt://r1",
        "verified": True,
        "independent": True,
        "contamination_clean": True,
        "scope_complete": True,
    },
    {
        "id": "r2",
        "requires": ["B"],
        "proves": ["C"],
        "receipt": "receipt://r2",
        "verified": True,
        "independent": True,
        "contamination_clean": True,
        "scope_complete": True,
    },
]

r = evaluate(ir, rules)
assert r["status"] == "FIXED_POINT_REACHED", r
assert r["newly_proved_predicates"] == ["B", "C"], r
assert r["unresolved_predicates"] == ["D"], r
assert r["iterations"] == 2, r
assert r["closed_residual_family_count"] == 1, r
assert [x["deduction_id"] for x in r["trace"]] == ["r1", "r2"], r

bad = [dict(rules[0], independent=False)]
r2 = evaluate(ir, bad)
assert r2["status"] == "FAIL_CLOSED", r2

print("test_proof_fixed_point_saturator_v1: PASS")
