from __future__ import annotations

from canonical.runtime import dominance_binding_v2 as bind
from canonical.runtime import dominance_semantic_binding_v4 as sem
from canonical.runtime.dominance_first_learning_router_v4 import route
from canonical.runtime.dominance_sufficiency_v4 import (
    INPUT_SCHEMA,
    compile_dominance_sufficiency_v4,
)

SHA_TARGET = "a" * 40
SHA_H1 = "b" * 40
SHA_H2 = "c" * 40
SHA_CONFIG = "d" * 40
TARGET = "1" * 64
METRIC = "terminal_success"
H1 = "2" * 64
H2 = "3" * 64
CONFIG = "4" * 64


def cb(path, sha=SHA_TARGET):
    return {"path": path, "git_blob_sha": sha}


def world_receipt(hid, semantic, path, sha):
    return {
        **cb(path, sha),
        "hypothesis_id": hid,
        "semantic_sha256": semantic,
        "independent_or_objective": True,
    }


def world_rows():
    return [
        {
            "id": "h1",
            "semantic_sha256": H1,
            "definition_blob_sha": SHA_H1,
        },
        {
            "id": "h2",
            "semantic_sha256": H2,
            "definition_blob_sha": SHA_H2,
        },
    ]


def dominance_doc(brain_h2="0.9"):
    rows = world_rows()
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
            "live_world_set_sha256": sem.live_world_digest(rows),
            "live_hypothesis_set_sha256": bind.live_digest(["h1", "h2"]),
            "scope_complete": True,
            "independent_or_objective": True,
        },
        "hypotheses": [
            {
                "id": "h1",
                "plausible": True,
                "semantic_sha256": H1,
                "definition_receipt": world_receipt(
                    "h1", H1, "canonical/h1-world.json", SHA_H1
                ),
            },
            {
                "id": "h2",
                "plausible": True,
                "semantic_sha256": H2,
                "definition_receipt": world_receipt(
                    "h2", H2, "canonical/h2-world.json", SHA_H2
                ),
            },
        ],
        "configurations": [
            {
                "id": "ROBUST",
                "brain_owned": True,
                "configuration_sha256": CONFIG,
                "configuration_definition_receipt": {
                    **cb("canonical/robust-config.json", SHA_CONFIG),
                    "configuration_id": "ROBUST",
                    "configuration_sha256": CONFIG,
                    "independent_or_objective": True,
                },
                "ownership_receipt": {
                    **cb("canonical/own.json"),
                    "configuration_id": "ROBUST",
                    "configuration_sha256": CONFIG,
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
                            "configuration_sha256": CONFIG,
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
                            "configuration_sha256": CONFIG,
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


def router_args(with_world_receipts=True):
    h1 = {
        "id": "h1",
        "plausible": True,
        "best_action": "A",
        "probability": "1/2",
        "semantic_sha256": H1,
    }
    h2 = {
        "id": "h2",
        "plausible": True,
        "best_action": "B",
        "probability": "1/2",
        "semantic_sha256": H2,
    }
    if with_world_receipts:
        h1["definition_receipt"] = world_receipt(
            "h1", H1, "canonical/h1-world.json", SHA_H1
        )
        h2["definition_receipt"] = world_receipt(
            "h2", H2, "canonical/h2-world.json", SHA_H2
        )
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


def test_v4_content_bound_witness_passes_without_execution_authority():
    out = compile_dominance_sufficiency_v4(dominance_doc())
    assert out["status"] == "PASS__CONTENT_BOUND_DOMINANCE_SUFFICIENT"
    assert out["selected_configuration"] == "ROBUST"
    assert out["selected_configuration_sha256"] == CONFIG
    assert out["execution_authority"] is False


def test_same_semantic_label_different_world_definition_fails_router_match():
    args = router_args()
    args["hypotheses"][0]["definition_receipt"]["git_blob_sha"] = "e" * 40
    out = route(**args, dominance_certificate=dominance_doc())
    assert out["route"] == "FAIL_CLOSED__DOMINANCE_WORLD_SET_MISMATCH"


def test_current_world_definition_receipt_semantic_mismatch_fails_closed():
    args = router_args()
    args["hypotheses"][0]["definition_receipt"]["semantic_sha256"] = H2
    out = route(**args, dominance_certificate=dominance_doc())
    assert out["route"] == "FAIL_CLOSED__CURRENT_WORLD_DEFINITIONS_UNBOUND"


def test_certificate_world_definition_substitution_fails_closed():
    x = dominance_doc()
    x["hypotheses"][0]["definition_receipt"]["git_blob_sha"] = "e" * 40
    out = compile_dominance_sufficiency_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "LIVE_WORLD_SET_SHA256_MISMATCH" in out["errors"][0]


def test_configuration_semantic_substitution_fails_ownership_binding():
    x = dominance_doc()
    x["configurations"][0]["configuration_sha256"] = "5" * 64
    out = compile_dominance_sufficiency_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "CONFIGURATION_SHA256_MISMATCH" in out["errors"][0]


def test_bound_receipt_must_bind_exact_configuration_semantics():
    x = dominance_doc()
    x["configurations"][0]["bounds"]["h1"]["bound_receipt"][
        "configuration_sha256"
    ] = "5" * 64
    out = compile_dominance_sufficiency_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "CONFIGURATION_SHA256_MISMATCH" in out["errors"][0]


def test_bound_receipt_must_bind_exact_world_semantics():
    x = dominance_doc()
    x["configurations"][0]["bounds"]["h1"]["bound_receipt"][
        "hypothesis_semantic_sha256"
    ] = H2
    out = compile_dominance_sufficiency_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "HYPOTHESIS_SEMANTIC_SHA256_MISMATCH" in out["errors"][0]


def test_legacy_live_hypothesis_digest_is_not_rewritten_in_memory():
    x = dominance_doc()
    x["hypothesis_coverage_receipt"]["live_hypothesis_set_sha256"] = "f" * 64
    out = compile_dominance_sufficiency_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "LIVE_HYPOTHESIS_SET_SHA256_MISMATCH" in " ".join(out["errors"])


def test_router_shortcut_requires_content_bound_current_worlds():
    out = route(
        **router_args(with_world_receipts=False),
        dominance_certificate=dominance_doc(),
    )
    assert out["route"] == "FAIL_CLOSED__CURRENT_WORLD_DEFINITIONS_UNBOUND"


def test_valid_shortcut_stops_probe_but_cannot_execute():
    out = route(**router_args(), dominance_certificate=dominance_doc())
    assert out["route"] == "DOMINANCE_SUFFICIENT_CERTIFICATE_V4"
    assert out["recommended_action"] == "ROBUST"
    assert out["recommended_action_sha256"] == CONFIG
    assert out["next_action"] is None
    assert out["trusted_execution_authorized"] is False
    assert out["certificate_only"] is True


def test_open_certificate_falls_back_to_existing_v3():
    out = route(
        **router_args(),
        dominance_certificate=dominance_doc(brain_h2="0.7"),
    )
    assert out["route"] == "LEARN"
    assert out["next_action"]["id"] == "probe"


def test_no_certificate_preserves_existing_v3_without_definition_receipts():
    out = route(
        **router_args(with_world_receipts=False),
        dominance_certificate=None,
    )
    assert out["route"] == "LEARN"
    assert out["next_action"]["id"] == "probe"
