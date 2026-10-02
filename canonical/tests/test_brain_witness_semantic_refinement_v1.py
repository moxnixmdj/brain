from canonical.runtime.brain_witness_semantic_refinement_v1 import evaluate as normalize
from canonical.runtime.protocol_implication_scope_algebra_v1 import evaluate as imply

TARGET = {
    "predicate_id": "MATCHED_TEST",
    "required_atoms": ["dimension:recovery", "invariant:no_critical_miss"],
    "metric_requirements": [
        {"metric": "success_noninferiority", "direction": "higher", "threshold": 0}
    ],
}

BASE_CLAIM = {
    "scope_id": "FROZEN_SCOPE",
    "receipt": "receipt://behavior",
    "semantic_binding_receipt": "receipt://semantic-binding",
    "verified": True,
    "independent": True,
    "contamination_clean": True,
    "source_traceable": True,
    "acceptance_scoped": True,
    "semantic_binding_verified": True,
}

BASE_METRIC = {
    "scope_id": "FROZEN_SCOPE",
    "receipt": "receipt://metric",
    "semantic_binding_receipt": "receipt://metric-binding",
    "verified": True,
    "independent": True,
    "contamination_clean": True,
    "source_traceable": True,
    "acceptance_scoped": True,
    "semantic_binding_verified": True,
}

doc = {
    "scope_id": "FROZEN_SCOPE",
    "target": TARGET,
    "witness_claims": [
        {**BASE_CLAIM, "atom": "dimension:recovery"},
        {**BASE_CLAIM, "atom": "ceiling:no_critical_miss", "receipt": "receipt://ceiling", "semantic_binding_receipt": "receipt://ceiling-binding"},
    ],
    "metric_bounds": [
        {**BASE_METRIC, "metric": "success_noninferiority", "lower": 0.1},
    ],
}

r = normalize(doc)
assert r["status"] == "NORMALIZED_WITNESS_READY", r
assert r["direct_target_coverage"] is False, r
assert r["missing_atoms"] == ["invariant:no_critical_miss"], r
assert r["missing_metrics"] == [], r

algebra_doc = {
    "target": {
        "required_atoms": TARGET["required_atoms"],
        "metric_requirements": TARGET["metric_requirements"],
    },
    "witness": r["normalized_witness"],
    "verified_implications": [
        {
            "if_all": ["ceiling:no_critical_miss"],
            "then": ["invariant:no_critical_miss"],
            "receipt": "receipt://verified-implication",
            "verified": True,
        }
    ],
}
a = imply(algebra_doc)
assert a["status"] == "PASS" and a["implies_target"] is True, a

bad = normalize({
    **doc,
    "witness_claims": [
        {**BASE_CLAIM, "atom": "dimension:recovery", "semantic_binding_verified": False},
    ],
})
assert bad["status"] == "FAIL_CLOSED", bad

bad_scope = normalize({
    **doc,
    "witness_claims": [
        {**BASE_CLAIM, "atom": "dimension:recovery", "scope_id": "OTHER"},
    ],
})
assert bad_scope["status"] == "FAIL_CLOSED", bad_scope

bad_metric = normalize({
    **doc,
    "metric_bounds": [
        {**BASE_METRIC, "metric": "success_noninferiority", "lower": 1.0, "upper": 0.0},
    ],
})
assert bad_metric["status"] == "FAIL_CLOSED", bad_metric

print("test_brain_witness_semantic_refinement_v1: PASS")
