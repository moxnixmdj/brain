from __future__ import annotations

from canonical.runtime.dominance_first_learning_router_v1 import route
from canonical.runtime.dominance_sufficiency_v1 import INPUT_SCHEMA


SHA = "a" * 40


def receipt(**flags):
    return {"path": "canonical/x.json", "git_blob_sha": SHA, **flags}


def dominance_doc(*, brain_h2="0.9", owned=True, scope_complete=True):
    return {
        "schema": INPUT_SCHEMA,
        "hypothesis_coverage_receipt": receipt(
            scope_complete=scope_complete,
            independent_or_objective=True,
        ),
        "hypotheses": [
            {"id": "h1", "plausible": True},
            {"id": "h2", "plausible": True},
        ],
        "configurations": [
            {
                "id": "ROBUST",
                "brain_owned": owned,
                "ownership_receipt": receipt(
                    donor_independent=True,
                    independent_or_objective=True,
                ),
                "bounds": {
                    "h1": {
                        "brain_lower": "1.0",
                        "comparator_upper": "0.8",
                        "bound_receipt": receipt(
                            scope_complete=True,
                            independent_or_objective=True,
                        ),
                    },
                    "h2": {
                        "brain_lower": brain_h2,
                        "comparator_upper": "0.8",
                        "bound_receipt": receipt(
                            scope_complete=True,
                            independent_or_objective=True,
                        ),
                    },
                },
            }
        ],
    }


def common_router_args():
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


def test_robust_dominance_stops_before_v3_discriminator():
    out = route(**common_router_args(), dominance_certificate=dominance_doc())
    assert out["route"] == "DOMINANCE_SUFFICIENT"
    assert out["recommended_action"] == "ROBUST"
    assert out["next_action"] is None
    assert out["trusted_execution_authorized"] is True
    assert out["dominance"]["additional_target_information_required_by_this_certificate"] is False


def test_open_dominance_falls_back_to_existing_v3_learning():
    out = route(
        **common_router_args(),
        dominance_certificate=dominance_doc(brain_h2="0.7"),
    )
    assert out["route"] == "LEARN"
    assert out["next_action"]["id"] == "probe"
    assert out["fallback_v3"]["route"] == "LEARN"
    assert out["dominance"]["status"].startswith("OPEN__")


def test_malformed_dominance_certificate_fails_closed_instead_of_being_ignored():
    out = route(
        **common_router_args(),
        dominance_certificate=dominance_doc(scope_complete=False),
    )
    assert out["route"] == "FAIL_CLOSED__DOMINANCE_CERTIFICATE_INVALID"
    assert out["trusted_execution_authorized"] is False
    assert out["recommended_action"] is None
    assert out["next_action"] is None


def test_absent_dominance_certificate_preserves_v3_behavior():
    out = route(**common_router_args(), dominance_certificate=None)
    assert out["route"] == "LEARN"
    assert out["next_action"]["id"] == "probe"
    assert out["dominance"] is None


def test_nonowned_robust_candidate_does_not_short_circuit_v3():
    out = route(
        **common_router_args(),
        dominance_certificate=dominance_doc(owned=False),
    )
    assert out["route"] == "LEARN"
    assert out["dominance"]["status"].startswith("OPEN__")


def test_v3_decision_sufficiency_still_operates_when_dominance_is_open():
    args = common_router_args()
    args["hypotheses"] = [
        {"id": "h1", "plausible": True, "best_action": "STOP", "probability": "1/2"},
        {"id": "h2", "plausible": True, "best_action": "STOP", "probability": "1/2"},
    ]
    out = route(
        **args,
        dominance_certificate=dominance_doc(brain_h2="0.7"),
    )
    assert out["route"] == "DECISION_SUFFICIENT_UNVERIFIED_MODEL"
    assert out["recommended_action"] == "STOP"
    assert out["next_action"] is None
