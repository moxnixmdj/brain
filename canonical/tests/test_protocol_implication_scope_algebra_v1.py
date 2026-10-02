from canonical.runtime.protocol_implication_scope_algebra_v1 import evaluate

doc = {
    "target": {
        "required_atoms": ["scope:A", "invariant:no_critical_failure"],
        "metric_requirements": [{"metric": "success_rate", "direction": "higher", "threshold": 0.8}],
    },
    "witness": {
        "verified": True,
        "independent": True,
        "contamination_clean": True,
        "proved_atoms": ["scope:A", "ceiling:no_failure"],
        "metric_bounds": {"success_rate": {"lower": 1.0}},
    },
    "verified_implications": [
        {
            "if_all": ["ceiling:no_failure"],
            "then": ["invariant:no_critical_failure"],
            "receipt": "receipt://floor",
            "verified": True,
        }
    ],
}
r = evaluate(doc)
assert r["status"] == "PASS" and r["implies_target"] is True, r
assert r["candidate_scope_relation"] == "PROVEN_STRONGER", r

r = evaluate({**doc, "witness": {**doc["witness"], "metric_bounds": {"success_rate": {"lower": 0.7}}}})
assert r["status"] == "TARGET_NOT_IMPLIED" and r["implies_target"] is False, r

r = evaluate({**doc, "verified_implications": [{**doc["verified_implications"][0], "verified": False}]})
assert r["status"] == "FAIL_CLOSED", r

print("test_protocol_implication_scope_algebra_v1: PASS")
