from __future__ import annotations

from canonical.runtime import dominance_binding_v2 as bind
from canonical.runtime.dominance_sufficiency_v2 import (
    INPUT_SCHEMA,
    compile_dominance_sufficiency_v2,
)

SHA = "a" * 40
TARGET = "b" * 64
METRIC = "terminal_success"


def cb(path="canonical/x.json"):
    return {"path": path, "git_blob_sha": SHA}


def doc(brain_h2="0.9"):
    live = ["h1", "h2"]
    live_sha = bind.live_digest(live)
    return {
        "schema": INPUT_SCHEMA,
        "target_contract_sha256": TARGET,
        "metric_id": METRIC,
        "target_contract_receipt": {
            **cb("canonical/target.json"),
            "target_contract_sha256": TARGET,
            "metric_id": METRIC,
            "load_bearing_dimensions_complete": True,
            "acceptance_relation_sound": True,
            "independent_or_objective": True,
        },
        "hypothesis_coverage_receipt": {
            **cb("canonical/coverage.json"),
            "target_contract_sha256": TARGET,
            "metric_id": METRIC,
            "live_hypothesis_set_sha256": live_sha,
            "scope_complete": True,
            "independent_or_objective": True,
        },
        "hypotheses": [
            {"id": "h1", "plausible": True},
            {"id": "h2", "plausible": True},
        ],
        "configurations": [
            {
                "id": "A",
                "brain_owned": True,
                "ownership_receipt": {
                    **cb("canonical/ownership.json"),
                    "configuration_id": "A",
                    "target_contract_sha256": TARGET,
                    "donor_independent": True,
                    "independent_or_objective": True,
                },
                "bounds": {
                    "h1": {
                        "brain_lower": "1.0",
                        "comparator_upper": "0.8",
                        "bound_receipt": {
                            **cb("canonical/h1.json"),
                            "configuration_id": "A",
                            "hypothesis_id": "h1",
                            "target_contract_sha256": TARGET,
                            "metric_id": METRIC,
                            "brain_lower": "1.0",
                            "comparator_upper": "0.8",
                            "evaluator_relation_proved": True,
                            "scope_complete": True,
                            "independent_or_objective": True,
                        },
                    },
                    "h2": {
                        "brain_lower": brain_h2,
                        "comparator_upper": "0.8",
                        "bound_receipt": {
                            **cb("canonical/h2.json"),
                            "configuration_id": "A",
                            "hypothesis_id": "h2",
                            "target_contract_sha256": TARGET,
                            "metric_id": METRIC,
                            "brain_lower": brain_h2,
                            "comparator_upper": "0.8",
                            "evaluator_relation_proved": True,
                            "scope_complete": True,
                            "independent_or_objective": True,
                        },
                    },
                },
            }
        ],
    }


def test_exactly_bound_robust_witness_passes_without_execution_authority():
    out = compile_dominance_sufficiency_v2(doc())
    assert out["status"] == "PASS__EXACTLY_BOUND_DOMINANCE_SUFFICIENT"
    assert out["selected_configuration"] == "A"
    assert out["worst_case_margin"] == "0.1"
    assert out["execution_authority"] is False
    assert out["certificate_only"] is True


def test_negative_margin_is_open_not_false_pass():
    out = compile_dominance_sufficiency_v2(doc(brain_h2="0.7"))
    assert out["status"] == "OPEN__NO_EXACTLY_BOUND_ROBUST_WITNESS"
    assert out["selected_configuration"] is None


def test_wrong_live_set_receipt_is_rejected():
    x = doc()
    x["hypothesis_coverage_receipt"]["live_hypothesis_set_sha256"] = "c" * 64
    out = compile_dominance_sufficiency_v2(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "LIVE_HYPOTHESIS_SET_SHA256_MISMATCH" in out["errors"][0]


def test_unrelated_ownership_receipt_is_rejected():
    x = doc()
    x["configurations"][0]["ownership_receipt"]["configuration_id"] = "B"
    out = compile_dominance_sufficiency_v2(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "CONFIGURATION_ID_MISMATCH" in out["errors"][0]


def test_bound_receipt_value_substitution_is_rejected():
    x = doc()
    x["configurations"][0]["bounds"]["h2"]["bound_receipt"]["brain_lower"] = "1.0"
    out = compile_dominance_sufficiency_v2(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "BRAIN_LOWER_MISMATCH" in out["errors"][0]


def test_bound_receipt_metric_substitution_is_rejected():
    x = doc()
    x["configurations"][0]["bounds"]["h1"]["bound_receipt"]["metric_id"] = "other"
    out = compile_dominance_sufficiency_v2(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "METRIC_ID_MISMATCH" in out["errors"][0]


def test_missing_evaluator_relation_is_rejected():
    x = doc()
    x["configurations"][0]["bounds"]["h1"]["bound_receipt"]["evaluator_relation_proved"] = False
    out = compile_dominance_sufficiency_v2(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "EVALUATOR_RELATION_PROVED_NOT_TRUE" in out["errors"][0]


def test_incomplete_target_contract_is_rejected():
    x = doc()
    x["target_contract_receipt"]["load_bearing_dimensions_complete"] = False
    out = compile_dominance_sufficiency_v2(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "LOAD_BEARING_DIMENSIONS_COMPLETE_NOT_TRUE" in out["errors"][0]


def test_donor_dependent_witness_is_rejected():
    x = doc()
    x["configurations"][0]["ownership_receipt"]["donor_independent"] = False
    out = compile_dominance_sufficiency_v2(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "DONOR_INDEPENDENT_NOT_TRUE" in out["errors"][0]


def test_target_contract_substitution_is_rejected():
    x = doc()
    x["configurations"][0]["bounds"]["h1"]["bound_receipt"]["target_contract_sha256"] = "c" * 64
    out = compile_dominance_sufficiency_v2(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "TARGET_CONTRACT_SHA256_MISMATCH" in out["errors"][0]
