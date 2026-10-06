from __future__ import annotations

import copy

from canonical.runtime import dominance_semantic_binding_v3 as sem
from canonical.runtime.dominance_first_learning_router_v3 import route
from canonical.runtime.dominance_sufficiency_v3 import (
    INPUT_SCHEMA,
    compile_dominance_sufficiency_v3,
)

SHA = "a" * 40
TARGET = "b" * 64
METRIC = "terminal_success"
H1 = "1" * 64
H2 = "2" * 64


def cb(path):
    return {"path": path, "git_blob_sha": SHA}


def dominance_doc(brain_h2="0.9"):
    worlds = [("h1", H1), ("h2", H2)]
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
            "live_world_set_sha256": sem.live_world_digest(worlds),
            "scope_complete": True,
            "independent_or_objective": True,
        },
        "hypotheses": [
            {
                "id": "h1",
                "plausible": True,
                "semantic_sha256": H1,
                "definition_receipt": {
                    **cb("canonical/h1-world.json"),
                    "hypothesis_id": "h1",
                    "semantic_sha256": H1,
                    "independent_or_objective": True,
                },
            },
            {
                "id": "h2",
                "plausible": True,
                "semantic_sha256": H2,
                "definition_receipt": {
                    **cb("canonical/h2-world.json"),
                    "hypothesis_id": "h2",
                    "semantic_sha256": H2,
                    "independent_or_objective": True,
                },
            },
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
                            **cb("canonical/h1-bound.json"),
                            "configuration_id": "ROBUST",
                            "hypothesis_id": "h1",
                            "hypothesis_semantic_sha256": H1,
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
                            **cb("canonical/h2-bound.json"),
                            "configuration_id": "ROBUST",
                            "hypothesis_id": "h2",
                            "hypothesis_semantic_sha256": H2,
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


def router_args(with_semantics=True):
    h1 = {"id": "h1", "plausible": True, "best_action": "A", "probability": "1/2"}
    h2 = {"id": "h2", "plausible": True, "best_action": "B", "probability": "1/2"}
    if with_semantics:
        h1["semantic_sha256"] = H1
        h2["semantic_sha256"] = H2
    return {
        "goal": "x",
        "verified_coverage": False,
        "required_facts": {"x"},
        "verified_facts": set(),
        "transfer_mappings": [],
        "hypotheses": [h1, h2],
        "actions": [
            {
                "id": "probe",
                "safe": True,
                "outcome_by_hypothesis": {"h1": "left", "h2": "right"},
                "time": 1,
            }
        ],
    }


def test_v3_semantically_bound_witness_passes_without_execution_authority():
    out = compile_dominance_sufficiency_v3(dominance_doc())
    assert out["status"] == "PASS__SEMANTICALLY_BOUND_DOMINANCE_SUFFICIENT"
    assert out["selected_configuration"] == "ROBUST"
    assert out["execution_authority"] is False


def test_bound_world_semantic_substitution_fails_closed():
    x = dominance_doc()
    x["configurations"][0]["bounds"]["h1"]["bound_receipt"]["hypothesis_semantic_sha256"] = H2
    out = compile_dominance_sufficiency_v3(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "HYPOTHESIS_SEMANTIC_SHA256_MISMATCH" in out["errors"][0]


def test_world_definition_receipt_substitution_fails_closed():
    x = dominance_doc()
    x["hypotheses"][0]["definition_receipt"]["semantic_sha256"] = H2
    out = compile_dominance_sufficiency_v3(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "SEMANTIC_SHA256_MISMATCH" in out["errors"][0]


def test_world_set_receipt_substitution_fails_closed():
    x = dominance_doc()
    x["hypothesis_coverage_receipt"]["live_world_set_sha256"] = "3" * 64
    out = compile_dominance_sufficiency_v3(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "LIVE_WORLD_SET_SHA256_MISMATCH" in out["errors"][0]


def test_router_shortcut_requires_same_semantic_world_set():
    x = dominance_doc()
    x["hypotheses"][1]["semantic_sha256"] = "4" * 64
    x["hypotheses"][1]["definition_receipt"]["semantic_sha256"] = "4" * 64
    x["configurations"][0]["bounds"]["h2"]["bound_receipt"]["hypothesis_semantic_sha256"] = "4" * 64
    worlds = [("h1", H1), ("h2", "4" * 64)]
    x["hypothesis_coverage_receipt"]["live_world_set_sha256"] = sem.live_world_digest(worlds)
    out = route(**router_args(), dominance_certificate=x)
    assert out["route"] == "FAIL_CLOSED__DOMINANCE_WORLD_SET_MISMATCH"
    assert out["trusted_execution_authorized"] is False


def test_router_requires_current_semantic_fingerprint_when_certificate_present():
    out = route(**router_args(with_semantics=False), dominance_certificate=dominance_doc())
    assert out["route"] == "FAIL_CLOSED__CURRENT_HYPOTHESIS_SEMANTICS_UNBOUND"


def test_valid_shortcut_stops_probe_but_remains_certificate_only():
    out = route(**router_args(), dominance_certificate=dominance_doc())
    assert out["route"] == "DOMINANCE_SUFFICIENT_CERTIFICATE"
    assert out["recommended_action"] == "ROBUST"
    assert out["next_action"] is None
    assert out["trusted_execution_authorized"] is False
    assert out["certificate_only"] is True


def test_open_certificate_falls_back_to_existing_v3():
    out = route(**router_args(), dominance_certificate=dominance_doc(brain_h2="0.7"))
    assert out["route"] == "LEARN"
    assert out["next_action"]["id"] == "probe"


def test_no_certificate_preserves_existing_v3_without_semantic_requirement():
    out = route(**router_args(with_semantics=False), dominance_certificate=None)
    assert out["route"] == "LEARN"
    assert out["next_action"]["id"] == "probe"
