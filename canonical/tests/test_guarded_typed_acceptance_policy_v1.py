from canonical.runtime.guarded_typed_acceptance_policy_v1 import assess
from canonical.runtime.independent_acceptance_model import assess as assess_base


def complete_model(kind="artifact"):
    obligations = {
        "artifact": ["existence", "schema", "roundtrip_or_parse"],
        "aggregate": [
            "component_omission",
            "component_mapping",
            "weight_or_factor",
            "correlation_or_interaction",
            "unit_or_scale",
            "aggregation_formula",
        ],
    }[kind]
    return {
        "requirements": [{
            "id": "R",
            "critical": True,
            "transform_kinds": [kind],
            "builder_dependencies": ["raw:source", "builder:logic"],
        }],
        "checks": [{
            "id": "C",
            "covers": ["R"],
            "provenance": "independent_oracle",
            "dependencies": ["raw:source", "oracle:logic"],
            "detects": obligations,
        }],
    }


def test_supported_complete_model_passes_both_gates():
    out = assess(complete_model("artifact"))
    assert out["pass"] is True, out
    assert out["structural_precondition"]["pass"] is True
    assert out["base_policy_executed"] is True
    assert out["base_result"]["pass"] is True


def test_supported_but_incomplete_acceptance_plan_fails_base_gate():
    m = complete_model("artifact")
    m["checks"][0]["detects"] = ["existence"]
    out = assess(m)
    assert out["pass"] is False
    assert out["structural_precondition"]["pass"] is True
    assert out["base_policy_executed"] is True
    assert out["base_result"]["pass"] is False


def test_unknown_transform_is_blocked_even_when_historical_base_gate_would_pass():
    m = {
        "requirements": [{
            "id": "R",
            "critical": True,
            "transform_kinds": ["UNKNOWN_TRANSFORM"],
            "builder_dependencies": ["raw:source"],
        }],
        "checks": [{
            "id": "C",
            "covers": ["R"],
            "provenance": "independent_oracle",
            "dependencies": ["raw:source"],
            "detects": [],
        }],
    }
    historical = assess_base(m)
    assert historical["pass"] is True
    out = assess(m)
    assert out["pass"] is False
    assert out["base_policy_executed"] is False
    assert out["structural_precondition"]["unknown_transform_kinds"] == ["UNKNOWN_TRANSFORM"]


def test_malformed_transform_collection_fails_before_base_policy():
    m = complete_model("artifact")
    m["requirements"][0]["transform_kinds"] = "artifact"
    out = assess(m)
    assert out["pass"] is False
    assert out["base_policy_executed"] is False


def test_explicit_failure_mode_only_requirement_remains_supported():
    m = {
        "requirements": [{
            "id": "R",
            "critical": True,
            "must_detect_failure_modes": ["custom_mode"],
            "builder_dependencies": ["raw:source"],
        }],
        "checks": [{
            "id": "C",
            "covers": ["R"],
            "provenance": "independent_oracle",
            "dependencies": ["raw:source"],
            "detects": ["custom_mode"],
        }],
    }
    out = assess(m)
    assert out["pass"] is True, out
    assert out["structural_precondition"]["observed_transform_kinds"] == []


def test_wrapper_never_claims_terminal_authority():
    out = assess(complete_model("aggregate"))
    assert out["pass"] is True
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
