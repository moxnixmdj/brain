from __future__ import annotations

from canonical.runtime import dominance_binding_v2 as bind
from canonical.runtime.dominance_first_learning_router_v2 import route
from canonical.runtime.dominance_sufficiency_v2 import INPUT_SCHEMA

SHA = "a" * 40
TARGET = "b" * 64
METRIC = "terminal_success"


def cb(path):
    return {"path": path, "git_blob_sha": SHA}


def dominance(brain_h2="0.9", complete=True):
    live = ["h1", "h2"]
    return {
        "schema": INPUT_SCHEMA,
        "target_contract_sha256": TARGET,
        "metric_id": METRIC,
        "target_contract_receipt": {
            **cb("canonical/target.json"),
            "target_contract_sha256": TARGET,
            "metric_id": METRIC,
            "load_bearing_dimensions_complete": complete,
            "acceptance_relation_sound": True,
            "independent_or_objective": True,
        },
        "hypothesis_coverage_receipt": {
            **cb("canonical/coverage.json"),
            "target_contract_sha256": TARGET,
            "metric_id": METRIC,
            "live_hypothesis_set_sha256": bind.live_digest(live),
            "scope_complete": True,
            "independent_or_objective": True,
        },
        "hypotheses": [
            {"id": "h1", "plausible": True},
            {"id": "h2", "plausible": True},
        ],
        "configurations": [
            {
                "id": "ROBUST",
                "brain_owned": True,
                "ownership_receipt": {
                    **cb("canonical/own.json"),
                    "configuration_id": "ROBUST",
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
                            "configuration_id": "ROBUST",
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
                            "configuration_id": "ROBUST",
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


def router_args():
    return {
        "goal": "x",
        "verified_coverage": False,
        "required_facts": {"x"},
        "verified_facts": set(),
        "transfer_mappings": [],
        "hypotheses": [
            {"id": "h1", "plausible": True, "best_action": "A", "probability": "1/2"},
            {"id": "h2", "plausible": True, "best_action": "B", "probability": "1/2"},
        ],
        "actions": [
            {
                "id": "probe",
                "safe": True,
                "outcome_by_hypothesis": {"h1": "left", "h2": "right"},
                "time": 1,
            }
        ],
    }


def test_dominance_certificate_stops_probe_but_does_not_authorize_execution():
    out = route(**router_args(), dominance_certificate=dominance())
    assert out["route"] == "DOMINANCE_SUFFICIENT_CERTIFICATE"
    assert out["recommended_action"] == "ROBUST"
    assert out["next_action"] is None
    assert out["trusted_execution_authorized"] is False
    assert out["certificate_only"] is True


def test_open_dominance_falls_back_to_v3_probe():
    out = route(**router_args(), dominance_certificate=dominance(brain_h2="0.7"))
    assert out["route"] == "LEARN"
    assert out["next_action"]["id"] == "probe"
    assert out["trusted_execution_authorized"] is False


def test_invalid_dominance_binding_fails_closed_not_fallback():
    out = route(**router_args(), dominance_certificate=dominance(complete=False))
    assert out["route"] == "FAIL_CLOSED__DOMINANCE_CERTIFICATE_INVALID"
    assert out["recommended_action"] is None
    assert out["next_action"] is None


def test_no_certificate_preserves_v3_route():
    out = route(**router_args(), dominance_certificate=None)
    assert out["route"] == "LEARN"
    assert out["next_action"]["id"] == "probe"


def test_existing_v3_same_action_sufficiency_remains_available_when_dominance_open():
    args = router_args()
    args["hypotheses"] = [
        {"id": "h1", "plausible": True, "best_action": "STOP", "probability": "1/2"},
        {"id": "h2", "plausible": True, "best_action": "STOP", "probability": "1/2"},
    ]
    out = route(**args, dominance_certificate=dominance(brain_h2="0.7"))
    assert out["route"] == "DECISION_SUFFICIENT_UNVERIFIED_MODEL"
    assert out["recommended_action"] == "STOP"
    assert out["trusted_execution_authorized"] is False
